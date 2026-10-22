# Studio API and generation jobs (one image; Cloud Run service and Cloud Run Job).
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Noto fonts so Devanagari, Tamil, Bengali, Gurmukhi, Urdu... render on slides and captions.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       fonts-noto-core fonts-noto-ui-core fonts-noto-color-emoji fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/app backend/app
COPY backend/bot backend/bot
# Editable install keeps the code in /srv/backend so it finds /srv/config and /srv/assets.
RUN pip install -e ./backend \
    && python -m playwright install --with-deps chromium \
    && python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"

COPY config config
COPY assets assets
RUN mkdir -p output

WORKDIR /srv/backend
ENV PORT=8080
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
