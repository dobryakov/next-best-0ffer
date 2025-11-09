from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from infra.db.models.recommendation import Recommendation, RecommendationStatus


class OfferSchema(BaseModel):
    product_id: str
    score: float
    reason: str
    variant: str | None = None
    features_snapshot: Dict[str, Any] = Field(default_factory=dict)


class RecommendationResponse(BaseModel):
    status: Literal["ready"] = "ready"
    customer_id: UUID
    offers: List[OfferSchema]
    generated_at: datetime
    model_version: str
    experiment_variant: str

    @classmethod
    def from_model(
        cls,
        recommendation: Recommendation,
        *,
        response_variant: str,
    ) -> "RecommendationResponse":
        metadata = recommendation.metadata_json or {}
        model_version = metadata.get("model_version", "als-lgbm-v1")
        offers_payload = [
            OfferSchema.model_validate(
                {
                    "product_id": offer.get("product_id"),
                    "score": offer.get("score", 0.0),
                    "reason": offer.get("reason", "n/a"),
                    "variant": offer.get("variant"),
                    "features_snapshot": offer.get("features_snapshot", {}),
                }
            )
            for offer in recommendation.offers
        ]
        return cls(
            customer_id=UUID(recommendation.customer_id),
            offers=offers_payload,
            generated_at=recommendation.generated_at or datetime.now(timezone.utc),
            model_version=model_version,
            experiment_variant=response_variant,
        )


class RecommendationPendingResponse(BaseModel):
    status: Literal["pending"] = "pending"
    reason: str = "calculation_in_progress"
    retry_after: datetime | None = None

    @classmethod
    def from_model(cls, recommendation: Recommendation) -> "RecommendationPendingResponse":
        return cls(
            reason=recommendation.reason or "calculation_in_progress",
            retry_after=recommendation.retry_after,
        )


class RecommendationFailedResponse(BaseModel):
    status: Literal["failed"] = "failed"
    reason: str


def is_ready(recommendation: Recommendation) -> bool:
    return recommendation.status == RecommendationStatus.READY


