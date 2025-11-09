from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.schemas.customer import (
    CustomerCreateRequest,
    CustomerResponse,
    CustomerUpdateRequest,
)
from domain.customers.repository import (
    CustomerConflictError,
    CustomerNotFoundError,
)
from domain.customers.service import CustomerService
from infra.db.session import get_session

router = APIRouter(tags=["Customers"])


def get_customer_service() -> CustomerService:
    return CustomerService()


@router.post(
    "/customers",
    summary="Создание нового покупателя",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    payload: CustomerCreateRequest,
    request: Request,
    session: Session = Depends(get_session),
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    trace_id = getattr(request.state, "trace_id", None)
    data = payload.model_dump()

    try:
        customer = service.create_customer(
            session,
            trace_id,
            customer_id=str(data["id"]),
            email=data.get("email"),
            phone=data.get("phone"),
            name=data.get("name"),
            segments=data.get("segments", []),
            attributes=data.get("attributes", {}),
        )
    except CustomerConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer already exists or violates uniqueness constraints.",
        ) from exc

    return CustomerResponse.from_orm_model(customer)


@router.put(
    "/customer/{customer_id}",
    summary="Обновление существующего покупателя",
    response_model=CustomerResponse,
)
def update_customer(
    customer_id: str,
    payload: CustomerUpdateRequest,
    request: Request,
    session: Session = Depends(get_session),
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    trace_id = getattr(request.state, "trace_id", None)
    data = payload.model_dump(exclude_unset=True)

    try:
        customer = service.update_customer(
            session,
            trace_id,
            customer_id=customer_id,
            email=data.get("email"),
            phone=data.get("phone"),
            name=data.get("name"),
            segments=data.get("segments"),
            attributes=data.get("attributes"),
        )
    except CustomerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found.",
        ) from exc
    except CustomerConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer update violates uniqueness constraints.",
        ) from exc

    return CustomerResponse.from_orm_model(customer)


