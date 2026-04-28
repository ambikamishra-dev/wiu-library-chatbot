import re
from app.core.loader import FAQEntry
import structlog

log = structlog.get_logger()


def normalize(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower().strip())


def keyword_match(query: str, entries: list[FAQEntry]) -> FAQEntry | None:
    q = normalize(query)
    best_match = None
    best_score = 0

    for entry in entries:
        score = 0

        for kw in entry.keywords:
            if kw in q:
                score += 1

        all_phrasings = [normalize(entry.question)] + [normalize(p)
                                                       for p in entry.alt_phrasings]
        for phrasing in all_phrasings:
            if q == phrasing or q in phrasing or phrasing in q:
                score += 3

        if score > best_score:
            best_score = score
            best_match = entry

    if best_match and best_score > 0:
        log.info("keyword_match_found", query=query,
                 faq_id=best_match.faq_id, score=best_score)
        return best_match

    log.info("keyword_match_none", query=query)
    return None
