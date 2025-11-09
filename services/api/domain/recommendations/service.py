from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Sequence
from uuid import uuid4

import structlog
from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session

from domain.recommendations.explanations import ExplanationContext, build_offer_reason
from infra.db.models.customer import Customer
from infra.db.models.recommendation import (
    CalculationJob,
    CalculationJobStatus,
    Recommendation,
    RecommendationStatus,
)
from infra.queues import recommendations as recommendations_queue
try:
    from services.workers.tasks.metrics import record_recommendation_job_scheduled
except ModuleNotFoundError:  # pragma: no cover - fallback для standalone запуска API
    def record_recommendation_job_scheduled(*_: object, **__: object) -> None:
        return None


class RecommendationError(Exception):
    """Базовая ошибка домена рекомендаций."""


class CustomerNotFoundError(RecommendationError):
    """Покупатель не найден."""


class VariantNotAllowedError(RecommendationError):
    """Запрошенный экспериментальный вариант не разрешён настройками."""


class CalculationJobNotFoundError(RecommendationError):
    """Задача расчёта не найдена."""


@dataclass(slots=True)
class RecommendationResult:
    """Результат запроса рекомендаций."""

    recommendation: Recommendation
    status: RecommendationStatus
    requested_variant: str
    requested_channel: str | None
    job: CalculationJob | None
    job_created: bool


class RecommendationOrchestrationService:
    """Сервис оркестрации расчёта Next Best Offer."""

    def __init__(
        self,
        *,
        queue_adapter=recommendations_queue,
    ) -> None:
        self._queue = queue_adapter
        self._logger = structlog.get_logger(__name__)

    def get_next_best_offer(
        self,
        session: Session,
        trace_id: str | None,
        *,
        customer_id: str,
        channel: str | None,
        variant: str | None,
        retry_window_seconds: int,
        allowed_variants: Sequence[str],
    ) -> RecommendationResult:
        normalized_variant = self._normalize_variant(variant, allowed_variants)
        customer = session.get(Customer, customer_id)
        if customer is None:
            raise CustomerNotFoundError(f"Customer {customer_id} not found")

        recommendation = self._get_or_create_recommendation(
            session,
            customer_id=customer_id,
            default_variant=normalized_variant,
            retry_window_seconds=retry_window_seconds,
        )

        active_job = self._get_active_job(session, recommendation.id)
        job_created = False

        if recommendation.status != RecommendationStatus.READY:
            if active_job is None:
                active_job = self._schedule_calculation_job(
                    session,
                    recommendation=recommendation,
                    customer=customer,
                    channel=channel,
                    variant=normalized_variant,
                    trace_id=trace_id,
                )
                job_created = True
            recommendation.reason = recommendation.reason or "calculation_in_progress"

        session.flush()
        return RecommendationResult(
            recommendation=recommendation,
            status=recommendation.status,
            requested_variant=normalized_variant,
            requested_channel=channel,
            job=active_job,
            job_created=job_created,
        )

    def run_job(
        self,
        session: Session,
        *,
        job_id: str,
        customer_id: str,
        channel: str | None,
        variant: str,
    ) -> Recommendation:
        job = session.get(CalculationJob, job_id)
        if job is None:
            raise CalculationJobNotFoundError(f"Calculation job {job_id} not found")

        recommendation = session.get(Recommendation, job.recommendation_id)
        if recommendation is None:
            raise RecommendationError("Recommendation entry missing for job.")

        if recommendation.customer_id != customer_id:
            self._logger.warning(
                "recommendations.job.customer_mismatch",
                job_id=job_id,
                expected_customer=recommendation.customer_id,
                provided_customer=customer_id,
            )

        customer = session.get(Customer, recommendation.customer_id)

        now = datetime.now(timezone.utc)
        job.status = CalculationJobStatus.RUNNING
        job.started_at = now
        job.requested_channel = channel
        job.requested_variant = variant

        offers = self._generate_offers(customer, variant, channel)

        recommendation.status = RecommendationStatus.READY
        recommendation.offers = offers
        recommendation.generated_at = now
        recommendation.retry_after = None
        recommendation.reason = "calculation_completed"
        recommendation.experiment_variant = variant
        recommendation.metadata_json = {
            **(recommendation.metadata_json or {}),
            "job_id": job_id,
            "model_version": "als-lgbm-v1",
            "variant": variant,
            "channel": channel or "omni",
        }

        job.status = CalculationJobStatus.COMPLETED
        job.finished_at = now
        job.last_error = None
        job.metadata_json = {
            **(job.metadata_json or {}),
            "completed_at": now.isoformat(),
        }

        session.flush()

        self._logger.info(
            "recommendations.job.completed",
            job_id=job_id,
            customer_id=recommendation.customer_id,
            variant=variant,
        )

        return recommendation

    def _normalize_variant(self, variant: str | None, allowed_variants: Sequence[str]) -> str:
        variants = list(allowed_variants) or ["control"]
        normalized = variant or variants[0]
        if normalized not in variants:
            raise VariantNotAllowedError(f"Variant '{normalized}' is not configured.")
        return normalized

    def _get_or_create_recommendation(
        self,
        session: Session,
        *,
        customer_id: str,
        default_variant: str,
        retry_window_seconds: int,
    ) -> Recommendation:
        stmt: Select[Recommendation] = select(Recommendation).where(
            Recommendation.customer_id == customer_id
        )
        recommendation = session.execute(stmt).scalar_one_or_none()

        future_retry = datetime.now(timezone.utc) + timedelta(seconds=max(retry_window_seconds, 1))

        if recommendation is None:
            recommendation = Recommendation(
                id=str(uuid4()),
                customer_id=customer_id,
                status=RecommendationStatus.PENDING,
                retry_after=future_retry,
                reason="calculation_in_progress",
                experiment_variant=default_variant,
                metadata_json={"requested_variant": default_variant},
            )
            session.add(recommendation)
            self._logger.info(
                "recommendations.record.created",
                recommendation_id=recommendation.id,
                customer_id=customer_id,
            )
        elif recommendation.status != RecommendationStatus.READY:
            recommendation.retry_after = future_retry
            recommendation.experiment_variant = default_variant
            recommendation.metadata_json = {
                **(recommendation.metadata_json or {}),
                "requested_variant": default_variant,
            }

        return recommendation

    def _get_active_job(self, session: Session, recommendation_id: str) -> CalculationJob | None:
        stmt: Select[CalculationJob] = (
            select(CalculationJob)
            .where(
                and_(
                    CalculationJob.recommendation_id == recommendation_id,
                    CalculationJob.status.in_(
                        (CalculationJobStatus.PENDING, CalculationJobStatus.RUNNING)
                    ),
                )
            )
            .order_by(CalculationJob.scheduled_at.desc())
        )
        return session.execute(stmt).scalar_one_or_none()

    def _schedule_calculation_job(
        self,
        session: Session,
        *,
        recommendation: Recommendation,
        customer: Customer,
        channel: str | None,
        variant: str,
        trace_id: str | None,
    ) -> CalculationJob:
        job = CalculationJob(
            id=str(uuid4()),
            recommendation_id=recommendation.id,
            customer_id=recommendation.customer_id,
            status=CalculationJobStatus.PENDING,
            requested_variant=variant,
            requested_channel=channel,
            metadata_json={
                "scheduled_at": datetime.now(timezone.utc).isoformat(),
                "trace_id": trace_id,
            },
        )
        session.add(job)
        session.flush()

        record_recommendation_job_scheduled(variant, channel or "omni")
        queued_task_id = self._queue.enqueue_recommendation_calculation(
            job_id=job.id,
            customer_id=recommendation.customer_id,
            channel=channel,
            variant=variant,
        )

        self._logger.info(
            "recommendations.job.scheduled",
            job_id=job.id,
            customer_id=recommendation.customer_id,
            variant=variant,
            channel=channel,
            trace_id=trace_id,
            queued_task_id=queued_task_id,
        )

        recommendation.metadata_json = {
            **(recommendation.metadata_json or {}),
            "last_job_id": job.id,
            "queued_task_id": queued_task_id,
            "requested_channel": channel,
        }
        return job

    def _generate_offers(
        self,
        customer: Customer | None,
        variant: str,
        channel: str | None,
    ) -> List[Dict[str, object]]:
        segments = list(getattr(customer, "segments", []) or [])
        context = ExplanationContext(
            customer_id=getattr(customer, "id", "unknown"),
            customer_segments=segments,
            variant=variant,
            channel=channel,
        )

        offers: List[Dict[str, object]] = []
        base_score = 0.92
        for index in range(3):
            product_id = f"SKU-{context.customer_id[:4] or 'GEN'}-{index + 1:02d}"
            score = round(base_score - index * 0.07, 4)
            offers.append(
                {
                    "product_id": product_id,
                    "score": score,
                    "reason": build_offer_reason(product_id, index, context),
                    "variant": variant,
                    "features_snapshot": {
                        "als_score": round(score - 0.05, 4),
                        "rerank_boost": round(0.12 - index * 0.03, 4),
                    },
                }
            )
        return offers


