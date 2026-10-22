"""Where drafts' media and the generation cache live: the local output/ folder or a bucket.

Locally (media_store="local") media stays in output/ and posts store paths relative to the
project. On Cloud Run (media_store="gcs") the disk is temporary, so finished media is uploaded to
the private studio bucket (posts store gs:// URIs) and each post's working folder (pictures,
voices, video clips) is synced to the bucket so a retry on a fresh machine reuses it.
"""

import logging
import mimetypes
import secrets
from functools import lru_cache
from pathlib import Path

from app.config import PROJECT_ROOT, settings

logger = logging.getLogger(__name__)

OUTPUT_DIR = (PROJECT_ROOT / "output").resolve()
GS = "gs://"


class MediaMissing(Exception):
    pass


def remote() -> bool:
    return settings.media_store == "gcs"


@lru_cache
def _bucket():
    from google.cloud import storage

    return storage.Client(project=settings.google_cloud_project).bucket(settings.studio_bucket)


def _blob_name(uri: str) -> str:
    return uri.removeprefix(f"{GS}{settings.studio_bucket}/")


def store_media(post_id: int, paths: list[Path]) -> list[str]:
    """Persist rendered files and return what to save in post.media_paths."""
    if not remote():
        return [str(p.resolve().relative_to(PROJECT_ROOT.resolve())) for p in paths]
    # A fresh folder per render, so a regenerated post never serves a stale file from cache.
    prefix = f"posts/post-{post_id:04d}/media-{secrets.token_hex(4)}"
    stored = []
    for path in paths:
        blob = _bucket().blob(f"{prefix}/{path.name}")
        blob.upload_from_filename(str(path), content_type=mimetypes.guess_type(path.name)[0])
        stored.append(f"{GS}{settings.studio_bucket}/{blob.name}")
    return stored


def media_exists(stored: str) -> bool:
    if stored.startswith(GS):
        return _bucket().blob(_blob_name(stored)).exists()
    return _local(stored) is not None


def media_bytes(stored: str) -> tuple[bytes, str]:
    content_type = mimetypes.guess_type(stored)[0] or "application/octet-stream"
    if stored.startswith(GS):
        blob = _bucket().blob(_blob_name(stored))
        if not blob.exists():
            raise MediaMissing(stored)
        return blob.download_as_bytes(), content_type
    path = _local(stored)
    if path is None:
        raise MediaMissing(stored)
    return path.read_bytes(), content_type


def local_copies(stored_paths: list[str], scratch: Path) -> list[Path]:
    """Local files for stored media (downloading bucket objects into `scratch`)."""
    paths = []
    for stored in stored_paths:
        if stored.startswith(GS):
            scratch.mkdir(parents=True, exist_ok=True)
            target = scratch / Path(stored).name
            _bucket().blob(_blob_name(stored)).download_to_filename(str(target))
            paths.append(target)
        else:
            path = _local(stored)
            if path is None:
                raise MediaMissing(stored)
            paths.append(path)
    return paths


def pull_work(post_id: int, work_dir: Path) -> None:
    """Restore a post's working folder from the bucket (no-op locally)."""
    if not remote():
        return
    work_dir.mkdir(parents=True, exist_ok=True)
    for blob in _bucket().list_blobs(prefix=_work_prefix(post_id)):
        target = work_dir / blob.name.rsplit("/", 1)[-1]
        if not target.exists():
            blob.download_to_filename(str(target))


def push_work(post_id: int, work_dir: Path) -> None:
    """Save a post's working folder to the bucket so retries reuse it (no-op locally)."""
    if not remote() or not work_dir.is_dir():
        return
    existing = {b.name for b in _bucket().list_blobs(prefix=_work_prefix(post_id))}
    for path in work_dir.iterdir():
        name = f"{_work_prefix(post_id)}{path.name}"
        if path.is_file() and name not in existing:
            _bucket().blob(name).upload_from_filename(str(path))


def _work_prefix(post_id: int) -> str:
    return f"work/post-{post_id:04d}/"


def _local(stored: str) -> Path | None:
    path = (PROJECT_ROOT / stored).resolve()
    return path if path.is_relative_to(OUTPUT_DIR) and path.is_file() else None
