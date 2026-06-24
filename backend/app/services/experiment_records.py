from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.business import ExperimentAttachment, ExperimentReagentUsage, ExperimentRecord, Project, ProjectMember, Reagent, ReagentLot
from app.models.user import User
from app.schemas.experiment_record import (
    EXPERIMENT_ATTACHMENT_TYPES,
    EXPERIMENT_RECORD_ADMIN_ROLES,
    EXPERIMENT_RECORD_CREATE_ROLES,
    EXPERIMENT_RECORD_STATUSES,
    EXPERIMENT_RECORD_TYPES,
    EXPERIMENT_RECORD_VIEW_ALL_ROLES,
    ExperimentAttachmentCreate,
    ExperimentRecordCreate,
    ExperimentRecordUpdate,
    ExperimentReagentUsageCreate,
)
from app.services.projects import get_existing_project, is_project_manager, is_project_member, user_brief


def is_view_all_user(user: User) -> bool:
    return user.role in EXPERIMENT_RECORD_VIEW_ALL_ROLES


def ensure_record_status(value: str) -> None:
    if value not in EXPERIMENT_RECORD_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid experiment record status")


def ensure_record_type(value: str) -> None:
    if value not in EXPERIMENT_RECORD_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid experiment record type")


def ensure_attachment_type(value: str) -> None:
    if value not in EXPERIMENT_ATTACHMENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid experiment attachment type")


def ensure_can_create_record(db: Session, user: User, project_id: int) -> Project:
    if user.role not in EXPERIMENT_RECORD_CREATE_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Experiment record create permission required")
    project = get_existing_project(db, project_id)
    if user.role in {"admin", "pm"} or is_project_member(db, user, project_id):
        return project
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project membership required")


def ensure_can_view_record(db: Session, user: User, record: ExperimentRecord) -> None:
    if is_view_all_user(user) or record.creator_id == user.id or is_project_member(db, user, record.project_id):
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment record not found")


def ensure_can_submit_record(db: Session, user: User, record: ExperimentRecord) -> None:
    if record.creator_id == user.id or record.owner_id == user.id or is_project_manager(db, user, record.project_id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Experiment record submit permission required")


def ensure_can_archive_record(user: User) -> None:
    if user.role not in EXPERIMENT_RECORD_ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Experiment record archive permission required")


def validate_owner(db: Session, owner_id: int | None) -> None:
    if owner_id is None:
        return
    user = db.get(User, owner_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner user not found")


def record_options(stmt: Select[tuple[ExperimentRecord]]) -> Select[tuple[ExperimentRecord]]:
    return stmt.options(
        selectinload(ExperimentRecord.project),
        selectinload(ExperimentRecord.creator),
        selectinload(ExperimentRecord.owner),
        selectinload(ExperimentRecord.reagent_usages),
        selectinload(ExperimentRecord.attachments),
    )


def get_record_or_404(db: Session, record_id: int) -> ExperimentRecord:
    record = db.scalar(record_options(select(ExperimentRecord).where(ExperimentRecord.id == record_id, ExperimentRecord.is_deleted.is_(False))))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment record not found")
    return record


def filter_records_for_user(stmt: Select[tuple[ExperimentRecord]], db: Session, user: User) -> Select[tuple[ExperimentRecord]]:
    stmt = stmt.where(ExperimentRecord.is_deleted.is_(False))
    if is_view_all_user(user):
        return stmt
    member_project_ids = select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
    return stmt.where(or_(ExperimentRecord.creator_id == user.id, ExperimentRecord.project_id.in_(member_project_ids)))


def paginate(db: Session, stmt: Select[tuple[ExperimentRecord]], page: int, page_size: int) -> dict:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(record_options(stmt.offset((page - 1) * page_size).limit(page_size))).all())
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _has_project(project_id: int):
    return exists().where(Project.id == project_id, Project.is_deleted.is_(False))


def list_records(
    db: Session,
    user: User,
    *,
    project_id: int | None = None,
    keyword: str | None = None,
    status_filter: str | None = None,
    record_type: str | None = None,
    creator_id: int | None = None,
    owner_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = select(ExperimentRecord).order_by(ExperimentRecord.id)
    stmt = filter_records_for_user(stmt, db, user).where(_has_project(ExperimentRecord.project_id))
    if project_id is not None:
        stmt = stmt.where(ExperimentRecord.project_id == project_id)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                ExperimentRecord.code.ilike(pattern),
                ExperimentRecord.title.ilike(pattern),
                ExperimentRecord.objective.ilike(pattern),
                ExperimentRecord.result_summary.ilike(pattern),
            )
        )
    if status_filter is not None:
        ensure_record_status(status_filter)
        stmt = stmt.where(ExperimentRecord.status == status_filter)
    if record_type is not None:
        ensure_record_type(record_type)
        stmt = stmt.where(ExperimentRecord.record_type == record_type)
    if creator_id is not None:
        stmt = stmt.where(ExperimentRecord.creator_id == creator_id)
    if owner_id is not None:
        stmt = stmt.where(ExperimentRecord.owner_id == owner_id)
    if date_from is not None:
        stmt = stmt.where(ExperimentRecord.experiment_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(ExperimentRecord.experiment_date <= date_to)
    page_data = paginate(db, stmt, page, page_size)
    return {
        "items": [serialize_record_list_item(record) for record in page_data["items"]],
        "total": page_data["total"],
        "page": page_data["page"],
        "page_size": page_data["page_size"],
    }


def _build_usage(db: Session, payload: ExperimentReagentUsageCreate, current_user_id: int) -> ExperimentReagentUsage:
    usage_data = payload.model_dump()
    reagent = db.get(Reagent, payload.reagent_id) if payload.reagent_id is not None else None
    lot = db.get(ReagentLot, payload.lot_id) if payload.lot_id is not None else None
    if payload.reagent_id is not None and reagent is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reagent not found")
    if payload.lot_id is not None and lot is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reagent lot not found")
    if lot is not None and reagent is not None and lot.reagent_id != reagent.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reagent lot does not belong to reagent")
    if usage_data.get("reagent_name_snapshot") is None and reagent is not None:
        usage_data["reagent_name_snapshot"] = reagent.name
    if usage_data.get("lot_code_snapshot") is None and lot is not None:
        usage_data["lot_code_snapshot"] = lot.lot_no
    return ExperimentReagentUsage(**usage_data, created_by=current_user_id)


def _build_attachment(payload: ExperimentAttachmentCreate, current_user_id: int) -> ExperimentAttachment:
    ensure_attachment_type(payload.file_type)
    return ExperimentAttachment(**payload.model_dump(), uploaded_by=current_user_id, created_by=current_user_id)


def create_record(db: Session, current_user: User, payload: ExperimentRecordCreate) -> ExperimentRecord:
    ensure_record_type(payload.record_type)
    ensure_record_status(payload.status)
    ensure_can_create_record(db, current_user, payload.project_id)
    validate_owner(db, payload.owner_id)
    data = payload.model_dump(exclude={"reagent_usages", "attachments"})
    record = ExperimentRecord(**data, creator_id=current_user.id, created_by=current_user.id)
    record.reagent_usages = [_build_usage(db, usage, current_user.id) for usage in payload.reagent_usages]
    record.attachments = [_build_attachment(attachment, current_user.id) for attachment in payload.attachments]
    db.add(record)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Experiment record code already exists") from exc
    return get_record_or_404(db, record.id)


def update_record(db: Session, current_user: User, record_id: int, payload: ExperimentRecordUpdate) -> ExperimentRecord:
    record = get_record_or_404(db, record_id)
    ensure_can_view_record(db, current_user, record)
    updates = payload.model_dump(exclude_unset=True)
    if "record_type" in updates and updates["record_type"] is not None:
        ensure_record_type(updates["record_type"])
    if "status" in updates and updates["status"] is not None:
        ensure_record_status(updates["status"])
    if "owner_id" in updates:
        validate_owner(db, updates["owner_id"])
    reagent_usages = updates.pop("reagent_usages", None)
    attachments = updates.pop("attachments", None)
    for field, value in updates.items():
        setattr(record, field, value)
    if reagent_usages is not None:
        record.reagent_usages = [_build_usage(db, usage, current_user.id) for usage in payload.reagent_usages or []]
    if attachments is not None:
        record.attachments = [_build_attachment(attachment, current_user.id) for attachment in payload.attachments or []]
    record.updated_by = current_user.id
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Experiment record code already exists") from exc
    return get_record_or_404(db, record.id)


def read_record_detail(db: Session, current_user: User, record_id: int) -> dict:
    record = get_record_or_404(db, record_id)
    ensure_can_view_record(db, current_user, record)
    return serialize_record_detail(record)


def submit_record(db: Session, current_user: User, record_id: int) -> ExperimentRecord:
    record = get_record_or_404(db, record_id)
    ensure_can_view_record(db, current_user, record)
    ensure_can_submit_record(db, current_user, record)
    if record.status not in {"draft", "in_progress"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft or in_progress records can be submitted")
    record.status = "submitted"
    record.updated_by = current_user.id
    db.commit()
    return get_record_or_404(db, record.id)


def archive_record(db: Session, current_user: User, record_id: int) -> ExperimentRecord:
    ensure_can_archive_record(current_user)
    record = get_record_or_404(db, record_id)
    record.status = "archived"
    record.updated_by = current_user.id
    db.commit()
    return get_record_or_404(db, record.id)


def serialize_record_list_item(record: ExperimentRecord) -> dict:
    return {
        "id": record.id,
        "code": record.code,
        "title": record.title,
        "project_id": record.project_id,
        "project_code": record.project.project_code,
        "project_name": record.project.name,
        "record_type": record.record_type,
        "status": record.status,
        "creator": user_brief(record.creator),
        "owner": user_brief(record.owner),
        "experiment_date": record.experiment_date,
        "updated_at": record.updated_at,
        "attachment_count": len(record.attachments),
        "reagent_usage_count": len(record.reagent_usages),
    }


def serialize_record_detail(record: ExperimentRecord) -> dict:
    item = serialize_record_list_item(record)
    item.update(
        {
            "project": {"id": record.project.id, "code": record.project.project_code, "name": record.project.name},
            "creator_id": record.creator_id,
            "owner_id": record.owner_id,
            "objective": record.objective,
            "procedure": record.procedure,
            "result_summary": record.result_summary,
            "conclusion": record.conclusion,
            "next_step": record.next_step,
            "risk_note": record.risk_note,
            "reagent_usages": record.reagent_usages,
            "attachments": record.attachments,
            "created_at": record.created_at,
        }
    )
    return item
