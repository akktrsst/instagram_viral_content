import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from bot.db.models import Post
from bot.publisher.graph_api import InstagramClient, InstagramError
from bot.publisher.storage import upload_media
from bot.storage import local_copies, media_exists
from bot.writer.schemas import VIDEO_FORMATS
from bot.writer.writer import compose_caption

# Instagram can take several minutes to process a reel before it can be published.
REEL_POLL_TIMEOUT = 600.0


def publish_post(session: Session, post: Post, client: InstagramClient | None = None) -> str:
    """Publish an approved post (image, carousel, photo, or reel). Never publishes twice."""
    if post.ig_media_id:
        raise InstagramError("This post is already on Instagram.")
    if post.status != "approved":
        raise InstagramError("Approve this post before publishing it.")
    if post.manual_post:
        raise InstagramError(
            "This reel is marked as needing a trending sound: download it and post it from the "
            "Instagram app so you can add the sound."
        )

    is_reel = post.format in VIDEO_FORMATS
    client = client or InstagramClient(poll_timeout=REEL_POLL_TIMEOUT if is_reel else 300.0)
    _ensure_media(session, post)
    scratch = Path(tempfile.mkdtemp(prefix=f"publish-{post.id}-"))

    post.status = "publishing"
    session.commit()
    try:
        urls = upload_media(local_copies(post.media_paths, scratch), post.id)
        caption = compose_caption(post.caption, post.hashtags)
        if is_reel:
            media_id = client.publish_reel(urls[0], caption, urls[1], post.collaborators)
        else:
            media_id = client.publish_images(urls, caption, post.collaborators)
    except Exception:
        post.status = "failed"
        session.commit()
        raise
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    post.ig_media_id = media_id
    post.status = "published"
    post.published_at = datetime.now(UTC)
    session.commit()
    return media_id


def expected_suffixes(post: Post) -> list[str] | None:
    """Media file types a ready post must have; None means any number of JPEG slides."""
    return [".mp4", ".jpg"] if post.format in VIDEO_FORMATS else None


def _ensure_media(session: Session, post: Post) -> None:
    suffixes = [Path(p).suffix for p in post.media_paths]
    wanted = expected_suffixes(post)
    ready = (
        bool(post.media_paths)
        and (suffixes == wanted if wanted else all(s == ".jpg" for s in suffixes))
        and all(media_exists(p) for p in post.media_paths)
    )
    if not ready:
        # Older drafts were rendered as PNG (or never rendered); re-render from the script.
        from bot.posts import render_media

        render_media(session, post)
