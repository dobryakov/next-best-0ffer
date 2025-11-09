from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import Select, func, select

from infra.db.models.customer import Customer, CustomerState
from infra.db.models.event import Event
from services.workers.tasks.celery_app import celery_app as stub_celery_app


@pytest.mark.integration
def test_event_ingestion_and_deduplication(api_client, db_session_fixture, capture_logs) -> None:
    customer_id = str(uuid4())
    customer = Customer(
        id=customer_id,
        email="dedup@example.com",
        segments=["electronics"],
        attributes={"lifetime_value": "gold"},
        state=CustomerState.ACTIVE,
    )
    db_session_fixture.add(customer)
    db_session_fixture.commit()

    stub_celery_app.sent_tasks.clear()

    occurred_at = datetime.now(timezone.utc).replace(microsecond=0)
    event_payload = {
        "category": "add_to_cart",
        "customer_id": customer_id,
        "product_ids": ["SKU-1", "SKU-2"],
        "channel": "mobile",
        "occurred_at": occurred_at.isoformat(),
        "payload": {"cart_total": 199.99},
    }

    response = api_client.post("/events", json=event_payload)
    assert response.status_code == 202
    body = response.json()
    assert body["duplicate"] is False
    first_event_id = body["event_id"]

    duplicate_payload = dict(event_payload)
    duplicate_payload["occurred_at"] = (occurred_at + timedelta(minutes=5)).isoformat()
    duplicate_response = api_client.post("/events", json=duplicate_payload)
    assert duplicate_response.status_code == 202
    duplicate_body = duplicate_response.json()
    assert duplicate_body["event_id"] == first_event_id
    assert duplicate_body["duplicate"] is True
    assert len(stub_celery_app.sent_tasks) == 1

    db_session_fixture.expire_all()
    event_stmt: Select[tuple[Event]] = select(Event).where(Event.id == first_event_id)
    persisted_event = db_session_fixture.execute(event_stmt).scalar_one()
    assert persisted_event.category.value == "add_to_cart"
    assert persisted_event.customer_id == customer_id
    assert persisted_event.product_ids == ["SKU-1", "SKU-2"]
    assert persisted_event.channel == "mobile"
    assert persisted_event.idempotency_token == body["idempotency_token"]

    count_stmt = select(func.count(Event.id))
    event_count = db_session_fixture.execute(count_stmt).scalar_one()
    assert event_count == 1

    events_log_records = [
        record for record in capture_logs.records if "events." in record.message
    ]
    assert any("events.ingested" in record.message for record in events_log_records)
    assert any("events.duplicate" in record.message for record in events_log_records)


