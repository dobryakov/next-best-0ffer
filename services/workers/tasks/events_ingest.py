from __future__ import annotations

from time import perf_counter
from typing import Any, Dict

import structlog
from celery import Task

from services.workers.tasks.celery_app import celery_app
from services.workers.tasks.metrics import (
    observe_event_processing_duration,
    record_event_processing_completed,
    record_event_processing_started,
)

LOGGER = structlog.get_logger(__name__)
TASK_NAME = "services.workers.tasks.events_ingest.process_event"


def enqueue_event_processing(
    *,
    event_id: str,
    event_payload: Dict[str, Any],
    priority: int | None = None,
) -> str:
    options: Dict[str, Any] = {"task_id": event_id}
    if priority is not None:
        options["priority"] = priority
    async_result = celery_app.send_task(
        TASK_NAME,
        kwargs={"event_id": event_id, "payload": event_payload},
        **options,
    )
    record_event_processing_started(event_payload.get("category", "unknown"))
    LOGGER.info(
        "events.task.enqueued",
        event_id=event_id,
        payload=event_payload,
        priority=priority,
    )
    return getattr(async_result, "id", event_id)


@celery_app.task(name=TASK_NAME, bind=True, autoretry_for=(Exception,), retry_backoff=True)
def process_event(self: Task, *, event_id: str, payload: Dict[str, Any]) -> str:
    start = perf_counter()
    category = payload.get("category", "unknown")
    LOGGER.info("events.task.started", event_id=event_id, category=category)

    try:
        # TODO: интеграция с feature store / enrichment pipeline.
        LOGGER.info(
            "events.task.processing",
            event_id=event_id,
            customer_id=payload.get("customer_id"),
            channel=payload.get("channel"),
            product_ids=payload.get("product_ids", []),
        )

        result_message = f"event {event_id} processed"
        LOGGER.info("events.task.completed", event_id=event_id, category=category)
        record_event_processing_completed(category, "success")
        return result_message
    except Exception as exc:  # pragma: no cover - Celery retryable path
        LOGGER.exception("events.task.failed", event_id=event_id, category=category)
        record_event_processing_completed(category, "error")
        raise self.retry(exc=exc)
    finally:
        duration = perf_counter() - start
        observe_event_processing_duration(category, duration)


