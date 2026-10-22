import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.schemas import ModelTier
from app.services.gemini import GenerationUnavailable
from bot import jobs
from bot.analytics import insights
from bot.db.models import AccountSnapshot, Metric, Post
from bot.db.session import get_session, init_db
from bot.languages import LANGUAGES
from bot.media.ai_images import MediaError
from bot.posts import PostStateError, approve_post, new_post, reject_post, update_post
from bot.publisher.graph_api import InstagramClient, InstagramError
from bot.publisher.publish import publish_post
from bot.skills import SkillError, create_skill, delete_skill, get_skill, list_skills
from bot.storage import MediaMissing, media_bytes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/dashboard", dependencies=[Depends(require_admin)])
DEMOGRAPHICS_MIN_FOLLOWERS = 100


@cache
def _ensure_schema() -> None:
    init_db()


def get_db() -> Iterator[Session]:
    _ensure_schema()
    with get_session() as session:
        yield session


DB = Annotated[Session, Depends(get_db)]


class MetricOut(BaseModel):
    checked_at: datetime
    reach: int | None
    views: int | None
    likes: int | None
    comments: int | None
    saves: int | None
    shares: int | None
    total_interactions: int | None


class PostOut(BaseModel):
    id: int
    topic: str
    format: str
    status: str
    caption: str
    hashtags: list[str]
    collaborators: list[str]
    alt_text: str
    manual_post: bool
    model: str
    media_urls: list[str]
    ig_media_id: str | None
    created_at: datetime
    published_at: datetime | None
    skill_id: str | None = None
    target_seconds: int | None = None
    language: str | None = None
    progress: dict | None = None
    error: str | None = None
    metrics: MetricOut | None = None


class CreatePostIn(BaseModel):
    topic: str = Field(min_length=3, max_length=1000)
    format: Literal["carousel", "image", "photo", "reel", "explainer", "story"] = "carousel"
    model_tier: ModelTier | None = None
    skill_id: str | None = Field(default=None, max_length=60)
    target_seconds: int | None = Field(default=None, ge=20, le=120)
    language: str | None = Field(default=None, max_length=20)


class SkillIn(BaseModel):
    description: str = Field(min_length=10, max_length=1000)


class UpdatePostIn(BaseModel):
    caption: str | None = Field(default=None, min_length=1, max_length=2000)
    hashtags: list[str] | None = Field(default=None, max_length=15)


class ApproveIn(BaseModel):
    collaborators: list[str] = Field(default=[], max_length=3)


@router.get("/overview")
def overview(db: DB):
    counts = dict(db.execute(select(Post.status, func.count()).group_by(Post.status)).all())
    snapshots = db.scalars(
        select(AccountSnapshot).order_by(AccountSnapshot.taken_at.desc()).limit(90)
    ).all()
    profile, quota, error = None, None, None
    try:
        client = InstagramClient()
        profile = insights.fetch_profile(client)
        limit = client.publishing_limit()
        quota = {
            "used": limit.get("quota_usage", 0),
            "total": limit.get("config", {}).get("quota_total", 100),
        }
    except InstagramError as exc:
        error = str(exc)
    return {
        "profile": profile,
        "instagram_error": error,
        "quota": quota,
        "post_counts": counts,
        "last_synced_at": snapshots[0].taken_at if snapshots else None,
        "snapshots": [
            {"taken_at": s.taken_at, "followers": s.followers, **s.day_metrics}
            for s in reversed(snapshots)
        ],
    }


@router.post("/sync")
def sync(db: DB):
    try:
        return insights.sync_insights(db)
    except InstagramError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


@router.get("/content")
def content(db: DB):
    """Recent Instagram media (bot-made or posted by hand) with their latest stored metrics."""
    try:
        media = insights.fetch_recent_media(InstagramClient())
    except InstagramError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    latest = _latest_metrics(db, [m["id"] for m in media])
    post_ids = dict(
        db.execute(
            select(Post.ig_media_id, Post.id).where(Post.ig_media_id.in_([m["id"] for m in media]))
        ).all()
    )
    return [
        {
            **m,
            "post_id": post_ids.get(m["id"]),
            "metrics": _metric_out(latest.get(m["id"])),
        }
        for m in media
    ]


@router.get("/audience")
def audience():
    try:
        client = InstagramClient()
        followers = insights.fetch_profile(client).get("followers_count", 0)
        if followers < DEMOGRAPHICS_MIN_FOLLOWERS:
            return {"followers": followers, "locked": True, "demographics": {}}
        return {
            "followers": followers,
            "locked": False,
            "demographics": insights.fetch_demographics(client),
        }
    except InstagramError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


@router.get("/posts", response_model=list[PostOut])
def list_posts(db: DB, status_filter: str | None = Query(default=None, alias="status")):
    query = select(Post).order_by(Post.id.desc()).limit(100)
    if status_filter:
        query = query.where(Post.status == status_filter)
    posts = db.scalars(query).all()
    _expire_stuck(db, posts)
    latest = _latest_metrics(db, [p.ig_media_id for p in posts if p.ig_media_id])
    return [_post_out(p, latest.get(p.ig_media_id)) for p in posts]


@router.post("/posts", response_model=PostOut, status_code=status.HTTP_202_ACCEPTED)
def create(body: CreatePostIn, db: DB):
    """Start creating a post; it appears with status "generating" and live progress."""
    skill = _skill_or_400(db, body.skill_id)
    if skill and skill.kind != body.format:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That skill is for a different format.")
    if body.language and body.language not in LANGUAGES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That language isn't available.")
    post = new_post(
        db,
        body.topic,
        body.format,
        tier=body.model_tier,
        skill_id=body.skill_id,
        target_seconds=body.target_seconds,
        language=body.language,
    )
    jobs.submit(post.id)
    return _post_out(post)


@router.get("/languages")
def languages():
    return [
        {"code": lang.code, "name": lang.name, "native": lang.native} for lang in LANGUAGES.values()
    ]


@router.get("/skills")
def skills(db: DB):
    return [
        s.model_dump(include={"id", "name", "description", "kind", "default_seconds", "builtin"})
        for s in list_skills(db)
    ]


@router.get("/skills/{skill_id}")
def skill_detail(skill_id: str, db: DB):
    return _skill_or_400(db, skill_id)


@router.post("/skills", status_code=status.HTTP_201_CREATED)
def create_new_skill(body: SkillIn, db: DB):
    try:
        return create_skill(db, body.description)
    except GenerationUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_skill(skill_id: str, db: DB):
    try:
        delete_skill(db, skill_id)
    except SkillError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.patch("/posts/{post_id}", response_model=PostOut)
def update(post_id: int, body: UpdatePostIn, db: DB):
    post = _get_post(db, post_id)
    with _state_errors():
        update_post(db, post, caption=body.caption, hashtags=body.hashtags)
    return _post_out(post)


@router.post("/posts/{post_id}/approve", response_model=PostOut)
def approve(post_id: int, body: ApproveIn, db: DB):
    post = _get_post(db, post_id)
    with _state_errors():
        approve_post(db, post, body.collaborators)
    return _post_out(post)


@router.post("/posts/{post_id}/reject", response_model=PostOut)
def reject(post_id: int, db: DB):
    post = _get_post(db, post_id)
    with _state_errors():
        reject_post(db, post)
    return _post_out(post)


@router.post("/posts/{post_id}/render", response_model=PostOut, status_code=202)
def render(post_id: int, db: DB):
    """Finish a post in the background: write it if writing failed, otherwise (re)make media."""
    post = _get_post(db, post_id)
    if post.status not in ("draft", "failed"):
        raise HTTPException(status.HTTP_409_CONFLICT, "This post can't be regenerated right now.")
    render_only = bool(post.script)
    post.status, post.error = "generating", None
    post.progress = {"step": "queued", "percent": 0, "message": "Waiting to start"}
    db.commit()
    jobs.submit(post.id, render_only=render_only)
    return _post_out(post)


@router.post("/posts/{post_id}/publish", response_model=PostOut)
def publish(post_id: int, db: DB):
    post = _get_post(db, post_id)
    try:
        publish_post(db, post)
    except (InstagramError, MediaError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return _post_out(post)


@router.get("/posts/{post_id}/media/{index}")
def media(post_id: int, index: int, db: DB):
    post = _get_post(db, post_id)
    if not 0 <= index < len(post.media_paths):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This media isn't available.")
    try:
        content, content_type = media_bytes(post.media_paths[index])
    except MediaMissing as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This media isn't available.") from exc
    return Response(
        content, media_type=content_type, headers={"Cache-Control": "private, max-age=3600"}
    )


STUCK_AFTER = timedelta(minutes=75)  # longer than the generation job's own time limit


def _expire_stuck(db: Session, posts: list[Post]) -> None:
    """A job that died (out of memory, timeout) can't report back; let the user retry."""
    cutoff = datetime.now(UTC) - STUCK_AFTER
    stuck = [p for p in posts if p.status == "generating" and _aware(p.updated_at) < cutoff]
    for post in stuck:
        post.status = "draft" if post.script else "failed"
        post.progress = None
        post.error = 'Creation took too long and was stopped. Press "Try again" to finish it.'
    if stuck:
        db.commit()


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _skill_or_400(db: Session, skill_id: str | None):
    try:
        return get_skill(db, skill_id)
    except SkillError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


def _get_post(db: Session, post_id: int) -> Post:
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Post #{post_id} not found.")
    return post


@contextmanager
def _state_errors() -> Iterator[None]:
    try:
        yield
    except PostStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


def _latest_metrics(db: Session, media_ids: list[str]) -> dict[str, Metric]:
    if not media_ids:
        return {}
    newest = (
        select(Metric.ig_media_id, func.max(Metric.id).label("id"))
        .where(Metric.ig_media_id.in_(media_ids))
        .group_by(Metric.ig_media_id)
        .subquery()
    )
    rows = db.scalars(select(Metric).join(newest, Metric.id == newest.c.id)).all()
    return {m.ig_media_id: m for m in rows}


def _metric_out(metric: Metric | None) -> MetricOut | None:
    return MetricOut.model_validate(metric, from_attributes=True) if metric else None


def _post_out(post: Post, metric: Metric | None = None) -> PostOut:
    return PostOut.model_validate(
        {
            **{c: getattr(post, c) for c in PostOut.model_fields if hasattr(post, c)},
            "media_urls": [
                f"/api/v1/dashboard/posts/{post.id}/media/{i}" for i in range(len(post.media_paths))
            ],
            "metrics": _metric_out(metric),
        }
    )
