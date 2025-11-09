from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from infra.db.models.customer import Customer, CustomerState
from infra.db.models.recommendation import Recommendation, RecommendationStatus


@pytest.mark.contract
def test_get_recommendations_ready_response(api_client, db_session_fixture) -> None:
    customer_id = str(uuid4())
    customer = Customer(
        id=customer_id,
        email="nbo-ready@example.com",
        segments=["loyal"],
        attributes={"lifetime_value": "platinum"},
        state=CustomerState.ACTIVE,
    )

    recommendation = Recommendation(
        id=str(uuid4()),
        customer_id=customer_id,
        status=RecommendationStatus.READY,
        offers=[
            {
                "product_id": "SKU-9000",
                "score": 0.91,
                "reason": "top_seller_for_segment",
                "features_snapshot": {"recency_days": 3},
            }
        ],
        generated_at=datetime.now(timezone.utc),
        metadata={"model_version": "als-lgbm-v1"},
        experiment_variant="control",
    )

    db_session_fixture.add_all([customer, recommendation])
    db_session_fixture.commit()

    response = api_client.get(f"/nbo/{customer_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["customer_id"] == customer_id
    assert body["experiment_variant"] == "control"
    assert len(body["offers"]) == 1
    offer = body["offers"][0]
    assert offer["product_id"] == "SKU-9000"
    assert pytest.approx(offer["score"], rel=1e-6) == 0.91
    assert offer["reason"]
    assert offer["features_snapshot"]["recency_days"] == 3
    assert "retry_after" not in body


@pytest.mark.contract
def test_get_recommendations_pending_response(api_client, db_session_fixture) -> None:
    customer_id = str(uuid4())
    customer = Customer(
        id=customer_id,
        email="nbo-pending@example.com",
        segments=["electronics"],
        attributes={},
        state=CustomerState.ACTIVE,
    )

    retry_after = datetime.now(timezone.utc) + timedelta(seconds=45)
    recommendation = Recommendation(
        id=str(uuid4()),
        customer_id=customer_id,
        status=RecommendationStatus.PENDING,
        retry_after=retry_after,
        experiment_variant="control",
        reason="calculation_in_progress",
    )

    db_session_fixture.add_all([customer, recommendation])
    db_session_fixture.commit()

    response = api_client.get(f"/nbo/{customer_id}")

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["reason"] == "calculation_in_progress"
    assert body["retry_after"]


@pytest.mark.contract
def test_get_recommendations_customer_not_found(api_client) -> None:
    missing_customer_id = str(uuid4())

    response = api_client.get(f"/nbo/{missing_customer_id}")

    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "Customer not found."


