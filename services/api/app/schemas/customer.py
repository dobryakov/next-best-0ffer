from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from infra.db.models.customer import Customer, CustomerState

PHONE_PATTERN = r"^\+[1-9]\d{1,14}$"


class CustomerBase(BaseModel):
    email: EmailStr | None = Field(default=None)
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    segments: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("segments")
    @classmethod
    def validate_segments(cls, value: List[str]) -> List[str]:
        if len(value) > 20:
            raise ValueError("Не более 20 сегментов для одного покупателя.")
        return value

    @field_validator("attributes")
    @classmethod
    def validate_attributes_size(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        serialized = str(value)
        if len(serialized.encode("utf-8")) > 16 * 1024:
            raise ValueError("Суммарный размер атрибутов должен быть <= 16KB.")
        return value


class CustomerCreateRequest(CustomerBase):
    id: UUID


class CustomerUpdateRequest(CustomerBase):
    email: EmailStr | None = Field(default=None)
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    segments: Optional[List[str]] = Field(default=None)
    attributes: Optional[Dict[str, Any]] = Field(default=None)


class CustomerResponse(CustomerBase):
    id: UUID
    state: CustomerState
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(cls, customer: Customer) -> "CustomerResponse":
        return cls(
            id=UUID(customer.id),
            email=customer.email,
            phone=customer.phone,
            name=customer.name,
            segments=list(customer.segments or []),
            attributes=dict(customer.attributes or {}),
            state=CustomerState(str(customer.state)),
            version=customer.version,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
        )


