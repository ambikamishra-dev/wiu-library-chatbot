import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import init_db
from app.core.guardrails import _rate_limit_store

client = TestClient(app)


def setup_function():
    _rate_limit_store.clear()


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_valid_query():
    response = client.post(
        "/api/chat", json={"message": "what are the library hours"})
    assert response.status_code == 200
    data = response.json()
    assert data["matched"] is True
    assert data["faq_id"] == "001"
    assert len(data["answer"]) > 0


def test_chat_returns_urls():
    response = client.post(
        "/api/chat", json={"message": "what are the library hours"})
    data = response.json()
    assert len(data["urls"]) > 0
    assert "url" in data["urls"][0]
    assert "label" in data["urls"][0]


def test_chat_no_match_returns_fallback():
    response = client.post(
        "/api/chat", json={"message": "where can I buy a parking permit"})
    assert response.status_code == 200
    data = response.json()
    assert data["matched"] is False
    assert data["faq_id"] is None
    assert len(data["urls"]) > 0


def test_chat_empty_message_blocked():
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 200
    data = response.json()
    assert data["matched"] is False


def test_chat_too_long_blocked():
    response = client.post("/api/chat", json={"message": "a" * 501})
    assert response.status_code == 200
    data = response.json()
    assert data["matched"] is False


def test_chat_xss_blocked():
    response = client.post(
        "/api/chat", json={"message": "<script>alert('xss')</script>"})
    assert response.status_code == 200
    data = response.json()
    assert data["matched"] is False


def test_chat_sql_injection_blocked():
    response = client.post(
        "/api/chat", json={"message": "SELECT * FROM users"})
    assert response.status_code == 200
    data = response.json()
    assert data["matched"] is False


def test_chat_rate_limited():
    from app.core.guardrails import RATE_LIMIT_REQUESTS
    for _ in range(RATE_LIMIT_REQUESTS):
        client.post("/api/chat", json={"message": "library hours"})
    response = client.post("/api/chat", json={"message": "library hours"})
    assert response.status_code == 200
    assert response.json()["matched"] is False


def test_chat_missing_message_field():
    response = client.post("/api/chat", json={})
    assert response.status_code == 422


def test_unanswered_endpoint_returns_list():
    response = client.get(
        "/api/admin/unanswered",
        auth=("libraryadmin", "wiu_library_2026")
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_reload_endpoint():
    response = client.get(
        "/api/admin/reload",
        auth=("libraryadmin", "wiu_library_2026")
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "reloaded"
    assert data["count"] == 11


def test_reload_rebuilds_corpus_cache():
    from app.core.semantic import _corpus_cache
    response = client.get(
        "/api/admin/reload",
        auth=("libraryadmin", "wiu_library_2026")
    )
    assert response.status_code == 200
    assert _corpus_cache["embeddings"] is not None


def test_unanswered_query_logged_to_db():
    client.post(
        "/api/chat", json={"message": "where can I park my car on campus"})
    response = client.get(
        "/api/admin/unanswered",
        auth=("libraryadmin", "wiu_library_2026")
    )
    queries = [r["query"] for r in response.json()]
    assert any("park" in q for q in queries)


def test_response_cache_hit_on_repeat_query():
    from app.api.routes import _response_cache
    _response_cache.clear()
    client.post("/api/chat", json={"message": "what are the library hours"})
    assert len(_response_cache) > 0
    response = client.post(
        "/api/chat", json={"message": "what are the library hours"})
    assert response.json()["matched"] is True


def test_admin_unanswered_requires_auth():
    response = client.get("/api/admin/unanswered")
    assert response.status_code == 401


def test_admin_reload_requires_auth():
    response = client.get("/api/admin/reload")
    assert response.status_code == 401


def test_admin_wrong_credentials_rejected():
    response = client.get(
        "/api/admin/unanswered",
        auth=("wronguser", "wrongpass")
    )
    assert response.status_code == 401


def test_admin_correct_credentials_accepted():
    response = client.get(
        "/api/admin/unanswered",
        auth=("libraryadmin", "wiu_library_2026")
    )
    assert response.status_code == 200
