"""Image-to-video clips for story key moments."""

import logging
import mimetypes
import time
from functools import lru_cache
from pathlib import Path

from google import genai
from google.genai import types

from app.config import settings
from bot.media.ai_images import MediaError

logger = logging.getLogger(__name__)

CLIP_LENGTHS = (4, 6, 8)  # seconds the video model supports
POLL_SECONDS = 10
TIMEOUT_SECONDS = 420


def video_enabled() -> bool:
    return bool(settings.video_model.strip())


def clip_length(seconds_needed: float) -> int:
    """Shortest supported clip that covers the narration (longest clip if none does)."""
    return next((n for n in CLIP_LENGTHS if n >= seconds_needed), CLIP_LENGTHS[-1])


@lru_cache
def _client() -> genai.Client:
    return genai.Client(
        vertexai=True,
        project=settings.google_cloud_project,
        location=settings.video_location,
    )


BUSY_RETRIES = 4
BUSY_WAIT_SECONDS = 60


def animate_image(
    image: Path,
    prompt: str,
    seconds: int,
    out: Path,
    *,
    with_audio: bool = False,
    model: str | None = None,
) -> Path:
    """Turn a still into a short, realistic clip that starts on that exact frame.

    With audio, the clip carries its own sound: ambience, effects and any dialogue written in
    the prompt, spoken with lip sync. Retries when the video service is overloaded."""
    for attempt in range(BUSY_RETRIES):
        try:
            return _animate_once(image, prompt, seconds, out, with_audio, model)
        except _Busy:
            if attempt == BUSY_RETRIES - 1:
                raise MediaError("Video creation is very busy right now.") from None
            logger.warning("Video service busy; retrying in %ss", BUSY_WAIT_SECONDS * (attempt + 1))
            time.sleep(BUSY_WAIT_SECONDS * (attempt + 1))
    raise AssertionError("unreachable")


class _Busy(Exception):
    pass


def _animate_once(
    image: Path, prompt: str, seconds: int, out: Path, with_audio: bool, model: str | None
) -> Path:
    mime = mimetypes.guess_type(image.name)[0] or "image/png"
    sound = "Natural, realistic sound for the scene. No background music." if with_audio else ""
    try:
        operation = _client().models.generate_videos(
            model=model or settings.video_model,
            prompt=(
                f"{prompt}\nRealistic, natural cinematic motion; subtle camera movement; "
                f"keep the subject and setting exactly as in the first frame. {sound}"
            ),
            image=types.Image(image_bytes=image.read_bytes(), mime_type=mime),
            config=types.GenerateVideosConfig(
                aspect_ratio="9:16",
                duration_seconds=seconds,
                resolution=settings.video_resolution,
                number_of_videos=1,
                generate_audio=with_audio,
                negative_prompt="text, captions, subtitles, watermark, logo, distorted faces, "
                "music",
            ),
        )
        deadline = time.monotonic() + TIMEOUT_SECONDS
        while not operation.done:
            if time.monotonic() > deadline:
                raise MediaError("The video clip took too long.")
            time.sleep(POLL_SECONDS)
            operation = _client().operations.get(operation)
    except MediaError:
        raise
    except Exception as exc:
        if any(code in str(exc) for code in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")):
            raise _Busy() from exc
        logger.exception("Video clip generation failed")
        raise MediaError("Couldn't create a video clip.") from exc

    if operation.error:
        logger.error("Video clip generation failed: %s", operation.error)
        if operation.error.get("code") in (8, 14) or "high load" in str(operation.error):
            raise _Busy()
        raise MediaError("Couldn't create a video clip.")
    videos = (operation.response.generated_videos if operation.response else None) or []
    if not videos or not videos[0].video:
        logger.error("Video response had no clip (possibly filtered): %s", operation.response)
        raise MediaError("Couldn't create a video clip.")

    video = videos[0].video
    if video.video_bytes:
        out.write_bytes(video.video_bytes)
    elif video.uri and video.uri.startswith("gs://"):
        from google.cloud import storage

        bucket, _, name = video.uri.removeprefix("gs://").partition("/")
        storage.Client(project=settings.google_cloud_project).bucket(bucket).blob(
            name
        ).download_to_filename(str(out))
    else:
        raise MediaError("Couldn't create a video clip.")
    return out
