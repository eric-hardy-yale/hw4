# Usability Improvements — Problem 8

Four improvements now that the core shop works: two in the front end, two in the agent and backend.

## Front end

### 1. One-tap chat suggestions that know what page you're on
**What we added:** a row of suggestion chips above the chat input. Tapping one sends it as a message.
- **Most pages:** shopping starters like "What hoodies do you have?", "Anything with Handsome Dan?", "Gifts under $40" and "Show me Berkeley College gear".
- **A product's page:** chips about that item, such as "Is this in stock in M?", "What colors does this come in?" and "Show me similar items".
- **After a reply:** general chips hide once the conversation has started, so they don't crowd the panel, and come back after **New chat**. The product-page chips stay available whenever you open an item.

**Why it helps:** many shoppers don't know what a chatbot can do, so they type nothing or something vague. Chips show off the best features (real stock checks, Handsome Dan → bulldog, price filters) in one tap, which is especially useful on a phone. The product-page chips also teach the "this item" feature from Problem 7. For the business, more shoppers reach a product card, and every card is one click from the detail page.

### 2. Stock at a glance on every card, plus sorting
**What we added:**
- **Stock badge:** each product card (Products page, chat results on the page) now shows a badge from live inventory:
  - **Only N left** when 20 or fewer units remain across all sizes (4 items today, e.g. "Only 9 left" on the Football Left Chest T-shirt)
  - **Some sizes sold out** when one or more sizes are at 0
  - **In stock** otherwise
- **Sizes line:** the card also lists the sizes in stock ("Sizes: XS S L XL XXL").
- **Sort and size filter:** the Products page has a **Sort** menu (Featured, Price low → high, Price high → low, Name A–Z) and an **In stock in [size]** filter. Picking M, for example, leaves the 80 of 102 items that have an M on the shelf. The Products API now returns stock with every product, in one query.

**Why it helps:** the most common question in the seed chats was about sizes. Shoppers can now skip the items that are out in their size without opening each one, or hide them entirely with the size filter. Budget shoppers (students, parents buying gifts) can sort by price. For the business, "Only 3 left" badges add honest urgency, and shoppers waste less time on dead ends.

## Agent / backend

### 3. `find_similar` tool: alternatives when something is sold out or the wrong color
**What we added:** a new agent tool, `find_similar(product_id, size, color, limit)`.
- **How it ranks:** it scores every other product by shared garment type, shared design words from the name, description and tags (bulldog, Berkeley, hockey, vintage…), shared colors, and closeness in price.
- **Filters:** it only returns items that actually have stock in the requested size, and in the requested color if one is given.
- **Prompt:** tells the agent to call it whenever a size is sold out, an item doesn't come in the asked-for color, or the shopper says "show me similar items".

**Why it helps:** before this, "Do you have the Crew Left Chest Hoodie in M?" got an honest "Sold out in M", and then the conversation stalled. Now the agent says it's sold out and immediately offers in-stock M hoodies with a similar look. That saves a sale instead of losing it. A single tool call also replaces two or three guessing searches, so these answers are faster and cheaper.

### 4. Price-check guardrail on every reply
**What we added:** a PydanticAI output validator (`@agent.output_validator` in `agent.py`) that runs before any reply reaches the shopper.
- **What it checks:** it pulls every dollar amount out of the reply text and compares it with the prices the tools actually returned this turn, plus any amounts the shopper typed ("under $40").
- **If a price is wrong:** the reply is rejected with `ModelRetry`, which tells the model which amounts were unsupported and asks it to fix them using tool results. That happens at most twice; after that the run fails safely with an apology.
- **Cards:** every product id the model wants to show must come from a tool this turn. Bad ids are dropped server-side. The validator is a check on the text, and the card filter does the same for cards.
- **Logging:** the number of retries is recorded in the audit trail.

**Why it helps:** the core promise of this shop is honest price and stock. The prompt already says "never invent a price", but prompts can be ignored. This is a hard, code-level check, so a made-up "$45 hoodie" or a stale "$60" can't reach a customer. It protects shoppers from wrong prices and protects the business from pricing disputes.

## Where to see each one in the running app

| # | Improvement | Where to look |
|---|---|---|
| 1 | Chat suggestions | Open **Chat with us** on Home or Products, where 4 starter chips show. Open any product, and the chips switch to "Is this in stock in M?", "What colors does this come in?" and "Show me similar items" |
| 2 | Stock badges, sizes, sort, size filter | **Products** page: green/yellow/red badges on every card, "Sizes:" line, **In stock in** and **Sort** menus |
| 3 | `find_similar` | Ask the chat "Do you have the Crew Left Chest Hoodie in M?" (it's sold out in M). The agent says so and offers in-stock M hoodies as cards. The `find_similar` call appears in `output/audit_trail.json` |
| 4 | Price check | Every run in `output/audit_trail.json` has `price_retries`. A scripted test with a fake model that claimed "$55" for the $68 hoodie was sent back once and fixed to "$68.00", and a made-up product id was dropped |
