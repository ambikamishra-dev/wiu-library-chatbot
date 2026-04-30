from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, HTTPException, status
import secrets
from app.core.semantic import build_corpus_cache
from app.config import settings
import sqlite3
import structlog
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.core.loader import load_faq
from app.core.matcher import keyword_match
from app.core.semantic import semantic_match
from app.core.guardrails import check


log = structlog.get_logger()
router = APIRouter()
DB_PATH = "logs/unanswered.db"

FALLBACK_RESPONSE = (
    "I'm sorry, I don't have an answer for that yet. "
    "For further assistance please contact the library directly."
)
FALLBACK_URL = "https://www.wiu.edu/libraries/contact.php"
FALLBACK_URL_LABEL = "Contact the Library →"
RATE_LIMITED_RESPONSE = "Too many requests. Please wait a moment before trying again."
BLOCKED_RESPONSE = "Your message could not be processed. Please rephrase your question."

security = HTTPBasic()


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        settings.admin_username.encode("utf8")
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        settings.admin_password.encode("utf8")
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


def init_db():
    import os
    os.makedirs("logs", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS unanswered (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            count INTEGER DEFAULT 1
        )
    """)
    con.commit()
    con.close()


def log_unanswered(query: str):
    con = sqlite3.connect(DB_PATH)
    existing = con.execute(
        "SELECT id FROM unanswered WHERE query = ?", (query,)
    ).fetchone()
    if existing:
        con.execute(
            "UPDATE unanswered SET count = count + 1 WHERE id = ?",
            (existing[0],)
        )
    else:
        con.execute(
            "INSERT INTO unanswered (query, timestamp) VALUES (?, ?)",
            (query, datetime.now(timezone.utc).isoformat())
        )
    con.commit()
    con.close()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    urls: list[dict] = []
    matched: bool
    faq_id: str | None = None


_response_cache: dict[str, ChatResponse] = {}


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    guard = check(req.message, client_ip)

    if not guard.allowed:
        if guard.reason == "rate_limited":
            log.warning("chat_rate_limited", ip=client_ip)
            return ChatResponse(answer=RATE_LIMITED_RESPONSE, matched=False)
        log.warning("chat_blocked", ip=client_ip, reason=guard.reason)
        return ChatResponse(answer=BLOCKED_RESPONSE, matched=False)

    query = guard.cleaned_query

    if query.lower() in _response_cache:
        log.info("chat_cache_hit", query=query, ip=client_ip)
        return _response_cache[query.lower()]

    entries = load_faq()
    match = keyword_match(query, entries) or semantic_match(query, entries)

    if match:
        log.info("chat_matched", faq_id=match.faq_id, ip=client_ip)
        response = ChatResponse(
            answer=match.answer,
            urls=match.urls,
            matched=True,
            faq_id=match.faq_id,
        )
        _response_cache[query.lower()] = response
        return response

    log_unanswered(query)
    log.info("chat_no_match", query=query, ip=client_ip)
    return ChatResponse(
        answer=FALLBACK_RESPONSE,
        urls=[{"url": FALLBACK_URL, "label": FALLBACK_URL_LABEL}],
        matched=False,
    )


@router.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/admin/unanswered")
async def unanswered(credentials: HTTPBasicCredentials = Depends(verify_admin)):
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT query, count, timestamp FROM unanswered ORDER BY count DESC"
    ).fetchall()
    con.close()
    return [{"query": r[0], "count": r[1], "first_seen": r[2]} for r in rows]


@router.get("/admin/reload")
async def reload_faq(credentials: HTTPBasicCredentials = Depends(verify_admin)):
    entries = load_faq(force_reload=True)
    build_corpus_cache(entries)
    _response_cache.clear()
    log.info("faq_reloaded_via_api", count=len(entries))
    return {"status": "reloaded", "count": len(entries)}
