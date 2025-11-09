from __future__ import annotations

from time import perf_counter

import structlog
from celery import Task

from services.workers.tasks.celery_app import celery_app
from services.workers.tasks.metrics import (
    observe_recommendation_latency,
    record_recommendation_job_completed,
    record_recommendation_job_scheduled,
)

LOGGER = structlog.get_logger(__name__)
TASK_NAME = "services.workers.pipelines.recommendations_flow.calculate_recommendations"


def enqueue_recommendation_calculation(
    *,
    job_id: str,
    customer_id: str,
    channel: str | None,
    variant: str,
) -> str:
    async_result = celery_app.send_task(
        TASK_NAME,
        kwargs={
            "job_id": job_id,
            "customer_id": customer_id,
            "channel": channel,
            "variant": variant,
        },
        task_id=job_id,
    )
    record_recommendation_job_scheduled(variant, channel or "omni")
    LOGGER.info(
        "recommendations.job.enqueued",
        job_id=job_id,
        customer_id=customer_id,
        channel=channel,
        variant=variant,
    )
    return getattr(async_result, "id", job_id)


@celery_app.task(name=TASK_NAME, bind=True, autoretry_for=(Exception,), retry_backoff=True)
def calculate_recommendations(
    self: Task,
    *,
    job_id: str,
    customer_id: str,
    channel: str | None,
    variant: str,
) -> str:
    from infra.db.session import session_scope
    from domain.recommendations.service import RecommendationOrchestrationService

    start = perf_counter()
    LOGGER.info(
        "recommendations.job.started",
        job_id=job_id,
        customer_id=customer_id,
        channel=channel,
        variant=variant,
    )

    try:
        service = RecommendationOrchestrationService()
        with session_scope() as session:
            service.run_job(
                session,
                job_id=job_id,
                customer_id=customer_id,
                channel=channel,
                variant=variant,
            )
        record_recommendation_job_completed(variant, "success")
        LOGGER.info(
            "recommendations.job.completed",
            job_id=job_id,
            customer_id=customer_id,
            channel=channel,
            variant=variant,
        )
        return f"recommendation_job:{job_id}"
    except Exception as exc:  # pragma: no cover - Celery retry path
        record_recommendation_job_completed(variant, "error")
        LOGGER.exception(
            "recommendations.job.failed",
            job_id=job_id,
            customer_id=customer_id,
            channel=channel,
            variant=variant,
        )
        raise self.retry(exc=exc)
    finally:
        observe_recommendation_latency(variant, perf_counter() - start)


def run_recommendation_job(
    *,
    job_id: str,
    customer_id: str,
    channel: str | None,
    variant: str,
) -> str:
    """Вспомогательная функция для синхронного запуска расчёта (например, в тестах)."""

    from infra.db.session import session_scope
    from domain.recommendations.service import RecommendationOrchestrationService

    service = RecommendationOrchestrationService()
    with session_scope() as session:
        service.run_job(
            session,
            job_id=job_id,
            customer_id=customer_id,
            channel=channel,
            variant=variant,
        )
    return job_id


