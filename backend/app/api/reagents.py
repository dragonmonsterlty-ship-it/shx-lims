from datetime import datetime

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.common import api_response
from app.schemas.reagent import (
    InventoryTxnCreate,
    InventoryTxnRead,
    ReagentCreate,
    ReagentLotCreate,
    ReagentLotRead,
    ReagentLotUpdate,
    ReagentRead,
    ReagentUpdate,
)
from app.services import reagents as reagent_service


reagents_router = APIRouter()
reagent_lots_router = APIRouter()
inventory_txns_router = APIRouter()


def paged_response(page_data: dict, read_model: type) -> dict:
    return api_response(
        {
            "items": [read_model.model_validate(item).model_dump() for item in page_data["items"]],
            "total": page_data["total"],
            "page": page_data["page"],
            "page_size": page_data["page_size"],
        }
    )


@reagents_router.post("", status_code=status.HTTP_201_CREATED)
def create_reagent(payload: ReagentCreate, db: DbSession, current_user: CurrentUser) -> dict:
    reagent = reagent_service.create_reagent(db, current_user, payload)
    return api_response(ReagentRead.model_validate(reagent).model_dump())


@reagents_router.get("")
def list_reagents(
    db: DbSession,
    current_user: CurrentUser,
    keyword: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    _ = current_user
    reagents = reagent_service.list_reagents(db, keyword=keyword, is_active=is_active, page=page, page_size=page_size)
    return paged_response(reagents, ReagentRead)


@reagents_router.get("/{reagent_id}")
def read_reagent(reagent_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    _ = current_user
    reagent = reagent_service.get_reagent_or_404(db, reagent_id)
    return api_response(ReagentRead.model_validate(reagent).model_dump())


@reagents_router.patch("/{reagent_id}")
def update_reagent(reagent_id: int, payload: ReagentUpdate, db: DbSession, current_user: CurrentUser) -> dict:
    reagent = reagent_service.update_reagent(db, current_user, reagent_id, payload)
    return api_response(ReagentRead.model_validate(reagent).model_dump())


@reagents_router.delete("/{reagent_id}")
def delete_reagent(reagent_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    reagent = reagent_service.deactivate_reagent(db, current_user, reagent_id)
    return api_response(ReagentRead.model_validate(reagent).model_dump())


@reagent_lots_router.post("", status_code=status.HTTP_201_CREATED)
def create_reagent_lot(payload: ReagentLotCreate, db: DbSession, current_user: CurrentUser) -> dict:
    lot = reagent_service.create_reagent_lot(db, current_user, payload)
    return api_response(ReagentLotRead.model_validate(lot).model_dump())


@reagent_lots_router.get("")
def list_reagent_lots(
    db: DbSession,
    current_user: CurrentUser,
    reagent_id: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    controlled_flag: bool | None = Query(default=None),
    low_stock: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    _ = current_user
    lots = reagent_service.list_reagent_lots(
        db,
        reagent_id=reagent_id,
        keyword=keyword,
        status_filter=status_filter,
        controlled_flag=controlled_flag,
        low_stock=low_stock,
        page=page,
        page_size=page_size,
    )
    return paged_response(lots, ReagentLotRead)


@reagent_lots_router.get("/low-stock")
def list_low_stock_reagent_lots(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    _ = current_user
    lots = reagent_service.list_reagent_lots(db, low_stock=True, page=page, page_size=page_size)
    return paged_response(lots, ReagentLotRead)


@reagent_lots_router.get("/{lot_id}")
def read_reagent_lot(lot_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    _ = current_user
    lot = reagent_service.get_lot_or_404(db, lot_id)
    return api_response(ReagentLotRead.model_validate(lot).model_dump())


@reagent_lots_router.patch("/{lot_id}")
def update_reagent_lot(lot_id: int, payload: ReagentLotUpdate, db: DbSession, current_user: CurrentUser) -> dict:
    lot = reagent_service.update_reagent_lot(db, current_user, lot_id, payload)
    return api_response(ReagentLotRead.model_validate(lot).model_dump())


@reagent_lots_router.delete("/{lot_id}")
def delete_reagent_lot(lot_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    lot = reagent_service.deactivate_reagent_lot(db, current_user, lot_id)
    return api_response(ReagentLotRead.model_validate(lot).model_dump())


@inventory_txns_router.post("", status_code=status.HTTP_201_CREATED)
def create_inventory_txn(payload: InventoryTxnCreate, db: DbSession, current_user: CurrentUser) -> dict:
    txn = reagent_service.create_inventory_txn(db, current_user, payload)
    return api_response(InventoryTxnRead.model_validate(txn).model_dump())


@inventory_txns_router.get("")
def list_inventory_txns(
    db: DbSession,
    current_user: CurrentUser,
    reagent_lot_id: int | None = Query(default=None),
    txn_type: str | None = Query(default=None),
    txn_at_from: datetime | None = Query(default=None),
    txn_at_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    _ = current_user
    txns = reagent_service.list_inventory_txns(
        db,
        reagent_lot_id=reagent_lot_id,
        txn_type=txn_type,
        txn_at_from=txn_at_from,
        txn_at_to=txn_at_to,
        page=page,
        page_size=page_size,
    )
    return paged_response(txns, InventoryTxnRead)


@inventory_txns_router.get("/{txn_id}")
def read_inventory_txn(txn_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    _ = current_user
    txn = reagent_service.get_txn_or_404(db, txn_id)
    return api_response(InventoryTxnRead.model_validate(txn).model_dump())
