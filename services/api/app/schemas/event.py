from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from infra.db.models.event import Event, EventCategory

MAX_PAYLOAD_BYTES = 16 * 1024


class EventRequest(BaseModel):
    idempotency_token: str | None = Field(default=None, min_length=8, max_length=128)
    category: EventCategory
    customer_id: UUID
    product_ids: List[str] | None = Field(default=None)
    channel: str = Field(..., min_length=1, max_length=64)
    occurred_at: datetime
    payload: Dict[str, Any] | None = Field(default_factory=dict)

    @field_validator("occurred_at", mode="before")
    @classmethod
    def _ensure_datetime(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(str(value))

        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @field_validator("occurred_at")
    @classmethod
    def _validate_occurred_at(cls, value: datetime) -> datetime:
        now = datetime.now(tz=timezone.utc)
        boundary = timedelta(days=7)
        if value < now - boundary or value > now + boundary:
            raise ValueError("occurred_at должен находиться в пределах ±7 дней.")
        return value

    @field_validator("product_ids", mode="before")
    @classmethod
    def _default_product_ids(cls, value: Any) -> List[str]:
        if value is None:
            return []
        return list(value)

    @field_validator("product_ids")
    @classmethod
    def _validate_product_ids(cls, value: List[str], info: ValidationInfo) -> List[str]:
        category = info.data.get("category")
        if category != EventCategory.SEARCH and len(value) == 0:
            raise ValueError("product_ids обязательны для категорий, отличных от search.")
        return value

    @field_validator("payload")
    @classmethod
    def _validate_payload_size(cls, value: Dict[str, Any] | None) -> Dict[str, Any]:
        data = value or {}
        serialized = str(data).encode("utf-8")
        if len(serialized) > MAX_PAYLOAD_BYTES:
            raise ValueError("payload должен быть меньше 16KB.")
        return data


class EventAcceptedResponse(BaseModel):
    status: Literal["accepted"] = "accepted"
    event_id: UUID
    idempotency_token: str
    duplicate: bool
    queued_task_id: str | None = None

    @classmethod
    def from_result(
        cls,
        *,
        event: Event,
        idempotency_token: str,
        duplicate: bool,
        queued_task_id: str | None,
    ) -> "EventAcceptedResponse":
        return cls(
            event_id=UUID(event.id),
            idempotency_token=idempotency_token,
            duplicate=duplicate,
            queued_task_id=queued_task_id,
        )


