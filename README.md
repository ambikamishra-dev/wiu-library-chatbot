# WIU Library Chatbot

A production-grade FAQ chatbot built for a university library. Students ask questions, the bot answers instantly from a curated dataset — no AI hallucination, no external API costs, no ongoing fees.

Designed to embed on any web page with a single line of HTML. The backend runs entirely on institution-owned infrastructure — no student data leaves the organization.

**Built by:** Ambika Mishra

---

## What it does

A chat widget sits on the page and waits. Users can click a pre-loaded quick question or type their own. The bot matches the query against a staff-curated FAQ and returns the exact answer that was written for it — with a clickable link to the relevant page when one exists.

When no confident match is found, the bot says so and provides a direct contact option. It does not guess, it does not generate, it does not hallucinate. Every unanswered query is logged so the FAQ can grow over time based on what people actually ask.

No LLM. No API calls. No ongoing cost.

---

## How the matching works

Every incoming query goes through two stages before a response is returned.

**Stage 1 — Keyword matching** runs first because it is fast and free. The query is normalized, punctuation stripped, and compared against keyword lists for each FAQ entry. If two or more keywords match, that entry wins and the response is returned immediately, no model involved.

**Stage 2 — Semantic matching** runs only when keyword matching finds nothing. The query is embedded using `BAAI/bge-small-en-v1.5` (a 33MB model that runs on CPU) and compared against pre-computed embeddings for all FAQ questions and their alternative phrasings. The closest match above a confidence threshold of 0.75 is returned.

Both stages include domain scoping — if the query has no library-related vocabulary and scores below 0.90 confidence, the bot returns a fallback rather than a plausible-sounding wrong answer.

FAQ embeddings are pre-computed once at startup and cached in memory. Per-request work is one query embedding only, keeping response times under 5ms even at 200 concurrent users.

---

## Stack decisions and why

**FastAPI over Flask** — async request handling, automatic request validation via Pydantic, and built-in OpenAPI docs without any extra setup. For a chatbot that needs to handle concurrent exam-season traffic, async matters.

**bge-small over larger models** — 33MB, runs on CPU, no GPU required, no cloud API dependency. Accurate enough for a bounded FAQ domain where questions are well-defined and consistent. A larger model would add latency and infrastructure cost without meaningful accuracy improvement.

**Excel over a database for FAQ data** — the FAQ is maintained by library staff, not developers. Excel gives them a familiar interface to update questions, answers, and keywords without touching any code or system. The loader reads the file at startup and a hot-reload endpoint pushes updates live without restarting the server.

**SQLite over Postgres for the unanswered log** — the unanswered log grows by maybe 50-100 rows per week. SQLite is a single file, zero configuration, and handles this load trivially. The schema is one table. Adding Postgres for this would be overengineering.

**Vanilla JS over React** — no build step, no bundler, no framework dependency. One script tag embeds the widget on any HTML page. The host page's existing styles and scripts are unaffected.

---

## Performance

Load tested with Locust on a MacBook Air (Apple M-series, no GPU):

- 200 concurrent users, 0% failure rate
- Median response time 1ms (cache hit), 4ms 95th percentile
- 92 requests per second sustained

The 1ms median comes from the response cache — repeated queries are served from an in-memory dictionary with no matching work. The semantic path (first time a query is seen) takes 200-400ms on CPU, well within the 3-second target.

---

## Project layout

app/
api/routes.py — all HTTP endpoints, orchestrates the pipeline
core/
loader.py — reads the Excel file, owns the FAQ cache
matcher.py — keyword matching with domain-aware scoring
semantic.py — embedding, corpus cache, cosine similarity
guardrails.py — input sanitization, rate limiting, injection blocking
static/ — JS widget and CSS served directly by FastAPI
templates/ — demo HTML page for local testing
main.py — app assembly, startup tasks, CORS, lifespan
config.py — typed settings from environment variables

tests/ — 68 tests across loader, matcher, semantic, guardrails, routes
data/ — FAQ Excel file (excluded from git)
logs/ — SQLite unanswered log (excluded from git)

---

## Running it

git clone https://github.com/ambikamishra-dev/wiu-library-chatbot.git
cd wiu-library-chatbot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# configure .env and add your FAQ Excel file to data/

python3 -m uvicorn app.main:app --reload

Or with Docker:

```bash
docker-compose up
```

Demo page at `http://127.0.0.1:8000/api/demo`.

---

## Endpoints

POST /api/chat — incoming query → matched answer or fallback
GET /api/health — liveness check
GET /api/config — returns API base URL for widget initialisation
GET /api/quick-buttons — returns pre-loaded question list for the widget
GET /api/admin/unanswered — [auth required] unanswered query log
GET /api/admin/reload — [auth required] reload FAQ data without restart

Admin endpoints require HTTP Basic Auth. Credentials set via `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env`.

---

## Configuration

All settings live in `.env`. See `.env.example` for the full list. The ones that matter most in production:

`SIMILARITY_THRESHOLD` — how confident the semantic matcher needs to be before returning a match. Currently 0.75. Lower means more matches but higher false-positive risk. Higher means stricter but more fallbacks.

`API_BASE_URL` — the public URL of the deployed backend. The widget fetches this at load time so the JS file never has a hardcoded URL.

`ADMIN_USERNAME` / `ADMIN_PASSWORD` — protect the unanswered log and reload endpoints. Change these before going live.

---

## Tests

```bash
python3 -m pytest tests/ -v
```

68 tests. Covers FAQ loading, keyword and semantic matching, domain scoping, input guardrails, rate limiting, admin authentication, response caching, and API integration end to end.

---

## Embedding on a page

```html
<script src="https://your-server-url/static/js/chatbot.js"></script>
```

One line. The widget loads the CSS, builds the DOM, fetches its configuration from the backend, and initialises — all without touching the host page's existing styles or scripts.

---

## License

MIT — free for institutional use.
