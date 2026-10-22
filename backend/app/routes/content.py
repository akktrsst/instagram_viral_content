from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import require_firebase_user
from app.schemas import (
    ContentReview,
    GeneratedContent,
    GenerateRequest,
    ReviewRequest,
)
from app.services.gemini import GenerationUnavailable, generate_content, review_content

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_firebase_user)])


@router.post("/content/generate", response_model=GeneratedContent)
def generate(
    request: GenerateRequest,
    task: Literal["ideas", "caption"] = Query(default="caption"),
):
    try:
        return generate_content(request, task)
    except GenerationUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


@router.post("/content/review", response_model=ContentReview)
def review(request: ReviewRequest):
    try:
        return review_content(request)
    except GenerationUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
