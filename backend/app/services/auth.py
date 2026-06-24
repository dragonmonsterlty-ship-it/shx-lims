from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, hash_token, new_refresh_token, utc_now, verify_password
from app.models.auth import RefreshToken
from app.models.user import User
from app.services.users import get_user_by_username


def _as_utc(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=utc_now().tzinfo)
    return value


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_token_pair(db: Session, user: User) -> tuple[str, str]:
    access_token = create_access_token(user_id=user.id, role=user.role)
    refresh_jti, refresh_token = new_refresh_token()
    token_record = RefreshToken(
        user_id=user.id,
        jti_hash=hash_token(refresh_jti),
        token_hash=hash_token(refresh_token),
        expires_at=utc_now() + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(token_record)
    db.commit()
    return access_token, refresh_token


def refresh_token_pair(db: Session, raw_refresh_token: str) -> tuple[User, str, str]:
    token_record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh_token)))
    now = utc_now()
    if token_record is None or token_record.revoked_at is not None or _as_utc(token_record.expires_at) <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = db.get(User, token_record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or missing user")

    token_record.revoked_at = now
    access_token, new_refresh = create_token_pair(db, user)
    return user, access_token, new_refresh


def revoke_refresh_token(db: Session, raw_refresh_token: str) -> None:
    token_record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_refresh_token)))
    if token_record is not None and token_record.revoked_at is None:
        token_record.revoked_at = utc_now()
        db.commit()


def change_password(db: Session, user: User, old_password: str, new_password: str) -> None:
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utc_now())
    )
    db.commit()
