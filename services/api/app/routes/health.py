from __future__ import annotations

import asyncio
import time
from typing import Dict, Literal

import redis.asyncio as redis_asyncio
from celery import Celery
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text

from services.api.infra.config.settings import Settings, get_settings
from services.api.infra.db.session import session_scope
from services.workers.tasks.celery_app import celery_app
from services.workers.tasks.config import HEALTHCHECK_TIMEOUT
from pydantic import BaseModel


class ComponentHealth(BaseModel):
    status: Literal["ok", "error"]
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "error"]
    components: Dict[str, ComponentHealth]


router = APIRouter(prefix="/health", tags=["health"])


async def _check_postgres() -> ComponentHealth:
    start = time.perf_counter()

    try:
        def _query() -> None:
            with session_scope() as session:
                session.execute(text("SELECT 1"))

        await asyncio.to_thread(_query)
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(status="ok", latency_ms=latency)
    except Exception as exc:  # pragma: no cover - health check should never raise
        return ComponentHealth(status="error", detail=str(exc))


async def _check_redis(settings: Settings) -> ComponentHealth:
    start = time.perf_counter()
    client = redis_asyncio.from_url(str(settings.redis_url), encoding="utf-8", decode_responses=True)

    try:
        await client.ping()
        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(status="ok", latency_ms=latency)
    except Exception as exc:  # pragma: no cover - health check should never raise
        return ComponentHealth(status="error", detail=str(exc))
    finally:
        await client.close()


async def _check_celery(app: Celery) -> ComponentHealth:
    start = time.perf_counter()

    try:
        result = await asyncio.to_thread(app.control.ping, timeout=HEALTHCHECK_TIMEOUT)
        if not result:
            return ComponentHealth(status="error", detail="No workers responded")

        latency = (time.perf_counter() - start) * 1000
        return ComponentHealth(status="ok", latency_ms=latency)
    except Exception as exc:  # pragma: no cover - health check should never raise
        return ComponentHealth(status="error", detail=str(exc))


@router.get(
    "",
    summary="Проверка состояния зависимостей сервиса",
    response_model=HealthResponse,
)
async def health_check(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    postgres, redis_state, celery_state = await asyncio.gather(
        _check_postgres(),
        _check_redis(settings),
        _check_celery(celery_app),
    )

    components = {
        "postgres": postgres,
        "redis": redis_state,
        "celery": celery_state,
    }

    if all(component.status == "ok" for component in components.values()):
        overall = "ok"
        http_status = status.HTTP_200_OK
    elif any(component.status == "ok" for component in components.values()):
        overall = "degraded"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        overall = "error"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    payload = HealthResponse(status=overall, components=components)
    response.status_code = http_status
    return payload


