from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.common import api_response
from app.services import audit_logs as audit_service


router = APIRouter()


@router.get("/{experiment_id}/timeline")
def read_experiment_timeline(experiment_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(audit_service.list_entity_timeline(db, current_user, "experiment", experiment_id))
