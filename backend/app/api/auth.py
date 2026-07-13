from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUserAllowPendingPassword, DbSession
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, RefreshRequest, LogoutRequest, TokenResponse
from app.schemas.common import api_response
from app.schemas.user import UserRead
from app.services.auth import authenticate_user, change_password, create_token_pair, refresh_token_pair, revoke_refresh_token


router = APIRouter()


@router.post("/login")
def login(payload: LoginRequest, db: DbSession) -> dict:
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    access_token, refresh_token = create_token_pair(db, user)
    data = LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserRead.model_validate(user),
        must_change_password=user.must_change_password,
    ).model_dump()
    return api_response(data)


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: DbSession) -> dict:
    _, access_token, refresh_token = refresh_token_pair(db, payload.refresh_token)
    data = TokenResponse(access_token=access_token, refresh_token=refresh_token).model_dump()
    return api_response(data)


@router.post("/logout")
def logout(payload: LogoutRequest, db: DbSession) -> dict:
    revoke_refresh_token(db, payload.refresh_token)
    return api_response({"logged_out": True})


@router.post("/change-password")
def change_current_password(
    payload: ChangePasswordRequest,
    db: DbSession,
    current_user: CurrentUserAllowPendingPassword,
) -> dict:
    change_password(db, current_user, payload.old_password, payload.new_password)
    return api_response({"must_change_password": False}, message="Password changed")
