from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.business import ProjectMember, Result, Sample, SampleTest, TestMethod
from app.models.user import User
from app.schemas.testing import (
    ReviewStatus,
    SampleCreate,
    SampleUpdate,
    TaskStatus,
    TestMethodCreate,
    TestMethodUpdate,
    TestResultCreate,
    TestResultUpdate,
    TestTaskCreate,
)
from app.services.projects import (
    get_accessible_project_ids,
    get_existing_project,
    is_admin,
    is_director,
    is_project_manager,
    is_project_member,
)


SAMPLE_STATUSES = {"registered", "in_testing", "pending_review", "completed", "cancelled"}
TASK_STATUSES = {"pending", "in_progress", "completed", "cancelled"}
RESULT_STATUSES = {"draft", "submitted", "approved", "rejected"}


def paginate(db: Session, stmt: Select, page: int, page_size: int) -> dict:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all())
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def ensure_sample_status(value: str) -> None:
    if value not in SAMPLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sample status")


def ensure_task_status(value: str) -> None:
    if value not in TASK_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task status")


def ensure_result_status(value: str) -> None:
    if value not in RESULT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid result status")


def ensure_can_manage_project(db: Session, user: User, project_id: int) -> None:
    if is_admin(user):
        return
    if user.role == "project_manager" and is_project_manager(db, user, project_id):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project management permission required")


def ensure_can_view_project(db: Session, user: User, project_id: int) -> None:
    if is_admin(user) or is_director(user) or is_project_member(db, user, project_id):
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")


def visible_project_filter(stmt: Select, db: Session, user: User, project_column):
    project_ids = get_accessible_project_ids(db, user)
    if project_ids is None:
        return stmt
    if not project_ids:
        return stmt.where(False)
    return stmt.where(project_column.in_(project_ids))


def sample_to_dict(sample: Sample) -> dict:
    return {
        "id": sample.id,
        "project_id": sample.project_id,
        "sample_no": sample.sample_code,
        "sample_code": sample.sample_code,
        "name": sample.name,
        "type": sample.sample_type,
        "sample_type": sample.sample_type,
        "source": sample.source,
        "batch_no": sample.batch_no,
        "amount": sample.amount,
        "unit": sample.unit,
        "storage_condition": sample.storage_condition,
        "status": sample.status,
        "priority": sample.priority,
        "received_at": sample.received_at,
        "due_date": sample.due_date,
        "notes": sample.notes,
        "is_deleted": sample.is_deleted,
        "created_by": sample.created_by,
        "created_at": sample.created_at,
        "updated_by": sample.updated_by,
        "updated_at": sample.updated_at,
    }


def get_sample(db: Session, sample_id: int) -> Sample:
    sample = db.scalar(select(Sample).where(Sample.id == sample_id, Sample.is_deleted.is_(False)))
    if sample is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")
    return sample


def read_sample(db: Session, current_user: User, sample_id: int) -> dict:
    sample = get_sample(db, sample_id)
    ensure_can_view_project(db, current_user, sample.project_id)
    return sample_to_dict(sample)


def list_samples(
    db: Session,
    current_user: User,
    *,
    project_id: int | None = None,
    keyword: str | None = None,
    status_filter: str | None = None,
    priority: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = select(Sample).where(Sample.is_deleted.is_(False)).order_by(Sample.id)
    stmt = visible_project_filter(stmt, db, current_user, Sample.project_id)
    if project_id is not None:
        stmt = stmt.where(Sample.project_id == project_id)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(or_(Sample.sample_code.ilike(pattern), Sample.name.ilike(pattern), Sample.source.ilike(pattern)))
    if status_filter is not None:
        ensure_sample_status(status_filter)
        stmt = stmt.where(Sample.status == status_filter)
    if priority is not None:
        stmt = stmt.where(Sample.priority == priority)
    data = paginate(db, stmt, page, page_size)
    return {**data, "items": [sample_to_dict(item) for item in data["items"]]}


def create_sample(db: Session, current_user: User, payload: SampleCreate) -> dict:
    get_existing_project(db, payload.project_id)
    ensure_can_manage_project(db, current_user, payload.project_id)
    ensure_sample_status(payload.status)
    sample = Sample(
        project_id=payload.project_id,
        sample_code=payload.sample_no,
        compound_name=payload.name,
        name=payload.name,
        sample_type=payload.type,
        source=payload.source,
        batch_no=payload.batch_no,
        amount=payload.amount,
        unit=payload.unit,
        storage_condition=payload.storage_condition,
        status=payload.status,
        priority=payload.priority,
        received_at=payload.received_at,
        due_date=payload.due_date,
        notes=payload.notes,
        created_by=current_user.id,
    )
    db.add(sample)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sample number already exists") from exc
    db.refresh(sample)
    return sample_to_dict(sample)


def update_sample(db: Session, current_user: User, sample_id: int, payload: SampleUpdate) -> dict:
    sample = get_sample(db, sample_id)
    ensure_can_manage_project(db, current_user, sample.project_id)
    updates = payload.model_dump(exclude_unset=True)
    if "type" in updates:
        updates["sample_type"] = updates.pop("type")
    for field, value in updates.items():
        setattr(sample, field, value)
    sample.updated_by = current_user.id
    db.commit()
    db.refresh(sample)
    return sample_to_dict(sample)


def change_sample_status(db: Session, current_user: User, sample_id: int, new_status: str) -> dict:
    sample = get_sample(db, sample_id)
    ensure_can_manage_project(db, current_user, sample.project_id)
    ensure_sample_status(new_status)
    sample.status = new_status
    sample.updated_by = current_user.id
    db.commit()
    db.refresh(sample)
    return sample_to_dict(sample)


def delete_sample(db: Session, current_user: User, sample_id: int) -> None:
    sample = get_sample(db, sample_id)
    ensure_can_manage_project(db, current_user, sample.project_id)
    sample.is_deleted = True
    sample.updated_by = current_user.id
    db.commit()


def method_to_dict(method: TestMethod) -> dict:
    return {
        "id": method.id,
        "code": method.code,
        "name": method.name,
        "category": method.category,
        "version": method.version,
        "description": method.description,
        "is_active": method.is_active,
        "created_by": method.created_by,
        "created_at": method.created_at,
        "updated_by": method.updated_by,
        "updated_at": method.updated_at,
    }


def ensure_admin(user: User) -> None:
    if not is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator permission required")


def get_method(db: Session, method_id: int) -> TestMethod:
    method = db.get(TestMethod, method_id)
    if method is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test method not found")
    return method


def list_methods(db: Session, current_user: User, *, include_inactive: bool, page: int, page_size: int) -> dict:
    stmt = select(TestMethod).order_by(TestMethod.id)
    if not include_inactive or not is_admin(current_user):
        stmt = stmt.where(TestMethod.is_active.is_(True))
    data = paginate(db, stmt, page, page_size)
    return {**data, "items": [method_to_dict(item) for item in data["items"]]}


def read_method(db: Session, current_user: User, method_id: int) -> dict:
    method = get_method(db, method_id)
    if not method.is_active and not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test method not found")
    return method_to_dict(method)


def create_method(db: Session, current_user: User, payload: TestMethodCreate) -> dict:
    ensure_admin(current_user)
    method = TestMethod(**payload.model_dump(), method=payload.category, created_by=current_user.id)
    db.add(method)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Test method code already exists") from exc
    db.refresh(method)
    return method_to_dict(method)


def update_method(db: Session, current_user: User, method_id: int, payload: TestMethodUpdate) -> dict:
    ensure_admin(current_user)
    method = get_method(db, method_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(method, field, value)
    if "category" in updates:
        method.method = updates["category"]
    method.updated_by = current_user.id
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Test method code already exists") from exc
    db.refresh(method)
    return method_to_dict(method)


def set_method_activation(db: Session, current_user: User, method_id: int, is_active: bool) -> dict:
    ensure_admin(current_user)
    method = get_method(db, method_id)
    method.is_active = is_active
    method.updated_by = current_user.id
    db.commit()
    db.refresh(method)
    return method_to_dict(method)


def task_options(stmt: Select):
    return stmt.options(
        selectinload(SampleTest.sample),
        selectinload(SampleTest.test_method),
        selectinload(SampleTest.result),
    )


def get_task(db: Session, task_id: int) -> SampleTest:
    task = db.scalar(task_options(select(SampleTest).where(SampleTest.id == task_id)))
    if task is None or task.sample.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test task not found")
    return task


def ensure_can_view_task(db: Session, current_user: User, task: SampleTest) -> None:
    if is_admin(current_user) or is_director(current_user):
        return
    if current_user.role == "project_manager" and is_project_manager(db, current_user, task.sample.project_id):
        return
    if current_user.role == "operator" and task.assigned_to == current_user.id:
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test task not found")


def task_to_dict(task: SampleTest) -> dict:
    result = task.result
    return {
        "id": task.id,
        "sample_id": task.sample_id,
        "method_id": task.test_method_id,
        "test_method_id": task.test_method_id,
        "assigned_to": task.assigned_to,
        "status": task.status,
        "priority": task.priority,
        "due_date": task.due_date,
        "sample": {
            "id": task.sample.id,
            "project_id": task.sample.project_id,
            "sample_no": task.sample.sample_code,
            "name": task.sample.name,
            "status": task.sample.status,
        },
        "method": {
            "id": task.test_method.id,
            "code": task.test_method.code,
            "name": task.test_method.name,
            "category": task.test_method.category,
            "version": task.test_method.version,
        },
        "result_id": result.id if result else None,
        "result_status": result.status if result else None,
        "created_by": task.created_by,
        "created_at": task.created_at,
        "updated_by": task.updated_by,
        "updated_at": task.updated_at,
    }


def ensure_active_project_assignee(db: Session, project_id: int, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.role != "operator" or not is_project_member(db, user, project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee must be an active operator in the project")
    return user


def list_tasks(
    db: Session,
    current_user: User,
    *,
    project_id: int | None = None,
    sample_id: int | None = None,
    assigned_to: int | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = task_options(select(SampleTest).join(Sample).where(Sample.is_deleted.is_(False)).order_by(SampleTest.id))
    if not (is_admin(current_user) or is_director(current_user)):
        if current_user.role == "project_manager":
            managed_ids = select(ProjectMember.project_id).where(
                ProjectMember.user_id == current_user.id,
                ProjectMember.role_in_project == "manager",
            )
            stmt = stmt.where(Sample.project_id.in_(managed_ids))
        else:
            stmt = stmt.where(SampleTest.assigned_to == current_user.id)
    if project_id is not None:
        stmt = stmt.where(Sample.project_id == project_id)
    if sample_id is not None:
        stmt = stmt.where(SampleTest.sample_id == sample_id)
    if assigned_to is not None:
        stmt = stmt.where(SampleTest.assigned_to == assigned_to)
    if status_filter is not None:
        ensure_task_status(status_filter)
        stmt = stmt.where(SampleTest.status == status_filter)
    data = paginate(db, stmt, page, page_size)
    return {**data, "items": [task_to_dict(item) for item in data["items"]]}


def read_task(db: Session, current_user: User, task_id: int) -> dict:
    task = get_task(db, task_id)
    ensure_can_view_task(db, current_user, task)
    return task_to_dict(task)


def create_task(db: Session, current_user: User, payload: TestTaskCreate) -> dict:
    sample = get_sample(db, payload.sample_id)
    ensure_can_manage_project(db, current_user, sample.project_id)
    method = get_method(db, payload.method_id)
    if not method.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test method is inactive")
    ensure_active_project_assignee(db, sample.project_id, payload.assigned_to)
    task = SampleTest(
        sample_id=sample.id,
        test_method_id=method.id,
        assigned_to=payload.assigned_to,
        status="pending",
        priority=payload.priority,
        due_date=payload.due_date,
        created_by=current_user.id,
    )
    sample.status = "in_testing"
    sample.updated_by = current_user.id
    db.add(task)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task already exists for sample and method") from exc
    return task_to_dict(get_task(db, task.id))


def update_task_assignee(db: Session, current_user: User, task_id: int, assigned_to: int) -> dict:
    task = get_task(db, task_id)
    ensure_can_manage_project(db, current_user, task.sample.project_id)
    if task.status in {"completed", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Closed task cannot be reassigned")
    ensure_active_project_assignee(db, task.sample.project_id, assigned_to)
    task.assigned_to = assigned_to
    task.updated_by = current_user.id
    db.commit()
    return task_to_dict(get_task(db, task.id))


def change_task_status(db: Session, current_user: User, task_id: int, new_status: TaskStatus) -> dict:
    task = get_task(db, task_id)
    ensure_task_status(new_status)
    if new_status == "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task completes only after result approval")
    if current_user.role == "operator":
        if task.assigned_to != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Assigned task required")
        allowed = {"pending": {"in_progress"}, "in_progress": set()}
    else:
        ensure_can_manage_project(db, current_user, task.sample.project_id)
        allowed = {"pending": {"in_progress", "cancelled"}, "in_progress": {"cancelled"}}
    if new_status not in allowed.get(task.status, set()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task status transition")
    task.status = new_status
    task.updated_by = current_user.id
    if new_status == "cancelled":
        refresh_sample_status(db, task.sample, current_user.id)
    db.commit()
    return task_to_dict(get_task(db, task.id))


def result_options(stmt: Select):
    return stmt.options(
        selectinload(Result.sample_test).selectinload(SampleTest.sample),
        selectinload(Result.sample_test).selectinload(SampleTest.test_method),
        selectinload(Result.sample_test).selectinload(SampleTest.result),
    )


def get_result(db: Session, result_id: int) -> Result:
    result = db.scalar(result_options(select(Result).where(Result.id == result_id)))
    if result is None or result.sample_test.sample.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test result not found")
    return result


def ensure_can_view_result(db: Session, current_user: User, result: Result) -> None:
    ensure_can_view_task(db, current_user, result.sample_test)


def ensure_assigned_result_editor(current_user: User, result: Result) -> None:
    if is_admin(current_user):
        return
    if current_user.role == "operator" and result.sample_test.assigned_to == current_user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Assigned result editor required")


def ensure_reviewer(db: Session, current_user: User, result: Result) -> None:
    if is_admin(current_user):
        return
    if current_user.role == "project_manager" and is_project_manager(
        db, current_user, result.sample_test.sample.project_id
    ):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Result review permission required")


def result_to_dict(result: Result) -> dict:
    return {
        "id": result.id,
        "task_id": result.sample_test_id,
        "sample_test_id": result.sample_test_id,
        "result_data": result.result_data,
        "conclusion": result.conclusion,
        "status": result.status,
        "submitted_by": result.submitted_by,
        "submitted_at": result.submitted_at,
        "reviewed_by": result.reviewed_by,
        "reviewed_at": result.reviewed_at,
        "review_comment": result.review_comment,
        "task": task_to_dict(result.sample_test),
        "created_by": result.created_by,
        "created_at": result.created_at,
        "updated_by": result.updated_by,
        "updated_at": result.updated_at,
    }


def list_results(
    db: Session,
    current_user: User,
    *,
    project_id: int | None = None,
    task_id: int | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = result_options(select(Result).join(SampleTest).join(Sample).where(Sample.is_deleted.is_(False)).order_by(Result.id))
    if not (is_admin(current_user) or is_director(current_user)):
        if current_user.role == "project_manager":
            managed_ids = select(ProjectMember.project_id).where(
                ProjectMember.user_id == current_user.id,
                ProjectMember.role_in_project == "manager",
            )
            stmt = stmt.where(Sample.project_id.in_(managed_ids))
        else:
            stmt = stmt.where(SampleTest.assigned_to == current_user.id)
    if project_id is not None:
        stmt = stmt.where(Sample.project_id == project_id)
    if task_id is not None:
        stmt = stmt.where(Result.sample_test_id == task_id)
    if status_filter is not None:
        ensure_result_status(status_filter)
        stmt = stmt.where(Result.status == status_filter)
    data = paginate(db, stmt, page, page_size)
    return {**data, "items": [result_to_dict(item) for item in data["items"]]}


def read_result(db: Session, current_user: User, result_id: int) -> dict:
    result = get_result(db, result_id)
    ensure_can_view_result(db, current_user, result)
    return result_to_dict(result)


def create_result(db: Session, current_user: User, payload: TestResultCreate) -> dict:
    task = get_task(db, payload.task_id)
    ensure_can_view_task(db, current_user, task)
    if task.status != "in_progress":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task must be in progress")
    if task.result is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task result already exists")
    result = Result(
        sample_test=task,
        result_data=payload.result_data,
        conclusion=payload.conclusion,
        status="draft",
        review_status="pending",
        entered_by=current_user.id,
        entered_at=datetime.now(UTC),
        created_by=current_user.id,
    )
    ensure_assigned_result_editor(current_user, result)
    db.add(result)
    db.commit()
    return result_to_dict(get_result(db, result.id))


def update_result(db: Session, current_user: User, result_id: int, payload: TestResultUpdate) -> dict:
    result = get_result(db, result_id)
    ensure_assigned_result_editor(current_user, result)
    if result.status not in {"draft", "rejected"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft or rejected results can be edited")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(result, field, value)
    if result.status == "rejected":
        result.status = "draft"
        result.review_status = "pending"
        result.review_comment = None
        result.reviewed_by = None
        result.reviewed_at = None
    result.entered_by = current_user.id
    result.entered_at = datetime.now(UTC)
    result.updated_by = current_user.id
    db.commit()
    return result_to_dict(get_result(db, result.id))


def submit_result(db: Session, current_user: User, result_id: int) -> dict:
    result = get_result(db, result_id)
    ensure_assigned_result_editor(current_user, result)
    if result.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft results can be submitted")
    result.status = "submitted"
    result.review_status = "pending"
    result.submitted_by = current_user.id
    result.submitted_at = datetime.now(UTC)
    result.updated_by = current_user.id
    result.sample_test.sample.status = "pending_review"
    result.sample_test.sample.updated_by = current_user.id
    db.commit()
    return result_to_dict(get_result(db, result.id))


def refresh_sample_status(db: Session, sample: Sample, actor_id: int) -> None:
    tasks = list(db.scalars(select(SampleTest).where(SampleTest.sample_id == sample.id)).all())
    active = [task for task in tasks if task.status != "cancelled"]
    if active and all(task.status == "completed" for task in active):
        sample.status = "completed"
    elif any(task.result and task.result.status == "submitted" for task in active):
        sample.status = "pending_review"
    elif active:
        sample.status = "in_testing"
    else:
        sample.status = "registered"
    sample.updated_by = actor_id


def approve_result(db: Session, current_user: User, result_id: int, comment: str | None) -> dict:
    result = get_result(db, result_id)
    ensure_reviewer(db, current_user, result)
    if result.status != "submitted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only submitted results can be approved")
    result.status = "approved"
    result.review_status = "approved"
    result.reviewed_by = current_user.id
    result.reviewed_at = datetime.now(UTC)
    result.review_comment = comment.strip() if comment else None
    result.updated_by = current_user.id
    result.sample_test.status = "completed"
    result.sample_test.updated_by = current_user.id
    refresh_sample_status(db, result.sample_test.sample, current_user.id)
    db.commit()
    return result_to_dict(get_result(db, result.id))


def reject_result(db: Session, current_user: User, result_id: int, comment: str) -> dict:
    result = get_result(db, result_id)
    ensure_reviewer(db, current_user, result)
    if result.status != "submitted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only submitted results can be rejected")
    result.status = "rejected"
    result.review_status = "rejected"
    result.reviewed_by = current_user.id
    result.reviewed_at = datetime.now(UTC)
    result.review_comment = comment
    result.updated_by = current_user.id
    result.sample_test.status = "in_progress"
    result.sample_test.updated_by = current_user.id
    result.sample_test.sample.status = "in_testing"
    result.sample_test.sample.updated_by = current_user.id
    db.commit()
    return result_to_dict(get_result(db, result.id))
