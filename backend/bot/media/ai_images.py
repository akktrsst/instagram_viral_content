import logging
import mimetypes
import time
from pathlib import Path
from typing import Literal

from google.genai import types

from app.config import settings
from app.services.gemini import vertex_client

logger = logging.getLogger(__name__)

AspectRatio = Literal["9:16", "3:4", "1:1"]
RETRYABLE = ("RESOURCE_EXHAUSTED", "UNAVAILABLE", "DEADLINE_EXCEEDED", "429", "503", "504")
# Pause before one more pass over all models when every model was rate limited.
QUOTA_COOLDOWN_SECONDS = 45


class MediaError(Exception):
    pass


def generate_image(
    prompt: str,
    aspect_ratio: AspectRatio,
    out_stem: Path,
    look: str,
    quality: str,
    reference: Path | None = None,
) -> Path:
    """Generate one image and save it next to `out_stem`.

    `look` is the post's own visual style (it follows the subject); `quality` is the brand's
    general finish and never overrides the subject or look."""
    full_prompt = (
        f"{prompt}\n" + (f"Look: {look}.\n" if look.strip() else "") + f"Finish: {quality}.\n"
        "Do not include any text, letters, numbers, captions, logos, or watermarks."
    )
    contents: list = [full_prompt]
    if reference is not None and reference.is_file():
        # Characters must match the reference sheet (same faces, hair, clothing).
        contents = [
            types.Part.from_bytes(
                data=reference.read_bytes(),
                mime_type=mimetypes.guess_type(reference.name)[0] or "image/png",
            ),
            "Use the attached reference sheet for the characters' exact appearance; do not copy "
            "its layout or background.\n" + full_prompt,
        ]
    fallbacks = [m.strip() for m in settings.image_fallback_models.split(",") if m.strip()]
    models = list(dict.fromkeys([settings.image_model, *fallbacks]))
    last_error: Exception | None = None
    for attempt in range(2):
        if attempt:
            logger.warning(
                "All image models are rate limited; retrying in %ss", QUOTA_COOLDOWN_SECONDS
            )
            time.sleep(QUOTA_COOLDOWN_SECONDS)
        for model in models:
            try:
                response = vertex_client().models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
                    ),
                )
            except Exception as exc:
                if not any(code in str(exc) for code in RETRYABLE):
                    logger.exception("Image generation with %s failed", model)
                    raise MediaError(
                        "We couldn't create the visuals for this post. Try rewording the brief "
                        "or try again."
                    ) from exc
                logger.warning("Image model %s is busy: %s", model, str(exc)[:120])
                last_error = exc
                continue
            return _save_image(response, out_stem)
    logger.warning("Image generation gave up after rate limits: %s", last_error)
    raise MediaError(
        'Visuals are busy right now. Wait a minute, then press "Generate media" on the draft.'
    ) from last_error


def _save_image(response: types.GenerateContentResponse, out_stem: Path) -> Path:
    for candidate in response.candidates or []:
        for part in (candidate.content.parts if candidate.content else None) or []:
            if part.inline_data and part.inline_data.data:
                suffix = mimetypes.guess_extension(part.inline_data.mime_type or "") or ".png"
                path = out_stem.with_suffix(".jpg" if suffix == ".jpe" else suffix)
                path.write_bytes(part.inline_data.data)
                return path
    logger.warning("Image response contained no image (likely blocked by safety filters)")
    raise MediaError("We couldn't create a picture for part of this post. Try rewording the brief.")
