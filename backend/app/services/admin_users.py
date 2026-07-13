from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.modules import serialize_modules
from app.models.user import User
from app.schemas.audit import UserPasswordReset, UserRoleUpdate, UserStatusUpdate
from app.schemas.user import AdminUserCreate, UserModulesUpdate
from app.services.audit_logs import capture, record_audit
from app.services.projects import is_admin


ROLE_VALUES = {"admin", "director", "project_manager", "researcher", "operator", "viewer"}


def ensure_admin_user(user: User) -> None:
    if not is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator permission required")


def list_admin_users(db: Session, current_user: User) -> list[User]:
    ensure_admin_user(current_user)
    return list(db.scalars(select(User).order_by(User.id)).all())


def create_admin_user(db: Session, current_user: User, payload: AdminUserCreate) -> User:
    ensure_admin_user(current_user)
    if db.scalar(select(User.id).where(User.username == payload.username)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = User(
        username=payload.username,
        full_name=payload.display_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        modules=serialize_modules(payload.modules),
        is_active=payload.is_active,
        must_change_password=True,
    )
    db.add(user)
    try:
        db.flush()
        record_audit(
            db,
            current_user,
            action="create",
            entity_type="user",
            entity_id=user.id,
            target_user_id=user.id,
            after_data={
                "username": user.username,
                "role": user.role,
                "is_active": user.is_active,
                "modules": payload.modules,
            },
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists") from exc
    db.refresh(user)
    return user


def update_user_modules(db: Session, current_user: User, user_id: int, payload: UserModulesUpdate) -> User:
    ensure_admin_user(current_user)
    target = get_target_user(db, user_id)
    target.modules = serialize_modules(payload.modules)
    record_audit(
        db,
        current_user,
        action="update",
        entity_type="user",
        entity_id=target.id,
        target_user_id=target.id,
        after_data={"modules": payload.modules},
    )
    db.commit()
    db.refresh(target)
    return target


def _active_admin_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User).where(User.role == "admin", User.is_active.is_(True))) or 0


def _ensure_not_last_active_admin(db: Session, target: User) -> None:
    if target.role == "admin" and target.is_active and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify the last active admin")


def get_target_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def update_user_status(db: Session, current_user: User, user_id: int, payload: UserStatusUpdate) -> User:
    ensure_admin_user(current_user)
    target = get_target_user(db, user_id)
    if target.id == current_user.id and not payload.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable yourself")
    if not payload.is_active:
        _ensure_not_last_active_admin(db, target)
    before = capture({"is_active": target.is_active})
    target.is_active = payload.is_active
    action = "enable_user" if payload.is_active else "disable_user"
    record_audit(
        db,
        current_user,
        action=action,
        entity_type="user",
        entity_id=target.id,
        target_user_id=target.id,
        before_data=before,
        after_data={"is_active": target.is_active},
    )
    db.commit()
    db.refresh(target)
    return target


def update_user_role(db: Session, current_user: User, user_id: int, payload: UserRoleUpdate) -> User:
    ensure_admin_user(current_user)
    if payload.role not in ROLE_VALUES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user role")
    target = get_target_user(db, user_id)
    if target.id == current_user.id and payload.role != "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove your own admin role")
    if payload.role != "admin":
        _ensure_not_last_active_admin(db, target)
    before = capture({"role": target.role})
    target.role = payload.role
    record_audit(
        db,
        current_user,
        action="change_role",
        entity_type="user",
        entity_id=target.id,
        target_user_id=target.id,
        before_data=before,
        after_data={"role": target.role},
    )
    db.commit()
    db.refresh(target)
    return target


def reset_user_password(db: Session, current_user: User, user_id: int, payload: UserPasswordReset) -> dict:
    ensure_admin_user(current_user)
    target = get_target_user(db, user_id)
    target.password_hash = hash_password(payload.new_password)
    target.must_change_password = True
    record_audit(
        db,
        current_user,
        action="reset_password",
        entity_type="user",
        entity_id=target.id,
        target_user_id=target.id,
        after_data={"must_change_password": True},
    )
    db.commit()
    db.refresh(target)
    return {"id": target.id, "must_change_password": target.must_change_password}
