import pytest
import time
from app.core.guardrails import check, RATE_LIMIT_REQUESTS, _rate_limit_store


def setup_function():
    _rate_limit_store.clear()


def test_valid_query_passes():
    result = check("what are the library hours", "127.0.0.1")
    assert result.allowed is True
    assert result.reason is None


def test_empty_query_blocked():
    result = check("", "127.0.0.1")
    assert result.allowed is False
    assert result.reason == "empty_query"


def test_whitespace_only_blocked():
    result = check("   ", "127.0.0.1")
    assert result.allowed is False


def test_too_short_blocked():
    result = check("a", "127.0.0.1")
    assert result.allowed is False
    assert result.reason == "query_too_short"


def test_too_long_blocked():
    result = check("a" * 501, "127.0.0.1")
    assert result.allowed is False
    assert result.reason == "query_too_long"


def test_html_stripped_and_allowed():
    result = check("what are <b>library</b> hours", "127.0.0.1")
    assert result.allowed is True
    assert "<b>" not in result.cleaned_query


def test_script_injection_blocked():
    result = check("<script>alert('xss')</script>", "127.0.0.1")
    assert result.allowed is False
    assert result.reason == "blocked_content"


def test_sql_injection_blocked():
    result = check("SELECT * FROM users", "127.0.0.1")
    assert result.allowed is False
    assert result.reason == "blocked_content"


def test_rate_limit_blocks_after_limit():
    ip = "10.0.0.1"
    for _ in range(RATE_LIMIT_REQUESTS):
        check("library hours", ip)
    result = check("library hours", ip)
    assert result.allowed is False
    assert result.reason == "rate_limited"


def test_rate_limit_different_ips_independent():
    for _ in range(RATE_LIMIT_REQUESTS):
        check("library hours", "10.0.0.2")
    result = check("library hours", "10.0.0.3")
    assert result.allowed is True


def test_cleaned_query_returned():
    result = check("  what are   library hours?  ", "127.0.0.1")
    assert result.allowed is True
    assert result.cleaned_query == "what are library hours?"
