from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.api.infra.db.models.customer import Customer, CustomerState


class CustomerRepositoryError(Exception):
    """Базовая ошибка репозитория покупателей."""


class CustomerConflictError(CustomerRepositoryError):
    """Нарушение уникальности или идемпотентности данных покупателя."""


class CustomerNotFoundError(CustomerRepositoryError):
    """Запрошенный покупатель отсутствует в хранилище."""


@dataclass(slots=True)
class CustomerCreateDTO:
    id: str
    email: str | None
    phone: str | None
    name: str | None
    segments: List[str]
    attributes: Dict[str, Any]
    state: CustomerState = CustomerState.ACTIVE


@dataclass(slots=True)
class CustomerUpdateDTO:
    email: str | None = None
    phone: str | None = None
    name: str | None = None
    segments: List[str] | None = None
    attributes: Dict[str, Any] | None = None
    state: CustomerState | None = None


class CustomerRepository:
    """Репозиторий работы с покупателями и аудитом идемпотентности."""

    def get_by_id(self, session: Session, customer_id: str) -> Customer | None:
        return session.get(Customer, customer_id)

    def create(self, session: Session, dto: CustomerCreateDTO) -> Customer:
        now = datetime.now(tz=timezone.utc)
        customer = Customer(
            id=dto.id,
            email=dto.email,
            phone=dto.phone,
            name=dto.name,
            segments=list(dto.segments),
            attributes=dict(dto.attributes),
            state=dto.state,
            version=1,
            created_at=now,
            updated_at=now,
        )

        session.add(customer)

        try:
            session.flush()
        except IntegrityError as exc:  # pragma: no cover - защищаемся от дубликатов
            raise CustomerConflictError("customer already exists or violates uniqueness") from exc

        return customer

    def update(
        self,
        session: Session,
        customer: Customer,
        dto: CustomerUpdateDTO,
    ) -> Tuple[Customer, Dict[str, Dict[str, Any]]]:
        changes: Dict[str, Dict[str, Any]] = {}

        def _apply(field: str, new_value: Any) -> None:
            old_value = getattr(customer, field)
            if new_value == old_value:
                return
            changes[field] = {"old": old_value, "new": new_value}
            setattr(customer, field, new_value)

        if dto.email is not None:
            _apply("email", dto.email)
        if dto.phone is not None:
            _apply("phone", dto.phone)
        if dto.name is not None:
            _apply("name", dto.name)
        if dto.segments is not None:
            _apply("segments", list(dto.segments))
        if dto.attributes is not None:
            _apply("attributes", dict(dto.attributes))
        if dto.state is not None:
            _apply("state", dto.state)

        if changes:
            customer.version += 1
            customer.updated_at = datetime.now(tz=timezone.utc)

        try:
            session.flush()
        except IntegrityError as exc:
            raise CustomerConflictError("uniqueness violation during update") from exc

        return customer, changes


