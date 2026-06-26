from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.business import Attachment, AuditLog
from app.models.user import User
from app.schemas.audit import AUDIT_ACTIONS, AUDIT_ENTITY_TYPES
from app.models.business import ProjectMember
from app.services.projects import is_admin, is_director, is_project_member


def ensure_action(value: str) -> None:
    if value not in AUDIT_ACTIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid audit action")


def ensure_entity_type(value: str) -> None:
    if value not in AUDIT_ENTITY_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid audit entity type")


def capture(data: Any) -> Any:
    return jsonable_encoder(data)


def record_audit(
    db: Session,
    actor: User,
    *,
    action: str,
    entity_type: str,
    entity_id: int,
    project_id: int | None = None,
    target_user_id: int | None = None,
    before_data: Any = None,
    after_data: Any = None,
    metadata: Any = None,
) -> AuditLog:
    ensure_action(action)
    ensure_entity_type(entity_type)
    log = AuditLog(
        actor_user_id=actor.id,
        actor_role=actor.role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        target_user_id=target_user_id,
        before_data=capture(before_data),
        after_data=capture(after_data),
        metadata_=capture(metadata),
    )
    db.add(log)
    return log


def audit_to_dict(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "actor_user_id": log.actor_user_id,
        "actor_role": log.actor_role,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "project_id": log.project_id,
        "target_user_id": log.target_user_id,
        "before_data": log.before_data,
        "after_data": log.after_data,
        "metadata": log.metadata_,
        "created_at": log.created_at,
    }


def _paginate(db: Session, stmt: Select[tuple[AuditLog]], page: int, page_size: int) -> dict:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all())
    return {"items": [audit_to_dict(item) for item in items], "total": total, "page": page, "page_size": page_size}


def _filter_logs_for_user(stmt: Select[tuple[AuditLog]], db: Session, user: User) -> Select[tuple[AuditLog]]:
    if is_admin(user):
        return stmt
    if user.role != "project_manager":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Audit log list permission required")
    project_ids = list(
        db.scalars(
            select(ProjectMember.project_id).where(
                ProjectMember.user_id == user.id,
                ProjectMember.role_in_project == "manager",
            )
        ).all()
    )
    if not project_ids:
        return stmt.where(False)
    return stmt.where(AuditLog.project_id.in_(project_ids))


def list_audit_logs(
    db: Session,
    current_user: User,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    project_id: int | None = None,
    actor_user_id: int | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    stmt = _filter_logs_for_user(stmt, db, current_user)
    if entity_type is not None:
        ensure_entity_type(entity_type)
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if project_id is not None:
        if not is_admin(current_user) and not is_director(current_user) and not is_project_member(db, current_user, project_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        stmt = stmt.where(AuditLog.project_id == project_id)
    if actor_user_id is not None:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if action is not None:
        ensure_action(action)
        stmt = stmt.where(AuditLog.action == action)
    if date_from is not None:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(AuditLog.created_at <= date_to)
    return _paginate(db, stmt, page, page_size)


def list_entity_timeline(db: Session, current_user: User, entity_type: str, entity_id: int) -> list[dict]:
    ensure_entity_access(db, current_user, entity_type, entity_id)
    logs = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.created_at, AuditLog.id)
        ).all()
    )
    return [audit_to_dict(log) for log in logs]


def ensure_entity_access(db: Session, current_user: User, entity_type: str, entity_id: int) -> None:
    ensure_entity_type(entity_type)
    if entity_type == "experiment":
        from app.services import experiment_records

        record = experiment_records.get_record_or_404(db, entity_id)
        experiment_records.ensure_can_view_record(db, current_user, record)
        return
    if entity_type == "daily_report":
        from app.services import daily_reports

        report = daily_reports.get_report_or_404(db, entity_id)
        daily_reports.ensure_can_view_report(db, current_user, report)
        return
    if entity_type == "sample":
        from app.services import testing

        sample = testing.get_sample(db, entity_id)
        testing.ensure_can_view_project(db, current_user, sample.project_id)
        return
    if entity_type == "test_task":
        from app.services import testing

        task = testing.get_task(db, entity_id)
        testing.ensure_can_view_task(db, current_user, task)
        return
    if entity_type == "test_result":
        from app.services import testing

        result = testing.get_result(db, entity_id)
        testing.ensure_can_view_result(db, current_user, result)
        return
    if entity_type == "attachment":
        from app.services.attachment_entities import resolve_attachment_entity

        attachment = db.get(Attachment, entity_id)
        if attachment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
        resolve_attachment_entity(db, current_user, attachment.entity_type, attachment.entity_id, action="read")
        return
    if entity_type == "user":
        if is_admin(current_user) or current_user.id == entity_id:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User audit permission required")
