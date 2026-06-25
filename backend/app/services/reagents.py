from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.business import InventoryTxn, Reagent, ReagentLot
from app.models.user import User
from app.schemas.reagent import (
    LOT_STATUSES,
    TXN_TYPES,
    InventoryTxnCreate,
    ReagentCreate,
    ReagentLotCreate,
    ReagentLotUpdate,
    ReagentUpdate,
)


def is_admin(user: User) -> bool:
    return user.role == "admin"


def ensure_can_manage_reagent_master(user: User) -> None:
    if user.role not in {"admin", "director"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reagent master data permission required")


def ensure_can_operate_inventory(user: User) -> None:
    if user.role not in {"admin", "director"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inventory operation permission required")


def ensure_lot_status(value: str) -> None:
    if value not in LOT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reagent lot status")


def ensure_txn_type(value: str) -> None:
    if value not in TXN_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid inventory transaction type")


def get_reagent_or_404(db: Session, reagent_id: int) -> Reagent:
    reagent = db.get(Reagent, reagent_id)
    if reagent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reagent not found")
    return reagent


def get_lot_or_404(db: Session, lot_id: int) -> ReagentLot:
    lot = db.get(ReagentLot, lot_id)
    if lot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reagent lot not found")
    return lot


def get_txn_or_404(db: Session, txn_id: int) -> InventoryTxn:
    txn = db.get(InventoryTxn, txn_id)
    if txn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory transaction not found")
    return txn


def paginate(db: Session, stmt: Select, page: int, page_size: int) -> dict:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all())
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def list_reagents(
    db: Session,
    *,
    keyword: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = select(Reagent).order_by(Reagent.id)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                Reagent.name.ilike(pattern),
                Reagent.cas_no.ilike(pattern),
                Reagent.catalog_no.ilike(pattern),
                Reagent.manufacturer.ilike(pattern),
            )
        )
    if is_active is not None:
        stmt = stmt.where(Reagent.is_active.is_(is_active))
    return paginate(db, stmt, page, page_size)


def create_reagent(db: Session, current_user: User, payload: ReagentCreate) -> Reagent:
    ensure_can_manage_reagent_master(current_user)
    reagent = Reagent(**payload.model_dump(), created_by=current_user.id)
    db.add(reagent)
    db.commit()
    db.refresh(reagent)
    return reagent


def update_reagent(db: Session, current_user: User, reagent_id: int, payload: ReagentUpdate) -> Reagent:
    ensure_can_manage_reagent_master(current_user)
    reagent = get_reagent_or_404(db, reagent_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reagent, field, value)
    reagent.updated_by = current_user.id
    db.commit()
    db.refresh(reagent)
    return reagent


def deactivate_reagent(db: Session, current_user: User, reagent_id: int) -> Reagent:
    ensure_can_manage_reagent_master(current_user)
    reagent = get_reagent_or_404(db, reagent_id)
    reagent.is_active = False
    reagent.updated_by = current_user.id
    db.commit()
    db.refresh(reagent)
    return reagent


def list_reagent_lots(
    db: Session,
    *,
    reagent_id: int | None = None,
    keyword: str | None = None,
    status_filter: str | None = None,
    controlled_flag: bool | None = None,
    low_stock: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = select(ReagentLot).options(selectinload(ReagentLot.reagent)).order_by(ReagentLot.id)
    if keyword or low_stock:
        stmt = stmt.join(Reagent)
    if reagent_id is not None:
        stmt = stmt.where(ReagentLot.reagent_id == reagent_id)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                ReagentLot.lot_no.ilike(pattern),
                ReagentLot.location.ilike(pattern),
                Reagent.name.ilike(pattern),
                Reagent.cas_no.ilike(pattern),
                Reagent.catalog_no.ilike(pattern),
            )
        )
    if status_filter is not None:
        ensure_lot_status(status_filter)
        stmt = stmt.where(ReagentLot.status == status_filter)
    if controlled_flag is not None:
        stmt = stmt.where(ReagentLot.controlled_flag.is_(controlled_flag))
    if low_stock:
        stmt = stmt.where(Reagent.min_stock.is_not(None)).where(ReagentLot.quantity < Reagent.min_stock)
    return paginate(db, stmt, page, page_size)


def create_reagent_lot(db: Session, current_user: User, payload: ReagentLotCreate) -> ReagentLot:
    ensure_can_manage_reagent_master(current_user)
    get_reagent_or_404(db, payload.reagent_id)
    ensure_lot_status(payload.status)
    if Decimal(payload.quantity) != Decimal("0"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Initial lot quantity must be 0; use inventory transactions")
    lot = ReagentLot(**payload.model_dump(), created_by=current_user.id)
    db.add(lot)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reagent lot already exists") from exc
    db.refresh(lot)
    return lot


def update_reagent_lot(db: Session, current_user: User, lot_id: int, payload: ReagentLotUpdate) -> ReagentLot:
    ensure_can_manage_reagent_master(current_user)
    lot = get_lot_or_404(db, lot_id)
    updates = payload.model_dump(exclude_unset=True)
    if "reagent_id" in updates and updates["reagent_id"] is not None:
        get_reagent_or_404(db, updates["reagent_id"])
    if "status" in updates and updates["status"] is not None:
        ensure_lot_status(updates["status"])

    for field, value in updates.items():
        setattr(lot, field, value)
    lot.updated_by = current_user.id
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Reagent lot already exists") from exc
    db.refresh(lot)
    return lot


def deactivate_reagent_lot(db: Session, current_user: User, lot_id: int) -> ReagentLot:
    ensure_can_manage_reagent_master(current_user)
    lot = get_lot_or_404(db, lot_id)
    lot.status = "quarantined"
    lot.updated_by = current_user.id
    db.commit()
    db.refresh(lot)
    return lot


def _locked_lot(db: Session, lot_id: int) -> ReagentLot:
    lot = db.scalar(select(ReagentLot).where(ReagentLot.id == lot_id).with_for_update())
    if lot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reagent lot not found")
    return lot


def _positive_quantity(value: Decimal | None, label: str) -> Decimal:
    if value is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} is required")
    decimal_value = Decimal(value)
    if decimal_value <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} must be greater than 0")
    return decimal_value


def _calculate_inventory_change(lot: ReagentLot, payload: InventoryTxnCreate) -> tuple[Decimal, Decimal]:
    ensure_txn_type(payload.txn_type)
    current_quantity = Decimal(lot.quantity)

    if payload.txn_type == "in":
        txn_quantity = _positive_quantity(payload.quantity, "quantity")
        new_balance = current_quantity + txn_quantity
        return txn_quantity, new_balance
    elif payload.txn_type == "out":
        txn_quantity = _positive_quantity(payload.quantity, "quantity")
        if txn_quantity > current_quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient reagent lot quantity")
        return txn_quantity, current_quantity - txn_quantity
    else:
        if payload.target_quantity is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_quantity is required for adjust")
        target_quantity = Decimal(payload.target_quantity)
        if target_quantity < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_quantity must not be negative")
        return target_quantity - current_quantity, target_quantity


def create_inventory_txn(db: Session, current_user: User, payload: InventoryTxnCreate) -> InventoryTxn:
    ensure_can_operate_inventory(current_user)
    lot = _locked_lot(db, payload.reagent_lot_id)
    txn_quantity, new_balance = _calculate_inventory_change(lot, payload)
    operator_id = payload.operator_id or current_user.id

    lot.quantity = new_balance
    lot.status = "depleted" if new_balance == 0 else "in_stock"
    lot.updated_by = current_user.id
    txn = InventoryTxn(
        reagent_lot_id=lot.id,
        txn_type=payload.txn_type,
        quantity=txn_quantity,
        balance_after=new_balance,
        reference=payload.reference,
        operator_id=operator_id,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def list_inventory_txns(
    db: Session,
    *,
    reagent_lot_id: int | None = None,
    txn_type: str | None = None,
    txn_at_from: datetime | None = None,
    txn_at_to: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = select(InventoryTxn).order_by(InventoryTxn.id)
    if reagent_lot_id is not None:
        stmt = stmt.where(InventoryTxn.reagent_lot_id == reagent_lot_id)
    if txn_type is not None:
        ensure_txn_type(txn_type)
        stmt = stmt.where(InventoryTxn.txn_type == txn_type)
    if txn_at_from is not None:
        stmt = stmt.where(InventoryTxn.txn_at >= txn_at_from)
    if txn_at_to is not None:
        stmt = stmt.where(InventoryTxn.txn_at <= txn_at_to)
    return paginate(db, stmt, page, page_size)
