from __future__ import annotations

from typing import Any, Dict

import structlog
from sqlalchemy.orm import Session

from services.api.infra.db.models.customer import Customer, CustomerAuditLog


class CustomerAuditTrail:
    """Фиксация версий покупателей и публикация событий для мониторинга."""

    def __init__(self) -> None:
        self._logger = structlog.get_logger("customer_audit")

    def record_created(self, session: Session, customer: Customer, trace_id: str | None) -> None:
        payload = self._serialize_customer(customer)
        audit_entry = CustomerAuditLog(
            customer_id=customer.id,
            version=customer.version,
            change_type="created",
            payload=payload,
            trace_id=trace_id,
        )
        session.add(audit_entry)
        self._logger.info(
            "customer_audit.created",
            customer_id=customer.id,
            version=customer.version,
            trace_id=trace_id,
            payload=payload,
        )

    def record_updated(
        self,
        session: Session,
        customer: Customer,
        *,
        trace_id: str | None,
        changes: Dict[str, Dict[str, Any]],
    ) -> None:
        payload = self._serialize_customer(customer)
        audit_entry = CustomerAuditLog(
            customer_id=customer.id,
            version=customer.version,
            change_type="updated",
            payload=payload,
            trace_id=trace_id,
        )
        session.add(audit_entry)
        self._logger.info(
            "customer_audit.updated",
            customer_id=customer.id,
            version=customer.version,
            trace_id=trace_id,
            changes=changes,
            payload=payload,
        )

    @staticmethod
    def _serialize_customer(customer: Customer) -> Dict[str, Any]:
        return {
            "id": customer.id,
            "email": customer.email,
            "phone": customer.phone,
            "name": customer.name,
            "segments": list(customer.segments or []),
            "attributes": dict(customer.attributes or {}),
            "state": customer.state.value if hasattr(customer.state, "value") else customer.state,
            "version": customer.version,
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
            "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
        }


