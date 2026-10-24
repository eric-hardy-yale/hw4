"""Model setup, database helpers, and the tools the shopping agent can call.

Every price and stock number the agent sees comes from here, read live from SQLite.
The tools only ever read catalogue and inventory, never users.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic_ai import RunContext
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from models import ProductCard, ProductSearchResult, ShopDeps, Shopper, SimilarProducts, SizeStock, StockCheck

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.getenv("CC_DB_PATH") or DATA_DIR / "campus_customs.db")

PORTKEY_BASE = "https://api.portkey.ai/v1"
DEFAULT_MODEL = "gpt-5.6-luna"
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
MAX_RESULTS = 12

# Words that should not narrow a search on their own.
STOP_WORDS = {
    "a", "an", "and", "any", "do", "for", "have", "i", "in", "is", "it", "me", "of", "on", "or",
    "show", "some", "something", "the", "to", "u", "with", "you", "your", "yale", "got", "want",
    "looking", "need", "item", "items", "merch", "gear", "stuff",
}
# Shopper words -> words that actually appear in the catalogue.
SYNONYMS = {
    "handsome dan": "bulldog",
    "dan": "bulldog",
    "dog": "bulldog",
    "tee": "t-shirt",
    "tees": "t-shirt",
    "tshirt": "t-shirt",
    "hoody": "hoodie",
    "hoodies": "hoodie",
    "crewnecks": "crewneck",
    "quarter zip": "quarter-zip",
    "1/4 zip": "quarter-zip",
    "quarterzip": "quarter-zip",
    "grey": "gray",
    "jackets": "jacket",
}


def get_model(name: str | None = None) -> OpenAIResponsesModel:
    """Yale Portkey gateway if PORTKEY_API_KEY is set, else plain OpenAI."""
    portkey = (os.getenv("PORTKEY_API_KEY") or "").strip()
    openai = (os.getenv("OPENAI_API_KEY") or "").strip()
    if portkey:
        provider = OpenAIProvider(base_url=PORTKEY_BASE, api_key=portkey)
    elif openai:
        provider = OpenAIProvider(api_key=openai)
    else:
        raise RuntimeError("Add PORTKEY_API_KEY (or OPENAI_API_KEY) to hw4/.env")
    return OpenAIResponsesModel(name or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL, provider=provider)


# --- database ------------------------------------------------------------------

@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Place the data pack in hw4/data/.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def size_key(size: str) -> int:
    return SIZE_ORDER.index(size) if size in SIZE_ORDER else 99


def inventory_map(conn: sqlite3.Connection, ids: list[str]) -> dict[str, list[SizeStock]]:
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    rows = conn.execute(f"SELECT product_id, size, quantity FROM inventory WHERE product_id IN ({marks})", ids)
    out: dict[str, list[SizeStock]] = {i: [] for i in ids}
    for r in rows:
        out[r["product_id"]].append(SizeStock(size=r["size"], quantity=r["quantity"]))
    for sizes in out.values():
        sizes.sort(key=lambda s: size_key(s.size))
    return out


def card_from_row(row: sqlite3.Row, sizes: list[SizeStock]) -> ProductCard:
    return ProductCard(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        price=row["price"],
        image_url=f"/media/{row['image_file_path']}",
        inventory=sizes,
        total_stock=sum(s.quantity for s in sizes),
    )


def load_cards(ids: list[str]) -> list[ProductCard]:
    """Cards for these ids, in the same order, skipping any id that isn't in the catalogue."""
    ids = list(dict.fromkeys(ids))
    if not ids:
        return []
    with connect() as conn:
        marks = ",".join("?" * len(ids))
        rows = {r["product_id"]: r for r in conn.execute(f"SELECT * FROM catalogue WHERE product_id IN ({marks})", ids)}
        inv = inventory_map(conn, list(rows))
    return [card_from_row(rows[i], inv[i]) for i in ids if i in rows]


def search_terms(query: str) -> list[str]:
    q = query.lower()
    for phrase, repl in SYNONYMS.items():
        if " " in phrase:
            q = q.replace(phrase, repl)
    words = re.findall(r"[a-z0-9][a-z0-9\-']*", q)
    terms = [SYNONYMS.get(w, w) for w in words if w not in STOP_WORDS]
    # Plural -> singular for simple cases ("crewnecks", "jackets").
    return list(dict.fromkeys(t[:-1] if t.endswith("s") and len(t) > 4 and not t.endswith("ss") else t for t in terms))


# --- tools ---------------------------------------------------------------------

def remember(ctx: RunContext[ShopDeps], cards: list[ProductCard]) -> None:
    """Record what the tools showed the model: ids may become cards, prices may appear in the reply."""
    for c in cards:
        ctx.deps.seen_product_ids.add(c.product_id)
        ctx.deps.seen_prices.add(round(c.price, 2))


def search_products(
    ctx: RunContext[ShopDeps],
    query: str = "",
    garment_type: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size_in_stock: str | None = None,
    limit: int = 8,
) -> ProductSearchResult:
    """Search the Campus Customs catalogue. Returns products with live price and stock by size.

    Args:
        query: Free-text keywords, e.g. "bulldog", "Berkeley college", "hockey", "The Game".
            Every keyword must match the name, type, description, colors, or tags. Leave empty to browse.
        garment_type: Optional type filter matched loosely, e.g. "hoodie", "crewneck", "t-shirt", "quarter-zip", "jacket", "fleece".
        color: Optional color filter, e.g. "navy", "gray", "white".
        max_price: Optional highest price in US dollars.
        size_in_stock: Optional size (XS, S, M, L, XL, XXL) that must have at least 1 unit.
        limit: How many products to return (1-12).
    """
    terms = search_terms(query)
    with connect() as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY price, name").fetchall()
        hits = []
        for r in rows:
            haystack = " ".join(
                [r["name"], r["garment_type"], r["description"], r["colors"], r["search_tags"]]
            ).lower()
            if any(t not in haystack for t in terms):
                continue
            if garment_type and not _type_matches(garment_type, r):
                continue
            if color and color.lower() not in r["colors"].lower() and color.lower() not in r["description"].lower():
                continue
            if max_price is not None and r["price"] > max_price:
                continue
            hits.append(r)
        inv = inventory_map(conn, [r["product_id"] for r in hits])

    if size_in_stock:
        size = size_in_stock.upper()
        hits = [r for r in hits if any(s.size == size and s.quantity > 0 for s in inv[r["product_id"]])]

    limit = max(1, min(limit, MAX_RESULTS))
    cards = [card_from_row(r, inv[r["product_id"]]) for r in hits[:limit]]
    remember(ctx, cards)
    note = ""
    if not hits:
        note = "No matches. Try fewer or simpler keywords before telling the shopper we don't carry it."
    elif len(hits) > limit:
        note = f"Showing {limit} of {len(hits)} matches. Narrow the search or raise the limit to see more."
    return ProductSearchResult(total_matches=len(hits), returned=len(cards), products=cards, note=note)


def _type_matches(wanted: str, row: sqlite3.Row) -> bool:
    w = SYNONYMS.get(wanted.lower().strip(), wanted.lower().strip())
    w = w[:-1] if w.endswith("s") and len(w) > 4 else w
    if w == "hoodie":  # also "hooded sweatshirt", "full-zip hood"
        w = "hood"
    return w in row["garment_type"].lower() or w in row["name"].lower()


def get_product(ctx: RunContext[ShopDeps], product_id: str) -> ProductCard | str:
    """Full details for one product: description, colors, price, and stock for every size.

    Args:
        product_id: The exact product_id from a search result, e.g. "basic-hoodie-big-yale".
    """
    cards = load_cards([product_id])
    if not cards:
        return f"No product with id {product_id!r}. Use search_products to find the right id."
    remember(ctx, cards)
    return cards[0]


def check_stock(ctx: RunContext[ShopDeps], product_id: str, size: str | None = None) -> StockCheck | str:
    """Live stock for a product, optionally for one size. Call this before saying a size is available.

    Args:
        product_id: The exact product_id from a search result.
        size: Optional size to check: XS, S, M, L, XL, or XXL.
    """
    cards = load_cards([product_id])
    if not cards:
        return f"No product with id {product_id!r}. Use search_products to find the right id."
    card = cards[0]
    remember(ctx, cards)
    available = [s.size for s in card.inventory if s.quantity > 0]
    sold_out = [s.size for s in card.inventory if s.quantity == 0]
    qty = None
    if size:
        size = size.upper().strip()
        match = next((s for s in card.inventory if s.size == size), None)
        if match is None:
            return f"{size!r} is not a size we stock. Sizes are {', '.join(SIZE_ORDER)}."
        qty = match.quantity
    return StockCheck(
        product_id=card.product_id,
        name=card.name,
        size=size,
        in_stock=(qty > 0) if qty is not None else bool(available),
        quantity=qty,
        sizes_available=available,
        sizes_sold_out=sold_out,
    )


def get_shopper(ctx: RunContext[ShopDeps]) -> Shopper | str:
    """Who is chatting: user id, first and last name, and email of the logged-in shopper.

    Use it when the shopper asks "who am I logged in as?" or "what's my email on file?".
    """
    if ctx.deps.shopper is None:
        return "The shopper is not logged in. They can log in or create an account from the top of the page."
    return ctx.deps.shopper


def get_current_page(ctx: RunContext[ShopDeps]) -> ProductCard | str:
    """The product the shopper is looking at right now (on its single-item page), with live price and stock.

    Use it when the shopper says "this", "it", or "this one" without naming an item.
    """
    page = ctx.deps.page
    if ctx.deps.current_product is None:
        where = page.path if page else "an unknown page"
        return f"The shopper is on {where}, not on a single product page. Ask which item they mean or search for it."
    remember(ctx, [ctx.deps.current_product])
    return ctx.deps.current_product


# --- find_similar (Problem 8) ------------------------------------------------------

FAMILIES = [  # garment family by keyword, checked in order
    ("quarter-zip", "quarter-zip"), ("fleece", "jacket"), ("jacket", "jacket"), ("hood", "hoodie"),
    ("crew", "crewneck"), ("mockneck", "crewneck"), ("t-shirt", "tee"), ("performance", "tee"),
]
GENERIC = {"yale", "campus", "customs", "college", "apparel", "merch", "long", "sleeve", "short", "front", "chest",
           "with", "and", "the", "featuring", "white", "navy", "blue", "gray", "heather", "ribbed", "cuffs", "hem",
           "collar", "logo", "lettering", "graphic", "wordmark", "sweatshirt", "pullover"}


def family(row: sqlite3.Row) -> str:
    t = row["garment_type"].lower()
    return next((fam for key, fam in FAMILIES if key in t), t)


def design_words(row: sqlite3.Row) -> set[str]:
    text = " ".join([row["name"], row["description"], " ".join(json.loads(row["search_tags"]))]).lower()
    return {w for w in re.findall(r"[a-z]{4,}", text) if w not in GENERIC}


def similar_cards(
    product_id: str, size: str | None = None, color: str | None = None, limit: int = 6
) -> tuple[str, list[ProductCard]] | None:
    """(base product name, in-stock alternatives ranked by similarity), or None for an unknown id.

    Shared by the find_similar tool and the "You might also like" row on the product page.
    """
    with connect() as conn:
        rows = conn.execute("SELECT * FROM catalogue").fetchall()
        base = next((r for r in rows if r["product_id"] == product_id), None)
        if base is None:
            return None
        inv = inventory_map(conn, [r["product_id"] for r in rows])

    base_family, base_words = family(base), design_words(base)
    base_colors = {c.lower() for c in json.loads(base["colors"])}
    scored = []
    for r in rows:
        if r["product_id"] == product_id:
            continue
        sizes = inv[r["product_id"]]
        if size and not any(s.size == size and s.quantity > 0 for s in sizes):
            continue
        if not any(s.quantity > 0 for s in sizes):
            continue
        colors = {c.lower() for c in json.loads(r["colors"])}
        if color and not any(color.lower() in c for c in colors) and color.lower() not in r["description"].lower():
            continue
        score = 0.0
        score += 5 if family(r) == base_family else 0
        score += 1.5 * len(base_words & design_words(r))
        score += 1 * len(base_colors & colors)
        score += 2 * max(0.0, 1 - abs(r["price"] - base["price"]) / 40)
        scored.append((score, r))
    scored.sort(key=lambda x: (-x[0], x[1]["price"], x[1]["name"]))
    limit = max(1, min(limit, 8))
    return base["name"], [card_from_row(r, inv[r["product_id"]]) for _, r in scored[:limit]]


def find_similar(
    ctx: RunContext[ShopDeps],
    product_id: str,
    size: str | None = None,
    color: str | None = None,
    limit: int = 6,
) -> SimilarProducts | str:
    """In-stock alternatives to a product: same kind of garment and a similar design, color, and price.

    Call this when a size is sold out, an item doesn't come in the color the shopper wants,
    or the shopper asks for "something similar" / "more like this".

    Args:
        product_id: The product to find alternatives for (from a search result or the current page).
        size: Only return items with at least 1 unit in this size (XS, S, M, L, XL, XXL).
        color: Only return items that come in this color, e.g. "gray" or "pink".
        limit: How many alternatives to return (1-8).
    """
    size = size.upper().strip() if size else None
    if size and size not in SIZE_ORDER:
        return f"{size!r} is not a size we stock. Sizes are {', '.join(SIZE_ORDER)}."
    found = similar_cards(product_id, size, color, limit)
    if found is None:
        return f"No product with id {product_id!r}. Use search_products to find the right id."
    base_name, cards = found
    remember(ctx, cards)
    note = "" if cards else "Nothing similar matches those filters. Offer a different size or color, or search more broadly."
    return SimilarProducts(based_on=base_name, size=size, color=color, products=cards, note=note)
