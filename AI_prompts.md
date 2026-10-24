# AI Prompts Log — Campus Customs Website

One section per problem: the prompt I typed, plus a follow-up if the first attempt fell short.

## Problem 1: Vibe coder prompts

**Prompt:**
> Create AI_prompts.md at the start of the assignment and keep it updated as you work. This file is the log of what you typed to your vibe coder.

**Result:** Created `AI_prompts.md` in the project root with one section per problem. The vibe coder adds each new prompt here as we go.

**Follow-up prompt:**
> Describe each problem to your vibe coder in your own words.

**What was lacking after the first:** The log didn't yet say that every problem has to be described in my own words, so I added that rule.

## Problem 2: Analyze the database

**Prompt:**
> Look at the database data/campus_customs.db and understand the fields of each table.

> At a minimum you should understand catalogue, inventory, and users

> You will keep growing this harness file in later problems (models, tools, safety, specs).

**Result:** The vibe coder queried every table in `data/campus_customs.db` and wrote the database section of `output/harness.md`: a field-by-field reference for catalogue, inventory and users, row counts, prices, stock by size, the hash format, and data-quality issues to handle in search. Empty Models / Tools / Safety / Specs sections are there to grow later.

**Follow-up:** None yet.

## Problem 3: Start harness.md

**Prompt:**
> Start the file output/harness.md. Write down each table and its fields, and one short line on why each field matters for the shop or the chatbot.

**Result:** Created `output/harness.md` from the live schema of `data/campus_customs.db` (`catalogue`, `inventory`, `users`, `chat_messages`). Each field has one line on why the shop or the chatbot needs it.

**Follow-up:** None yet.

## Problem 4: Front end, products, chat widget, and accounts

**Prompt:**
> Scaffold a React + Vite + TypeScript front end for Campus Customs. Put a nav bar at the top that links to the main pages: Home, Products, About Us, Log in, Create account. Pull Campus Customs–style wording from https://yalebulldogblue.com/ for Home and About Us, but write these pages in your own voice (do not copy the original site text).

> On the Products page, show product images from the catalogue (use the image paths in the database) with basic product info (name, price, short description). Make each product open a single-item page (large image on one side, full product text on the other — description, price, sizes/stock when you have them). Clicking a card on Products should take the shopper there. Add a chat interface in the bottom right of the site (a floating chat panel is fine). It does not need to talk to an agent yet — a stub that will call your backend later is enough for this problem. You will need a small API soon to read the database. It is fine to start a simple FastAPI app in backend/main.py just to serve products and images, then grow it into the agent backend in Problem 5.

> Build a normal create-account / login flow. Create account: first name, last name, email, password (confirm password is a nice touch). Log in: email and password. New accounts go into the users table. Make sure to store passwords securely so hackers (human or AI) cannot access them.

**Result:**
- **Front end:** a Vite React TS app in `frontend/` with a nav bar, Home and About Us written in our own words, a Products grid (102 items with images, filters and search), a single-item page with sizes and stock, and a floating chat widget.
- **Backend:** `backend/main.py` serves `/api/products`, `/api/products/{id}` and the images at `/media/products/`.
- **Accounts:** sign-up and login write to and read from `users`. Passwords are stored as PBKDF2-SHA256 with a random salt per user (`pbkdf2_sha256$salt$hash`), and login uses a constant-time compare. The session is an HttpOnly signed cookie, and repeated failed logins are rate-limited.
- **Checked in the browser:** the seeded test user logs in, a wrong password is rejected, and a new account (`bulldog.tester@example.com`) was created through the form, landed in `users` as id 4, and could log back in.

**Follow-up prompt:**
> The seed database already has a test user you can use while building (test@campuscustoms.yale.edu / password; PBKDF2-HMAC-SHA256, 120,000 iterations, stored as pbkdf2_sha256$salt$hash). Re-hash what the user typed with the stored salt and compare in constant time; signup and login must use the same settings. Confirm you can log in as that user, and that a brand-new account you create also works.

**What was lacking after the first:** The first pass couldn't verify existing users, because the iteration count isn't stored in the database. This gave the exact hash settings and how to test them.

## Problem 5: Shop chatbot agent

**Prompt:**
> Build the shop chatbot as a PydanticAI agent behind FastAPI, plugged into your front-end chat widget. Put the API app in backend/main.py — that is the file you run with Uvicorn. Keep the agent as these four files next to it (same idea as Homework 3): backend/prompts/prompt.md — system prompt (grow this same file later), backend/agent.py — agent entry / wiring, backend/tools.py — tools the agent can call, backend/models.py — Pydantic / PydanticAI structured types. In main.py, expose a chat route so a message from the website returns a reply from the agent (and whatever else you need for products/auth). You will need your AI model API key for the agent.

> Put Campus Customs voice and safety basics into prompts/prompt.md (you will expand tools and safety later). Start or update types in models.py for chat replies / product cards as needed.

> In output/harness.md, note how the front end talks to FastAPI and how the agent is loaded (prompt file + model). Make sure the backend runs from the backend/ folder like this: uvicorn main:app --reload --port 8000

> Give the agent tools that look up real information from campus_customs.db: Product description, Price, How many are in stock (by size when the customer asks). The agent must use the database — it should not invent prices or quantities. If a size is out of stock, say so clearly.

**Result:**
- **Agent:** a PydanticAI agent in `backend/` (`prompts/prompt.md`, `agent.py`, `tools.py`, `models.py`) with three database tools: `search_products`, `get_product` and `check_stock`. It returns a structured `ShopReply`, which is the reply text plus product ids.
- **Chat route:** `POST /api/chat` in `main.py` runs the agent with the shopper's first name and recent chat history. It returns the reply plus product cards built from the database, and only for ids a tool actually returned. Logged-in chats are saved to `chat_messages`, and every run is logged to `output/audit_trail.json`.
- **Chat widget:** shows Markdown replies and clickable product cards.

**Follow-up prompt:**
> Expand prompts/prompt.md so the agent knows to call these tools for price and stock questions. Add or update return types in models.py. In output/harness.md, list each tool and explain which model fields you chose for lookup results and why.

**What was lacking after the first:** The first prompt only had general rules, so this added a tool table to the prompt (which tool for price, stock and description questions, and how to word a sold-out answer). It also documented the `ProductCard`, `ProductSearchResult` and `StockCheck` fields in the harness.

## Problem 6: Dynamic product cards from the chat

**Prompt:**
> Now we will add a neat feature to the site. When a customer asks about a type of item — for example "what hoodies do you have?" — the agent should search the catalogue and the website should dynamically show those matching items as product cards (image, name, price, short info). This is an API contract: the agent returns structured product matches and then the front end renders them on the website. It looks really cool.

> After the dynamic product cards are loaded by your new feature, make sure the same single-item page behavior you built in Problem 3 still works: each product card — including the ones the chat just put on the page — should still open that detail view (large image + full info) when clicked.

**Result:**
- **Contract:** the agent's structured output (`ShopReply`) now has `product_ids` plus a `results_title`. `/api/chat` returns `ChatResponse {reply, products: ProductCard[], results_title, tools_used}`, with every card rebuilt from the database.
- **On the page:** the front end puts those cards in a "From your chat" section at the top of the current page, using the same `ProductCard` component as the Products page, so every card still opens the single-item page.
- **Checked in the browser:** clicked a chat card, saw the detail page, pressed Back, and the cards were still there.

**Follow-up prompt:**
> Update prompts/prompt.md and output/harness.md so it is clear how search results reach the page.

**What was lacking after the first:** The feature worked, but the prompt and harness didn't explain the path from search tool to on-page cards, so the prompt now tells the agent to fill `product_ids`/`results_title`, and the harness has the full data-flow diagram and contract table.

## Problem 7: Chat memory, who is chatting, and page context

**Prompt:**
> When a shopper is logged in, save their chat history in the database in an appropriate table and reload it when they return. The agent should know who is chatting (name, email) — put that in agent deps (or an equivalent clear pattern) and/or tools the agent can call. Also pass enough page context that if someone is on a product page and asks "do you have this in pink?", the agent knows which item they mean. Hint: you can put code into the agent context.

**Result:**
- **History:** logged-in chats are saved to `chat_messages` (one row per message, with cards in `products_json`). They reload through `GET /api/chat/history` on login, and the agent's memory is read from that table, not from the browser.
- **Who is chatting:** a `Shopper` (id, first and last name, email) is built from the session cookie and put in `ShopDeps`. The agent sees it through a dynamic instruction and the `get_shopper` tool.
- **Page context:** the widget sends `page {path, product_id}`. The server loads that product from the database into `ShopDeps.current_product`, and a second dynamic instruction plus `get_current_page` tell the agent what "this" means.
- **Checked in the browser:** the test user's saved chat reloaded, and the product page sent the right `product_id`.

**Follow-up prompt:**
> Guests can still chat, but history only needs to persist for logged-in users. Document in output/harness.md: how user chat history is stored, what customer fields the agent sees, and how page context is passed.

**What was lacking after the first:** The first prompt didn't say what guests get, so this made the split explicit (guests keep history in the browser and nothing is saved). It also documented storage, customer fields and page context in the harness.

## Problem 8: Usability improvements

**Prompt:**
> Now that the core shop works, improve it. Choose and implement: 2 front-end usability improvements, 2 agent / backend usability improvements. Front-end improvements are things that make the site look better and make it easier to use. Agent / backend improvements are things that make the agent output better, more accurate, or safer. These could be new agent tools or things that make the agent run faster or cheaper. Write output/usability.md before or as you build. For each of the improvements, say: What you added, Why it helps a Campus Customs shopper or the business

**Result:**
- **Front end:** (1) chat suggestion chips that switch to "this item" questions on a product page, and (2) stock badges, an in-stock sizes line, a sort menu, and an "In stock in [size]" filter on the Products page.
- **Agent:** (3) a `find_similar` tool that offers in-stock alternatives when a size is sold out or the color is wrong, and (4) a price-check output validator that sends back any reply with a dollar amount the tools didn't return.
- **Write-up:** `output/usability.md` covers what each one is, why it helps, and where to see it.

**Follow-up prompt:**
> Then make sure all improvements actually show up in the running app. Graders will read the write-up and look for the features.

**What was lacking after the first:** The write-up described the features but didn't prove they were visible, so I checked each one in the running app and added a "Where to see each one" table. Badges, sort, the M filter (80 of 102) and the product-page chips were checked in the browser. The price check was tested with a fake model that said "$55" and was corrected to "$68.00".

## Problem 9: Storefront design

**Prompt:**
> Add creative design so the site feels like a real Campus Customs storefront — fonts, color, hierarchy, motion, product presentation, chat feel. Write output/design.md: what you changed and why it should help customers stick around and buy. Keep it concrete and short.

**Result:**
- **Look:** self-hosted Libre Baskerville, Graduate (varsity) and Inter fonts, Yale blue on a warm off-white background, and a new Home page (hero collage of real products, category tiles with photos and "From $" prices, an assistant promo band, a staples row).
- **Product pages:** zoom, color swatches, a size picker, "Ask the assistant about this" and a "You might also like" row (new `/api/products/{id}/similar` endpoint).
- **Chat:** avatar, online dot, typing dots, spring-in panel, and a pulsing button. All motion respects reduced-motion settings.
- **Checked:** in the browser on desktop and on a 375 px phone screen. `output/design.md` explains each change.

**Follow-up:** None needed.

## Problem 10: App check, audit trail, safety, and finishing the harness

**Prompt:**
> Test the live site and document it in output/app_check.html (a page you can double-click open). Include clear screenshots and short captions for: Chat checking the inventory level of an item (honest stock/price from the DB) The dynamic search-result cards appearing after a category question (e.g. hoodies) One of the usability features you added Make the HTML easy to grade: heading for each check, screenshot, one or two sentences on what the screenshot proves. Put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png).

> Keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/result, stop reason). Do not wipe it between runs. Also, think of some safety rules to give the agent and put them in prompts/prompt.md.

> Finish output/harness.md so it is clear how the system works. Model fields in models.py and why you chose them Tools and abilities Safety rules Specs (loop limits, result caps, models, how to run front + back)

**Result:**
- **Audit trail:** every agent run is appended to `output/audit_trail.json` (time, message, tool calls with short args and results, reply, stop reason, price retries, duration). It is never wiped, and failed runs now log their tool calls too.
- **Loop limits:** 8 model requests and 10 tool calls per message.
- **Safety rules:** `prompts/prompt.md` now has a full Safety rules section (honesty, what the agent can't do, privacy, prompt injection, tone and scope, and the code guardrails).
- **Harness:** `output/harness.md` now has a one-minute overview, a models table, a tools and abilities table, a safety section, and specs.
- **Live app check:** ran with the real model (`gpt-5.6-luna` via Portkey). `output/app_check.html` has four screenshots in `output/app_check_images/`: an inventory check (S = 12, M sold out, $68.00), hoodie cards on the page, a chat card opening the detail page, and the stock badge / size filter / sort feature. A table of other live checks covers "this in pink?", a discount-code-and-other-customer trick, and a prompt-injection attempt. Every number was checked against the database.
- **Fixes found while testing live:**
  - Azure's content filter blocked a jailbreak message, and the chat used to show a generic error. It now politely declines.
  - On a product page, the agent said "I've put them on the page", but the chat cards were hidden there. They now show below the product.
