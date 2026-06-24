from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.business import DailyLog, Project, Sample
from app.models.user import User
from app.schemas.daily_log import DAILY_LOG_STATUSES, DailyLogCreate, DailyLogReview, DailyLogReturn, DailyLogUpdate
from app.services.projects import get_accessible_project_ids, is_admin, is_director, is_project_manager, is_project_member


def ensure_daily_log_status(value: str) -> None:
    if value not in DAILY_LOG_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid daily log status")


def _ensure_project_scope(db: Session, current_user: User, project_id: int | None) -> None:
    if project_id is None:
        return
    project = db.get(Project, project_id)
    if project is None or project.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if is_admin(current_user):
        return
    if is_director(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Director is read-only")
    if not is_project_member(db, current_user, project_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access required")


def _ensure_related_sample_matches_project(db: Session, project_id: int | None, related_sample_id: int | None) -> None:
    if related_sample_id is None:
        return
    sample = db.get(Sample, related_sample_id)
    if sample is None or sample.is_deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Related sample not found")
    if project_id is None or sample.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Related sample must belong to the same project")


def _visible_daily_log_stmt(db: Session, current_user: User) -> Select[tuple[DailyLog]]:
    stmt = select(DailyLog).where(DailyLog.is_deleted.is_(False))
    if is_admin(current_user) or is_director(current_user):
        return stmt
    if current_user.role == "operator":
        return stmt.where(DailyLog.user_id == current_user.id)
    if current_user.role == "project_manager":
        project_ids = get_accessible_project_ids(db, current_user) or []
        if not project_ids:
            return stmt.where(DailyLog.user_id == current_user.id)
        return stmt.where((DailyLog.project_id.in_(project_ids)) | (DailyLog.user_id == current_user.id))
    return stmt.where(False)


def _get_existing_daily_log(db: Session, daily_log_id: int) -> DailyLog:
    daily_log = db.get(DailyLog, daily_log_id)
    if daily_log is None or daily_log.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily log not found")
    return daily_log


def get_visible_daily_log(db: Session, current_user: User, daily_log_id: int) -> DailyLog:
    daily_log = _get_existing_daily_log(db, daily_log_id)
    if is_admin(current_user) or is_director(current_user):
        return daily_log
    if current_user.role == "operator" and daily_log.user_id == current_user.id:
        return daily_log
    if current_user.role == "project_manager":
        if daily_log.user_id == current_user.id:
            return daily_log
        if daily_log.project_id is not None and is_project_member(db, current_user, daily_log.project_id):
            return daily_log
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily log not found")


def ensure_can_upload_daily_log_attachment(db: Session, current_user: User, daily_log: DailyLog) -> None:
    if is_director(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Director is read-only")
    if is_admin(current_user):
        return
    if daily_log.user_id == current_user.id and daily_log.status in {"draft", "returned"}:
        return
    if (
        current_user.role == "project_manager"
        and daily_log.project_id is not None
        and daily_log.status in {"draft", "submitted", "returned"}
        and is_project_manager(db, current_user, daily_log.project_id)
    ):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Daily log attachment upload permission required")


def list_daily_logs(
    db: Session,
    current_user: User,
    project_id: int | None = None,
    user_id: int | None = None,
    status_filter: str | None = None,
    log_date_from=None,
    log_date_to=None,
) -> list[DailyLog]:
    if status_filter is not None:
        ensure_daily_log_status(status_filter)
    stmt = _visible_daily_log_stmt(db, current_user)
    if project_id is not None:
        if not (is_admin(current_user) or is_director(current_user)):
            if not is_project_member(db, current_user, project_id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access required")
        stmt = stmt.where(DailyLog.project_id == project_id)
    if user_id is not None:
        if current_user.role == "operator" and user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operators can only view own daily logs")
        stmt = stmt.where(DailyLog.user_id == user_id)
    if status_filter is not None:
        stmt = stmt.where(DailyLog.status == status_filter)
    if log_date_from is not None:
        stmt = stmt.where(DailyLog.log_date >= log_date_from)
    if log_date_to is not None:
        stmt = stmt.where(DailyLog.log_date <= log_date_to)
    return list(db.scalars(stmt.order_by(DailyLog.log_date.desc(), DailyLog.id.desc())).all())


def create_daily_log(db: Session, current_user: User, payload: DailyLogCreate) -> DailyLog:
    if is_director(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Director is read-only")
    _ensure_project_scope(db, current_user, payload.project_id)
    _ensure_related_sample_matches_project(db, payload.project_id, payload.related_sample_id)
    daily_log = DailyLog(
        user_id=current_user.id,
        project_id=payload.project_id,
        log_date=payload.log_date,
        content=payload.content,
        related_sample_id=payload.related_sample_id,
        status="draft",
        created_by=current_user.id,
    )
    db.add(daily_log)
    db.commit()
    db.refresh(daily_log)
    return daily_log


def update_daily_log(db: Session, current_user: User, daily_log_id: int, payload: DailyLogUpdate) -> DailyLog:
    daily_log = get_visible_daily_log(db, current_user, daily_log_id)
    if is_director(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Director is read-only")
    if daily_log.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the author can edit this daily log")
    if daily_log.status not in {"draft", "returned"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft or returned daily logs can be edited")

    updates = payload.model_dump(exclude_unset=True)
    new_project_id = updates.get("project_id", daily_log.project_id)
    new_related_sample_id = updates.get("related_sample_id", daily_log.related_sample_id)
    _ensure_project_scope(db, current_user, new_project_id)
    _ensure_related_sample_matches_project(db, new_project_id, new_related_sample_id)
    for field, value in updates.items():
        setattr(daily_log, field, value)
    daily_log.updated_by = current_user.id
    db.commit()
    db.refresh(daily_log)
    return daily_log


def submit_daily_log(db: Session, current_user: User, daily_log_id: int) -> DailyLog:
    daily_log = get_visible_daily_log(db, current_user, daily_log_id)
    if is_director(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Director is read-only")
    if daily_log.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the author can submit this daily log")
    if daily_log.status not in {"draft", "returned"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft or returned daily logs can be submitted")
    daily_log.status = "submitted"
    daily_log.updated_by = current_user.id
    db.commit()
    db.refresh(daily_log)
    return daily_log


def _ensure_reviewer(db: Session, current_user: User, daily_log: DailyLog) -> None:
    if is_director(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Director is read-only")
    if daily_log.user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Author cannot review own daily log")
    if is_admin(current_user):
        return
    if daily_log.project_id is not None and current_user.role == "project_manager" and is_project_manager(db, current_user, daily_log.project_id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Daily log review permission required")


def review_daily_log(db: Session, current_user: User, daily_log_id: int, payload: DailyLogReview) -> DailyLog:
    daily_log = get_visible_daily_log(db, current_user, daily_log_id)
    _ensure_reviewer(db, current_user, daily_log)
    if daily_log.status != "submitted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only submitted daily logs can be reviewed")
    daily_log.status = "reviewed"
    daily_log.reviewed_by = current_user.id
    daily_log.reviewed_at = datetime.now(UTC)
    daily_log.review_comment = payload.review_comment
    daily_log.updated_by = current_user.id
    db.commit()
    db.refresh(daily_log)
    return daily_log


def return_daily_log(db: Session, current_user: User, daily_log_id: int, payload: DailyLogReturn) -> DailyLog:
    daily_log = get_visible_daily_log(db, current_user, daily_log_id)
    _ensure_reviewer(db, current_user, daily_log)
    if daily_log.status != "submitted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only submitted daily logs can be returned")
    daily_log.status = "returned"
    daily_log.reviewed_by = current_user.id
    daily_log.reviewed_at = datetime.now(UTC)
    daily_log.review_comment = payload.review_comment
    daily_log.updated_by = current_user.id
    db.commit()
    db.refresh(daily_log)
    return daily_log


def soft_delete_daily_log(db: Session, current_user: User, daily_log_id: int) -> None:
    daily_log = get_visible_daily_log(db, current_user, daily_log_id)
    if daily_log.status == "reviewed" and not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reviewed daily logs cannot be deleted")
    if is_admin(current_user):
        pass
    elif daily_log.user_id == current_user.id and daily_log.status == "draft":
        pass
    elif current_user.role == "project_manager" and daily_log.project_id is not None and is_project_manager(db, current_user, daily_log.project_id):
        pass
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Daily log delete permission required")
    daily_log.is_deleted = True
    daily_log.updated_by = current_user.id
    db.commit()
