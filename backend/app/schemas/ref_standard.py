from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RefStandardSource(StrEnum):
    self_made = "self_made"
    purchased = "purchased"


class RefStandardStatus(StrEnum):
    in_stock = "in_stock"
    depleted = "depleted"
    disposed = "disposed"


class RefStandardCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    batch_no: str | None = Field(default=None, max_length=80)
    source: RefStandardSource
    spec: str | None = Field(default=None, max_length=200)
    assigned_value: str | None = None
    initial_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    unit: str | None = Field(default=None, max_length=30)
    storage_condition: str | None = Field(default=None, max_length=100)
    expires_at: date | None = None
    notes: str | None = None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_manual_code(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("code must not be blank")
        return normalized

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized


class RefStandardUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    batch_no: str | None = Field(default=None, max_length=80)
    source: RefStandardSource | None = None
    spec: str | None = Field(default=None, max_length=200)
    assigned_value: str | None = None
    unit: str | None = Field(default=None, max_length=30)
    storage_condition: str | None = Field(default=None, max_length=100)
    expires_at: date | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized


class RefStandardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    batch_no: str | None = None
    source: RefStandardSource
    spec: str | None = None
    assigned_value: str | None = None
    initial_amount: Decimal
    current_amount: Decimal
    unit: str | None = None
    storage_condition: str | None = None
    expires_at: date | None = None
    status: RefStandardStatus
    notes: str | None = None
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime | None = None
    is_deleted: bool


class RefStandardPage(BaseModel):
    items: list[RefStandardRead]
    total: int
    page: int
    page_size: int
