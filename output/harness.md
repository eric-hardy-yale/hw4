# Harness — Campus Customs Website

The working spec for the vibe coder and the shopping agent. It grows one section per problem: data, models, tools, safety, and specs. Query results were taken directly from the database on 2026-10-24.

## Database (`data/campus_customs.db`) — Problems 2–3

SQLite. The backend reads it directly. The file is never committed (`data/` and `*.db` are in `.gitignore`).

### `catalogue` — 102 products, one row each
| Field | Type | What it holds | Why it matters |
|---|---|---|---|
| `product_id` | TEXT PK | Slug, same as the image filename stem (`basic-hoodie-big-yale`) | Stable key that joins to inventory. The chatbot returns it so the page knows which cards to show |
| `name` | TEXT | Display name | What shoppers see on cards and what the bot says in replies |
| `garment_type` | TEXT | Free text, 22 spellings for ~8 kinds (`hoodie` / `pullover hoodie`) | Lets "show me hoodies" work. Match by keyword, case-insensitive |
| `description` | TEXT | One-sentence visual description | Lets the bot answer "what does it look like" and match words like "bulldog" |
| `colors` | TEXT (JSON list) | `["navy blue", "white"]` | Answers "do you have it in pink?" honestly. Parse with `json.loads` |
| `search_tags` | TEXT (JSON list) | Search keywords | Extra hits for free-text chat searches |
| `image_file_path` | TEXT | `products/<id>.jpg`, relative to `data/` (all 102 exist) | Product photo on the page, served at `/media/products/` |
| `price` | REAL | USD, 7 price points from $32 to $98 | The only source for prices. The bot must never guess one |

### `inventory` — 612 rows = 102 products × 6 sizes
| Field | Type | What it holds | Why it matters |
|---|---|---|---|
| `id` | INTEGER PK | Row id | Internal only |
| `product_id` | TEXT FK | → `catalogue.product_id`, unique with `size` | Ties stock to the right product |
| `size` | TEXT | `XS, S, M, L, XL, XXL` | Shoppers ask by size ("got this in M?") |
| `quantity` | INTEGER | 0–25. **0 = sold out in that size** (145 rows) | Honest stock answers. Read live, never cached or guessed |

### `users` — 3 rows (test user: `test@campuscustoms.yale.edu`)
| Field | Type | What it holds | Why it matters |
|---|---|---|---|
| `id` | INTEGER PK | User id | Ties a session and chat history to an account |
| `name` | TEXT | Full name | Shown in the header after login |
| `email` | TEXT UNIQUE | Login id | Sign-up must reject duplicates |
| `password_hash` | TEXT | `pbkdf2_sha256$<salt>$<hex>` | Passwords are never stored in plain text. Login re-hashes and compares. The iteration count isn't stored and must be confirmed |
| `created_at` | TEXT | UTC `datetime('now')` | Account record-keeping |
| `first_name`, `last_name` | TEXT, nullable | Added later | Lets the bot greet shoppers by first name. Sign-up fills these and `name` |

### Also present: `chat_messages` (22 rows)
| Field | Why it matters |
|---|---|
| `user_id` → `users.id` | Whose conversation it is |
| `role` (`user` / `assistant`) | Rebuilds the chat in order |
| `content` | The message text |
| `products_json` | Product cards shown with an assistant reply. It gives the card shape: catalogue fields + `image_url` + `inventory` + `total_stock` |
| `created_at` | Ordering |

### Rules that follow from the data
- **Price and stock come only from the DB**, read live at answer time. The agent never guesses or remembers them.
- The catalogue is **tops and outerwear only** (no shorts, hats, accessories). Asked for something not stocked, the agent says so.
- "Handsome Dan" isn't in any tag. Treat it as *bulldog* (10 products).
- Images are served from `data/products/` at `/media/products/<file>`.
- Passwords are only ever stored as hashes.

### Data-quality issues the agent/search must handle

1. **Inconsistent `garment_type`**: 22 spellings for about 8 real categories (`short-sleeve t-shirt` vs `short-sleeve T-shirt` vs `t-shirt`, `hoodie` vs `pullover hoodie`, `quarter-zip pullover` vs `quarter-zip pullover sweatshirt`). Filters should be case-insensitive and keyword-based ("hoodie", "crewneck", "quarter-zip", "fleece", "jacket", "t-shirt").
2. **Messy generated names**: `Champion Reverse Weave Hoodie 1`, `Ua Mens Tech L S 2 0`. The display name may need cleanup.
3. **No category for shorts, hats, or accessories**: the catalogue is tops and outerwear only, so the agent must say "we don't carry that" rather than invent items.
4. **No "Handsome Dan" tag**: 10 products mention "bulldog", but none mention "Handsome Dan" by name. The agent prompt could map "Handsome Dan" to bulldog.
5. **"Fleece" is ambiguous**: 7 products mention fleece. Some are quarter-zips ($72), not the $98 jackets.

## Architecture: how the front end talks to FastAPI — Problems 4–5

```
Browser (Vite dev server :5173)  ──/api/*, /media/*──▶  FastAPI (uvicorn :8000, run from backend/)
   React pages + chat widget          (Vite proxy)        main.py ─▶ SQLite data/campus_customs.db
                                                              └──▶ agent.py ─▶ Portkey ─▶ OpenAI model
```

- **Run the backend from `backend/`:** `uvicorn main:app --reload --port 8000`. `main.py` finds the database at `../data/campus_customs.db` and loads keys from `../.env`.
- **Same origin:** `frontend/vite.config.ts` proxies `/api` and `/media` to `http://127.0.0.1:8000`, so the browser only ever talks to port 5173. The session cookie stays first-party and the code needs no hard-coded backend URL. All calls go through `frontend/src/api.ts`.

| Route | Used by | What it does |
|---|---|---|
| `GET /api/products?q=` | Products page | All catalogue rows (optional text search), parsed `colors`/`search_tags`, `image_url` |
| `GET /api/products/{id}` | Single-item page | One product plus `inventory` by size and `total_stock` |
| `GET /media/products/<file>.jpg` | Every `<img>` | Static files from `data/products/` |
| `POST /api/auth/signup` · `/login` · `/logout` · `GET /api/auth/me` | Create account, Log in, nav bar | Writes/reads `users`, sets or clears the HttpOnly `cc_session` cookie |
| `POST /api/chat` `{message, history[], page}` | Chat widget | Runs the agent. Returns `{reply, products[], results_title, tools_used[]}`. Logged-in chats are saved to `chat_messages` |
| `GET` / `DELETE /api/chat/history` | Chat widget | Reload or clear the logged-in shopper's saved chat |

- **Accounts:** PBKDF2-HMAC-SHA256, 120,000 iterations, random 16-byte salt per user, stored as `pbkdf2_sha256$salt$hash`, the same format as the seed users. Login re-hashes with the stored salt and compares with `hmac.compare_digest`. Unknown emails still run a dummy hash, so timing doesn't reveal which emails exist. After 5 failures in 15 minutes, logins for that email are blocked with a 429. The session cookie is HMAC-signed (`SESSION_SECRET`), HttpOnly, SameSite=Lax, and expires after 7 days. `password_hash` is never sent to the browser.

## Agent: how it is loaded — Problem 5

The agent is four files next to `main.py`:

| File | Role |
|---|---|
| `prompts/prompt.md` | System prompt: Campus Customs voice, what we sell, which tool to call for which question, honesty and safety rules. Read once at startup as the agent's `instructions` |
| `agent.py` | Builds `Agent(get_model(), deps_type=ShopDeps, output_type=ShopReply, instructions=prompt.md, tools=[search_products, get_product, check_stock, find_similar, get_current_page, get_shopper], retries=2)` plus the `check_prices` output validator (Problem 8). Adds dynamic instructions for the shopper and the current page (Problem 7). `run_agent()` runs it, filters product ids, and appends to `output/audit_trail.json` |
| `tools.py` | `get_model()`, SQLite helpers, and the tools |
| `models.py` | Pydantic types for tool results, the agent's output, the API, and the audit trail |

- **Model:** `get_model()` uses the Yale Portkey gateway (`https://api.portkey.ai/v1`) with `PORTKEY_API_KEY` from `hw4/.env`, falling back to `OPENAI_API_KEY`. The default model is `gpt-5.6-luna` (OpenAI 5.6 series), and `OPENAI_MODEL` in `.env` overrides it. It's called through the OpenAI Responses API with a concise reasoning summary, so the audit trail can show the agent's thoughts.
- **Lazy import:** `main.py` imports `agent` inside the chat route. If the key is missing, the shop, products and accounts still work, and the chat says the assistant is offline.
- **Conversation memory:** the last 12 turns are passed as PydanticAI `message_history`. They come from `chat_messages` for logged-in shoppers and from the browser for guests (see Problem 7).
- **No invented cards:** the model returns `product_ids`, but `run_agent` keeps only ids a tool actually returned this turn (`ShopDeps.seen_product_ids`). It then rebuilds each card from the database, so prices on cards are always real.

## Tools — Problem 5

The product tools read `catalogue` + `inventory` live. No tool queries `users`; `get_shopper` only returns the `Shopper` the server already put in the deps. They return Pydantic models, not free text, so the model reads named fields instead of parsing prose.

| Tool | Answers | Returns |
|---|---|---|
| `search_products(query, garment_type, color, max_price, size_in_stock, limit≤12)` | "What hoodies do you have?", "bulldog tees under $40 in XL" | `ProductSearchResult` |
| `get_product(product_id)` | Description and price of one item | `ProductCard` (or an error string for an unknown id) |
| `check_stock(product_id, size)` | "Is it in M?", "how many left?" | `StockCheck` (or an error string for an unknown id or size) |
| `find_similar(product_id, size, color, limit≤8)` (Problem 8) | Sold out in a size, wrong color, "more like this" | `SimilarProducts {based_on, size, color, products[], note}`: in-stock alternatives ranked by garment family, shared design words, colors, and price closeness |
| `get_current_page()` (Problem 7) | "Do you have **this** in pink?" | `ProductCard` for the item on screen, or a note that the shopper isn't on a product page |
| `get_shopper()` (Problem 7) | "Who am I logged in as?" | `Shopper` (id, names, email), or "not logged in" |

Search handles the messy data. Keywords are AND-matched across name, type, description, colors and tags. Shopper words are mapped to catalogue words ("Handsome Dan" → bulldog, "tee" → t-shirt, "1/4 zip" → quarter-zip, "grey" → gray). Garment type matching is loose, so `hoodie` also matches "hooded sweatshirt" and "full-zip hood".

### Fields chosen for lookup results, and why

**`ProductCard`** (used by both the website and the agent)
| Field | Why |
|---|---|
| `product_id` | The key the agent passes to `check_stock`/`get_product` and puts in `product_ids` for cards |
| `name` | What the agent says and the card shows |
| `garment_type`, `colors` | Answer "is it a hoodie?" and "do you have it in pink?" without guessing |
| `description` | Lets the agent describe the look honestly (graphic, placement, pocket) |
| `price` | The exact catalogue price. The prompt tells the agent to quote it verbatim |
| `image_url` | Lets the widget show the photo, not used by the model |
| `inventory: list[SizeStock]` | Per-size `quantity`, so one search can answer most size questions |
| `total_stock` | Quick "is any of it in stock?" check |

`search_tags` and `image_file_path` are left out on purpose. Tags are only used for matching, and they would add tokens without helping the answer.

**`ProductSearchResult`**: `total_matches` (so the agent can say "we have 27 hoodies" truthfully even when only 8 come back), `returned`, `products`, and `note` (tells the agent to retry with simpler words before saying "we don't carry it", or that results were capped).

**`StockCheck`**: `in_stock` (one unambiguous yes/no), `quantity` for the asked size (`0` = sold out, the prompt requires saying so clearly), `sizes_available` and `sizes_sold_out` (so a sold-out answer can offer alternatives without a second call), and `name` (so the reply names the right item).

**`ShopReply`** (agent output): `reply` (Markdown text) plus `product_ids`. Keeping ids separate from the text lets the server check them and build the cards from the database.

**`ShopDeps`** (per-run context): `first_name` for the greeting only (no email or hash ever reaches the model), and `seen_product_ids` for the anti-hallucination filter.

**`AuditEntry` / `ToolStep`**: time, user id, message, thoughts, each tool call with args and a result preview, reply, product ids, model, stop reason, and duration. This is the evidence that answers came from tool calls.

## How search results reach the page — Problem 6

When a shopper asks about a kind of item ("what hoodies do you have?"), the matches appear on the website itself as full product cards, not just as text in the chat.

```
shopper types in chat widget
  → POST /api/chat {message, history}
  → agent calls search_products(...)          (tools.py, reads SQLite; ids recorded in ShopDeps.seen_product_ids)
  → agent returns ShopReply {reply, product_ids[], results_title}   (models.py, structured output)
  → run_agent keeps only ids a tool returned, rebuilds each card from the DB with load_cards()
  → ChatResponse {reply, products: ProductCard[], results_title, tools_used}
  → ChatWidget: shows the reply + mini cards, and calls showResults(results_title, products)
  → ChatResultsProvider (React context) → <ChatResults/> renders a "From your chat" card grid
    at the top of the current page (Home, Products, About…) and scrolls it into view
  → each card is the same <ProductCard/> used on Products → links to /products/:id (single-item page)
```

**The API contract** (`POST /api/chat` response, `models.ChatResponse`):

| Field | Type | Meaning |
|---|---|---|
| `reply` | string (Markdown) | The agent's short answer for the chat bubble |
| `products` | `ProductCard[]` | Matches to render, best first, at most 12. Same shape as `/api/products/{id}`: `product_id, name, garment_type, description, colors, price, image_url, inventory[], total_stock` |
| `results_title` | string | Heading for the on-page section, e.g. "Hoodies". Empty when `products` is empty |
| `tools_used` | string[] | Which tools ran, for debugging |

**Why it's built this way:**
- **The model never writes card data.** It only picks `product_ids`, and the server fills in name, price, image and stock from the database. A hallucinated id is dropped, and a price on a card can't be wrong.
- **One card component everywhere.** Chat results reuse `ProductCard`, so clicking any card, from Products, from the on-page chat section, or from the mini cards in the widget, opens the same single-item page (large image + full info).
- **Results persist while you browse.** The section lives in a React context above the router, so a shopper can open a product, press Back, and the chat's cards are still there. It's hidden on the single-item page itself so the detail view stays clean. **Clear** removes it, and a new chat search replaces it.
- **Text stays short.** The prompt tells the agent to name 3–5 favorites and say "I've put them on the page" instead of listing every price in the bubble.

Verified in the browser: the chat put 4 hoodie cards at the top of Home. Clicking the Crew Left Chest Hoodie card opened its detail page ($68.00, M sold out). Back returned to Home with the 4 cards still there, and a mini card in the chat panel also opened its detail page.

## Chat memory, shopper identity, and page context — Problem 7

### How user chat history is stored
- **Table:** the existing `chat_messages` table (`id, user_id → users.id, role, content, products_json, created_at`). It's the same shape as the seed rows, so the test user's old chats reload too.
- **Write:** after each `/api/chat` call by a **logged-in** shopper, `main.py` inserts two rows: the user message, and the assistant reply with its product cards serialized into `products_json`.
- **Reload:** `GET /api/chat/history` returns the newest 50 rows for the cookie's user, oldest first, as `SavedMessage {role, text, products[], created_at}`. The widget calls it whenever the logged-in user changes (page load, login), so a returning shopper sees the old conversation with its cards.
- **Agent memory:** for logged-in shoppers, the server reads the last 12 rows from `chat_messages` and passes them as `message_history`. It ignores any history the browser sends, so a page script can't feed the agent fake past turns.
- **Guests:** they can chat, but nothing is saved. The widget keeps the conversation in React state and sends the last 12 turns with each message. A reload or logout starts fresh.
- **New chat:** `DELETE /api/chat/history` deletes only the caller's own rows (401 for guests).
- **Ownership:** the user id always comes from the signed HttpOnly session cookie (`current_shopper()`), never from the request body.

### What customer fields the agent sees
`ShopDeps.shopper` is a `Shopper` model built server-side from `users`:

| Field | Why |
|---|---|
| `user_id` | Ties the run to the audit trail and saved chats. The model doesn't need it in replies |
| `first_name`, `last_name`, `name` | Friendly greeting and "who am I logged in as?" |
| `email` | Answers "what email is on my account?" The prompt says to share it only when asked |

It is **never** given `password_hash`, `created_at`, or anything about other users. The fields reach the model two ways: a dynamic `@agent.instructions` block ("## Shopper — Logged in as Test User…") added on every run, and the `get_shopper()` tool, which returns the same `Shopper`.

### How page context is passed
1. `ChatWidget` reads the router path. On `/products/:id` it sends `page: {path, product_id}` with every message (`PageContext` in `models.py`). Elsewhere `product_id` is null.
2. `run_agent` looks that id up with `load_cards()` (live price and stock). An unknown id is ignored. The result is stored in `ShopDeps.current_product`, and the id is added to `seen_product_ids` so the item can appear as a card.
3. A second dynamic instruction, `page_context()`, writes the item's name, id, type, colors, price and stock by size into the agent's instructions ("When they say 'this'… they mean this item").
4. The `get_current_page()` tool returns the same `ProductCard`, for when the model wants it as structured data.

So "do you have this in pink?" on the Basic Hoodie Big Yale page resolves to `basic-hoodie-big-yale` (colors: navy blue, white). The agent says it doesn't come in pink and searches for pink alternatives. The widget shows "The assistant can see the item on this page" so the shopper knows.

Verified in the browser:
- Logged in as the test user, the widget reloaded their 6 saved messages and 9 product cards from `chat_messages`.
- On `/products/basic-hoodie-big-yale`, the chat request carried `page: {path: "/products/basic-hoodie-big-yale", product_id: "basic-hoodie-big-yale"}`.
- `GET /api/chat/history` returns `[]` for a guest, and `DELETE` returns 401.

A stand-in test model confirmed that `get_current_page` and `get_shopper` return the right product and user. A live model test is pending: there's no API key in `.env` yet.

## Usability improvements — Problem 8
Full write-up in `output/usability.md`.
- **Front end:** chat suggestion chips that change on product pages; stock badges, a sizes line, sort, and an "In stock in [size]" filter on product cards (`/api/products` now includes inventory).
- **Agent:** the `find_similar` tool for sold-out sizes and wrong colors, and the `check_prices` output validator. It rejects any `$` amount in a reply that didn't come from this turn's tool results (`ShopDeps.seen_prices`) or from the shopper's own words or history (`allowed_amounts`), with up to 2 `ModelRetry`s. Retries are logged as `price_retries` in the audit trail.

## Safety
Basics are in `prompts/prompt.md` (prices and stock only from tools, no orders, payments or account changes, no sensitive data, prompt-injection resistance, stay on topic). Server-side guards: the price-check output validator (Problem 8), a card filter that only shows real, tool-returned ids, password hashing, HttpOnly signed sessions, login rate limiting, and request size limits (message ≤ 2,000 chars, history ≤ 20 turns). _To be expanded in a later problem._

## Specs
_To be filled in a later problem._
