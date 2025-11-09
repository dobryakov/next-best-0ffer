from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest


@pytest.mark.contract
def test_register_event_contract(api_client) -> None:
    customer_id = str(uuid4())
    create_customer_payload = {
        "id": customer_id,
        "email": "event-user@example.com",
        "segments": ["electronics"],
    }
    create_resp = api_client.post("/customers", json=create_customer_payload)
    assert create_resp.status_code == 201

    occurred_at = datetime.now(timezone.utc).isoformat()
    event_payload = {
        "category": "view",
        "customer_id": customer_id,
        "product_ids": ["SKU-1001"],
        "channel": "web",
        "occurred_at": occurred_at,
        "payload": {"referrer": "homepage", "campaign": "black-friday"},
    }

    response = api_client.post("/events", json=event_payload)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["duplicate"] is False
    assert body["event_id"]
    assert body["idempotency_token"]
    assert body["queued_task_id"]

    duplicate_response = api_client.post("/events", json=event_payload)
    assert duplicate_response.status_code == 202
    dup_body = duplicate_response.json()
    assert dup_body["event_id"] == body["event_id"]
    assert dup_body["idempotency_token"] == body["idempotency_token"]
    assert dup_body["duplicate"] is True
    assert dup_body["queued_task_id"] is None


