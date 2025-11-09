from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict

import structlog
from celery import Celery

from infra.config.settings import Settings

TASK_NAME = "services.workers.tasks.events_ingest.process_event"
_logger = structlog.get_logger(__name__)

try:  # pragma: no cover - интеграция с воркерами при наличии пакета
    from services.workers.tasks.events_ingest import enqueue_event_processing as _worker_enqueue
except ModuleNotFoundError:  # pragma: no cover - fallback при отсутствии пакета
    _worker_enqueue = None


@lru_cache(maxsize=1)
def _build_celery_client(broker: str, backend: str, default_queue: str) -> Celery:
    celery = Celery("nbo-api", broker=broker, backend=backend)
    celery.conf.task_default_queue = default_queue
    return celery


def enqueue_event(
    settings: Settings,
    *,
    event_id: str,
    payload: Dict[str, Any],
    priority: int | None = None,
) -> str:
    if _worker_enqueue is not None:
        return _worker_enqueue(event_id=event_id, event_payload=payload, priority=priority)

    celery = _build_celery_client(
        settings.celery_broker,
        settings.celery_backend,
        settings.celery_task_default_queue,
    )
    options: Dict[str, Any] = {"task_id": event_id}
    if priority is not None:
        options["priority"] = priority

    async_result = celery.send_task(
        TASK_NAME,
        kwargs={"event_id": event_id, "payload": payload},
        **options,
    )
    _logger.info(
        "events.enqueue.local_client",
        event_id=event_id,
        priority=priority,
        broker=settings.celery_broker,
    )
    return getattr(async_result, "id", event_id)


