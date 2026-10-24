"""Campus Customs shop API.

Run from backend/:  uvicorn main:app --reload --port 8000
Open API docs:      http://127.0.0.1:8000/docs
Frontend (Vite):    http://127.0.0.1:5173  (proxies /api and /media here)

Problem 4: serves the product catalogue, stock by size, and product images,
plus create-account / log-in / log-out backed by the users table.
Problem 5: /api/chat runs the PydanticAI shopping agent (agent.py, tools.py, models.py,\nprompts/prompt.md) and saves logged-in shoppers' chats to chat_messages.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Cookie, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from models import ChatRequest, ChatResponse, ChatTurn, ProductCard, SavedMessage, Shopper

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.getenv("CC_DB_PATH") or DATA_DIR / "campus_customs.db")
load_dotenv(ROOT / ".env")

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

app = FastAPI(title="Campus Customs", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Product images live in data/products/ and are referenced as products/<id>.jpg in the catalogue.
if DATA_DIR.is_dir():
    app.mount("/media/products", StaticFiles(directory=DATA_DIR / "products"), name="media")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    if not DB_PATH.exists():
        raise HTTPException(503, f"Database not found at {DB_PATH}. Place the data pack in hw4/data/.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def product_from_row(row: sqlite3.Row) -> dict:
    image = row["image_file_path"]
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": row["description"],
        "colors": json.loads(row["colors"]),
        "search_tags": json.loads(row["search_tags"]),
        "image_file_path": image,
        "image_url": f"/media/{image}",  # -> /media/products/<id>.jpg
        "price": row["price"],
    }


def inventory_for(conn: sqlite3.Connection, product_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
    ).fetchall()
    sizes = [{"size": r["size"], "quantity": r["quantity"]} for r in rows]
    return sorted(sizes, key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else 99)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "database": DB_PATH.exists()}


@app.get("/api/products")
def list_products(q: str | None = Query(None, description="Search name, type, description, tags")) -> list[dict]:
    sql = "SELECT * FROM catalogue"
    params: list[str] = []
    if q:
        like = f"%{q.lower()}%"
        sql += (
            " WHERE lower(name) LIKE ? OR lower(garment_type) LIKE ?"
            " OR lower(description) LIKE ? OR lower(search_tags) LIKE ? OR lower(colors) LIKE ?"
        )
        params = [like] * 5
    sql += " ORDER BY name"
    with connect() as conn:
        products = [product_from_row(r) for r in conn.execute(sql, params).fetchall()]
        # Stock for every card in one query (Problem 8: stock badges on the Products page).
        stock: dict[str, list[dict]] = {}
        for r in conn.execute("SELECT product_id, size, quantity FROM inventory"):
            stock.setdefault(r["product_id"], []).append({"size": r["size"], "quantity": r["quantity"]})
    for p in products:
        sizes = sorted(stock.get(p["product_id"], []), key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else 99)
        p["inventory"] = sizes
        p["total_stock"] = sum(s["quantity"] for s in sizes)
    return products


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Product not found")
        product = product_from_row(row)
        product["inventory"] = inventory_for(conn, product_id)
    product["total_stock"] = sum(s["quantity"] for s in product["inventory"])
    return product


# ---------------------------------------------------------------- accounts
# Passwords are stored only as PBKDF2-HMAC-SHA256 hashes in the same format as the seed data:
#   pbkdf2_sha256$<salt>$<hex digest>, 120,000 iterations, random 16-byte salt per user.
# Login re-hashes the typed password with the stored salt and compares in constant time.
HASH_ALGO = "pbkdf2_sha256"
HASH_ITERATIONS = 120_000
SESSION_COOKIE = "cc_session"
SESSION_TTL = 7 * 24 * 3600  # one week
# Sign session cookies with SESSION_SECRET from .env; without it, a random key (sessions reset on restart).
SESSION_SECRET = (os.getenv("SESSION_SECRET") or secrets.token_hex(32)).encode()
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Same-size dummy hash so a login for an unknown email costs the same time as a real one.
_DUMMY_HASH = f"{HASH_ALGO}${'0' * 32}${'0' * 64}"
_failed_logins: dict[str, list[float]] = {}
MAX_FAILED, FAIL_WINDOW = 5, 15 * 60


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), HASH_ITERATIONS).hex()
    return f"{HASH_ALGO}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, _ = stored.split("$")
    except ValueError:
        return False
    if algo != HASH_ALGO:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


def make_session(user_id: int) -> str:
    payload = f"{user_id}.{int(time.time()) + SESSION_TTL}"
    sig = hmac.new(SESSION_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def read_session(token: str | None) -> int | None:
    if not token:
        return None
    try:
        user_id, expires, sig = token.split(".")
    except ValueError:
        return None
    expected = hmac.new(SESSION_SECRET, f"{user_id}.{expires}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected) or int(expires) < time.time():
        return None
    return int(user_id)


def set_session_cookie(response: Response, user_id: int) -> None:
    # HttpOnly: page scripts (and injected ones) can't read it. SameSite=Lax blocks cross-site posts.
    response.set_cookie(
        SESSION_COOKIE, make_session(user_id), max_age=SESSION_TTL,
        httponly=True, samesite="lax", secure=os.getenv("COOKIE_SECURE") == "1",
    )


def public_user(row: sqlite3.Row) -> dict:
    """Never send password_hash to the browser."""
    return {
        "id": row["id"],
        "name": row["name"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "email": row["email"],
    }


def too_many_failures(email: str) -> bool:
    now = time.time()
    recent = [t for t in _failed_logins.get(email, []) if now - t < FAIL_WINDOW]
    _failed_logins[email] = recent
    return len(recent) >= MAX_FAILED


@app.get("/api/products/{product_id}/similar")
def similar_products(product_id: str, limit: int = Query(4, ge=1, le=8)) -> list[dict]:
    """'You might also like' on the single-item page (same ranking as the agent's find_similar tool)."""
    from tools import similar_cards  # tools.py has no API-key dependency

    found = similar_cards(product_id, limit=limit)
    if found is None:
        raise HTTPException(404, "Product not found")
    return [c.model_dump() for c in found[1]]


class SignupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


@app.post("/api/auth/signup", status_code=201)
def signup(req: SignupRequest, response: Response) -> dict:
    email = req.email.strip().lower()
    first, last = req.first_name.strip(), req.last_name.strip()
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Please enter a valid email address.")
    if not first or not last:
        raise HTTPException(422, "Please enter your first and last name.")
    with connect() as conn:
        if conn.execute("SELECT 1 FROM users WHERE lower(email) = ?", (email,)).fetchone():
            raise HTTPException(409, "An account with that email already exists. Try logging in.")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
            (f"{first} {last}", email, hash_password(req.password), first, last),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    set_session_cookie(response, row["id"])
    return public_user(row)


@app.post("/api/auth/login")
def login(req: LoginRequest, response: Response) -> dict:
    email = req.email.strip().lower()
    if too_many_failures(email):
        raise HTTPException(429, "Too many failed attempts. Please wait a few minutes and try again.")
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()
    # Always run the hash so a wrong email and a wrong password take the same time.
    ok = verify_password(req.password, row["password_hash"] if row else _DUMMY_HASH) and row is not None
    if not ok:
        _failed_logins.setdefault(email, []).append(time.time())
        raise HTTPException(401, "Email or password is incorrect.")
    _failed_logins.pop(email, None)
    set_session_cookie(response, row["id"])
    return public_user(row)


@app.post("/api/auth/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@app.get("/api/auth/me")
def me(cc_session: str | None = Cookie(None)) -> dict | None:
    user_id = read_session(cc_session)
    if user_id is None:
        return None
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return public_user(row) if row else None


# ---------------------------------------------------------------- chat
def save_chat(user_id: int, role: str, content: str, products: list | None = None) -> None:
    """Keep a logged-in shopper's chat in chat_messages (same shape as the seed rows)."""
    products_json = json.dumps([p.model_dump() for p in products]) if products else None
    with connect() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, ?, ?, ?)",
            (user_id, role, content, products_json),
        )
        conn.commit()


HISTORY_TURNS = 12  # how many saved messages the agent sees as memory
RELOAD_LIMIT = 50  # how many saved messages the widget reloads


def current_shopper(cc_session: str | None) -> Shopper | None:
    """The logged-in user from the signed cookie, or None. Never trusts ids sent by the browser."""
    user_id = read_session(cc_session)
    if user_id is None:
        return None
    with connect() as conn:
        row = conn.execute(
            "SELECT id, name, first_name, last_name, email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if row is None:
        return None
    return Shopper(user_id=row["id"], name=row["name"], first_name=row["first_name"],
                   last_name=row["last_name"], email=row["email"])


def load_saved(user_id: int, limit: int) -> list[sqlite3.Row]:
    """The newest `limit` chat_messages rows for this user, oldest first."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT role, content, products_json, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))


def saved_products(products_json: str | None) -> list[ProductCard]:
    if not products_json:
        return []
    try:
        return [ProductCard.model_validate(p) for p in json.loads(products_json)]
    except (ValueError, TypeError):
        return []


@app.get("/api/chat/history", response_model=list[SavedMessage])
def chat_history(cc_session: str | None = Cookie(None)) -> list[SavedMessage]:
    """A logged-in shopper's saved chat, so the widget can reload it when they come back."""
    shopper = current_shopper(cc_session)
    if shopper is None:
        return []
    return [
        SavedMessage(role=r["role"], text=r["content"], products=saved_products(r["products_json"]),
                     created_at=r["created_at"])
        for r in load_saved(shopper.user_id, RELOAD_LIMIT)
        if r["role"] in ("user", "assistant")
    ]


@app.delete("/api/chat/history")
def clear_chat_history(cc_session: str | None = Cookie(None)) -> dict:
    """'Start a new chat' for a logged-in shopper: removes only their own messages."""
    shopper = current_shopper(cc_session)
    if shopper is None:
        raise HTTPException(401, "Log in to manage saved chats.")
    with connect() as conn:
        conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (shopper.user_id,))
        conn.commit()
    return {"ok": True}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, cc_session: str | None = Cookie(None)) -> ChatResponse:
    """One shopper message in, one agent reply (plus product cards) out."""
    shopper = current_shopper(cc_session)
    try:
        # Imported here so the shop and accounts still work if the API key is missing.
        from agent import run_agent
    except Exception as exc:
        print(f"Agent unavailable: {type(exc).__name__}: {exc}")
        return ChatResponse(reply="Our chat assistant is offline right now (no AI key configured). "
                                  "You can still browse every product on the Products page.")

    if shopper:
        # Memory comes from the database, not from whatever the browser sends.
        history = [ChatTurn(role=r["role"], text=r["content"]) for r in load_saved(shopper.user_id, HISTORY_TURNS)]
    else:
        history = req.history
    response = run_agent(req.message, history, shopper=shopper, page=req.page)
    if shopper:
        save_chat(shopper.user_id, "user", req.message)
        save_chat(shopper.user_id, "assistant", response.reply, response.products)
    return response
