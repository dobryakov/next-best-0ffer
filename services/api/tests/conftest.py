from __future__ import annotations

import os
import sys
from collections.abc import Generator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

_TESTS_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _TESTS_DIR.parent

if "services" not in sys.modules:
    sys.modules["services"] = ModuleType("services")

if "services.api" not in sys.modules:
    services_pkg = sys.modules["services"]
    api_pkg = ModuleType("services.api")
    api_pkg.__path__ = [str(_PROJECT_DIR)]
    sys.modules["services.api"] = api_pkg
    setattr(services_pkg, "api", api_pkg)

workers_pkg = sys.modules.setdefault("services.workers", ModuleType("services.workers"))
tasks_pkg = sys.modules.setdefault("services.workers.tasks", ModuleType("services.workers.tasks"))

workers_path = _PROJECT_DIR.parent / "workers"
workers_pkg.__path__ = [str(workers_path)]
tasks_pkg.__path__ = [str(workers_path / "tasks")]

pipelines_pkg = sys.modules.setdefault(
    "services.workers.pipelines", ModuleType("services.workers.pipelines")
)

recommendations_flow_module = ModuleType("services.workers.pipelines.recommendations_flow")
recommendations_flow_module.enqueued_jobs: list[dict[str, Any]] = []


def _enqueue_recommendation_calculation(
    *,
    job_id: str,
    customer_id: str,
    channel: str | None,
    variant: str,
) -> str:
    record = {
        "job_id": job_id,
        "customer_id": customer_id,
        "channel": channel,
        "variant": variant,
    }
    recommendations_flow_module.enqueued_jobs.append(record)
    result = celery_app_module.celery_app.send_task(
        "services.workers.pipelines.recommendations_flow.calculate_recommendations",
        kwargs={
            "job_id": job_id,
            "customer_id": customer_id,
            "channel": channel,
            "variant": variant,
        },
        task_id=job_id,
    )
    return result.id


def _run_recommendation_job(
    *,
    job_id: str,
    customer_id: str,
    channel: str | None,
    variant: str,
) -> str:
    from domain.recommendations.service import RecommendationOrchestrationService
    from infra.db.session import session_scope

    service = RecommendationOrchestrationService()
    with session_scope() as session:
        service.run_job(
            session,
            job_id=job_id,
            customer_id=customer_id,
            channel=channel,
            variant=variant,
        )
    return job_id


recommendations_flow_module.enqueue_recommendation_calculation = (  # type: ignore[attr-defined]
    _enqueue_recommendation_calculation
)
recommendations_flow_module.run_recommendation_job = _run_recommendation_job  # type: ignore[attr-defined]
sys.modules["services.workers.pipelines.recommendations_flow"] = recommendations_flow_module
setattr(pipelines_pkg, "recommendations_flow", recommendations_flow_module)

celery_app_module = ModuleType("services.workers.tasks.celery_app")


class _DummyCeleryControl:
    def ping(self, timeout: int | None = None) -> list[dict[str, str]]:
        return [{"worker": "pong"}]


class _DummyAsyncResult:
    def __init__(self, task_id: str) -> None:
        self.id = task_id


class _DummyCelery:
    def __init__(self) -> None:
        self.control = _DummyCeleryControl()
        self.sent_tasks: list[dict[str, Any]] = []

    def task(self, *args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    def send_task(
        self,
        name: str,
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
        **options: Any,
    ) -> _DummyAsyncResult:
        task_id = options.get("task_id") or f"task-{len(self.sent_tasks)+1}"
        record = {
            "name": name,
            "args": args or tuple(),
            "kwargs": kwargs or {},
            "options": options,
            "task_id": task_id,
        }
        self.sent_tasks.append(record)
        return _DummyAsyncResult(task_id)


celery_app_module.celery_app = _DummyCelery()
tasks_pkg.celery_app = celery_app_module
sys.modules["services.workers.tasks.celery_app"] = celery_app_module

events_ingest_module = ModuleType("services.workers.tasks.events_ingest")


def _enqueue_event_processing(
    *,
    event_id: str,
    event_payload: dict[str, Any],
    priority: int | None = None,
) -> str:
    options: dict[str, Any] = {"task_id": event_id}
    if priority is not None:
        options["priority"] = priority
    result = celery_app_module.celery_app.send_task(
        "services.workers.tasks.events_ingest.process_event",
        kwargs={"event_id": event_id, "payload": event_payload},
        **options,
    )
    return result.id


events_ingest_module.enqueue_event_processing = _enqueue_event_processing  # type: ignore[attr-defined]
sys.modules["services.workers.tasks.events_ingest"] = events_ingest_module
tasks_pkg.events_ingest = events_ingest_module

config_module = ModuleType("services.workers.tasks.config")
config_module.HEALTHCHECK_TIMEOUT = 1
sys.modules["services.workers.tasks.config"] = config_module
tasks_pkg.config = config_module

metrics_module = ModuleType("services.workers.tasks.metrics")
metrics_module.record_event_enqueued = lambda *args, **kwargs: None  # type: ignore[attr-defined]
metrics_module.record_event_processing_started = lambda *args, **kwargs: None  # type: ignore[attr-defined]
metrics_module.record_event_processing_completed = lambda *args, **kwargs: None  # type: ignore[attr-defined]
metrics_module.observe_event_processing_duration = lambda *args, **kwargs: None  # type: ignore[attr-defined]
metrics_module.record_recommendation_job_scheduled = lambda *args, **kwargs: None  # type: ignore[attr-defined]
metrics_module.record_recommendation_job_completed = lambda *args, **kwargs: None  # type: ignore[attr-defined]
metrics_module.observe_recommendation_latency = lambda *args, **kwargs: None  # type: ignore[attr-defined]
sys.modules["services.workers.tasks.metrics"] = metrics_module
tasks_pkg.metrics = metrics_module

setattr(workers_pkg, "tasks", tasks_pkg)
setattr(workers_pkg, "pipelines", pipelines_pkg)
services_pkg = sys.modules["services"]
setattr(services_pkg, "workers", workers_pkg)

# Глобальные переменные окружения для корректной инициализации настроек FastAPI-приложения
os.environ["POSTGRES_DSN"] = "postgresql+psycopg://nbo:nbo@postgres:5432/nbo"
os.environ.setdefault("REDIS_URL", "redis://redis:6379/0")
os.environ.setdefault("ALS_FACTORS", "32")
os.environ.setdefault("ALS_REG", "0.05")
os.environ.setdefault("LGBM_MODEL_PATH", "/opt/models/lgbm-test.bin")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("API_HOST", "0.0.0.0")
os.environ.setdefault("API_PORT", "9090")
os.environ.setdefault("DB_ECHO", "0")
os.environ.setdefault("DB_POOL_SIZE", "5")
os.environ.setdefault("DB_MAX_OVERFLOW", "5")
os.environ.setdefault("DB_POOL_TIMEOUT", "10")
os.environ.setdefault("CELERY_BROKER_URL", "redis://redis:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
os.environ.setdefault("CELERY_TIMEZONE", "UTC")
os.environ.setdefault("CELERY_DEFAULT_QUEUE", "nbo_default")
os.environ["CELERY_IMPORTS"] = (
    '["services.workers.tasks.events_ingest","services.workers.pipelines.recommendations_flow"]'
)
os.environ.setdefault("FEAST_REPO_PATH", "/opt/feast_repo")
os.environ.setdefault("MODEL_REGISTRY_PATH", "/opt/models")
os.environ.setdefault("NBO_RETRY_WINDOW_SECONDS", "30")
os.environ.setdefault("EVENT_IDEMPOTENCY_WINDOW_SECONDS", "600")
os.environ["AB_VARIANTS"] = '["control","treatmentA"]'
os.environ.setdefault("TRACING_ENDPOINT", "http://jaeger:4318")
os.environ.setdefault("METRICS_PORT", "9091")

from app.main import create_app  # noqa: E402
from infra.db import session as db_session  # noqa: E402
from infra.db.models import Base  # noqa: E402
import infra.db.models.customer  # noqa: E402,F401
import infra.db.models.event  # noqa: E402,F401
import infra.db.models.recommendation  # noqa: E402,F401
import domain.customers.audit  # noqa: E402,F401


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="session", autouse=True)
def override_sessionmaker(test_engine) -> Generator[None, None, None]:
    original_engine = getattr(db_session, "_engine")
    original_session_local = db_session.SessionLocal

    testing_session_local = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    db_session._engine = test_engine  # type: ignore[attr-defined]
    db_session.SessionLocal = testing_session_local

    yield

    db_session._engine = original_engine  # type: ignore[attr-defined]
    db_session.SessionLocal = original_session_local


@pytest.fixture(autouse=True)
def reset_database(test_engine) -> Generator[None, None, None]:
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)


@pytest.fixture
def db_session_fixture() -> Generator[Session, None, None]:
    with db_session.session_scope() as session:
        yield session


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def capture_logs(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level("INFO")
    return caplog


