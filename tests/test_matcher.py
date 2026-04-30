import pytest
from app.core.loader import load_faq
from app.core.matcher import keyword_match, normalize


@pytest.fixture(scope="session")
def entries():
    return load_faq(force_reload=True)


def test_normalize_lowercase():
    assert normalize(
        "WHEN Does The Library CLOSE?") == "when does the library close"


def test_normalize_strips_punctuation():
    assert normalize("library hours!") == "library hours"


def test_normalize_strips_whitespace():
    assert normalize("  library hours  ") == "library hours"


def test_keyword_match_direct(entries):
    match = keyword_match("when does the library close", entries)
    assert match is not None
    assert match.faq_id == "001"


def test_keyword_match_renew(entries):
    match = keyword_match("how do I renew my books", entries)
    assert match is not None
    assert match.faq_id == "002"


def test_keyword_match_database(entries):
    match = keyword_match("can I access databases from home", entries)
    assert match is not None
    assert match.faq_id == "003"


def test_keyword_match_case_insensitive(entries):
    match = keyword_match("LIBRARY HOURS", entries)
    assert match is not None
    assert match.faq_id == "001"


def test_keyword_match_with_punctuation(entries):
    match = keyword_match("what are the library hours?", entries)
    assert match is not None
    assert match.faq_id == "001"


def test_keyword_match_returns_none_for_no_match(entries):
    match = keyword_match("where can I buy a parking permit", entries)
    assert match is None


def test_keyword_match_returns_highest_score(entries):
    match = keyword_match("when does the library open and close", entries)
    assert match is not None
    assert match.faq_id == "001"
