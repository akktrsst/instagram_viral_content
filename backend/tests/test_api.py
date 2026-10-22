import pytest
from fastapi.testclient import TestClient

from app.auth import require_firebase_user
from app.main import app


@pytest.fixture
def authenticated_client():
    app.dependency_overrides[require_firebase_user] = lambda: {"uid": "test-user"}
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_live_healthcheck():
    response = TestClient(app).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_rejects_invalid_task(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/content/generate?task=unknown",
        json={"topic": "coffee"},
    )
    assert response.status_code == 422


def test_generate_validates_topic(authenticated_client):
    response = authenticated_client.post("/api/v1/content/generate", json={"topic": "x"})
    assert response.status_code == 422


def test_review_validates_caption(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/content/review",
        json={"topic": "coffee", "caption": "", "hashtags": []},
    )
    assert response.status_code == 422


def test_generate_validates_model_tier(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/content/generate",
        json={"topic": "coffee rituals", "model_tier": "ultra"},
    )
    assert response.status_code == 422


def test_auth_routes_reject_missing_bearer_token():
    response = TestClient(app).post(
        "/api/v1/content/generate",
        json={"topic": "coffee rituals"},
    )
    assert response.status_code == 401
