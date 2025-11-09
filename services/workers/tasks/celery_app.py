from __future__ import annotations

from celery import Celery

from services.api.infra.config.settings import get_settings
from services.workers.tasks.config import BEAT_SCHEDULE, TASK_DEFAULTS


def _build_celery_app() -> Celery:
    settings = get_settings()

    celery = Celery(
        "nbo-workers",
        broker=settings.celery_broker,
        backend=settings.celery_backend,
        include=list(settings.celery_imports),
    )

    config = dict(TASK_DEFAULTS)
    config["task_default_queue"] = settings.celery_task_default_queue

    celery.conf.update(
        config,
        timezone=settings.celery_timezone,
        beat_schedule=BEAT_SCHEDULE,
        result_extended=True,
    )

    return celery


celery_app = _build_celery_app()

__all__ = ["celery_app"]


