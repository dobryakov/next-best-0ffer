from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
import structlog
from sqlalchemy.orm import Session

from app.schemas.event import EventAcceptedResponse, EventRequest
from domain.events.service import EventIngestionService, IngestEventCommand
from infra.config.settings import Settings, get_settings
from infra.db.session import get_session
from infra.queues.events import enqueue_event

try:  # pragma: no cover - метрики доступны только при установленном пакете воркеров
    from services.workers.tasks.metrics import record_event_enqueued
except ModuleNotFoundError:  # pragma: no cover
    def record_event_enqueued(category: str, channel: str) -> None:
        _logger.info(
            "events.metrics.skipped",
            category=category,
            channel=channel,
        )

router = APIRouter(tags=["Events"])
_logger = structlog.get_logger(__name__)


def get_event_service() -> EventIngestionService:
    return EventIngestionService()


@router.post(
    "/events",
    summary="Регистрация клиентского события",
    response_model=EventAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def register_event(
    payload: EventRequest,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    service: EventIngestionService = Depends(get_event_service),
) -> EventAcceptedResponse:
    trace_id = getattr(request.state, "trace_id", None)
    command = IngestEventCommand(
        category=payload.category,
        customer_id=str(payload.customer_id),
        product_ids=payload.product_ids or [],
        channel=payload.channel,
        occurred_at=payload.occurred_at,
        payload=payload.payload or {},
        idempotency_token=payload.idempotency_token,
    )

    try:
        event, created, idempotency_token = service.ingest_event(
            session,
            trace_id,
            command=command,
            idempotency_window_seconds=settings.event_idempotency_window_seconds,
        )
    except Exception as exc:  # pragma: no cover - защитный слой
        _logger.exception(
            "events.failed",
            trace_id=trace_id,
            customer_id=command.customer_id,
            category=command.category.value,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest event.",
        ) from exc

    queued_task_id: str | None = None
    if created:
        try:
            queue_payload = {
                "event_id": event.id,
                "customer_id": event.customer_id,
                "category": event.category.value,
                "product_ids": event.product_ids,
                "channel": event.channel,
                "occurred_at": event.occurred_at.isoformat(),
            }
            queued_task_id = enqueue_event(
                settings,
                event_id=event.id,
                payload=queue_payload,
            )
            record_event_enqueued(event.category.value, event.channel)
        except Exception as exc:  # pragma: no cover - защита от падения Celery
            _logger.exception(
                "events.enqueue_failed",
                event_id=event.id,
                trace_id=trace_id,
                error=str(exc),
            )

    response = EventAcceptedResponse.from_result(
        event=event,
        idempotency_token=idempotency_token,
        duplicate=not created,
        queued_task_id=queued_task_id,
    )
    return response


