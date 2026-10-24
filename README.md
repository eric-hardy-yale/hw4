# Campus Customs — HW4

Shop site for Campus Customs: a React + Vite TypeScript front end and a FastAPI backend whose chatbot is a PydanticAI agent. Prices and stock come from a local SQLite database.

## 1. Place the data pack (not in git)

Unzip the course `data.zip` so the folder sits inside `hw4/`:

```
hw4/data/
├── campus_customs.db
└── products/        # images referenced by the catalogue table
```

## 2. Add your API key

```bash
cp .env.example .env
```

Then put your `PORTKEY_API_KEY` in `.env`. Optionally, also set `SESSION_SECRET` to a long random string so logins survive a backend restart. Without a key, the shop and accounts still work, but the chat says it's offline.

## 3. Back end (FastAPI, port 8000)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

Run this from the `backend/` folder. API docs: http://127.0.0.1:8000/docs

## 4. Front end (Vite, port 5173)

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. Vite forwards `/api` and `/media` to the backend on port 8000, so start the backend first.

## Try it

- Log in with the seeded test user `test@campuscustoms.yale.edu` (password `password`), or create a new account.
- Open **Chat with us** (bottom right) and ask things like "what hoodies do you have?", "is the Crew Left Chest Hoodie in M?" or "anything with Handsome Dan?".
- Each chat run is appended to `output/audit_trail.json`.

## Layout

- `backend/` holds the FastAPI app (`main.py`) and the agent (`agent.py`, `tools.py`, `models.py`, `prompts/prompt.md`).
- `frontend/` holds the Vite React TypeScript app.
- `output/` holds the harness, design and usability notes, the app check, and the audit trail.
- `AI_prompts.md` logs the prompts typed to the vibe coder, one section per problem.
