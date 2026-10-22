import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import require_firebase_user
from app.config import settings
from app.main import app
from app.routes.dashboard import get_db
from bot.db.models import Base, Post

ADMIN = {"uid": "a", "email": "owner@example.com", "email_verified": True}


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", "owner@example.com")
    monkeypatch.delenv("FIREBASE_AUTH_EMULATOR_HOST", raising=False)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        app.dependency_overrides[get_db] = lambda: session
        yield session
    app.dependency_overrides.clear()


def client_as(user: dict) -> TestClient:
    app.dependency_overrides[require_firebase_user] = lambda: user
    return TestClient(app)


def add_post(db, **overrides) -> Post:
    data = {"topic": "t", "format": "carousel", "script": {}, "caption": "c", "model": "m"}
    post = Post(**{**data, **overrides})
    db.add(post)
    db.commit()
    return post


def test_non_admin_is_forbidden(db):
    response = client_as({**ADMIN, "email": "someone@else.com"}).get("/api/v1/dashboard/posts")
    assert response.status_code == 403


def test_unverified_admin_email_is_forbidden(db):
    response = client_as({**ADMIN, "email_verified": False}).get("/api/v1/dashboard/posts")
    assert response.status_code == 403
    assert response.json()["detail"] == "EMAIL_NOT_VERIFIED"


def test_admin_lists_posts_with_media_urls(db):
    add_post(db, media_paths=["output/x/slide_01.jpg", "output/x/slide_02.jpg"])
    response = client_as(ADMIN).get("/api/v1/dashboard/posts")
    assert response.status_code == 200
    (post,) = response.json()
    assert post["media_urls"] == [
        f"/api/v1/dashboard/posts/{post['id']}/media/0",
        f"/api/v1/dashboard/posts/{post['id']}/media/1",
    ]


def test_media_outside_output_dir_is_refused(db):
    post = add_post(db, media_paths=["backend/app/config.py"])
    response = client_as(ADMIN).get(f"/api/v1/dashboard/posts/{post.id}/media/0")
    assert response.status_code == 404


def test_edit_and_approve_flow(db):
    post = add_post(db, collaborators=["gemini_guess"])
    client = client_as(ADMIN)

    edited = client.patch(
        f"/api/v1/dashboard/posts/{post.id}", json={"caption": "New", "hashtags": ["AI Tools"]}
    )
    assert edited.json()["caption"] == "New"
    assert edited.json()["hashtags"] == ["#aitools"]

    approved = client.post(f"/api/v1/dashboard/posts/{post.id}/approve", json={})
    assert approved.json()["status"] == "approved"
    assert approved.json()["collaborators"] == []

    conflict = client.patch(f"/api/v1/dashboard/posts/{post.id}", json={"caption": "Again"})
    assert conflict.status_code == 409


def test_published_post_cannot_be_rejected(db):
    post = add_post(db, status="published", ig_media_id="1")
    response = client_as(ADMIN).post(f"/api/v1/dashboard/posts/{post.id}/reject")
    assert response.status_code == 409


def test_create_post_starts_background_generation(db, monkeypatch):
    from bot import jobs

    started = []
    monkeypatch.setattr(jobs, "submit", lambda post_id, render_only=False: started.append(post_id))
    response = client_as(ADMIN).post(
        "/api/v1/dashboard/posts",
        json={
            "topic": "A ghost in the library",
            "format": "story",
            "skill_id": "horror-story",
            "target_seconds": 45,
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "generating"
    assert body["target_seconds"] == 45 and body["skill_id"] == "horror-story"
    assert started == [body["id"]]


def test_skill_must_match_format(db):
    response = client_as(ADMIN).post(
        "/api/v1/dashboard/posts",
        json={"topic": "A ghost story", "format": "carousel", "skill_id": "horror-story"},
    )
    assert response.status_code == 400


def test_unknown_language_is_rejected(db):
    response = client_as(ADMIN).post(
        "/api/v1/dashboard/posts",
        json={"topic": "A story", "format": "story", "language": "klingon"},
    )
    assert response.status_code == 400


def test_languages_include_hindi_and_bhojpuri(db):
    codes = {lang["code"] for lang in client_as(ADMIN).get("/api/v1/dashboard/languages").json()}
    assert {"hi", "bho", "hinglish", "en-IN"} <= codes


def test_posts_stuck_generating_are_released(db):
    from datetime import UTC, datetime, timedelta

    old = datetime.now(UTC) - timedelta(hours=2)
    add_post(db, status="generating", script={}, updated_at=old)
    (post,) = client_as(ADMIN).get("/api/v1/dashboard/posts").json()
    assert post["status"] == "failed"
    assert "Try again" in post["error"]


def test_estimate_shows_movie_costs_more(db):
    client = client_as(ADMIN)
    movie = client.get("/api/v1/dashboard/estimate?style=movie&seconds=120").json()
    cine = client.get("/api/v1/dashboard/estimate?style=cinematic&seconds=120").json()
    assert movie["usd"] > cine["usd"] > 0 and movie["minutes"] > 0
