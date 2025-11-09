from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple
from uuid import NAMESPACE_URL, uuid5

import structlog
from sqlalchemy.orm import Session

from domain.events.idempotency import EventFingerprint, generate_event_identities
from domain.events.repository import EventCreateDTO, EventRepository
from infra.db.models.event import Event, EventCategory


@dataclass(slots=True)
class IngestEventCommand:
    category: EventCategory
    customer_id: str
    product_ids: List[str]
    channel: str
    occurred_at: datetime
    payload: Dict[str, Any]
    idempotency_token: str | None = None


class EventIngestionService:
    """Сервис приёма событий с идемпотентностью и постановкой в очередь."""

    def __init__(self, repository: EventRepository | None = None) -> None:
        self._repository = repository or EventRepository()
        self._logger = structlog.get_logger(__name__)

    def ingest_event(
        self,
        session: Session,
        trace_id: str | None,
        *,
        command: IngestEventCommand,
        idempotency_window_seconds: int,
    ) -> Tuple[Event, bool, str]:
        fingerprint = EventFingerprint(
            category=command.category.value,
            customer_id=command.customer_id,
            product_ids=list(command.product_ids),
            channel=command.channel,
            occurred_at=command.occurred_at,
            payload=dict(command.payload),
        )

        fallback_tokens: List[str] = []

        if command.idempotency_token:
            idempotency_token = command.idempotency_token
            event_id = str(uuid5(NAMESPACE_URL, idempotency_token))
        else:
            primary_identity, fallback_identities = generate_event_identities(
                fingerprint,
                window_seconds=idempotency_window_seconds,
            )
            event_id = primary_identity.event_id
            idempotency_token = primary_identity.token
            fallback_tokens = [candidate.token for candidate in fallback_identities]

        dto = EventCreateDTO(
            event_id=event_id,
            idempotency_token=idempotency_token,
            category=command.category,
            customer_id=command.customer_id,
            product_ids=list(command.product_ids),
            channel=command.channel,
            occurred_at=command.occurred_at,
            payload=dict(command.payload),
        )

        alternate_tokens: List[str] | None = None
        if fallback_tokens:
            alternate_tokens = fallback_tokens

        event, created = self._repository.create_or_get(
            session,
            dto,
            alternate_tokens=alternate_tokens,
        )

        log_event = "events.ingested" if created else "events.duplicate"
        self._logger.info(
            log_event,
            event_id=event.id,
            customer_id=event.customer_id,
            category=event.category.value,
            trace_id=trace_id,
        )

        return event, created, event.idempotency_token


