import secrets
from pathlib import Path

from app.config import settings

CONTENT_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".mp4": "video/mp4"}


def upload_media(paths: list[Path], post_id: int) -> list[str]:
    """Upload files to the public media bucket and return their URLs.

    Instagram fetches media from these URLs, so the bucket is public-read; the random path
    segment keeps URLs unguessable and the bucket's lifecycle rule deletes files after 30 days.
    """
    from google.cloud import storage

    bucket = storage.Client(project=settings.google_cloud_project).bucket(settings.media_bucket)
    prefix = f"posts/{post_id}-{secrets.token_urlsafe(12)}"
    urls = []
    for path in paths:
        blob = bucket.blob(f"{prefix}/{path.name}")
        blob.upload_from_filename(str(path), content_type=CONTENT_TYPES.get(path.suffix.lower()))
        urls.append(f"https://storage.googleapis.com/{bucket.name}/{blob.name}")
    return urls
