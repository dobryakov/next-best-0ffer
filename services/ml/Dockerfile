FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/services/ml:${PYTHONPATH:-}

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        libgomp1 \
        libopenblas-dev \
        liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p services/ml

COPY pyproject.toml services/ml/pyproject.toml
COPY . services/ml

WORKDIR /app/services/ml

RUN pip install --upgrade pip setuptools wheel \
    && pip install -e ".[dev]"

CMD ["python", "-m", "pipelines.run", "--mode=dev"]

