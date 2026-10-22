"""Post lifecycle shared by the CLI and the dashboard API."""

import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT, settings
from app.schemas import ModelTier
from app.services.gemini import model_for_tier
from bot.db.models import Post
from bot.settings import PostFormat, load_brand_kit
from bot.skills import get_skill
from bot.storage import store_media
from bot.writer.schemas import load_draft
from bot.writer.story import Progress, write_story
from bot.writer.writer import (
    compose_caption,
    is_manual_post,
    normalize_hashtags,
    write_post,
)

OUTPUT_DIR = PROJECT_ROOT / "output"
EDITABLE_STATUSES = ("draft", "failed")
MAX_COLLABORATORS = 3


class PostStateError(Exception):
    pass


def new_post(
    session: Session,
    topic: str,
    fmt: PostFormat,
    *,
    tier: ModelTier | None = None,
    skill_id: str | None = None,
    target_seconds: int | None = None,
    language: str | None = None,
) -> Post:
    """Save a placeholder post (status "generating") that generate_post fills in."""
    skill = get_skill(session, skill_id)
    if fmt == "story":
        target_seconds = target_seconds or (skill.default_seconds if skill else 60)
    post = Post(
        topic=topic,
        format=fmt,
        script={},
        caption="",
        model=model_for_tier(tier) or settings.gemini_model,
        status="generating",
        skill_id=skill.id if skill else None,
        target_seconds=target_seconds,
        language=language,
        progress={"step": "queued", "percent": 0, "message": "Waiting to start"},
    )
    session.add(post)
    session.commit()
    return post


def generate_post(
    session: Session,
    post: Post,
    *,
    tier: ModelTier | None = None,
    render: bool = True,
    progress: Progress | None = None,
) -> Post:
    """Write the post (and render its media) into an existing placeholder."""
    report = progress or (lambda *_: None)
    skill = get_skill(session, post.skill_id)
    if post.format == "story":
        draft = write_story(
            post.topic,
            post.target_seconds or 60,
            skill=skill,
            tier=tier,
            language=post.language,
            progress=report,
        )
    else:
        report("writing", 10, "Writing the post")
        draft = write_post(post.topic, post.format, tier=tier, skill=skill, language=post.language)
    post.script = draft.model_dump()
    post.caption = draft.caption
    post.hashtags = draft.hashtags
    post.collaborators = draft.suggested_collaborators
    post.alt_text = draft.alt_text
    post.manual_post = is_manual_post(draft)
    session.commit()

    out_dir = post_dir(post)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "caption.txt").write_text(compose_caption(draft.caption, draft.hashtags) + "\n")
    (out_dir / "script.json").write_text(draft.model_dump_json(indent=2))
    if render:
        render_media(session, post, progress=report)
    post.status = "draft"
    post.progress = None
    post.error = None
    session.commit()
    return post


def create_post(
    session: Session,
    topic: str,
    fmt: PostFormat,
    *,
    tier: ModelTier | None = None,
    render: bool = True,
    skill_id: str | None = None,
    target_seconds: int | None = None,
    language: str | None = None,
    progress: Progress | None = None,
) -> Post:
    """Write and render a post in one go (used by the CLI)."""
    post = new_post(
        session,
        topic,
        fmt,
        tier=tier,
        skill_id=skill_id,
        target_seconds=target_seconds,
        language=language,
    )
    try:
        return generate_post(session, post, tier=tier, render=render, progress=progress)
    except Exception as exc:
        post.status = "draft" if post.script else "failed"
        post.progress = None
        post.error = str(exc)
        session.commit()
        raise


def post_dir(post: Post) -> Path:
    return OUTPUT_DIR / f"post-{post.id:04d}-{_slug(post.topic)}"


def render_media(session: Session, post: Post, progress: Progress | None = None) -> Post:
    """(Re)render a post's images or video from its stored script.

    Videos reuse pictures, voiceovers and clips left by an earlier, interrupted attempt."""
    _require_status(post, (*EDITABLE_STATUSES, "approved", "generating"), "rendered")
    draft = load_draft(post.format, post.script)
    if post.format == "story":
        from bot.media.story_video import render_story

        paths = render_story(draft, post_dir(post), progress=progress, language=post.language)
    else:
        from bot.media.render import render_post

        if progress:
            progress("rendering", 60, "Creating the visuals")
        paths = render_post(draft, post_dir(post), language=post.language)
    post.media_paths = store_media(post.id, paths)
    session.commit()
    return post


def update_post(
    session: Session, post: Post, *, caption: str | None = None, hashtags: list[str] | None = None
) -> Post:
    _require_status(post, EDITABLE_STATUSES, "edited")
    if caption is not None:
        post.caption = caption.strip()
    if hashtags is not None:
        post.hashtags = normalize_hashtags(hashtags)[:15]
    session.commit()
    return post


def approve_post(session: Session, post: Post, collaborators: list[str] | None = None) -> Post:
    """Approve for publishing. Only explicitly listed collaborators (or brand defaults) are invited,
    never Gemini's suggestions."""
    _require_status(post, EDITABLE_STATUSES, "approved")
    chosen = collaborators if collaborators else load_brand_kit().default_collaborators
    post.collaborators = [c.strip().lstrip("@") for c in chosen if c.strip()][:MAX_COLLABORATORS]
    post.status = "approved"
    session.commit()
    return post


def reject_post(session: Session, post: Post) -> Post:
    if post.status in ("published", "publishing", "generating"):
        raise PostStateError(f"Post #{post.id} is {post.status} and can't be rejected.")
    post.status = "rejected"
    session.commit()
    return post


def _require_status(post: Post, allowed: tuple[str, ...], action: str) -> None:
    if post.status not in allowed:
        raise PostStateError(f"Post #{post.id} is '{post.status}' and can't be {action}.")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "post"
