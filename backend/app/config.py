from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Viral Content Studio"
    app_env: str = "development"
    # Comma-separated origins allowed to call the API from a browser.
    frontend_origin: str = "http://localhost:5173"
    # Comma-separated emails allowed to use the dashboard (approve/publish/insights).
    admin_emails: str = ""
    google_cloud_project: str = "instagram-viral-content-a8eba"
    google_cloud_location: str = "global"
    gemini_model_lite: str = "gemini-3.5-flash-lite"
    gemini_model: str = "gemini-3.8-flash"
    gemini_model_pro: str = "gemini-3.1-pro-preview"
    embedding_model: str = "gemini-embedding-2"
    image_model: str = "gemini-3.1-flash-image"
    # Tried in order when the image model is rate limited or overloaded.
    image_fallback_models: str = "gemini-nano-banana-2.1"
    # Real video clips for story key moments (image-to-video). Leave VIDEO_MODEL empty to use
    # moving stills only; failures always fall back to stills.
    video_model: str = "veo-3.1-lite-generate-001"
    video_location: str = "us-central1"
    video_resolution: str = "1080p"
    video_clips_per_story: int = 2
    # "Movie" style: every shot is a generated clip with its own sound and lip-synced dialogue.
    movie_video_model: str = "veo-3.1-fast-generate-001"
    movie_price_per_second: float = 0.12  # shown to users as an estimate before they create
    cinematic_price_per_second: float = 0.03
    # Tried in order when a model is overloaded (429/503/504).
    gemini_fallback_models: str = "gemini-3.7-flash,gemini-3.5-flash"

    # Bot database. CLOUDSQL_INSTANCE ("project:region:instance") switches from local SQLite
    # to Cloud SQL Postgres via the Cloud SQL Python Connector.
    database_url: str | None = None
    cloudsql_instance: str | None = None
    db_name: str = "viral_content"
    db_user: str = "bot"
    db_password: str | None = None

    # Instagram publishing (Instagram API with Instagram Login) and the public media bucket.
    ig_user_id: str | None = None
    ig_access_token: str | None = None
    ig_graph_version: str = "v24.0"
    media_bucket: str = "instagram-viral-content-a8eba-media"

    # Where drafts' media and the resume cache live: "local" (output/ folder) or "gcs" (the
    # private studio bucket; needed on Cloud Run, whose disk is temporary).
    media_store: str = "local"
    studio_bucket: str = "instagram-viral-content-a8eba-studio"
    # How generation runs: "thread" (in this process) or "cloudrun" (one Cloud Run Job per post).
    job_runner: str = "thread"
    generate_job: str = "studio-generate"
    cloud_region: str = "us-central1"

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
