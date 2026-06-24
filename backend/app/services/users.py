from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.project import PROJECT_OWNER_ROLES


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def list_users(db: Session, *, role_group: str | None = None, keyword: str | None = None) -> list[User]:
    stmt = select(User).where(User.is_active.is_(True)).order_by(User.id)
    if role_group == "project_owner":
        stmt = stmt.where(User.role.in_(PROJECT_OWNER_ROLES))
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(or_(User.username.ilike(pattern), User.full_name.ilike(pattern), User.email.ilike(pattern)))
    return list(db.scalars(stmt).all())


def list_project_owner_candidates(db: Session, *, keyword: str | None = None) -> list[User]:
    return list_users(db, role_group="project_owner", keyword=keyword)
