from __future__ import annotations

import uuid

import pytest


@pytest.mark.contract
def test_create_customer_contract(api_client):
    customer_id = str(uuid.uuid4())
    payload = {
        "id": customer_id,
        "email": "user@example.com",
        "phone": "+12345678901",
        "name": "Иван Петров",
        "segments": ["vip", "electronics"],
        "attributes": {"preferred_channel": "email"},
    }

    response = api_client.post("/customers", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == customer_id
    assert body["email"] == payload["email"]
    assert body["phone"] == payload["phone"]
    assert body["name"] == payload["name"]
    assert body["segments"] == payload["segments"]
    assert body["attributes"] == payload["attributes"]
    assert "created_at" in body
    assert "updated_at" in body
    assert body["state"] == "active"
    assert body["version"] == 1


@pytest.mark.contract
def test_update_customer_contract(api_client):
    customer_id = str(uuid.uuid4())
    create_payload = {"id": customer_id, "name": "Анна Сидорова"}
    update_payload = {
        "email": "anna@example.com",
        "name": "Анна Смирнова",
        "segments": ["loyal"],
        "attributes": {"lifetime_value": "high"},
    }

    create_response = api_client.post("/customers", json=create_payload)
    assert create_response.status_code == 201

    response = api_client.put(f"/customer/{customer_id}", json=update_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == customer_id
    assert body["email"] == update_payload["email"]
    assert body["name"] == update_payload["name"]
    assert body["segments"] == update_payload["segments"]
    assert body["attributes"] == update_payload["attributes"]
    assert body["state"] == "active"
    assert body["version"] == 2
    assert body["updated_at"] != body["created_at"]


