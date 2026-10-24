"""Pydantic types shared by main.py, the agent, and its tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Size = Literal["XS", "S", "M", "L", "XL", "XXL"]


# --- catalogue -----------------------------------------------------------------

class SizeStock(BaseModel):
    size: str
    quantity: int = Field(description="Units in stock right now. 0 means sold out in this size.")


class ProductCard(BaseModel):
    """One product as the website and the agent see it. Built from catalogue + inventory rows."""

    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    price: float = Field(description="US dollars, from the catalogue table.")
    image_url: str = Field(description="Browser path to the photo, /media/products/<file>.jpg")
    inventory: list[SizeStock] = []
    total_stock: int = 0


class ProductSearchResult(BaseModel):
    """What search_products hands back to the agent."""

    total_matches: int
    returned: int
    products: list[ProductCard]
    note: str = ""


class SimilarProducts(BaseModel):
    """What find_similar hands back to the agent (Problem 8)."""

    based_on: str = Field(description="Name of the product the alternatives are similar to.")
    size: str | None = Field(None, description="Every alternative has stock in this size, if one was given.")
    color: str | None = Field(None, description="Every alternative comes in this color, if one was given.")
    products: list[ProductCard]
    note: str = ""


class StockCheck(BaseModel):
    """What check_stock hands back to the agent."""

    product_id: str
    name: str
    size: str | None
    in_stock: bool
    quantity: int | None = Field(None, description="Units for the requested size, if one was asked.")
    sizes_available: list[str]
    sizes_sold_out: list[str]


# --- agent ---------------------------------------------------------------------

class Shopper(BaseModel):
    """Who is chatting. Built server-side from the session cookie, never from the browser's word."""

    user_id: int
    first_name: str | None
    last_name: str | None
    name: str
    email: str


class PageContext(BaseModel):
    """Where the shopper is on the site when they send a message."""

    path: str = Field("/", max_length=200, description="Browser path, e.g. /products/basic-hoodie-big-yale")
    product_id: str | None = Field(None, max_length=120, description="Set when the shopper is on a single-item page.")


@dataclass
class ShopDeps:
    """Per-request context the agent's instructions and tools can read. Never includes password hashes."""

    shopper: Shopper | None = None  # None = not logged in
    page: PageContext | None = None
    current_product: ProductCard | None = None  # the item on screen, loaded from the DB
    seen_product_ids: set[str] = field(default_factory=set)  # ids the tools actually returned
    seen_prices: set[float] = field(default_factory=set)  # prices the tools returned (Problem 8 price check)
    allowed_amounts: set[float] = field(default_factory=set)  # $ amounts the shopper typed or saw earlier
    price_retries: int = 0  # how often the price check sent a reply back


class ShopReply(BaseModel):
    """The agent's structured answer."""

    reply: str = Field(description="Friendly answer to the shopper, in Markdown. Short.")
    product_ids: list[str] = Field(
        default_factory=list,
        description="product_id values (from tool results only) to show as cards on the page, best first. Max 12.",
    )
    results_title: str = Field(
        "",
        description="Short heading for the cards shown on the page, e.g. 'Hoodies' or 'Bulldog tees in XL'. "
        "Empty when product_ids is empty.",
    )


# --- API -----------------------------------------------------------------------

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Used only for guests. Logged-in shoppers' history is read from chat_messages instead.
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    page: PageContext | None = None


class SavedMessage(BaseModel):
    """One row of chat_messages as the widget reloads it."""

    role: Literal["user", "assistant"]
    text: str
    products: list[ProductCard] = []
    created_at: str


class ChatResponse(BaseModel):
    """API contract for POST /api/chat. The front end renders `products` as cards on the page."""

    reply: str
    products: list[ProductCard] = Field(default_factory=list, description="Matches to show, best first.")
    results_title: str = Field("", description="Heading for the on-page card section.")
    tools_used: list[str] = []


# --- audit trail ---------------------------------------------------------------

class ToolStep(BaseModel):
    tool: str
    args: dict
    result: str = Field(description="Short preview of what the tool returned.")


class AuditEntry(BaseModel):
    """One agent run, appended to output/audit_trail.json."""

    time: datetime
    user_id: int | None
    user_message: str
    thoughts: list[str]
    tool_calls: list[ToolStep]
    reply: str
    product_ids: list[str]
    model: str
    stop_reason: str
    price_retries: int = Field(0, description="Replies the price check sent back (Problem 8).")
    duration_seconds: float
