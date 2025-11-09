from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase

# Модули моделей импортируются для регистрации в metadata при инициализации Alembic.
class Base(DeclarativeBase):
    """Базовый класс SQLAlchemy моделей проекта."""


metadata = Base.metadata


# Импортируем подмодули моделей после определения Base, чтобы они зарегистрировались в metadata.
from infra.db.models import customer  # noqa: E402,F401,E702
from infra.db.models import event  # noqa: E402,F401,E702

