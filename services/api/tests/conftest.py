from __future__ import annotations

import os
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Глобальные переменные окружения для корректной инициализации настроек FastAPI-приложения
os.environ.setdefault("POSTGRES_DSN", "postgresql+psycopg://nbo:nbo@postgres:5432/nbo")
os.environ.setdefault("REDIS_URL", "redis://redis:6379/0")
os.environ.setdefault("ALS_FACTORS", "32")
os.environ.setdefault("ALS_REG", "0.05")
os.environ.setdefault("LGBM_MODEL_PATH", "/opt/models/lgbm-test.bin")

from services.api.app.main import create_app  # noqa: E402
from services.api.infra.db import session as db_session  # noqa: E402
from services.api.infra.db.models import Base  # noqa: E402
import services.api.infra.db.models.customer  # noqa: E402,F401
import services.api.domain.customers.audit  # noqa: E402,F401


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


