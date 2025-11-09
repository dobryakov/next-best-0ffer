"""
Профиль нагрузочного тестирования для Next Best Offer API.

Сценарии включают прогрев данных (создание покупателей и событий)
и имитацию пользовательского потока: регистрация событий и запрос NBO.
"""

from __future__ import annotations

import logging
import os
import random
import string
from datetime import datetime, timezone
from typing import List
from uuid import NAMESPACE_URL, uuid4, uuid5

import requests
from locust import HttpUser, between, events, task

TRACE_HEADER = "X-Trace-Id"
WARMUP_CUSTOMERS = 5
CUSTOMER_SEGMENTS = [["electronics", "vip"], ["fashion", "loyal"], ["home", "new"]]
PRODUCT_IDS = ["SKU-001", "SKU-002", "SKU-003", "SKU-004", "SKU-005"]
CHANNELS = ["web", "mobile", "pos"]

_CUSTOMER_IDS: List[str] = []
_LOGGER = logging.getLogger(__name__)
_CUSTOMER_NAMESPACE_PREFIX = "nbo-perf-user"
ENABLE_NBO_TASKS = os.environ.get("PERF_ENABLE_NBO", "0") == "1"


def _rand_trace() -> str:
    return str(uuid4())


def _stable_customer_id(idx: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"{_CUSTOMER_NAMESPACE_PREFIX}-{idx}"))


def _stable_contacts(idx: int, customer_id: str) -> tuple[str, str]:
    email = f"{_CUSTOMER_NAMESPACE_PREFIX}-{idx}@loadtest.example.com"
    raw = customer_id.replace("-", "")
    numeric = str(int(raw[:12], 16)).zfill(12)
    phone = f"+1987{numeric[:8]}"
    return email, phone


def _host_from_environment(environment_host: str | None) -> str:
    if environment_host:
        return environment_host.rstrip("/")
    return os.environ.get("PERF_TARGET_HOST", "http://localhost:9090").rstrip("/")


def _bootstrap_customers(host: str) -> None:
    """
    Создаёт стартовых покупателей и прогревает события,
    чтобы расчёты рекомендаций имели исходные данные.
    """
    session = requests.Session()
    created: List[str] = []
    for idx in range(WARMUP_CUSTOMERS):
        customer_id = _stable_customer_id(idx)
        email, phone = _stable_contacts(idx, customer_id)
        payload = {
            "id": customer_id,
            "email": email,
            "phone": phone,
            "name": f"Perf Tester {idx}",
            "segments": random.choice(CUSTOMER_SEGMENTS),
            "attributes": {"cohort": "performance"},
        }
        response = session.post(
            f"{host}/customers",
            json=payload,
            headers={"Content-Type": "application/json", TRACE_HEADER: _rand_trace()},
            timeout=10,
        )
        if response.status_code == 201:
            created.append(customer_id)
        elif response.status_code == 409:
            _LOGGER.info(
                "Покупатель %s уже существует, используем существующую запись для нагрузки.",
                customer_id,
            )
            created.append(customer_id)
        else:
            response.raise_for_status()

    _CUSTOMER_IDS[:] = created

    for customer_id in created:
        _send_warmup_events(session, host, customer_id)


def _send_warmup_events(session: requests.Session, host: str, customer_id: str) -> None:
    now = datetime.now(tz=timezone.utc)
    for product_id in random.sample(PRODUCT_IDS, k=3):
        payload = {
            "idempotency_token": _idempotency_token(),
            "category": "view",
            "customer_id": customer_id,
            "product_ids": [product_id],
            "channel": random.choice(CHANNELS),
            "occurred_at": now.isoformat(),
            "payload": {"source": "warmup"},
        }
        response = session.post(
            f"{host}/events",
            json=payload,
            headers={"Content-Type": "application/json", TRACE_HEADER: _rand_trace()},
            timeout=10,
        )
        response.raise_for_status()


def _idempotency_token() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=16))


@events.test_start.add_listener
def on_test_start(environment, **_) -> None:
    """
    Прогреваем данные перед началом нагрузки.
    """
    host = _host_from_environment(environment.host)
    if not _CUSTOMER_IDS:
        _bootstrap_customers(host)


class NBOUser(HttpUser):
    """
    Модель пользователя:

    - регистрирует событие взаимодействия;
    - запрашивает рекомендацию;
    - выполняет повторный запрос для проверки окна retry.
    """

    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        if not _CUSTOMER_IDS:
            # Если прогрев не успел выполниться — создаём локально.
            host = _host_from_environment(self.environment.host)
            _bootstrap_customers(host)
        self.customer_id = random.choice(_CUSTOMER_IDS)

    @task(3)
    def register_event(self) -> None:
        product_id = random.choice(PRODUCT_IDS)
        payload = {
            "idempotency_token": _idempotency_token(),
            "category": "view",
            "customer_id": self.customer_id,
            "product_ids": [product_id],
            "channel": random.choice(CHANNELS),
            "occurred_at": datetime.now(tz=timezone.utc).isoformat(),
            "payload": {"source": "locust"},
        }
        headers = {"Content-Type": "application/json", TRACE_HEADER: _rand_trace()}
        with self.client.post(
            "/events",
            json=payload,
            headers=headers,
            name="POST /events",
            catch_response=True,
        ) as response:
            if response.status_code not in {202}:
                response.failure(f"Unexpected status {response.status_code}")

    if ENABLE_NBO_TASKS:

        @task(2)
        def get_nbo(self) -> None:
            headers = {TRACE_HEADER: _rand_trace()}
            with self.client.get(
                f"/nbo/{self.customer_id}",
                params={"channel": random.choice(CHANNELS)},
                headers=headers,
                name="GET /nbo/{customer_id}",
                catch_response=True,
            ) as response:
                if response.status_code not in {200, 202, 404}:
                    response.failure(f"Unexpected status {response.status_code}")

        @task(1)
        def repeat_nbo(self) -> None:
            """
            Повторный запрос NBO имитирует клиента, который ожидает завершения расчёта.
            """
            headers = {TRACE_HEADER: _rand_trace()}
            with self.client.get(
                f"/nbo/{self.customer_id}",
                headers=headers,
                name="GET /nbo/{customer_id} (retry)",
                catch_response=True,
            ) as response:
                if response.status_code not in {200, 202, 404}:
                    response.failure(f"Unexpected status {response.status_code}")


