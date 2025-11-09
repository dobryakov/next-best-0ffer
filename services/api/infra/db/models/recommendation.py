from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from infra.db.models import Base


class RecommendationStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index("uq_recommendations_customer", "customer_id", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(RecommendationStatus, name="recommendation_status"),
        default=RecommendationStatus.PENDING,
        nullable=False,
    )
    offers: Mapped[List[Dict[str, Any]]] = mapped_column(
        MutableList.as_mutable(JSON), default=list, nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    experiment_variant: Mapped[str] = mapped_column(String(64), default="control", nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",
        MutableDict.as_mutable(JSON),
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    jobs: Mapped[List["CalculationJob"]] = relationship(
        "CalculationJob",
        back_populates="recommendation",
        cascade="all, delete-orphan",
    )


class CalculationJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CalculationJob(Base):
    __tablename__ = "calculation_jobs"
    __table_args__ = (
        Index(
            "ix_calculation_jobs_active",
            "recommendation_id",
            "status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    recommendation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[CalculationJobStatus] = mapped_column(
        Enum(CalculationJobStatus, name="calculation_job_status"),
        default=CalculationJobStatus.PENDING,
        nullable=False,
    )
    requested_variant: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",
        MutableDict.as_mutable(JSON),
        default=dict,
        nullable=False,
    )

    recommendation: Mapped[Recommendation] = relationship("Recommendation", back_populates="jobs")


