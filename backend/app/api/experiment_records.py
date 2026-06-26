from datetime import date

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.common import api_response
from app.schemas.experiment_record import ExperimentRecordCreate, ExperimentRecordDetail, ExperimentRecordPage, ExperimentRecordUpdate
from app.services import experiment_records as record_service
from app.services import audit_logs as audit_service


router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_experiment_record(payload: ExperimentRecordCreate, db: DbSession, current_user: CurrentUser) -> dict:
    record = record_service.create_record(db, current_user, payload)
    detail = record_service.serialize_record_detail(record)
    return api_response(ExperimentRecordDetail.model_validate(detail).model_dump())


@router.get("")
def list_experiment_records(
    db: DbSession,
    current_user: CurrentUser,
    project_id: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    record_type: str | None = Query(default=None),
    type_filter: str | None = Query(default=None, alias="type"),
    creator_id: int | None = Query(default=None),
    owner_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    records = record_service.list_records(
        db,
        current_user,
        project_id=project_id,
        keyword=keyword,
        status_filter=status_filter,
        record_type=record_type if record_type is not None else type_filter,
        creator_id=creator_id,
        owner_id=owner_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return api_response(ExperimentRecordPage.model_validate(records).model_dump())


@router.get("/{record_id}")
def read_experiment_record(record_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    detail = record_service.read_record_detail(db, current_user, record_id)
    return api_response(ExperimentRecordDetail.model_validate(detail).model_dump())


@router.get("/{record_id}/timeline")
def read_experiment_record_timeline(record_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(audit_service.list_entity_timeline(db, current_user, "experiment", record_id))


@router.patch("/{record_id}")
def update_experiment_record(record_id: int, payload: ExperimentRecordUpdate, db: DbSession, current_user: CurrentUser) -> dict:
    record = record_service.update_record(db, current_user, record_id, payload)
    detail = record_service.serialize_record_detail(record)
    return api_response(ExperimentRecordDetail.model_validate(detail).model_dump())


@router.post("/{record_id}/submit")
def submit_experiment_record(record_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    record = record_service.submit_record(db, current_user, record_id)
    detail = record_service.serialize_record_detail(record)
    return api_response(ExperimentRecordDetail.model_validate(detail).model_dump())


@router.post("/{record_id}/archive")
def archive_experiment_record(record_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    record = record_service.archive_record(db, current_user, record_id)
    detail = record_service.serialize_record_detail(record)
    return api_response(ExperimentRecordDetail.model_validate(detail).model_dump())


@router.post("/{record_id}/dispense")
def dispense_experiment_record(record_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    record = record_service.dispense_record(db, current_user, record_id)
    return api_response(ExperimentRecordDetail.model_validate(record_service.serialize_record_detail(record)).model_dump())
