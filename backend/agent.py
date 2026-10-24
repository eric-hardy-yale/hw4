"""The Campus Customs shopping agent. main.py calls run_agent(...) -> ChatResponse.

Wiring: system prompt from prompts/prompt.md, model from tools.get_model() (Portkey),
tools from tools.py, structured output ShopReply from models.py.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
# Load the key before tools.py builds the model.
load_dotenv(ROOT / ".env")

from pydantic_ai import Agent, ModelRetry, RunContext, capture_run_messages  # noqa: E402
from pydantic_ai.messages import (  # noqa: E402
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIResponsesModelSettings  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402

from models import AuditEntry, ChatResponse, ChatTurn, PageContext, ShopDeps, Shopper, ShopReply, ToolStep  # noqa: E402
from tools import (  # noqa: E402
    DEFAULT_MODEL,
    check_stock,
    find_similar,
    get_current_page,
    get_model,
    get_product,
    get_shopper,
    load_cards,
    search_products,
)

PROMPT_PATH = HERE / "prompts" / "prompt.md"
AUDIT_PATH = ROOT / "output" / "audit_trail.json"
MODEL_NAME = os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
MAX_CARDS = 12
# Loop limits: at most 8 model calls and 10 tool calls per shopper message, so a confused
# model can't spin forever or run up cost. Hitting a limit ends the run with a friendly apology.
LOOP_LIMITS = UsageLimits(request_limit=8, tool_calls_limit=10)
_audit_lock = threading.Lock()

agent = Agent(
    get_model(MODEL_NAME),
    deps_type=ShopDeps,
    output_type=ShopReply,
    instructions=PROMPT_PATH.read_text(encoding="utf-8"),
    tools=[search_products, get_product, check_stock, find_similar, get_current_page, get_shopper],
    retries=2,  # tool and price-check retries (the price check may send a reply back twice)
    # Ask for a short reasoning summary so the audit trail has "thoughts" to show.
    model_settings=OpenAIResponsesModelSettings(openai_reasoning_summary="concise"),
)


@agent.instructions
def shopper_context(ctx: RunContext[ShopDeps]) -> str:
    """Who is chatting, added to the instructions on every run."""
    s = ctx.deps.shopper
    if s is None:
        return "## Shopper\nNot logged in, so you don't know their name. Chat history is not saved for guests."
    return (
        f"## Shopper\nLogged in as {s.name} (first name {s.first_name or s.name.split()[0]}, email {s.email}). "
        "Their earlier chats with you are included above. Only share their email if they ask what it is."
    )


@agent.instructions
def page_context(ctx: RunContext[ShopDeps]) -> str:
    """What the shopper is looking at, so "do you have this in pink?" resolves to the right item."""
    page, item = ctx.deps.page, ctx.deps.current_product
    if item is not None:
        sizes = ", ".join(f"{x.size}: {x.quantity}" for x in item.inventory)
        return (
            f"## Current page\nThe shopper is on the single-item page for **{item.name}** "
            f"(product_id `{item.product_id}`, {item.garment_type}, colors: {', '.join(item.colors)}, "
            f"price ${item.price:.2f}, stock by size: {sizes}). "
            "When they say \"this\", \"it\" or \"this one\", they mean this item. "
            "For a color or style it doesn't come in, say so and use search_products to suggest similar items."
        )
    if page is not None:
        return f"## Current page\nThe shopper is on `{page.path}` (not a single product page)."
    return ""


MONEY_RE = re.compile(r"\$\s?(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)")


def dollar_amounts(text: str) -> set[float]:
    return {round(float(m.replace(",", "")), 2) for m in MONEY_RE.findall(text)}


@agent.output_validator
def check_prices(ctx: RunContext[ShopDeps], output: ShopReply) -> ShopReply:
    """Problem 8 guardrail: every $ amount in the reply must come from a tool result this turn,
    or from something the shopper typed / was already told. Otherwise send it back to the model."""
    allowed = ctx.deps.seen_prices | ctx.deps.allowed_amounts
    bad = sorted(a for a in dollar_amounts(output.reply) if a not in allowed)
    if bad:
        ctx.deps.price_retries += 1
        shown = ", ".join(f"${a:.2f}" for a in bad)
        raise ModelRetry(
            f"Your reply mentions {shown}, but no tool returned that price this turn. Prices must be copied "
            "exactly from tool results. Call search_products/get_product for the item and use its `price`, "
            "or remove the amount."
        )
    return output


def to_history(turns: list[ChatTurn]) -> list[ModelMessage]:
    """Earlier chat turns from the browser, so follow-ups like 'do you have it in M?' make sense."""
    out: list[ModelMessage] = []
    for t in turns[-12:]:
        if t.role == "user":
            out.append(ModelRequest(parts=[UserPromptPart(content=t.text)]))
        else:
            out.append(ModelResponse(parts=[TextPart(content=t.text)]))
    return out


def run_agent(
    message: str,
    history: list[ChatTurn] | None = None,
    shopper: Shopper | None = None,
    page: PageContext | None = None,
) -> ChatResponse:
    started = time.perf_counter()
    user_id = shopper.user_id if shopper else None
    # Look the on-screen product up in the DB (an unknown id from the browser is simply ignored).
    found = load_cards([page.product_id]) if page and page.product_id else []
    current = found[0] if found else None
    deps = ShopDeps(shopper=shopper, page=page, current_product=current)
    # Amounts the shopper typed ("under $40") or already saw in this chat may be repeated.
    deps.allowed_amounts = dollar_amounts(message) | {a for t in (history or []) for a in dollar_amounts(t.text)}
    if current:
        deps.seen_product_ids.add(current.product_id)
    with capture_run_messages() as run_messages:
        try:
            result = agent.run_sync(
                message, deps=deps, message_history=to_history(history or []), usage_limits=LOOP_LIMITS
            )
            error = None
        except Exception as exc:  # keep the chat alive and still log the failed run
            error = exc
    if error is not None:
        exc = error
        reply = "Sorry, I hit a snag reaching our shop assistant. Please try again in a moment."
        append_audit(AuditEntry(
            time=datetime.now(timezone.utc), user_id=user_id, user_message=message,
            thoughts=thoughts(run_messages), tool_calls=tool_steps(run_messages), reply=reply, product_ids=[], model=MODEL_NAME,
            stop_reason=f"error: {type(exc).__name__}: {exc}", price_retries=deps.price_retries,
            duration_seconds=round(time.perf_counter() - started, 2),
        ))
        return ChatResponse(reply=reply)

    output: ShopReply = result.output
    # Only show cards for ids a tool actually returned this turn, so the model can't invent products.
    ids = [i for i in output.product_ids if i in deps.seen_product_ids][:MAX_CARDS]
    cards = load_cards(ids)

    messages = result.new_messages()
    steps = tool_steps(messages)
    append_audit(AuditEntry(
        time=datetime.now(timezone.utc),
        user_id=user_id,
        user_message=message,
        thoughts=thoughts(messages),
        tool_calls=steps,
        reply=output.reply,
        product_ids=[c.product_id for c in cards],
        model=MODEL_NAME,
        stop_reason=stop_reason(messages),
        price_retries=deps.price_retries,
        duration_seconds=round(time.perf_counter() - started, 2),
    ))
    return ChatResponse(
        reply=output.reply,
        products=cards,
        results_title=(output.results_title.strip()[:60] or "From your chat") if cards else "",
        tools_used=list(dict.fromkeys(s.tool for s in steps if s.tool != "final_result")),
    )


# --- audit trail -----------------------------------------------------------------

def tool_steps(messages: list[ModelMessage]) -> list[ToolStep]:
    returns = {
        part.tool_call_id: part.model_response_str()
        for msg in messages
        for part in msg.parts
        if isinstance(part, ToolReturnPart)
    }
    return [
        ToolStep(tool=part.tool_name, args=part.args_as_dict(), result=preview(returns.get(part.tool_call_id, "")))
        for msg in messages
        if isinstance(msg, ModelResponse)
        for part in msg.parts
        if isinstance(part, ToolCallPart)
    ]


def thoughts(messages: list[ModelMessage]) -> list[str]:
    """Reasoning summaries, plus any text the model wrote before calling a tool."""
    out = []
    for msg in messages:
        if not isinstance(msg, ModelResponse):
            continue
        calls_tool = any(isinstance(p, ToolCallPart) for p in msg.parts)
        for part in msg.parts:
            if isinstance(part, ThinkingPart) and part.content.strip():
                out.append(part.content.strip())
            elif isinstance(part, TextPart) and calls_tool and part.content.strip():
                out.append(part.content.strip())
    return out


def stop_reason(messages: list[ModelMessage]) -> str:
    last = next((m for m in reversed(messages) if isinstance(m, ModelResponse)), None)
    if last is None:
        return "no model response"
    return f"{last.finish_reason or 'unknown'}: model returned its final structured reply"


def preview(text: str, limit: int = 300) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + " …"


def append_audit(entry: AuditEntry) -> None:
    """Add one run to output/audit_trail.json without wiping earlier rows."""
    with _audit_lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            rows = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
            if not isinstance(rows, list):
                rows = [rows]
        except FileNotFoundError:
            rows = []
        except json.JSONDecodeError:  # keep the unreadable file instead of overwriting it
            AUDIT_PATH.rename(AUDIT_PATH.with_suffix(f".broken-{int(time.time())}.json"))
            rows = []
        rows.append(entry.model_dump(mode="json"))
        AUDIT_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
