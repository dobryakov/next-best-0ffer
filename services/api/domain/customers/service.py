from __future__ import annotations

from typing import Any, Dict, Tuple

import structlog
from sqlalchemy.orm import Session

from domain.customers.repository import (
    CustomerConflictError,
    CustomerCreateDTO,
    CustomerNotFoundError,
    CustomerRepository,
    CustomerUpdateDTO,
)
from domain.customers.audit import CustomerAuditTrail
from infra.db.models.customer import Customer, CustomerState


class CustomerService:
    """Бизнес-логика управления покупателями, сегментами и аудитом изменений."""

    def __init__(
        self,
        repository: CustomerRepository | None = None,
        audit_trail: CustomerAuditTrail | None = None,
    ) -> None:
        self._repository = repository or CustomerRepository()
        self._audit_trail = audit_trail or CustomerAuditTrail()
        self._logger = structlog.get_logger(__name__)

    def create_customer(
        self,
        session: Session,
        trace_id: str | None,
        *,
        customer_id: str,
        email: str | None,
        phone: str | None,
        name: str | None,
        segments: list[str],
        attributes: Dict[str, Any],
        state: CustomerState = CustomerState.ACTIVE,
    ) -> Customer:
        dto = CustomerCreateDTO(
            id=customer_id,
            email=email,
            phone=phone,
            name=name,
            segments=segments,
            attributes=attributes,
            state=state,
        )

        customer = self._repository.create(session, dto)
        self._audit_trail.record_created(session, customer, trace_id=trace_id)
        self._logger.info(
            "customer.created",
            customer_id=customer.id,
            trace_id=trace_id,
            segments=customer.segments,
        )
        return customer

    def update_customer(
        self,
        session: Session,
        trace_id: str | None,
        *,
        customer_id: str,
        email: str | None,
        phone: str | None,
        name: str | None,
        segments: list[str] | None,
        attributes: Dict[str, Any] | None,
        state: CustomerState | None = None,
    ) -> Customer:
        customer = self._repository.get_by_id(session, customer_id)
        if customer is None:
            raise CustomerNotFoundError(f"Customer {customer_id} not found")

        dto = CustomerUpdateDTO(
            email=email,
            phone=phone,
            name=name,
            segments=segments,
            attributes=attributes,
            state=state,
        )

        customer, changes = self._repository.update(session, customer, dto)
        self._maybe_record_update(session, customer, changes, trace_id)
        return customer

    def _maybe_record_update(
        self,
        session: Session,
        customer: Customer,
        changes: Dict[str, Dict[str, Any]],
        trace_id: str | None,
    ) -> None:
        if not changes:
            self._logger.info(
                "customer.update.noop",
                customer_id=customer.id,
                trace_id=trace_id,
            )
            return

        self._audit_trail.record_updated(
            session,
            customer,
            trace_id=trace_id,
            changes=changes,
        )
        self._logger.info(
            "customer.updated",
            customer_id=customer.id,
            trace_id=trace_id,
            changed_fields=list(changes.keys()),
        )


