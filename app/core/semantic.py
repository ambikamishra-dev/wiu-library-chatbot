import structlog
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from app.core.loader import FAQEntry
from app.config import settings

log = structlog.get_logger()

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
_model = SentenceTransformer(EMBEDDING_MODEL)

_corpus_cache: dict = {
    "texts": [],
    "embeddings": None,
    "mapped": []
}

# Library domain vocabulary for scope check.
# If query has zero overlap with these terms AND semantic score is below 0.85,
# we reject the match — prevents false positives on out-of-scope queries.
LIBRARY_DOMAIN_TERMS = {
    "library", "malpass", "book", "books", "database", "databases",
    "hours", "close", "renew", "renewal", "reserve", "reserves",
    "print", "printing", "study", "room", "access", "catalog", "ishare",
    "interlibrary", "loan", "article", "articles", "research", "resource",
    "librarian", "checkout", "borrow", "return", "account", "wiu",
    "course", "textbook", "instruction", "classroom", "computer",
    "open", "schedule", "when", "sunday", "saturday", "weekend"
}


# Terms that indicate the query is about a non-library campus facility
# These override a positive domain match
NON_LIBRARY_TERMS = {
    "cafeteria", "cafe", "food", "dining", "restaurant", "parking",
    "gym", "fitness", "recreation", "health", "clinic", "bookstore",
    "financial", "aid", "tuition", "registration", "admissions",
    "dormitory", "dorm", "housing", "shuttle", "bus", "transit"
}


def _is_library_related(query: str) -> bool:
    words = set(query.lower().split())
    # Reject if query contains non-library facility terms
    if words & NON_LIBRARY_TERMS:
        return False
    return bool(words & LIBRARY_DOMAIN_TERMS)


def _build_corpus(entries: list[FAQEntry]) -> tuple[list[str], list[FAQEntry]]:
    texts, mapped = [], []
    for entry in entries:
        for phrasing in [entry.question] + entry.alt_phrasings:
            texts.append(phrasing)
            mapped.append(entry)
    return texts, mapped


def build_corpus_cache(entries: list[FAQEntry]) -> None:
    texts, mapped = _build_corpus(entries)
    embeddings = _model.encode(texts, normalize_embeddings=True)
    _corpus_cache["texts"] = texts
    _corpus_cache["embeddings"] = embeddings
    _corpus_cache["mapped"] = mapped
    log.info("corpus_embeddings_cached", count=len(texts))


def semantic_match(query: str, entries: list[FAQEntry]) -> FAQEntry | None:
    if _corpus_cache["embeddings"] is None:
        build_corpus_cache(entries)

    query_embedding = _model.encode([query], normalize_embeddings=True)
    scores = cosine_similarity(query_embedding, _corpus_cache["embeddings"])[0]

    best_idx = int(scores.argmax())
    best_score = float(scores[best_idx])

    if best_score >= settings.similarity_threshold:
        # Domain scope check — if score is below 0.85 and query has no
        # library-related terms, reject to avoid false positives
        if best_score < 0.90 and not _is_library_related(query):
            log.info("semantic_match_out_of_scope",
                     query=query, score=round(best_score, 3))
            return None
        match = _corpus_cache["mapped"][best_idx]
        log.info("semantic_match_found", query=query,
                 faq_id=match.faq_id, score=round(best_score, 3))
        return match

    log.info("semantic_match_none", query=query,
             best_score=round(best_score, 3))
    return None
