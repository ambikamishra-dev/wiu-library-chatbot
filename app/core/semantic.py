import structlog
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from app.core.loader import FAQEntry
from app.config import settings

log = structlog.get_logger()

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
_model = SentenceTransformer(EMBEDDING_MODEL)


def _build_corpus(entries: list[FAQEntry]) -> tuple[list[str], list[FAQEntry]]:
    texts, mapped = [], []
    for entry in entries:
        for phrasing in [entry.question] + entry.alt_phrasings:
            texts.append(phrasing)
            mapped.append(entry)
    return texts, mapped


def semantic_match(query: str, entries: list[FAQEntry]) -> FAQEntry | None:
    texts, mapped = _build_corpus(entries)
    if not texts:
        return None

    corpus_embeddings = _model.encode(texts, normalize_embeddings=True)
    query_embedding = _model.encode([query], normalize_embeddings=True)
    scores = cosine_similarity(query_embedding, corpus_embeddings)[0]

    best_idx = int(scores.argmax())
    best_score = float(scores[best_idx])

    if best_score >= settings.similarity_threshold:
        match = mapped[best_idx]
        log.info("semantic_match_found", query=query,
                 faq_id=match.faq_id, score=round(best_score, 3))
        return match

    log.info("semantic_match_none", query=query,
             best_score=round(best_score, 3))
    return None
