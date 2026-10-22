from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from app.config import PROJECT_ROOT

CONFIG_DIR = PROJECT_ROOT / "config"

PostFormat = Literal["reel", "carousel", "image", "photo", "explainer", "story"]


class Niche(BaseModel):
    name: str
    description: str
    audience: str
    keywords: list[str] = []


class Posting(BaseModel):
    timezone: str = "UTC"
    max_posts_per_day: int = Field(default=2, ge=1, le=10)
    default_times: list[str] = ["09:00", "19:00"]


class Sources(BaseModel):
    hashtags: list[str] = Field(default=[], max_length=30)
    subreddits: list[str] = []
    youtube_queries: list[str] = []
    rss_feeds: list[str] = []
    competitor_accounts: list[str] = []


class ScoringWeights(BaseModel):
    growth_speed: float = 0.35
    competitor_engagement: float = 0.25
    niche_fit: float = 0.20
    hook_strength: float = 0.20


class BotSettings(BaseModel):
    niche: Niche
    posting: Posting = Posting()
    format_mix: dict[PostFormat, float] = {"reel": 0.5, "carousel": 0.35, "image": 0.15}
    sources: Sources = Sources()
    scoring_weights: ScoringWeights = ScoringWeights()


class Colors(BaseModel):
    background: str
    surface: str
    primary: str
    accent: str
    text: str
    muted: str


class Fonts(BaseModel):
    heading: str = "Inter"
    body: str = "Inter"
    heading_file: str | None = None
    body_file: str | None = None


class Voiceover(BaseModel):
    voice: str = "en-IN-Chirp3-HD-Achird"
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0)


class BrandKit(BaseModel):
    brand_name: str
    handle: str
    colors: Colors
    fonts: Fonts = Fonts()
    logo: str | None = None
    voice: str
    banned_words: list[str] = []
    ctas: list[str] = []
    hashtags_always: list[str] = []
    default_collaborators: list[str] = Field(default=[], max_length=3)
    ai_disclosure: str | None = None
    image_style: str = Field(
        default="high quality, sharp focus, well composed", alias="image_finish"
    )
    voiceover: Voiceover = Voiceover()


def load_bot_settings(path: Path = CONFIG_DIR / "settings.yaml") -> BotSettings:
    return BotSettings.model_validate(yaml.safe_load(path.read_text()))


def load_brand_kit(path: Path = CONFIG_DIR / "brand_kit.yaml") -> BrandKit:
    return BrandKit.model_validate(yaml.safe_load(path.read_text()))


def resolve_asset(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_ROOT / candidate
