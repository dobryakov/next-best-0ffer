FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app:${PYTHONPATH:-}

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
        libopenblas-dev \
        liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p services/workers

COPY pyproject.toml services/workers/pyproject.toml
COPY . services/workers

WORKDIR /app/services/workers

RUN pip install --upgrade pip setuptools wheel \
    && pip install -e ".[dev]"

CMD ["celery", "-A", "services.workers.tasks.celery_app", "worker", "--loglevel=INFO"]

