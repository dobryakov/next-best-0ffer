from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс SQLAlchemy моделей проекта."""


metadata = Base.metadata


