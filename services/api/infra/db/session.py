from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from infra.config.settings import get_settings

_settings = get_settings()

_engine: Engine = create_engine(
    str(_settings.postgres_dsn),
    echo=_settings.db_echo,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
    pool_timeout=_settings.db_pool_timeout,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_engine() -> Engine:
    """Возвращает singleton экземпляр SQLAlchemy Engine."""

    return _engine


@contextmanager
def session_scope() -> Iterator[Session]:
    """Контекстный менеджер для безопасной работы с сессией."""

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Generator[Session, None, None]:
    """Зависимость FastAPI для инъекции сессии."""

    with session_scope() as session:
        yield session


