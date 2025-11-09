from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
import structlog
from sqlalchemy.orm import Session

from app.schemas.recommendation import (
    RecommendationPendingResponse,
    RecommendationResponse,
)
from domain.recommendations.service import (
    CustomerNotFoundError,
    RecommendationError,
    RecommendationOrchestrationService,
    RecommendationResult,
    VariantNotAllowedError,
)
from infra.config.settings import Settings, get_settings
from infra.db.models.recommendation import RecommendationStatus
from infra.db.session import get_session

router = APIRouter(tags=["Recommendations"])
_logger = structlog.get_logger(__name__)


def get_recommendations_service() -> RecommendationOrchestrationService:
    return RecommendationOrchestrationService()


@router.get(
    "/nbo/{customer_id}",
    summary="Получить Next Best Offer для покупателя",
    response_model=RecommendationResponse,
    responses={
        status.HTTP_202_ACCEPTED: {
            "description": "Рекомендации ещё рассчитываются",
            "model": RecommendationPendingResponse,
        },
        status.HTTP_404_NOT_FOUND: {"description": "Покупатель не найден"},
    },
)
def read_next_best_offer(
    customer_id: UUID,
    request: Request,
    channel: str | None = None,
    variant: str | None = None,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    service: RecommendationOrchestrationService = Depends(get_recommendations_service),
) -> RecommendationResponse | JSONResponse:
    trace_id = getattr(request.state, "trace_id", None)

    try:
        result = service.get_next_best_offer(
            session,
            trace_id,
            customer_id=str(customer_id),
            channel=channel,
            variant=variant,
            retry_window_seconds=settings.nbo_retry_window_seconds,
            allowed_variants=settings.ab_variants,
        )
    except CustomerNotFoundError as exc:
        _logger.info(
            "recommendations.customer_missing",
            customer_id=str(customer_id),
            trace_id=trace_id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.") from exc
    except VariantNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RecommendationError as exc:  # pragma: no cover - защитный путь
        _logger.exception(
            "recommendations.get.failed",
            customer_id=str(customer_id),
            trace_id=trace_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch recommendation.",
        ) from exc

    return _build_response(result, requested_variant=variant)


def _build_response(
    result: RecommendationResult,
    *,
    requested_variant: str | None,
) -> RecommendationResponse | JSONResponse:
    if result.status == RecommendationStatus.READY:
        response_variant = requested_variant or result.requested_variant
        return RecommendationResponse.from_model(
            result.recommendation,
            response_variant=response_variant,
        )

    if result.status == RecommendationStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.recommendation.reason or "Recommendation calculation failed.",
        )

    pending_payload = RecommendationPendingResponse.from_model(result.recommendation)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=pending_payload.model_dump(mode="json"),
    )


