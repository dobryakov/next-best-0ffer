from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from infra.db.models.event import Event, EventCategory


@dataclass(slots=True)
class EventCreateDTO:
    event_id: str
    idempotency_token: str
    category: EventCategory
    customer_id: str
    product_ids: List[str]
    channel: str
    occurred_at: datetime
    payload: Dict[str, Any]


class EventRepositoryError(Exception):
    """Базовая ошибка репозитория событий."""


class EventRepository:
    """Репозиторий событий с обеспечением идемпотентности записей."""

    def get_by_id(self, session: Session, event_id: str) -> Event | None:
        return session.get(Event, event_id)

    def get_by_token(self, session: Session, token: str) -> Event | None:
        statement = select(Event).where(Event.idempotency_token == token)
        return session.execute(statement).scalar_one_or_none()

    def create_or_get(
        self,
        session: Session,
        dto: EventCreateDTO,
    ) -> Tuple[Event, bool]:
        existing = self.get_by_token(session, dto.idempotency_token)
        if existing is not None:
            return existing, False

        ingested_at = datetime.now(tz=timezone.utc)
        event = Event(
            id=dto.event_id,
            idempotency_token=dto.idempotency_token,
            category=dto.category,
            customer_id=dto.customer_id,
            product_ids=list(dto.product_ids),
            channel=dto.channel,
            occurred_at=dto.occurred_at,
            payload=dict(dto.payload),
            ingested_at=ingested_at,
        )

        session.add(event)

        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            # Попытка повторного чтения, если другая транзакция сохранила событие.
            existing = self.get_by_token(session, dto.idempotency_token)
            if existing is None:
                raise
            return existing, False

        session.refresh(event)
        return event, True


