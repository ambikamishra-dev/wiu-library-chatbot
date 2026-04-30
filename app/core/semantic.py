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
        match = _corpus_cache["mapped"][best_idx]
        log.info("semantic_match_found", query=query,
                 faq_id=match.faq_id, score=round(best_score, 3))
        return match

    log.info("semantic_match_none", query=query,
             best_score=round(best_score, 3))
    return None
