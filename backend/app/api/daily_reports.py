from datetime import date

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.common import api_response
from app.schemas.daily_report import DailyReportCreate, DailyReportDetail, DailyReportPage, DailyReportReview, DailyReportReturn, DailyReportUpdate
from app.services import daily_reports as report_service
from app.services import audit_logs as audit_service


router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_daily_report(payload: DailyReportCreate, db: DbSession, current_user: CurrentUser) -> dict:
    report = report_service.create_report(db, current_user, payload)
    detail = report_service.serialize_report_detail(report)
    return api_response(DailyReportDetail.model_validate(detail).model_dump())


@router.get("")
def list_daily_reports(
    db: DbSession,
    current_user: CurrentUser,
    user_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    experiment_record_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    reports = report_service.list_reports(
        db,
        current_user,
        user_id=user_id,
        project_id=project_id,
        experiment_record_id=experiment_record_id,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return api_response(DailyReportPage.model_validate(reports).model_dump())


@router.get("/{report_id}")
def read_daily_report(report_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    report = report_service.get_report_or_404(db, report_id)
    report_service.ensure_can_view_report(db, current_user, report)
    detail = report_service.serialize_report_detail(report)
    return api_response(DailyReportDetail.model_validate(detail).model_dump())


@router.get("/{report_id}/timeline")
def read_daily_report_timeline(report_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(audit_service.list_entity_timeline(db, current_user, "daily_report", report_id))


@router.patch("/{report_id}")
def update_daily_report(report_id: int, payload: DailyReportUpdate, db: DbSession, current_user: CurrentUser) -> dict:
    report = report_service.update_report(db, current_user, report_id, payload)
    detail = report_service.serialize_report_detail(report)
    return api_response(DailyReportDetail.model_validate(detail).model_dump())


@router.post("/{report_id}/submit")
def submit_daily_report(report_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    report = report_service.submit_report(db, current_user, report_id)
    detail = report_service.serialize_report_detail(report)
    return api_response(DailyReportDetail.model_validate(detail).model_dump())


@router.post("/{report_id}/review")
def review_daily_report(report_id: int, payload: DailyReportReview, db: DbSession, current_user: CurrentUser) -> dict:
    report = report_service.review_report(db, current_user, report_id, payload)
    detail = report_service.serialize_report_detail(report)
    return api_response(DailyReportDetail.model_validate(detail).model_dump())


@router.post("/{report_id}/return")
def return_daily_report(report_id: int, payload: DailyReportReturn, db: DbSession, current_user: CurrentUser) -> dict:
    report = report_service.return_report(db, current_user, report_id, payload)
    detail = report_service.serialize_report_detail(report)
    return api_response(DailyReportDetail.model_validate(detail).model_dump())


@router.post("/{report_id}/archive")
def archive_daily_report(report_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    report = report_service.archive_report(db, current_user, report_id)
    detail = report_service.serialize_report_detail(report)
    return api_response(DailyReportDetail.model_validate(detail).model_dump())
