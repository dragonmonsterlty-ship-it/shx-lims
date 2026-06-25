from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


LOT_STATUSES = {"in_stock", "depleted", "expired", "quarantined"}
TXN_TYPES = {"in", "out", "adjust"}


class ReagentBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    cas_no: str | None = Field(default=None, max_length=30)
    catalog_no: str | None = Field(default=None, max_length=80)
    manufacturer: str | None = Field(default=None, max_length=120)
    grade: str | None = Field(default=None, max_length=50)
    default_unit: str | None = Field(default=None, max_length=30)
    min_stock: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    is_active: bool = True


class ReagentCreate(ReagentBase):
    pass


class ReagentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    cas_no: str | None = Field(default=None, max_length=30)
    catalog_no: str | None = Field(default=None, max_length=80)
    manufacturer: str | None = Field(default=None, max_length=120)
    grade: str | None = Field(default=None, max_length=50)
    default_unit: str | None = Field(default=None, max_length=30)
    min_stock: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    is_active: bool | None = None


class ReagentRead(ReagentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_by: int | None = None
    created_at: datetime
    updated_by: int | None = None
    updated_at: datetime | None = None


class ReagentLotBase(BaseModel):
    reagent_id: int
    lot_no: str = Field(min_length=1, max_length=80)
    expiry_date: date | None = None
    unit: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=120)
    storage_condition: str | None = Field(default=None, max_length=100)
    opened_at: date | None = None
    controlled_flag: bool = False
    status: str = Field(default="in_stock", max_length=20)


class ReagentLotCreate(ReagentLotBase):
    quantity: Decimal = Field(default=Decimal("0"), max_digits=18, decimal_places=4)


class ReagentLotUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reagent_id: int | None = None
    lot_no: str | None = Field(default=None, min_length=1, max_length=80)
    expiry_date: date | None = None
    unit: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=120)
    storage_condition: str | None = Field(default=None, max_length=100)
    opened_at: date | None = None
    controlled_flag: bool | None = None
    status: str | None = Field(default=None, max_length=20)


class ReagentLotRead(ReagentLotBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quantity: Decimal
    created_by: int | None = None
    created_at: datetime
    updated_by: int | None = None
    updated_at: datetime | None = None


class InventoryTxnCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reagent_lot_id: int
    txn_type: str = Field(max_length=10)
    quantity: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    target_quantity: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    reference: str | None = Field(default=None, max_length=200)
    operator_id: int | None = None


class InventoryTxnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reagent_lot_id: int
    txn_type: str
    quantity: Decimal
    balance_after: Decimal | None = None
    reference: str | None = None
    operator_id: int | None = None
    txn_at: datetime
    source_type: str = "manual"
    source_id: int | None = None
    shortage_qty: Decimal | None = None
