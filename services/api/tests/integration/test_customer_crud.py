from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from infra.db.models.customer import Customer


@pytest.mark.integration
def test_customer_create_and_update_flow(api_client, db_session_fixture, capture_logs):
    customer_id = str(uuid.uuid4())
    create_payload = {
        "id": customer_id,
        "email": "first@example.com",
        "segments": ["electronics"],
        "attributes": {"preferred_channel": "sms"},
    }

    create_response = api_client.post("/customers", json=create_payload)
    assert create_response.status_code == 201

    update_payload = {
        "email": "updated@example.com",
        "phone": "+19876543210",
        "segments": ["electronics", "vip"],
        "attributes": {"preferred_channel": "email", "lifetime_value": "gold"},
    }
    update_response = api_client.put(f"/customer/{customer_id}", json=update_payload)

    assert update_response.status_code == 200
    updated_body = update_response.json()
    assert updated_body["version"] == 2
    assert updated_body["email"] == update_payload["email"]
    assert updated_body["phone"] == update_payload["phone"]
    assert updated_body["segments"] == update_payload["segments"]
    assert updated_body["attributes"] == update_payload["attributes"]

    customer_in_db = db_session_fixture.execute(
        select(Customer).where(Customer.id == customer_id)
    ).scalar_one()
    assert customer_in_db.email == update_payload["email"]
    assert customer_in_db.phone == update_payload["phone"]
    assert customer_in_db.version == 2

    audit_logs = [record for record in capture_logs.records if "customer_audit" in record.message]
    assert any("created" in record.message for record in audit_logs)
    assert any("updated" in record.message for record in audit_logs)


