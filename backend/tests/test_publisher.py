import json
from urllib.parse import parse_qs

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from bot.db.models import Base, Post
from bot.publisher import publish as publish_module
from bot.publisher.graph_api import InstagramClient, InstagramError


class FakeGraph:
    def __init__(self, statuses=("IN_PROGRESS", "FINISHED")):
        self.calls = []
        self.statuses = list(statuses)
        self.next_id = 100

    def handler(self, request: httpx.Request) -> httpx.Response:
        params = (
            dict(request.url.params)
            if request.method == "GET"
            else {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        )
        self.calls.append((request.method, request.url.path, params))
        path = request.url.path
        if path.endswith(("/media", "/media_publish")):
            self.next_id += 1
            return httpx.Response(200, json={"id": str(self.next_id)})
        if request.method == "GET":
            status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
            return httpx.Response(200, json={"status_code": status})
        return httpx.Response(404, json={"error": {"message": "unexpected"}})

    def client(self) -> InstagramClient:
        return InstagramClient(
            user_id="42",
            access_token="token",
            version="v24.0",
            http=httpx.Client(transport=httpx.MockTransport(self.handler)),
            poll_interval=0,
        )


def test_single_image_publish_flow():
    graph = FakeGraph()
    media_id = graph.client().publish_images(["https://x/a.jpg"], "Hello", ["@friend"])

    posts = [c for c in graph.calls if c[0] == "POST"]
    assert posts[0][1] == "/v24.0/42/media"
    assert posts[0][2]["image_url"] == "https://x/a.jpg"
    assert json.loads(posts[0][2]["collaborators"]) == ["friend"]
    assert posts[-1][1] == "/v24.0/42/media_publish"
    assert media_id == "102"


def test_carousel_creates_children_then_parent():
    graph = FakeGraph(statuses=("FINISHED",))
    graph.client().publish_images(["https://x/1.jpg", "https://x/2.jpg"], "Cap")

    creates = [c[2] for c in graph.calls if c[1].endswith("/media")]
    assert [c.get("is_carousel_item") for c in creates[:2]] == ["true", "true"]
    assert creates[2]["media_type"] == "CAROUSEL"
    assert creates[2]["children"] == "101,102"
    assert "caption" not in creates[0]


def test_container_error_raises():
    graph = FakeGraph(statuses=("ERROR",))
    with pytest.raises(InstagramError, match="couldn't process"):
        graph.client().publish_images(["https://x/a.jpg"], "Hello")


def _client_returning(error: dict) -> InstagramClient:
    def handler(request):
        return httpx.Response(400, json={"error": error})

    return InstagramClient(
        user_id="1", access_token="t", http=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_instagram_user_message_is_shown():
    client = _client_returning(
        {"message": "(#100) bad param", "error_user_msg": "Caption too long"}
    )
    with pytest.raises(InstagramError, match="^Caption too long$"):
        client.account()


def test_developer_error_details_stay_out_of_the_message():
    with pytest.raises(InstagramError) as raised:
        _client_returning({"message": "(#100) Invalid parameter", "code": 100}).account()
    assert "#100" not in str(raised.value)
    assert "try again" in str(raised.value)


def test_expired_connection_asks_for_renewal():
    with pytest.raises(InstagramError, match="renewed"):
        _client_returning({"message": "Invalid OAuth access token", "code": 190}).account()


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_post(session, **overrides) -> Post:
    data = {"topic": "t", "format": "image", "script": {}, "caption": "c", "model": "m"}
    post = Post(**{**data, **overrides})
    session.add(post)
    session.commit()
    return post


def test_publish_requires_approval(session):
    post = make_post(session)
    with pytest.raises(InstagramError, match="Approve"):
        publish_module.publish_post(session, post, client=FakeGraph().client())


def test_publish_never_republishes(session):
    post = make_post(session, status="approved", ig_media_id="999")
    with pytest.raises(InstagramError, match="already on Instagram"):
        publish_module.publish_post(session, post, client=FakeGraph().client())


def test_publish_marks_post_published(session, monkeypatch, tmp_path):
    image = tmp_path / "slide.jpg"
    image.write_bytes(b"jpeg")
    monkeypatch.setattr(publish_module, "_ensure_media", lambda s, p: None)
    monkeypatch.setattr(publish_module, "local_copies", lambda stored, scratch: [image])
    monkeypatch.setattr(publish_module, "upload_media", lambda paths, post_id: ["https://x/s.jpg"])
    post = make_post(session, status="approved", hashtags=["#a"], collaborators=[])

    media_id = publish_module.publish_post(session, post, client=FakeGraph().client())

    assert post.status == "published"
    assert post.ig_media_id == media_id
    assert post.published_at is not None


def test_publish_failure_marks_post_failed(session, monkeypatch, tmp_path):
    monkeypatch.setattr(publish_module, "_ensure_media", lambda s, p: None)
    monkeypatch.setattr(
        publish_module, "local_copies", lambda stored, scratch: [tmp_path / "a.jpg"]
    )
    monkeypatch.setattr(publish_module, "upload_media", lambda paths, post_id: ["https://x/s.jpg"])
    post = make_post(session, status="approved")

    with pytest.raises(InstagramError):
        publish_module.publish_post(session, post, client=FakeGraph(statuses=("ERROR",)).client())
    assert post.status == "failed"
    assert post.ig_media_id is None


def test_reel_publishes_video_with_cover(session, monkeypatch, tmp_path):
    files = [tmp_path / "video.mp4", tmp_path / "cover.jpg"]
    monkeypatch.setattr(publish_module, "_ensure_media", lambda s, p: None)
    monkeypatch.setattr(publish_module, "local_copies", lambda stored, scratch: files)
    monkeypatch.setattr(
        publish_module,
        "upload_media",
        lambda paths, post_id: [f"https://x/{p.name}" for p in paths],
    )
    graph = FakeGraph(statuses=("FINISHED",))
    post = make_post(session, format="reel", status="approved")

    publish_module.publish_post(session, post, client=graph.client())

    (create,) = [c[2] for c in graph.calls if c[1].endswith("/media")]
    assert create["media_type"] == "REELS"
    assert create["video_url"] == "https://x/video.mp4"
    assert create["cover_url"] == "https://x/cover.jpg"
    assert post.status == "published"


def test_trending_sound_reel_is_not_auto_published(session):
    post = make_post(session, format="reel", status="approved", manual_post=True)
    with pytest.raises(InstagramError, match="trending sound"):
        publish_module.publish_post(session, post, client=FakeGraph().client())
