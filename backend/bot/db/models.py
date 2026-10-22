from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Trend(Base):
    __tablename__ = "trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(40))
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    growth_speed: Mapped[float] = mapped_column(Float, default=0.0)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String(300))
    trend_ids: Mapped[list] = mapped_column(JSON, default=list)
    format: Mapped[str] = mapped_column(String(20))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Post(Base):
    """Status flow: [generating ->] draft -> approved -> published | failed (or rejected)."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    idea_id: Mapped[int | None] = mapped_column(ForeignKey("ideas.id"))
    topic: Mapped[str] = mapped_column(Text)
    format: Mapped[str] = mapped_column(String(20))
    script: Mapped[dict] = mapped_column(JSON)
    caption: Mapped[str] = mapped_column(Text)
    hashtags: Mapped[list] = mapped_column(JSON, default=list)
    collaborators: Mapped[list] = mapped_column(JSON, default=list)
    alt_text: Mapped[str] = mapped_column(Text, default="")
    media_paths: Mapped[list] = mapped_column(JSON, default=list)
    manual_post: Mapped[bool] = mapped_column(Boolean, default=False)
    skill_id: Mapped[str | None] = mapped_column(String(60))
    language: Mapped[str | None] = mapped_column(String(20))
    target_seconds: Mapped[int | None] = mapped_column(Integer)
    # While status is "generating": {"step": ..., "percent": 0-100, "message": ...}
    progress: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ig_media_id: Mapped[str | None] = mapped_column(String(40), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Metric(Base):
    """A point-in-time insights reading for one Instagram media (bot-made or posted by hand)."""

    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ig_media_id: Mapped[str] = mapped_column(String(40), index=True)
    post_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id"), index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reach: Mapped[int | None] = mapped_column(Integer)
    views: Mapped[int | None] = mapped_column(Integer)
    plays: Mapped[int | None] = mapped_column(Integer)
    likes: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[int | None] = mapped_column(Integer)
    saves: Mapped[int | None] = mapped_column(Integer)
    shares: Mapped[int | None] = mapped_column(Integer)
    total_interactions: Mapped[int | None] = mapped_column(Integer)
    avg_watch_time: Mapped[float | None] = mapped_column(Float)


class AccountSnapshot(Base):
    """Daily account totals; followers over time come from this table."""

    __tablename__ = "account_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    followers: Mapped[int] = mapped_column(Integer)
    follows: Mapped[int] = mapped_column(Integer)
    media_count: Mapped[int] = mapped_column(Integer)
    # Totals for the day before taken_at: reach, views, profile_views, accounts_engaged, ...
    day_metrics: Mapped[dict] = mapped_column(JSON, default=dict)


class Skill(Base):
    """A user-created content skill; built-in skills live in config/skills/*.yaml."""

    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    spec: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CollabCandidate(Base):
    __tablename__ = "collab_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True)
    followers: Mapped[int | None] = mapped_column(Integer)
    engagement_rate: Mapped[float | None] = mapped_column(Float)
    niche_overlap: Mapped[float | None] = mapped_column(Float)
    contacted: Mapped[bool] = mapped_column(Boolean, default=False)
