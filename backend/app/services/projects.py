from fastapi import HTTPException, status
from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.business import ExperimentRecord, Project, ProjectMember
from app.models.user import User
from app.schemas.project import (
    PROJECT_MEMBER_ROLES,
    PROJECT_OWNER_ROLES,
    PROJECT_STATUSES,
    PROJECT_WRITE_ROLES,
    ProjectCreate,
    ProjectMemberCreate,
    ProjectUpdate,
)


def is_admin(user: User) -> bool:
    return user.role == "admin"


def is_director(user: User) -> bool:
    return user.role == "director"


def is_project_owner_role(user: User) -> bool:
    return user.role in PROJECT_OWNER_ROLES


def is_project_write_role(user: User) -> bool:
    return user.role in PROJECT_WRITE_ROLES


def is_project_member(db: Session, user: User, project_id: int) -> bool:
    return db.scalar(
        select(
            exists().where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user.id,
            )
        )
    )


def is_project_manager(db: Session, user: User, project_id: int) -> bool:
    return db.scalar(
        select(
            exists().where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user.id,
                ProjectMember.role_in_project == "manager",
            )
        )
    )


def get_accessible_project_ids(db: Session, user: User) -> list[int] | None:
    if is_admin(user) or is_director(user):
        return None
    return list(db.scalars(select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)).all())


def filter_projects_for_user(stmt: Select[tuple[Project]], db: Session, user: User) -> Select[tuple[Project]]:
    stmt = stmt.where(Project.is_deleted.is_(False))
    if is_admin(user) or is_director(user):
        return stmt
    accessible_ids = get_accessible_project_ids(db, user)
    if not accessible_ids:
        return stmt.where(False)
    return stmt.where(Project.id.in_(accessible_ids))


def ensure_can_create_project(user: User) -> None:
    if not is_project_write_role(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project create permission required")


def ensure_can_update_project(db: Session, user: User, project_id: int) -> None:
    if is_admin(user):
        return
    if user.role == "project_manager" and is_project_manager(db, user, project_id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project update permission required")


def ensure_can_manage_members(db: Session, user: User, project_id: int) -> None:
    if is_admin(user):
        return
    if user.role == "project_manager" and is_project_manager(db, user, project_id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project manager role required")


def ensure_project_status(value: str) -> None:
    if value not in PROJECT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project status")


def ensure_project_member_role(value: str) -> None:
    if value not in PROJECT_MEMBER_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project member role")


def ensure_project_owner_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead user not found")
    if not is_project_owner_role(user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project owner must have an owner-level role")
    return user


def get_existing_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def get_accessible_project(db: Session, user: User, project_id: int) -> Project:
    project = get_existing_project(db, project_id)
    if is_admin(user) or is_director(user) or is_project_member(db, user, project_id):
        return project
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


def project_options(stmt: Select[tuple[Project]]) -> Select[tuple[Project]]:
    return stmt.options(selectinload(Project.lead_user), selectinload(Project.members).selectinload(ProjectMember.user))


def paginate(db: Session, stmt: Select[tuple[Project]], page: int, page_size: int) -> dict:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(project_options(stmt.offset((page - 1) * page_size).limit(page_size))).all())
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def user_brief(user: User | None) -> dict | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "name": user.full_name,
        "username": user.username,
        "role": user.role,
        "email": user.email,
        "department": user.department,
    }


def next_plan_summary(project: Project) -> str | None:
    if project.next_plan is None:
        return None
    return project.next_plan[:120]


def project_member_users(project: Project, *, role_in_project: str | None = None) -> list[User]:
    users = []
    for member in project.members:
        if role_in_project is not None and member.role_in_project != role_in_project:
            continue
        if member.user is not None and member.user.is_active:
            users.append(member.user)
    return users


def project_member_count(project: Project) -> int:
    return len([member for member in project.members if member.role_in_project == "member"])


def experiment_record_count(db: Session, project_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(ExperimentRecord).where(
            ExperimentRecord.project_id == project_id,
            ExperimentRecord.is_deleted.is_(False),
        )
    ) or 0


def serialize_project_list_item(project: Project) -> dict:
    owner = user_brief(project.lead_user)
    return {
        "id": project.id,
        "code": project.project_code,
        "name": project.name,
        "type": project.project_type,
        "status": project.status,
        "owner": owner,
        "manager": owner,
        "priority": project.priority,
        "start_date": project.start_date,
        "expected_end_date": project.end_date,
        "member_count": project_member_count(project),
        "current_stage": project.current_stage,
        "progress": project.progress,
        "updated_at": project.updated_at,
        "risk_summary": project.risk_summary,
        "next_plan_summary": next_plan_summary(project),
    }


def serialize_project_detail(project: Project, db: Session | None = None) -> dict:
    item = serialize_project_list_item(project)
    owner = item["owner"]
    item.update(
        {
            "project_code": project.project_code,
            "project_type": project.project_type,
            "lead_user_id": project.lead_user_id,
            "description": project.description,
            "principal": owner,
            "members": [user_brief(user) for user in project_member_users(project, role_in_project="member")],
            "recent_update": project.recent_update,
            "experiment_record_count": experiment_record_count(db, project.id) if db is not None else 0,
            "attachment_count": 0,
            "inventory_item_count": 0,
            "next_plan": project.next_plan,
            "remark": project.remark,
            "created_by": project.created_by,
            "created_at": project.created_at,
            "is_deleted": project.is_deleted,
        }
    )
    return item


def list_projects(
    db: Session,
    user: User,
    *,
    keyword: str | None = None,
    status_filter: str | None = None,
    project_type: str | None = None,
    owner_id: int | None = None,
    priority: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = select(Project).order_by(Project.id)
    stmt = filter_projects_for_user(stmt, db, user)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                Project.project_code.ilike(pattern),
                Project.name.ilike(pattern),
                Project.lead_user.has(User.full_name.ilike(pattern)),
                Project.lead_user.has(User.username.ilike(pattern)),
            )
        )
    if status_filter is not None:
        ensure_project_status(status_filter)
        stmt = stmt.where(Project.status == status_filter)
    if project_type is not None:
        stmt = stmt.where(Project.project_type == project_type)
    if owner_id is not None:
        stmt = stmt.where(Project.lead_user_id == owner_id)
    if priority is not None:
        stmt = stmt.where(Project.priority == priority)
    page_data = paginate(db, stmt, page, page_size)
    return {
        "items": [serialize_project_list_item(project) for project in page_data["items"]],
        "total": page_data["total"],
        "page": page_data["page"],
        "page_size": page_data["page_size"],
    }


def create_project(db: Session, current_user: User, payload: ProjectCreate) -> Project:
    ensure_can_create_project(current_user)
    ensure_project_status(payload.status)
    if not is_admin(current_user) and payload.lead_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project managers can only create self-owned projects")
    ensure_project_owner_user(db, payload.lead_user_id)

    project = Project(
        project_code=payload.project_code,
        name=payload.name,
        project_type=payload.project_type,
        lead_user_id=payload.lead_user_id,
        status=payload.status,
        priority=payload.priority,
        description=payload.description,
        start_date=payload.start_date,
        end_date=payload.end_date,
        current_stage=payload.current_stage,
        progress=payload.progress,
        recent_update=payload.recent_update,
        risk_summary=payload.risk_summary,
        next_plan=payload.next_plan,
        remark=payload.remark,
        created_by=current_user.id,
    )
    db.add(project)
    try:
        db.flush()
        db.add(
            ProjectMember(
                project_id=project.id,
                user_id=payload.lead_user_id,
                role_in_project="manager",
                created_by=current_user.id,
            )
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project code or member already exists") from exc
    db.refresh(project)
    return project


def update_project(db: Session, current_user: User, project_id: int, payload: ProjectUpdate) -> Project:
    project = get_existing_project(db, project_id)
    ensure_can_update_project(db, current_user, project_id)
    updates = payload.model_dump(exclude_unset=True)
    if not is_admin(current_user):
        forbidden_fields = {"project_code", "lead_user_id"}.intersection(updates)
        if forbidden_fields:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project managers cannot update protected project fields")

    if "status" in updates and updates["status"] is not None:
        ensure_project_status(updates["status"])
    if "lead_user_id" in updates and updates["lead_user_id"] is not None:
        ensure_project_owner_user(db, updates["lead_user_id"])

    for field, value in updates.items():
        setattr(project, field, value)
    if "lead_user_id" in updates and updates["lead_user_id"] is not None:
        existing_manager = db.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == updates["lead_user_id"],
            )
        )
        if existing_manager is None:
            db.add(
                ProjectMember(
                    project_id=project_id,
                    user_id=updates["lead_user_id"],
                    role_in_project="manager",
                    created_by=current_user.id,
                )
            )
        else:
            existing_manager.role_in_project = "manager"
            existing_manager.updated_by = current_user.id
    project.updated_by = current_user.id
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project code already exists") from exc
    db.refresh(project)
    return project


def soft_delete_project(db: Session, current_user: User, project_id: int) -> Project:
    project = get_existing_project(db, project_id)
    ensure_can_update_project(db, current_user, project_id)
    project.is_deleted = True
    project.updated_by = current_user.id
    db.commit()
    db.refresh(project)
    return project


def list_project_members(db: Session, current_user: User, project_id: int) -> list[ProjectMember]:
    get_accessible_project(db, current_user, project_id)
    stmt = (
        select(ProjectMember)
        .options(selectinload(ProjectMember.user))
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.id)
    )
    return list(db.scalars(stmt).all())


def read_project_detail(db: Session, current_user: User, project_id: int) -> dict:
    get_accessible_project(db, current_user, project_id)
    project = db.scalar(
        project_options(select(Project).where(Project.id == project_id, Project.is_deleted.is_(False)))
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return serialize_project_detail(project, db)


def read_project_summary(db: Session, current_user: User, project_id: int) -> dict:
    detail = read_project_detail(db, current_user, project_id)
    return {
        "type": detail["type"],
        "owner": detail["owner"],
        "manager": detail["manager"],
        "member_count": detail["member_count"],
        "current_stage": detail["current_stage"],
        "updated_at": detail["updated_at"],
        "next_plan_summary": detail["next_plan_summary"],
        "risk_summary": detail["risk_summary"],
    }


def add_project_member(db: Session, current_user: User, project_id: int, payload: ProjectMemberCreate) -> ProjectMember:
    get_existing_project(db, project_id)
    ensure_can_manage_members(db, current_user, project_id)
    ensure_project_member_role(payload.role_in_project)
    if not is_admin(current_user) and payload.role_in_project != "member":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project managers can only add project members")

    user = db.get(User, payload.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")

    member = ProjectMember(
        project_id=project_id,
        user_id=payload.user_id,
        role_in_project=payload.role_in_project,
        created_by=current_user.id,
    )
    db.add(member)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project member already exists") from exc
    db.refresh(member)
    return member


def remove_project_member(db: Session, current_user: User, project_id: int, user_id: int) -> None:
    get_existing_project(db, project_id)
    ensure_can_manage_members(db, current_user, project_id)

    member = db.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id))
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found")
    if not is_admin(current_user) and member.role_in_project != "member":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project managers can only remove project members")
    db.delete(member)
    db.commit()
