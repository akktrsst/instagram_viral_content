"""Background generation so long videos don't block a web request."""

import logging
from concurrent.futures import ThreadPoolExecutor

from app.config import settings
from app.services.gemini import GenerationUnavailable
from bot.db.models import Post
from bot.db.session import get_session
from bot.media.ai_images import MediaError
from bot.posts import generate_post, post_dir, render_media
from bot.skills import SkillError
from bot.storage import pull_work, push_work

logger = logging.getLogger(__name__)

# Two at a time: image and video models have small per-minute quotas.
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="generate")
FRIENDLY_ERRORS = (GenerationUnavailable, MediaError, SkillError)
INTERRUPTED = 'Creation was interrupted. Press "Try again" to finish it.'


def submit(post_id: int, *, render_only: bool = False) -> None:
    if settings.job_runner == "cloudrun":
        _start_cloud_run_job(post_id, render_only)
    else:
        _pool.submit(run, post_id, render_only)


def _start_cloud_run_job(post_id: int, render_only: bool) -> None:
    """One Cloud Run Job execution per post: CPU for as long as it takes, billed only then."""
    from google.cloud import run_v2

    args = ["-m", "bot", "run-job", str(post_id)] + (["--render-only"] if render_only else [])
    name = run_v2.JobsClient.job_path(
        settings.google_cloud_project, settings.cloud_region, settings.generate_job
    )
    run_v2.JobsClient().run_job(
        request=run_v2.RunJobRequest(
            name=name,
            overrides=run_v2.RunJobRequest.Overrides(
                container_overrides=[run_v2.RunJobRequest.Overrides.ContainerOverride(args=args)]
            ),
        )
    )


def run(post_id: int, render_only: bool = False) -> None:
    """Write and/or render one post, recording progress and a friendly error on failure."""
    with get_session() as session:
        post = session.get(Post, post_id)
        if post is None:
            return
        work_dir = post_dir(post) / "reel_work"
        pull_work(post_id, work_dir)

        def progress(step: str, percent: int, message: str) -> None:
            post.progress = {"step": step, "percent": percent, "message": message}
            session.commit()

        try:
            if render_only:
                render_media(session, post, progress=progress)
                post.status, post.progress, post.error = "draft", None, None
                session.commit()
            else:
                generate_post(session, post, progress=progress)
        except Exception as exc:
            push_work(post_id, work_dir)
            if isinstance(exc, FRIENDLY_ERRORS):
                logger.warning("Post %s generation failed: %s", post_id, exc)
                message = str(exc)
            else:
                logger.exception("Post %s generation crashed", post_id)
                message = "Something went wrong while creating this post. Please try again."
            session.rollback()
            post = session.get(Post, post_id)
            # Text that was written is kept, so "Try again" only redoes what's missing.
            post.status = "draft" if post.script else "failed"
            post.progress = None
            post.error = message
            session.commit()
        else:
            push_work(post_id, work_dir)


def recover_interrupted() -> int:
    """Mark posts left "generating" by a previous server run as needing a retry."""
    with get_session() as session:
        stuck = session.query(Post).filter(Post.status == "generating").all()
        for post in stuck:
            post.status = "draft" if post.script else "failed"
            post.progress = None
            post.error = INTERRUPTED
        session.commit()
        return len(stuck)
