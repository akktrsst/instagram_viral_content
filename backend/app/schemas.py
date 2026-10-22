from typing import Literal

from pydantic import BaseModel, Field

ModelTier = Literal["lite", "standard", "pro"]


class GenerateRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    platform: str = Field(default="Instagram", min_length=2, max_length=40)
    tone: str = Field(default="engaging", min_length=2, max_length=60)
    goal: str = Field(default="increase saves and shares", max_length=200)
    model_tier: ModelTier | None = None


class GeneratedContent(BaseModel):
    title: str = Field(max_length=160)
    caption: str = Field(max_length=2200)
    hashtags: list[str] = Field(max_length=15)


class ReviewRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    platform: str = Field(default="Instagram", min_length=2, max_length=40)
    tone: str = Field(default="engaging", min_length=2, max_length=60)
    caption: str = Field(min_length=1, max_length=2200)
    hashtags: list[str] = Field(max_length=15)
    model_tier: ModelTier | None = None


class ContentReview(BaseModel):
    score: int = Field(ge=1, le=100)
    summary: str = Field(max_length=500)
    strengths: list[str] = Field(max_length=5)
    improvements: list[str] = Field(max_length=5)
