from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.audit import PasswordResetResult, UserPasswordReset, UserRoleUpdate, UserStatusUpdate
from app.schemas.common import ApiResponse, api_response
from app.schemas.user import AdminUserCreate, UserRead
from app.services import admin_users as admin_user_service


router = APIRouter()


@router.get("/users", response_model=ApiResponse[list[UserRead]])
def list_admin_users(db: DbSession, current_user: CurrentUser) -> dict:
    users = admin_user_service.list_admin_users(db, current_user)
    return api_response([UserRead.model_validate(user).model_dump() for user in users])


@router.post("/users", response_model=ApiResponse[UserRead], status_code=201)
def create_admin_user(payload: AdminUserCreate, db: DbSession, current_user: CurrentUser) -> dict:
    user = admin_user_service.create_admin_user(db, current_user, payload)
    return api_response(UserRead.model_validate(user).model_dump())


@router.patch("/users/{user_id}/status", response_model=ApiResponse[UserRead])
def update_user_status(user_id: int, payload: UserStatusUpdate, db: DbSession, current_user: CurrentUser) -> dict:
    user = admin_user_service.update_user_status(db, current_user, user_id, payload)
    return api_response(UserRead.model_validate(user).model_dump())


@router.patch("/users/{user_id}/role", response_model=ApiResponse[UserRead])
def update_user_role(user_id: int, payload: UserRoleUpdate, db: DbSession, current_user: CurrentUser) -> dict:
    user = admin_user_service.update_user_role(db, current_user, user_id, payload)
    return api_response(UserRead.model_validate(user).model_dump())


@router.post("/users/{user_id}/reset-password", response_model=ApiResponse[PasswordResetResult])
def reset_user_password(user_id: int, payload: UserPasswordReset, db: DbSession, current_user: CurrentUser) -> dict:
    result = admin_user_service.reset_user_password(db, current_user, user_id, payload)
    return api_response(PasswordResetResult.model_validate(result).model_dump())
