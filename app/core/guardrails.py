import re
import time
import structlog
from collections import defaultdict
from dataclasses import dataclass

log = structlog.get_logger()

MAX_QUERY_LENGTH = 500
MIN_QUERY_LENGTH = 2
RATE_LIMIT_REQUESTS = 20
RATE_LIMIT_WINDOW = 60

BLOCKED_PATTERNS = [
    r"<script",
    r"javascript:",
    r"on\w+\s*=",
    r"(drop|delete|insert|select|update)\s+",
]

_rate_limit_store: dict[str, list[float]] = defaultdict(list)


@dataclass
class GuardrailResult:
    allowed: bool
    cleaned_query: str
    reason: str | None = None


def check(query: str, client_ip: str = "unknown") -> GuardrailResult:
    if not query or not query.strip():
        return GuardrailResult(allowed=False, cleaned_query="", reason="empty_query")

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            log.warning("guardrail_blocked_pattern",
                        ip=client_ip, pattern=pattern)
            return GuardrailResult(allowed=False, cleaned_query=query, reason="blocked_content")

    cleaned = re.sub(r"<[^>]+>", "", query)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) < MIN_QUERY_LENGTH:
        log.warning("guardrail_too_short", ip=client_ip, length=len(cleaned))
        return GuardrailResult(allowed=False, cleaned_query=cleaned, reason="query_too_short")

    if len(cleaned) > MAX_QUERY_LENGTH:
        log.warning("guardrail_too_long", ip=client_ip, length=len(cleaned))
        return GuardrailResult(allowed=False, cleaned_query=cleaned, reason="query_too_long")

    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if t > window_start
    ]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
        log.warning("guardrail_rate_limited", ip=client_ip)
        return GuardrailResult(allowed=False, cleaned_query=cleaned, reason="rate_limited")

    _rate_limit_store[client_ip].append(now)
    return GuardrailResult(allowed=True, cleaned_query=cleaned)
