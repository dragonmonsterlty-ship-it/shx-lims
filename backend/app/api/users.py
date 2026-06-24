from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.schemas.common import api_response
from app.schemas.user import UserRead
from app.services import users as user_service


router = APIRouter()


@router.get("/me")
def read_current_user(current_user: CurrentUser) -> dict:
    return api_response(UserRead.model_validate(current_user).model_dump())


@router.get("")
def list_users(
    db: DbSession,
    current_user: CurrentUser,
    role_group: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
) -> dict:
    _ = current_user
    users = user_service.list_users(db, role_group=role_group, keyword=keyword)
    return api_response([UserRead.model_validate(user).model_dump() for user in users])


@router.get("/project-owner-candidates")
def list_project_owner_candidates(
    db: DbSession,
    current_user: CurrentUser,
    keyword: str | None = Query(default=None),
) -> dict:
    _ = current_user
    users = user_service.list_project_owner_candidates(db, keyword=keyword)
    return api_response([UserRead.model_validate(user).model_dump() for user in users])
