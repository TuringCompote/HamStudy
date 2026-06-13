# Elmer — single-container image (spec §0.2 / §8). FastAPI + SQLite + vanilla JS.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HAMSTUDY_DB=/app/data/hamstudy.db \
    HAMSTUDY_RECOMMENDATION=/app/data/recommendation.json \
    HAMSTUDY_JOURNAL=/app/data/journal

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code only — DB + secrets + downloaded refs come from mounts/env, not the image.
COPY app ./app
COPY prompts ./prompts
COPY seed ./seed

EXPOSE 8000

# /app/data is a mounted volume (SQLite, recommendation.json, journal/).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
