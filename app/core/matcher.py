import re
from app.core.loader import FAQEntry
import structlog

log = structlog.get_logger()

# Words too generic to be meaningful library keywords on their own.
# These appear in everyday English and will match non-library queries
# if used as sole keyword triggers.
GENERIC_TERMS = {
    "time", "get", "find", "make", "use",
    "need", "want", "know", "go", "do", "can", "my", "classes", "open"
}


def normalize(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower().strip())


def keyword_match(query: str, entries: list[FAQEntry]) -> FAQEntry | None:
    q = normalize(query)
    best_match = None
    best_score = 0

    for entry in entries:
        score = 0

        for kw in entry.keywords:
            # Skip generic terms — they cause false positives on
            # non-library queries like "what time does the cafeteria open"
            if kw in q and kw not in GENERIC_TERMS:
                score += 1

        all_phrasings = [normalize(entry.question)] + [
            normalize(p) for p in entry.alt_phrasings
        ]
        for phrasing in all_phrasings:
            if q == phrasing or q in phrasing or phrasing in q:
                score += 3

        if score > best_score:
            best_score = score
            best_match = entry

    if best_match and best_score >= 2:
        log.info("keyword_match_found", query=query,
                 faq_id=best_match.faq_id, score=best_score)
        return best_match
