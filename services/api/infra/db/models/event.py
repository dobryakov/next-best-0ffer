from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from infra.db.models import Base


class EventCategory(StrEnum):
    VIEW = "view"
    SEARCH = "search"
    ADD_TO_CART = "add_to_cart"
    PURCHASE = "purchase"


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_customer_category", "customer_id", "category"),
        Index("uq_events_idempotency_token", "idempotency_token", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    category: Mapped[EventCategory] = mapped_column(
        Enum(EventCategory, name="event_category"), nullable=False
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_ids: Mapped[List[str]] = mapped_column(
        MutableList.as_mutable(JSON), default=list, nullable=False
    )
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON), default=dict, nullable=False
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


