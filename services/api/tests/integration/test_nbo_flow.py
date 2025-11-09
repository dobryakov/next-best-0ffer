from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import Select, select

from infra.db.models.customer import Customer, CustomerState
from infra.db.models.recommendation import (
    CalculationJob,
    CalculationJobStatus,
    Recommendation,
    RecommendationStatus,
)
from services.workers.pipelines import recommendations_flow


@pytest.mark.integration
def test_nbo_full_flow(api_client, db_session_fixture, capture_logs) -> None:
    customer_id = str(uuid4())
    customer = Customer(
        id=customer_id,
        email="nbo-flow@example.com",
        segments=["vip"],
        attributes={"preferred_channel": "web"},
        state=CustomerState.ACTIVE,
    )
    db_session_fixture.add(customer)
    db_session_fixture.commit()

    first_response = api_client.get(f"/nbo/{customer_id}")
    assert first_response.status_code == 202
    pending_body = first_response.json()
    assert pending_body["status"] == "pending"
    assert pending_body["reason"] == "calculation_in_progress"

    job_stmt: Select[tuple[CalculationJob]] = select(CalculationJob)
    job = db_session_fixture.execute(job_stmt).scalar_one()
    assert job.customer_id == customer_id
    assert job.status == CalculationJobStatus.PENDING

    recommendations_flow.run_recommendation_job(
        job_id=job.id,
        customer_id=customer_id,
        channel="web",
        variant="control",
    )

    db_session_fixture.expire_all()

    ready_response = api_client.get(f"/nbo/{customer_id}?variant=treatmentA&channel=mobile")
    assert ready_response.status_code == 200
    ready_body = ready_response.json()
    assert ready_body["customer_id"] == customer_id
    assert ready_body["experiment_variant"] == "treatmentA"
    assert len(ready_body["offers"]) > 0

    offer = ready_body["offers"][0]
    assert offer["reason"]
    assert offer["product_id"]

    recommendation_stmt: Select[tuple[Recommendation]] = select(Recommendation).where(
        Recommendation.customer_id == customer_id
    )
    recommendation = db_session_fixture.execute(recommendation_stmt).scalar_one()
    assert recommendation.status == RecommendationStatus.READY
    assert recommendation.generated_at is not None

    job_check_stmt: Select[tuple[CalculationJob]] = select(CalculationJob).where(
        CalculationJob.id == job.id
    )
    job_after = db_session_fixture.execute(job_check_stmt).scalar_one()
    assert job_after.status == CalculationJobStatus.COMPLETED
    assert job_after.finished_at is not None

    logs = [record for record in capture_logs.records if "recommendations." in record.message]
    assert any("recommendations.job.scheduled" in record.message for record in logs)
    assert any("recommendations.job.completed" in record.message for record in logs)


