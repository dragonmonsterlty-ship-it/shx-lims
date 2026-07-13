from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.business import DailyReport, ExperimentRecord, Result, Sample, SampleTest
from app.models.user import User
from app.services import daily_reports, experiment_records, testing
from app.services.projects import is_admin, is_director, is_project_manager, is_project_member


AttachmentEntityType = Literal["experiment", "daily_report", "sample", "test_task", "test_result", "ref_standard"]
AttachmentAction = Literal["read", "upload", "delete"]

ENTITY_TYPES = {"experiment", "daily_report", "sample", "test_task", "test_result", "ref_standard"}
ACTIONS = {"read", "upload", "delete"}
DAILY_REPORT_PROJECT_ERROR = "Daily report attachments require exactly one linked project."


@dataclass(frozen=True)
class ResolvedAttachmentEntity:
    entity_type: AttachmentEntityType
    entity_id: int
    project_id: int | None
    object: object
    editable: bool


def resolve_attachment_entity(
    db: Session,
    current_user: User,
    entity_type: str,
    entity_id: int,
    *,
    action: str = "read",
) -> ResolvedAttachmentEntity:
    if entity_type not in ENTITY_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid attachment entity type")
    if action not in ACTIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid attachment action")

    if entity_type == "experiment":
        return _resolve_experiment(db, current_user, entity_id, action)
    if entity_type == "daily_report":
        return _resolve_daily_report(db, current_user, entity_id, action)
    if entity_type == "sample":
        return _resolve_sample(db, current_user, entity_id, action)
    if entity_type == "test_task":
        return _resolve_task(db, current_user, entity_id, action)
    if entity_type == "ref_standard":
        return _resolve_ref_standard(db, current_user, entity_id, action)
    return _resolve_result(db, current_user, entity_id, action)


def _resolve_ref_standard(
    db: Session, current_user: User, entity_id: int, action: str
) -> ResolvedAttachmentEntity:
    from app.services import ref_standards

    standard = ref_standards.read_ref_standard(db, current_user, entity_id)
    editable = standard.status != "disposed"
    if action != "read":
        ref_standards.ensure_can_write_ref_standards(current_user)
        if not editable:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Disposed reference standard does not allow attachment changes",
            )
    return ResolvedAttachmentEntity("ref_standard", standard.id, None, standard, editable)


def _deny_director_write(current_user: User, action: str) -> None:
    if action != "read" and is_director(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Directors have read-only attachment access")


def _resolve_experiment(
    db: Session, current_user: User, entity_id: int, action: str
) -> ResolvedAttachmentEntity:
    record = experiment_records.get_record_or_404(db, entity_id)
    experiment_records.ensure_can_view_record(db, current_user, record)
    _deny_director_write(current_user, action)
    editable = record.status != "archived"
    if action != "read":
        experiment_records.ensure_can_edit_record(db, current_user, record)
        if not editable:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Experiment record does not allow attachment changes")
    return ResolvedAttachmentEntity("experiment", record.id, record.project_id, record, editable)


def _resolve_daily_report(
    db: Session, current_user: User, entity_id: int, action: str
) -> ResolvedAttachmentEntity:
    report = daily_reports.get_report_or_404(db, entity_id)
    daily_reports.ensure_can_view_report(db, current_user, report)
    project_id = _single_daily_report_project_id(report)
    _deny_director_write(current_user, action)
    editable = report.status in {"draft", "returned"}
    if action != "read":
        if is_admin(current_user):
            pass
        elif current_user.role == "project_manager" and is_project_manager(db, current_user, project_id):
            pass
        elif current_user.role == "operator" and report.user_id == current_user.id and editable:
            pass
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Daily report attachment permission required")
    return ResolvedAttachmentEntity("daily_report", report.id, project_id, report, editable)


def _single_daily_report_project_id(report: DailyReport) -> int:
    project_ids = daily_reports.report_project_ids(report)
    if len(project_ids) != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=DAILY_REPORT_PROJECT_ERROR)
    return next(iter(project_ids))


def _resolve_sample(db: Session, current_user: User, entity_id: int, action: str) -> ResolvedAttachmentEntity:
    sample = testing.get_sample(db, entity_id)
    testing.ensure_can_view_project(db, current_user, sample.project_id)
    _deny_director_write(current_user, action)
    editable = sample.status not in {"completed", "cancelled"} and not sample.is_deleted
    if action != "read":
        _ensure_can_write_sample_attachment(db, current_user, sample)
        if not editable:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sample does not allow attachment changes")
    return ResolvedAttachmentEntity("sample", sample.id, sample.project_id, sample, editable)


def _ensure_can_write_sample_attachment(db: Session, current_user: User, sample: Sample) -> None:
    if is_admin(current_user):
        return
    if current_user.role == "project_manager" and is_project_manager(db, current_user, sample.project_id):
        return
    if current_user.role == "operator" and is_project_member(db, current_user, sample.project_id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sample attachment permission required")


def _resolve_task(db: Session, current_user: User, entity_id: int, action: str) -> ResolvedAttachmentEntity:
    task = testing.get_task(db, entity_id)
    testing.ensure_can_view_task(db, current_user, task)
    _deny_director_write(current_user, action)
    editable = task.status not in {"completed", "cancelled"} and not task.sample.is_deleted
    if action != "read":
        _ensure_can_write_task_attachment(db, current_user, task)
        if not editable:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test task does not allow attachment changes")
    return ResolvedAttachmentEntity("test_task", task.id, task.sample.project_id, task, editable)


def _ensure_can_write_task_attachment(db: Session, current_user: User, task: SampleTest) -> None:
    if is_admin(current_user):
        return
    if current_user.role == "project_manager" and is_project_manager(db, current_user, task.sample.project_id):
        return
    if current_user.role == "operator" and task.assigned_to == current_user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Test task attachment permission required")


def _resolve_result(db: Session, current_user: User, entity_id: int, action: str) -> ResolvedAttachmentEntity:
    result = testing.get_result(db, entity_id)
    testing.ensure_can_view_result(db, current_user, result)
    _deny_director_write(current_user, action)
    editable = result.status in {"draft", "rejected"} and not result.sample_test.sample.is_deleted
    if action != "read":
        _ensure_can_write_result_attachment(db, current_user, result)
        if not editable:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test result does not allow attachment changes")
    return ResolvedAttachmentEntity("test_result", result.id, result.sample_test.sample.project_id, result, editable)


def _ensure_can_write_result_attachment(db: Session, current_user: User, result: Result) -> None:
    if is_admin(current_user):
        return
    project_id = result.sample_test.sample.project_id
    if current_user.role == "project_manager" and is_project_manager(db, current_user, project_id):
        return
    if current_user.role == "operator" and result.sample_test.assigned_to == current_user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Test result attachment permission required")
