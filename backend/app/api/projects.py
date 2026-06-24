from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.common import api_response
from app.schemas.project import ProjectCreate, ProjectDetail, ProjectMemberCreate, ProjectMemberRead, ProjectPage, ProjectSummary, ProjectUpdate
from app.services import projects as project_service


router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: DbSession, current_user: CurrentUser) -> dict:
    project = project_service.create_project(db, current_user, payload)
    detail = project_service.read_project_detail(db, current_user, project.id)
    return api_response(ProjectDetail.model_validate(detail).model_dump())


@router.get("")
def list_projects(
    db: DbSession,
    current_user: CurrentUser,
    keyword: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    project_type: str | None = Query(default=None, alias="type"),
    owner_id: int | None = Query(default=None),
    manager_id: int | None = Query(default=None),
    priority: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    projects = project_service.list_projects(
        db,
        current_user,
        keyword=keyword,
        status_filter=status_filter,
        project_type=project_type,
        owner_id=owner_id if owner_id is not None else manager_id,
        priority=priority,
        page=page,
        page_size=page_size,
    )
    return api_response(ProjectPage.model_validate(projects).model_dump())


@router.get("/{project_id}")
def read_project(project_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    project = project_service.read_project_detail(db, current_user, project_id)
    return api_response(ProjectDetail.model_validate(project).model_dump())


@router.get("/{project_id}/summary")
def read_project_summary(project_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    summary = project_service.read_project_summary(db, current_user, project_id)
    return api_response(ProjectSummary.model_validate(summary).model_dump())


@router.patch("/{project_id}")
def update_project(project_id: int, payload: ProjectUpdate, db: DbSession, current_user: CurrentUser) -> dict:
    project = project_service.update_project(db, current_user, project_id, payload)
    detail = project_service.read_project_detail(db, current_user, project.id)
    return api_response(ProjectDetail.model_validate(detail).model_dump())


@router.delete("/{project_id}")
def delete_project(project_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    project_service.soft_delete_project(db, current_user, project_id)
    return api_response({"deleted": True})


@router.get("/{project_id}/members")
def list_project_members(project_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    members = project_service.list_project_members(db, current_user, project_id)
    return api_response([ProjectMemberRead.model_validate(member).model_dump() for member in members])


@router.post("/{project_id}/members", status_code=status.HTTP_201_CREATED)
def add_project_member(project_id: int, payload: ProjectMemberCreate, db: DbSession, current_user: CurrentUser) -> dict:
    member = project_service.add_project_member(db, current_user, project_id, payload)
    return api_response(ProjectMemberRead.model_validate(member).model_dump())


@router.delete("/{project_id}/members/{user_id}")
def delete_project_member(project_id: int, user_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    project_service.remove_project_member(db, current_user, project_id, user_id)
    return api_response({"deleted": True})
