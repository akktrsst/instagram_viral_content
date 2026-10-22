import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.content import router as content_router
from app.routes.dashboard import router as dashboard_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # With Cloud Run Jobs, generation outlives API restarts, so only recover in-process runs.
    if settings.app_env != "test" and settings.job_runner == "thread":
        from bot.jobs import recover_interrupted

        try:
            if count := recover_interrupted():
                logger.warning("Marked %s interrupted posts for retry", count)
        except Exception:
            logger.exception("Could not check for interrupted posts")
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.frontend_origin.split(",") if o.strip()],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(content_router)
app.include_router(dashboard_router)


@app.get("/health/live", tags=["health"])
def live():
    return {"status": "ok"}
