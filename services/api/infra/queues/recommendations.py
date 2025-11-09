from __future__ import annotations

from functools import lru_cache
from typing import Any

import structlog
from celery import Celery

from infra.config.settings import Settings

TASK_NAME = "services.workers.pipelines.recommendations_flow.calculate_recommendations"
_logger = structlog.get_logger(__name__)

try:  # pragma: no cover
    from services.workers.pipelines.recommendations_flow import (
        enqueue_recommendation_calculation as _worker_enqueue,
    )
except ModuleNotFoundError:  # pragma: no cover
    _worker_enqueue = None


@lru_cache(maxsize=1)
def _build_celery_client(broker: str, backend: str, default_queue: str) -> Celery:
    celery = Celery("nbo-recommendations", broker=broker, backend=backend)
    celery.conf.task_default_queue = default_queue
    return celery


def enqueue_recommendation_calculation(
    *,
    job_id: str,
    customer_id: str,
    channel: str | None,
    variant: str,
    settings: Settings | None = None,
) -> str:
    if _worker_enqueue is not None:
        return _worker_enqueue(
            job_id=job_id,
            customer_id=customer_id,
            channel=channel,
            variant=variant,
        )

    current_settings = settings or Settings()

    celery = _build_celery_client(
        current_settings.celery_broker,
        current_settings.celery_backend,
        current_settings.celery_task_default_queue,
    )
    options: dict[str, Any] = {"task_id": job_id}
    async_result = celery.send_task(
        TASK_NAME,
        kwargs={
            "job_id": job_id,
            "customer_id": customer_id,
            "channel": channel,
            "variant": variant,
        },
        **options,
    )
    _logger.info(
        "recommendations.enqueue.local_client",
        job_id=job_id,
        customer_id=customer_id,
        channel=channel,
        variant=variant,
    )
    return getattr(async_result, "id", job_id)


