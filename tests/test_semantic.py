import pytest
from app.core.loader import load_faq
from app.core.semantic import (
    semantic_match,
    build_corpus_cache,
    _corpus_cache,
)


@pytest.fixture(scope="session")
def entries():
    return load_faq(force_reload=True)


@pytest.fixture(autouse=True)
def reset_cache():
    _corpus_cache["texts"] = []
    _corpus_cache["embeddings"] = None
    _corpus_cache["mapped"] = []
    yield


def test_corpus_cache_populated_after_build(entries):
    build_corpus_cache(entries)
    assert _corpus_cache["embeddings"] is not None
    assert len(_corpus_cache["texts"]) > 0
    assert len(_corpus_cache["mapped"]) == len(_corpus_cache["texts"])


def test_corpus_cache_count_matches_phrasings(entries):
    build_corpus_cache(entries)
    expected = sum(1 + len(e.alt_phrasings) for e in entries)
    assert len(_corpus_cache["texts"]) == expected


def test_semantic_match_paraphrase(entries):
    match = semantic_match("is the library still open right now", entries)
    assert match is not None
    assert match.faq_id == "001"


def test_semantic_match_returns_none_below_threshold(entries):
    match = semantic_match("what is the meaning of life", entries)
    assert match is None


def test_semantic_match_remote_access(entries):
    match = semantic_match(
        "how do I get into the library website from my apartment", entries)
    assert match is not None
    assert match.faq_id in ("003", "009")


def test_semantic_match_offcampus_database(entries):
    match = semantic_match(
        "how do I access library resources when I am not on campus", entries)
    assert match is not None
    assert match.faq_id == "003"


def test_semantic_match_builds_cache_if_empty(entries):
    assert _corpus_cache["embeddings"] is None
    match = semantic_match("library hours", entries)
    assert _corpus_cache["embeddings"] is not None


def test_semantic_match_timeout(entries, monkeypatch):
    """
    If embedding raises TimeoutError, semantic_match returns None
    instead of hanging the request indefinitely.
    """
    import concurrent.futures
    from app.core import semantic

    # Build corpus cache first with real model
    build_corpus_cache(entries)

    # Now patch encode to simulate timeout on query embedding only
    def timeout_encode(*args, **kwargs):
        raise concurrent.futures.TimeoutError()

    monkeypatch.setattr(semantic._model, "encode", timeout_encode)

    match = semantic_match("what are the library hours", entries)
    assert match is None
