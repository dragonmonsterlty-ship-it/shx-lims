from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.business import DailyReport, DailyReportAttachment, DailyReportItem, ExperimentRecord, Project, ProjectMember
from app.models.user import User
from app.schemas.daily_report import (
    DAILY_REPORT_REVIEW_ROLES,
    DAILY_REPORT_STATUSES,
    DAILY_REPORT_WORK_TYPES,
    DailyReportAttachmentCreate,
    DailyReportCreate,
    DailyReportItemCreate,
    DailyReportReview,
    DailyReportReturn,
    DailyReportUpdate,
)
from app.services.audit_logs import capture, record_audit
from app.services.projects import is_project_member, user_brief


def is_review_role(user: User) -> bool:
    return user.role in DAILY_REPORT_REVIEW_ROLES


def ensure_report_status(value: str) -> None:
    if value not in DAILY_REPORT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid daily report status")


def ensure_work_type(value: str) -> None:
    if value not in DAILY_REPORT_WORK_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid daily report work type")


def report_options(stmt: Select[tuple[DailyReport]]) -> Select[tuple[DailyReport]]:
    return stmt.options(
        selectinload(DailyReport.user),
        selectinload(DailyReport.reviewer),
        selectinload(DailyReport.items).selectinload(DailyReportItem.experiment_record),
        selectinload(DailyReport.attachments),
    )


def get_report_or_404(db: Session, report_id: int) -> DailyReport:
    report = db.scalar(report_options(select(DailyReport).where(DailyReport.id == report_id)))
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily report not found")
    return report


def report_project_ids(report: DailyReport) -> set[int]:
    return {item.project_id for item in report.items if item.project_id is not None}


def manages_any_report_project(db: Session, user: User, report: DailyReport) -> bool:
    project_ids = report_project_ids(report)
    if not project_ids:
        return False
    return bool(
        db.scalar(
            select(
                exists().where(
                    ProjectMember.user_id == user.id,
                    ProjectMember.role_in_project == "manager",
                    ProjectMember.project_id.in_(project_ids),
                )
            )
        )
    )


def ensure_can_view_report(db: Session, user: User, report: DailyReport) -> None:
    if user.role in {"admin", "director"} or report.user_id == user.id:
        return
    if user.role == "project_manager" and manages_any_report_project(db, user, report):
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily report not found")


def filter_reports_for_user(stmt: Select[tuple[DailyReport]], user: User) -> Select[tuple[DailyReport]]:
    if user.role in {"admin", "director"}:
        return stmt
    if user.role == "project_manager":
        managed_ids = select(ProjectMember.project_id).where(
            ProjectMember.user_id == user.id,
            ProjectMember.role_in_project == "manager",
        )
        return stmt.where(
            or_(
                DailyReport.user_id == user.id,
                exists().where(
                    DailyReportItem.daily_report_id == DailyReport.id,
                    DailyReportItem.project_id.in_(managed_ids),
                ),
            )
        )
    return stmt.where(DailyReport.user_id == user.id)


def ensure_can_create_for_user(current_user: User, user_id: int) -> None:
    if current_user.id == user_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only create own daily report")


def ensure_can_modify_report(current_user: User, report: DailyReport) -> None:
    if report.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can modify this daily report")
    if report.status not in {"draft", "returned"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft or returned daily reports can be modified")


def ensure_can_submit_report(current_user: User, report: DailyReport) -> None:
    if current_user.id == report.user_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Daily report submit permission required")


def ensure_can_review_report(db: Session, current_user: User, report: DailyReport) -> None:
    if not is_review_role(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Daily report review permission required")
    if current_user.id == report.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reporter cannot review own daily report")
    if current_user.role == "project_manager" and not manages_any_report_project(db, current_user, report):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily report not found")


def validate_user(db: Session, user_id: int) -> None:
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Report user not found")


def validate_item_refs(db: Session, current_user: User, item: DailyReportItemCreate) -> None:
    ensure_work_type(item.work_type)
    if item.project_id is not None:
        project = db.get(Project, item.project_id)
        if project is None or project.is_deleted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project not found")
        if not is_review_role(current_user) and not is_project_member(db, current_user, item.project_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access required")
    if item.experiment_record_id is not None:
        record = db.get(ExperimentRecord, item.experiment_record_id)
        if record is None or record.is_deleted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Experiment record not found")
        if item.project_id is not None and record.project_id != item.project_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Experiment record must belong to the item project")
        if not is_review_role(current_user) and not is_project_member(db, current_user, record.project_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access required")


def build_item(db: Session, current_user: User, payload: DailyReportItemCreate) -> DailyReportItem:
    validate_item_refs(db, current_user, payload)
    return DailyReportItem(**payload.model_dump(), created_by=current_user.id)


def build_attachment(payload: DailyReportAttachmentCreate, current_user_id: int) -> DailyReportAttachment:
    return DailyReportAttachment(**payload.model_dump(), uploaded_by=current_user_id, created_by=current_user_id)


def paginate(db: Session, stmt: Select[tuple[DailyReport]], page: int, page_size: int) -> dict:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(report_options(stmt.offset((page - 1) * page_size).limit(page_size))).all())
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def list_reports(
    db: Session,
    current_user: User,
    *,
    user_id: int | None = None,
    project_id: int | None = None,
    experiment_record_id: int | None = None,
    status_filter: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = filter_reports_for_user(select(DailyReport).order_by(DailyReport.report_date.desc(), DailyReport.id.desc()), current_user)
    if user_id is not None:
        if not is_review_role(current_user) and user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only view own daily reports")
        stmt = stmt.where(DailyReport.user_id == user_id)
    if project_id is not None:
        if not is_review_role(current_user) and not is_project_member(db, current_user, project_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access required")
        stmt = stmt.where(exists().where(DailyReportItem.daily_report_id == DailyReport.id, DailyReportItem.project_id == project_id))
    if experiment_record_id is not None:
        stmt = stmt.where(
            exists().where(
                DailyReportItem.daily_report_id == DailyReport.id,
                DailyReportItem.experiment_record_id == experiment_record_id,
            )
        )
    if status_filter is not None:
        ensure_report_status(status_filter)
        stmt = stmt.where(DailyReport.status == status_filter)
    if date_from is not None:
        stmt = stmt.where(DailyReport.report_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(DailyReport.report_date <= date_to)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                DailyReport.summary.ilike(pattern),
                DailyReport.issues.ilike(pattern),
                DailyReport.next_plan.ilike(pattern),
                exists().where(DailyReportItem.daily_report_id == DailyReport.id, DailyReportItem.content.ilike(pattern)),
            )
        )
    page_data = paginate(db, stmt, page, page_size)
    return {
        "items": [serialize_report_list_item(report) for report in page_data["items"]],
        "total": page_data["total"],
        "page": page_data["page"],
        "page_size": page_data["page_size"],
    }


def create_report(db: Session, current_user: User, payload: DailyReportCreate) -> DailyReport:
    ensure_report_status(payload.status)
    user_id = payload.user_id or current_user.id
    validate_user(db, user_id)
    ensure_can_create_for_user(current_user, user_id)
    report = DailyReport(
        user_id=user_id,
        report_date=payload.report_date,
        status=payload.status,
        summary=payload.summary,
        issues=payload.issues,
        next_plan=payload.next_plan,
        created_by=current_user.id,
    )
    report.items = [build_item(db, current_user, item) for item in payload.items]
    report.attachments = [build_attachment(attachment, current_user.id) for attachment in payload.attachments]
    db.add(report)
    db.flush()
    record_audit(
        db,
        current_user,
        action="create",
        entity_type="daily_report",
        entity_id=report.id,
        project_id=next(iter(report_project_ids(report)), None),
        after_data={"id": report.id, "user_id": report.user_id, "status": report.status, "report_date": report.report_date},
    )
    db.commit()
    return get_report_or_404(db, report.id)


def update_report(db: Session, current_user: User, report_id: int, payload: DailyReportUpdate) -> DailyReport:
    report = get_report_or_404(db, report_id)
    ensure_can_view_report(db, current_user, report)
    ensure_can_modify_report(current_user, report)
    before = capture(serialize_report_detail(report))
    updates = payload.model_dump(exclude_unset=True)
    items = updates.pop("items", None)
    attachments = updates.pop("attachments", None)
    for field, value in updates.items():
        setattr(report, field, value)
    if items is not None:
        report.items = [build_item(db, current_user, item) for item in payload.items or []]
    if attachments is not None:
        report.attachments = [build_attachment(attachment, current_user.id) for attachment in payload.attachments or []]
    report.updated_by = current_user.id
    db.flush()
    record_audit(
        db,
        current_user,
        action="update",
        entity_type="daily_report",
        entity_id=report.id,
        project_id=next(iter(report_project_ids(report)), None),
        before_data=before,
        after_data=serialize_report_detail(report),
    )
    db.commit()
    return get_report_or_404(db, report.id)


def submit_report(db: Session, current_user: User, report_id: int) -> DailyReport:
    report = get_report_or_404(db, report_id)
    ensure_can_view_report(db, current_user, report)
    ensure_can_submit_report(current_user, report)
    if report.status not in {"draft", "returned"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft or returned daily reports can be submitted")
    before = capture({"status": report.status})
    report.status = "submitted"
    report.submitted_at = datetime.now(UTC)
    report.updated_by = current_user.id
    db.flush()
    record_audit(
        db,
        current_user,
        action="submit",
        entity_type="daily_report",
        entity_id=report.id,
        project_id=next(iter(report_project_ids(report)), None),
        before_data=before,
        after_data={"status": report.status},
    )
    db.commit()
    return get_report_or_404(db, report.id)


def review_report(db: Session, current_user: User, report_id: int, payload: DailyReportReview) -> DailyReport:
    report = get_report_or_404(db, report_id)
    ensure_can_view_report(db, current_user, report)
    ensure_can_review_report(db, current_user, report)
    if report.status != "submitted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only submitted daily reports can be reviewed")
    before = capture({"status": report.status, "review_comment": report.review_comment})
    report.status = "confirmed"
    report.reviewer_id = current_user.id
    report.reviewed_at = datetime.now(UTC)
    report.review_comment = payload.review_comment
    report.updated_by = current_user.id
    db.flush()
    record_audit(
        db,
        current_user,
        action="approve",
        entity_type="daily_report",
        entity_id=report.id,
        project_id=next(iter(report_project_ids(report)), None),
        before_data=before,
        after_data={"status": report.status, "review_comment": report.review_comment},
    )
    db.commit()
    return get_report_or_404(db, report.id)


def return_report(db: Session, current_user: User, report_id: int, payload: DailyReportReturn) -> DailyReport:
    report = get_report_or_404(db, report_id)
    ensure_can_view_report(db, current_user, report)
    ensure_can_review_report(db, current_user, report)
    if report.status != "submitted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only submitted daily reports can be returned")
    before = capture({"status": report.status, "review_comment": report.review_comment})
    report.status = "returned"
    report.reviewer_id = current_user.id
    report.reviewed_at = datetime.now(UTC)
    report.review_comment = payload.review_comment
    report.updated_by = current_user.id
    db.flush()
    record_audit(
        db,
        current_user,
        action="reject",
        entity_type="daily_report",
        entity_id=report.id,
        project_id=next(iter(report_project_ids(report)), None),
        before_data=before,
        after_data={"status": report.status, "review_comment": report.review_comment},
    )
    db.commit()
    return get_report_or_404(db, report.id)


def archive_report(db: Session, current_user: User, report_id: int) -> DailyReport:
    report = get_report_or_404(db, report_id)
    ensure_can_view_report(db, current_user, report)
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Daily report archive permission required")
    before = capture({"status": report.status})
    report.status = "archived"
    report.updated_by = current_user.id
    db.flush()
    record_audit(
        db,
        current_user,
        action="archive",
        entity_type="daily_report",
        entity_id=report.id,
        project_id=next(iter(report_project_ids(report)), None),
        before_data=before,
        after_data={"status": report.status},
    )
    db.commit()
    return get_report_or_404(db, report.id)


def experiment_record_brief(record: ExperimentRecord | None) -> dict | None:
    if record is None:
        return None
    return {
        "id": record.id,
        "code": record.code,
        "title": record.title,
        "status": record.status,
        "record_type": record.record_type,
        "experiment_date": record.experiment_date,
    }


def serialize_item(item: DailyReportItem) -> dict:
    return {
        "id": item.id,
        "daily_report_id": item.daily_report_id,
        "project_id": item.project_id,
        "experiment_record_id": item.experiment_record_id,
        "work_type": item.work_type,
        "content": item.content,
        "progress_note": item.progress_note,
        "hours_spent": item.hours_spent,
        "problem_note": item.problem_note,
        "next_step": item.next_step,
        "sort_order": item.sort_order,
        "experiment_record": experiment_record_brief(item.experiment_record),
        "created_by": item.created_by,
        "created_at": item.created_at,
        "updated_by": item.updated_by,
        "updated_at": item.updated_at,
    }


def serialize_report_list_item(report: DailyReport) -> dict:
    project_ids = {item.project_id for item in report.items if item.project_id is not None}
    experiment_record_ids = {item.experiment_record_id for item in report.items if item.experiment_record_id is not None}
    return {
        "id": report.id,
        "user": user_brief(report.user),
        "report_date": report.report_date,
        "status": report.status,
        "summary": report.summary,
        "item_count": len(report.items),
        "project_count": len(project_ids),
        "experiment_record_count": len(experiment_record_ids),
        "submitted_at": report.submitted_at,
        "reviewed_at": report.reviewed_at,
        "updated_at": report.updated_at,
    }


def serialize_report_detail(report: DailyReport) -> dict:
    item = serialize_report_list_item(report)
    item.update(
        {
            "user_id": report.user_id,
            "reviewer_id": report.reviewer_id,
            "reviewer": user_brief(report.reviewer),
            "issues": report.issues,
            "next_plan": report.next_plan,
            "review_comment": report.review_comment,
            "items": [serialize_item(report_item) for report_item in sorted(report.items, key=lambda x: (x.sort_order, x.id))],
            "attachments": report.attachments,
            "created_at": report.created_at,
        }
    )
    return item
