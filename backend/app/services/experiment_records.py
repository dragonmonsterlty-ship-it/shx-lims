from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.business import (
    ExperimentAttachment,
    ExperimentReagentUsage,
    ExperimentRecord,
    ExperimentRecordParticipant,
    InventoryTxn,
    Project,
    ProjectMember,
    Reagent,
    ReagentLot,
)
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
    if user.role in {"admin", "director"} or is_project_member(db, user, project_id):
        return project
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project membership required")


def ensure_can_view_record(db: Session, user: User, record: ExperimentRecord) -> None:
    if is_view_all_user(user):
        return
    if user.role == "project_manager" and is_project_manager(db, user, record.project_id):
        return
    if user.role == "operator" and (
        record.creator_id == user.id
        or record.owner_id == user.id
        or any(item.user_id == user.id for item in record.participants)
    ):
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment record not found")


def ensure_can_submit_record(db: Session, user: User, record: ExperimentRecord) -> None:
    if record.creator_id == user.id or record.owner_id == user.id or is_project_manager(db, user, record.project_id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Experiment record submit permission required")


def ensure_can_edit_record(db: Session, user: User, record: ExperimentRecord) -> None:
    if user.role == "admin":
        return
    if user.role == "project_manager" and is_project_manager(db, user, record.project_id):
        return
    if user.role == "operator" and (
        record.creator_id == user.id
        or record.owner_id == user.id
        or any(item.user_id == user.id for item in record.participants)
    ):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Experiment record edit permission required")


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
        selectinload(ExperimentRecord.participants),
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
    if user.role == "project_manager":
        managed_project_ids = select(ProjectMember.project_id).where(
            ProjectMember.user_id == user.id,
            ProjectMember.role_in_project == "manager",
        )
        return stmt.where(ExperimentRecord.project_id.in_(managed_project_ids))
    participant_records = select(ExperimentRecordParticipant.experiment_record_id).where(
        ExperimentRecordParticipant.user_id == user.id
    )
    return stmt.where(
        or_(
            ExperimentRecord.creator_id == user.id,
            ExperimentRecord.owner_id == user.id,
            ExperimentRecord.id.in_(participant_records),
        )
    )


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
    if lot is not None and reagent is None:
        reagent = lot.reagent
        usage_data["reagent_id"] = lot.reagent_id
    if lot is not None and reagent is not None and lot.reagent_id != reagent.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reagent lot does not belong to reagent")
    if usage_data.get("reagent_name_snapshot") is None and reagent is not None:
        usage_data["reagent_name_snapshot"] = reagent.name
    if usage_data.get("lot_code_snapshot") is None and lot is not None:
        usage_data["lot_code_snapshot"] = lot.lot_no
    return ExperimentReagentUsage(**usage_data, created_by=current_user_id)


def _participant_rows(db: Session, project_id: int, participant_ids: list[int]) -> list[ExperimentRecordParticipant]:
    unique_ids = list(dict.fromkeys(participant_ids))
    if not unique_ids:
        return []
    project_user_ids = set(
        db.scalars(select(ProjectMember.user_id).where(ProjectMember.project_id == project_id)).all()
    )
    active_user_ids = set(
        db.scalars(select(User.id).where(User.id.in_(unique_ids), User.is_active.is_(True))).all()
    )
    if set(unique_ids) - project_user_ids or set(unique_ids) - active_user_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Participants must be active project members")
    return [ExperimentRecordParticipant(user_id=user_id) for user_id in unique_ids]


def _build_attachment(payload: ExperimentAttachmentCreate, current_user_id: int) -> ExperimentAttachment:
    ensure_attachment_type(payload.file_type)
    return ExperimentAttachment(**payload.model_dump(), uploaded_by=current_user_id, created_by=current_user_id)


def create_record(db: Session, current_user: User, payload: ExperimentRecordCreate) -> ExperimentRecord:
    ensure_record_type(payload.record_type)
    ensure_record_status(payload.status)
    ensure_can_create_record(db, current_user, payload.project_id)
    validate_owner(db, payload.owner_id)
    data = payload.model_dump(exclude={"reagent_usages", "attachments", "participant_ids"})
    record = ExperimentRecord(**data, creator_id=current_user.id, created_by=current_user.id)
    record.participants = _participant_rows(db, payload.project_id, payload.participant_ids)
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
    ensure_can_edit_record(db, current_user, record)
    updates = payload.model_dump(exclude_unset=True)
    if "record_type" in updates and updates["record_type"] is not None:
        ensure_record_type(updates["record_type"])
    if "status" in updates and updates["status"] is not None:
        ensure_record_status(updates["status"])
    if "owner_id" in updates:
        validate_owner(db, updates["owner_id"])
    reagent_usages = updates.pop("reagent_usages", None)
    attachments = updates.pop("attachments", None)
    participant_ids = updates.pop("participant_ids", None)
    for field, value in updates.items():
        setattr(record, field, value)
    if reagent_usages is not None:
        completed_usages = [usage for usage in record.reagent_usages if usage.outbound_status != "pending"]
        record.reagent_usages = completed_usages + [
            _build_usage(db, usage, current_user.id) for usage in payload.reagent_usages or []
        ]
    if attachments is not None:
        record.attachments = [_build_attachment(attachment, current_user.id) for attachment in payload.attachments or []]
    if participant_ids is not None:
        record.participants = _participant_rows(db, record.project_id, payload.participant_ids or [])
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


def ensure_can_dispense_record(db: Session, current_user: User, record: ExperimentRecord) -> None:
    if current_user.role in {"admin", "director"}:
        return
    if current_user.role == "project_manager" and is_project_manager(db, current_user, record.project_id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Experiment dispense permission required")


def dispense_record(db: Session, current_user: User, record_id: int) -> ExperimentRecord:
    record = get_record_or_404(db, record_id)
    ensure_can_dispense_record(db, current_user, record)
    usages = list(
        db.scalars(
            select(ExperimentReagentUsage)
            .where(ExperimentReagentUsage.experiment_record_id == record.id)
            .with_for_update()
        ).all()
    )
    for usage in usages:
        if usage.outbound_status != "pending":
            continue
        if usage.lot_id is None or usage.quantity is None or Decimal(usage.quantity) <= 0:
            continue
        lot = db.scalar(select(ReagentLot).where(ReagentLot.id == usage.lot_id).with_for_update())
        if lot is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reagent lot not found")
        requested = Decimal(usage.quantity)
        available = Decimal(lot.quantity)
        deducted = min(requested, available)
        shortage = requested - deducted
        new_balance = available - deducted
        lot.quantity = new_balance
        lot.status = "depleted" if new_balance == 0 else "in_stock"
        lot.updated_by = current_user.id
        usage.outbound_status = "insufficient" if shortage > 0 else "dispensed"
        usage.shortage_qty = shortage if shortage > 0 else None
        usage.dispensed_by = current_user.id
        usage.dispensed_at = datetime.now(UTC)
        usage.updated_by = current_user.id
        db.add(
            InventoryTxn(
                reagent_lot_id=lot.id,
                txn_type="out",
                quantity=deducted,
                balance_after=new_balance,
                reference=f"Experiment {record.code}",
                operator_id=current_user.id,
                source_type="experiment",
                source_id=record.id,
                shortage_qty=usage.shortage_qty,
            )
        )
    db.commit()
    return get_record_or_404(db, record.id)


def list_records_for_lot(db: Session, current_user: User, lot_id: int) -> list[dict]:
    _ = current_user
    records = list(
        db.scalars(
            record_options(
                select(ExperimentRecord)
                .join(ExperimentReagentUsage)
                .where(ExperimentReagentUsage.lot_id == lot_id)
                .order_by(ExperimentRecord.id)
            )
        ).unique()
    )
    result = []
    for record in records:
        for usage in record.reagent_usages:
            if usage.lot_id == lot_id:
                result.append(
                    {
                        "experiment_id": record.id,
                        "experiment_no": record.code,
                        "title": record.title,
                        "project_id": record.project_id,
                        "project_code": record.project.project_code,
                        "project_name": record.project.name,
                        "actual_qty": usage.quantity,
                        "unit": usage.unit,
                        "outbound_status": usage.outbound_status,
                        "shortage_qty": usage.shortage_qty,
                    }
                )
    return result


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
            "participant_ids": sorted(item.user_id for item in record.participants),
            "reagent_usages": [
                {
                    "id": usage.id,
                    "experiment_record_id": usage.experiment_record_id,
                    "reagent_id": usage.reagent_id,
                    "lot_id": usage.lot_id,
                    "reagent_name_snapshot": usage.reagent_name_snapshot,
                    "lot_code_snapshot": usage.lot_code_snapshot,
                    "quantity": usage.quantity,
                    "unit": usage.unit,
                    "purpose": usage.purpose,
                    "remark": usage.remark,
                    "outbound_status": usage.outbound_status,
                    "shortage_qty": usage.shortage_qty,
                    "stock_available": usage.lot.quantity if usage.lot is not None else None,
                    "dispensed_by": usage.dispensed_by,
                    "dispensed_at": usage.dispensed_at,
                    "created_by": usage.created_by,
                    "created_at": usage.created_at,
                    "updated_by": usage.updated_by,
                    "updated_at": usage.updated_at,
                }
                for usage in record.reagent_usages
            ],
            "attachments": record.attachments,
            "created_at": record.created_at,
        }
    )
    return item
