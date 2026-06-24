from datetime import date

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.common import api_response
from app.schemas.daily_log import DailyLogCreate, DailyLogRead, DailyLogReview, DailyLogReturn, DailyLogUpdate
from app.schemas.attachment import AttachmentRead
from app.services import attachments as attachment_service
from app.services import daily_logs as daily_log_service


router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_daily_log(payload: DailyLogCreate, db: DbSession, current_user: CurrentUser) -> dict:
    daily_log = daily_log_service.create_daily_log(db, current_user, payload)
    return api_response(DailyLogRead.model_validate(daily_log).model_dump())


@router.get("")
def list_daily_logs(
    db: DbSession,
    current_user: CurrentUser,
    project_id: int | None = None,
    user_id: int | None = None,
    status: str | None = None,
    log_date_from: date | None = None,
    log_date_to: date | None = None,
) -> dict:
    daily_logs = daily_log_service.list_daily_logs(db, current_user, project_id, user_id, status, log_date_from, log_date_to)
    return api_response([DailyLogRead.model_validate(daily_log).model_dump() for daily_log in daily_logs])


@router.get("/{daily_log_id}")
def read_daily_log(daily_log_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    daily_log = daily_log_service.get_visible_daily_log(db, current_user, daily_log_id)
    return api_response(DailyLogRead.model_validate(daily_log).model_dump())


@router.patch("/{daily_log_id}")
def update_daily_log(daily_log_id: int, payload: DailyLogUpdate, db: DbSession, current_user: CurrentUser) -> dict:
    daily_log = daily_log_service.update_daily_log(db, current_user, daily_log_id, payload)
    return api_response(DailyLogRead.model_validate(daily_log).model_dump())


@router.delete("/{daily_log_id}")
def delete_daily_log(daily_log_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    daily_log_service.soft_delete_daily_log(db, current_user, daily_log_id)
    return api_response({"deleted": True})


@router.post("/{daily_log_id}/submit")
def submit_daily_log(daily_log_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    daily_log = daily_log_service.submit_daily_log(db, current_user, daily_log_id)
    return api_response(DailyLogRead.model_validate(daily_log).model_dump())


@router.post("/{daily_log_id}/review")
def review_daily_log(daily_log_id: int, payload: DailyLogReview, db: DbSession, current_user: CurrentUser) -> dict:
    daily_log = daily_log_service.review_daily_log(db, current_user, daily_log_id, payload)
    return api_response(DailyLogRead.model_validate(daily_log).model_dump())


@router.post("/{daily_log_id}/return")
def return_daily_log(daily_log_id: int, payload: DailyLogReturn, db: DbSession, current_user: CurrentUser) -> dict:
    daily_log = daily_log_service.return_daily_log(db, current_user, daily_log_id, payload)
    return api_response(DailyLogRead.model_validate(daily_log).model_dump())


@router.get("/{daily_log_id}/attachments")
def list_daily_log_attachments(daily_log_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    attachments = attachment_service.list_daily_log_attachments(db, current_user, daily_log_id)
    return api_response([AttachmentRead.model_validate(attachment).model_dump() for attachment in attachments])
