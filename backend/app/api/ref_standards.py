from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.common import ApiResponse, api_response
from app.schemas.ref_standard import (
    RefStandardCreate,
    RefStandardPage,
    RefStandardRead,
    RefStandardSource,
    RefStandardStatus,
    RefStandardUpdate,
)
from app.services import ref_standards as ref_standard_service


router = APIRouter()


@router.get("", response_model=ApiResponse[RefStandardPage])
def list_ref_standards(
    db: DbSession,
    current_user: CurrentUser,
    keyword: str | None = Query(default=None),
    code: str | None = Query(default=None),
    name: str | None = Query(default=None),
    batch_no: str | None = Query(default=None),
    source: RefStandardSource | None = Query(default=None),
    status_filter: RefStandardStatus | None = Query(default=None, alias="status"),
    expiring_within_days: int | None = Query(default=None, ge=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    page_data = ref_standard_service.list_ref_standards(
        db,
        current_user,
        keyword=keyword,
        code=code,
        name=name,
        batch_no=batch_no,
        source=source.value if source is not None else None,
        status_filter=status_filter.value if status_filter is not None else None,
        expiring_within_days=expiring_within_days,
        page=page,
        page_size=page_size,
    )
    return api_response(
        RefStandardPage(
            items=[RefStandardRead.model_validate(item) for item in page_data["items"]],
            total=page_data["total"],
            page=page_data["page"],
            page_size=page_data["page_size"],
        )
    )


@router.post("", response_model=ApiResponse[RefStandardRead], status_code=status.HTTP_201_CREATED)
def create_ref_standard(
    payload: RefStandardCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    standard = ref_standard_service.create_ref_standard(db, current_user, payload)
    return api_response(RefStandardRead.model_validate(standard))


@router.get("/{standard_id}", response_model=ApiResponse[RefStandardRead])
def read_ref_standard(standard_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    standard = ref_standard_service.read_ref_standard(db, current_user, standard_id)
    return api_response(RefStandardRead.model_validate(standard))


@router.patch("/{standard_id}", response_model=ApiResponse[RefStandardRead])
def update_ref_standard(
    standard_id: int,
    payload: RefStandardUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    standard = ref_standard_service.update_ref_standard(db, current_user, standard_id, payload)
    return api_response(RefStandardRead.model_validate(standard))


@router.post("/{standard_id}/dispose", response_model=ApiResponse[RefStandardRead])
def dispose_ref_standard(standard_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    standard = ref_standard_service.dispose_ref_standard(db, current_user, standard_id)
    return api_response(RefStandardRead.model_validate(standard))
