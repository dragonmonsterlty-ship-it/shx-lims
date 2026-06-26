from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.common import ApiResponse, api_response
from app.schemas.testing import (
    RejectComment,
    ReviewComment,
    SampleCreate,
    SamplePage,
    SampleRead,
    SampleStatusChange,
    SampleUpdate,
    TestMethodActivation,
    TestMethodCreate,
    TestMethodPage,
    TestMethodRead,
    TestMethodUpdate,
    TestResultCreate,
    TestResultPage,
    TestResultRead,
    TestResultUpdate,
    TestTaskAssigneeUpdate,
    TestTaskCreate,
    TestTaskPage,
    TestTaskRead,
    TestTaskStatusChange,
)
from app.services import testing as testing_service
from app.services import audit_logs as audit_service


samples_router = APIRouter()
methods_router = APIRouter()
tasks_router = APIRouter()
results_router = APIRouter()


@samples_router.get("", response_model=ApiResponse[SamplePage])
def list_samples(
    db: DbSession,
    current_user: CurrentUser,
    project_id: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    data = testing_service.list_samples(
        db, current_user, project_id=project_id, keyword=keyword, status_filter=status_filter,
        priority=priority, page=page, page_size=page_size,
    )
    return api_response(SamplePage.model_validate(data).model_dump())


@samples_router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[SampleRead])
def create_sample(payload: SampleCreate, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(SampleRead.model_validate(testing_service.create_sample(db, current_user, payload)).model_dump())


@samples_router.get("/{sample_id}", response_model=ApiResponse[SampleRead])
def read_sample(sample_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(SampleRead.model_validate(testing_service.read_sample(db, current_user, sample_id)).model_dump())


@samples_router.get("/{sample_id}/timeline")
def read_sample_timeline(sample_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(audit_service.list_entity_timeline(db, current_user, "sample", sample_id))


@samples_router.patch("/{sample_id}", response_model=ApiResponse[SampleRead])
def update_sample(sample_id: int, payload: SampleUpdate, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(SampleRead.model_validate(testing_service.update_sample(db, current_user, sample_id, payload)).model_dump())


@samples_router.delete("/{sample_id}", response_model=ApiResponse[dict[str, bool]])
def delete_sample(sample_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    testing_service.delete_sample(db, current_user, sample_id)
    return api_response({"deleted": True})


@samples_router.post("/{sample_id}/status", response_model=ApiResponse[SampleRead])
def change_sample_status(sample_id: int, payload: SampleStatusChange, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(SampleRead.model_validate(testing_service.change_sample_status(db, current_user, sample_id, payload.status)).model_dump())


@methods_router.get("", response_model=ApiResponse[TestMethodPage])
def list_methods(
    db: DbSession,
    current_user: CurrentUser,
    include_inactive: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
) -> dict:
    data = testing_service.list_methods(db, current_user, include_inactive=include_inactive, page=page, page_size=page_size)
    return api_response(TestMethodPage.model_validate(data).model_dump())


@methods_router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[TestMethodRead])
def create_method(payload: TestMethodCreate, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(TestMethodRead.model_validate(testing_service.create_method(db, current_user, payload)).model_dump())


@methods_router.get("/{method_id}", response_model=ApiResponse[TestMethodRead])
def read_method(method_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(TestMethodRead.model_validate(testing_service.read_method(db, current_user, method_id)).model_dump())


@methods_router.patch("/{method_id}", response_model=ApiResponse[TestMethodRead])
def update_method(method_id: int, payload: TestMethodUpdate, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(TestMethodRead.model_validate(testing_service.update_method(db, current_user, method_id, payload)).model_dump())


@methods_router.post("/{method_id}/activation", response_model=ApiResponse[TestMethodRead])
def activate_method(method_id: int, payload: TestMethodActivation, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(TestMethodRead.model_validate(testing_service.set_method_activation(db, current_user, method_id, payload.is_active)).model_dump())


@tasks_router.get("", response_model=ApiResponse[TestTaskPage])
def list_tasks(
    db: DbSession,
    current_user: CurrentUser,
    project_id: int | None = Query(default=None),
    sample_id: int | None = Query(default=None),
    assigned_to: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    data = testing_service.list_tasks(
        db, current_user, project_id=project_id, sample_id=sample_id, assigned_to=assigned_to,
        status_filter=status_filter, page=page, page_size=page_size,
    )
    return api_response(TestTaskPage.model_validate(data).model_dump())


@tasks_router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[TestTaskRead])
def create_task(payload: TestTaskCreate, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(TestTaskRead.model_validate(testing_service.create_task(db, current_user, payload)).model_dump())


@tasks_router.get("/{task_id}", response_model=ApiResponse[TestTaskRead])
def read_task(task_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(TestTaskRead.model_validate(testing_service.read_task(db, current_user, task_id)).model_dump())


@tasks_router.get("/{task_id}/timeline")
def read_task_timeline(task_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(audit_service.list_entity_timeline(db, current_user, "test_task", task_id))


@tasks_router.patch("/{task_id}/assignee", response_model=ApiResponse[TestTaskRead])
def update_task_assignee(task_id: int, payload: TestTaskAssigneeUpdate, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(TestTaskRead.model_validate(testing_service.update_task_assignee(db, current_user, task_id, payload.assigned_to)).model_dump())


@tasks_router.post("/{task_id}/status", response_model=ApiResponse[TestTaskRead])
def change_task_status(task_id: int, payload: TestTaskStatusChange, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(TestTaskRead.model_validate(testing_service.change_task_status(db, current_user, task_id, payload.status)).model_dump())


@results_router.get("", response_model=ApiResponse[TestResultPage])
def list_results(
    db: DbSession,
    current_user: CurrentUser,
    project_id: int | None = Query(default=None),
    task_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    data = testing_service.list_results(
        db, current_user, project_id=project_id, task_id=task_id, status_filter=status_filter,
        page=page, page_size=page_size,
    )
    return api_response(TestResultPage.model_validate(data).model_dump())


@results_router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[TestResultRead])
def create_result(payload: TestResultCreate, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(TestResultRead.model_validate(testing_service.create_result(db, current_user, payload)).model_dump())


@results_router.get("/{result_id}", response_model=ApiResponse[TestResultRead])
def read_result(result_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(TestResultRead.model_validate(testing_service.read_result(db, current_user, result_id)).model_dump())


@results_router.get("/{result_id}/timeline")
def read_result_timeline(result_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(audit_service.list_entity_timeline(db, current_user, "test_result", result_id))


@results_router.patch("/{result_id}", response_model=ApiResponse[TestResultRead])
def update_result(result_id: int, payload: TestResultUpdate, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(TestResultRead.model_validate(testing_service.update_result(db, current_user, result_id, payload)).model_dump())


@results_router.post("/{result_id}/submit", response_model=ApiResponse[TestResultRead])
def submit_result(result_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(TestResultRead.model_validate(testing_service.submit_result(db, current_user, result_id)).model_dump())


@results_router.post("/{result_id}/approve", response_model=ApiResponse[TestResultRead])
def approve_result(result_id: int, payload: ReviewComment, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(TestResultRead.model_validate(testing_service.approve_result(db, current_user, result_id, payload.comment)).model_dump())


@results_router.post("/{result_id}/reject", response_model=ApiResponse[TestResultRead])
def reject_result(result_id: int, payload: RejectComment, db: DbSession, current_user: CurrentUser) -> dict:
    return api_response(TestResultRead.model_validate(testing_service.reject_result(db, current_user, result_id, payload.comment)).model_dump())
