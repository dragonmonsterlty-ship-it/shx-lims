from datetime import datetime

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.schemas.audit import AuditLogPage, AuditLogRead
from app.schemas.common import ApiResponse, api_response
from app.services import audit_logs as audit_service


router = APIRouter()


@router.get("", response_model=ApiResponse[AuditLogPage])
def list_audit_logs(
    db: DbSession,
    current_user: CurrentUser,
    entity_type: str | None = Query(default=None),
    entity_id: int | None = Query(default=None),
    project_id: int | None = Query(default=None),
    actor_user_id: int | None = Query(default=None),
    action: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    data = audit_service.list_audit_logs(
        db,
        current_user,
        entity_type=entity_type,
        entity_id=entity_id,
        project_id=project_id,
        actor_user_id=actor_user_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return api_response(AuditLogPage.model_validate(data).model_dump())


@router.get("/entity/{entity_type}/{entity_id}", response_model=ApiResponse[list[AuditLogRead]])
def read_entity_timeline(entity_type: str, entity_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    data = audit_service.list_entity_timeline(db, current_user, entity_type, entity_id)
    return api_response([AuditLogRead.model_validate(item).model_dump() for item in data])
