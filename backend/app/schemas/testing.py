from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SampleStatus = Literal["registered", "in_testing", "pending_review", "completed", "cancelled"]
TaskStatus = Literal["pending", "in_progress", "completed", "cancelled"]
ReviewStatus = Literal["draft", "submitted", "approved", "rejected"]


class PageBase(BaseModel):
    total: int
    page: int
    page_size: int


class SampleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: int
    sample_no: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    type: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=200)
    batch_no: str | None = Field(default=None, max_length=80)
    amount: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    unit: str | None = Field(default=None, max_length=30)
    storage_condition: str | None = Field(default=None, max_length=100)
    status: SampleStatus = "registered"
    priority: str = Field(default="normal", max_length=10)
    received_at: datetime | None = None
    due_date: date | None = None
    notes: str | None = None


class SampleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=200)
    batch_no: str | None = Field(default=None, max_length=80)
    amount: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    unit: str | None = Field(default=None, max_length=30)
    storage_condition: str | None = Field(default=None, max_length=100)
    priority: str | None = Field(default=None, max_length=10)
    received_at: datetime | None = None
    due_date: date | None = None
    notes: str | None = None


class SampleStatusChange(BaseModel):
    status: SampleStatus


class SampleRead(BaseModel):
    id: int
    project_id: int
    sample_no: str
    sample_code: str
    name: str
    type: str | None = None
    sample_type: str | None = None
    source: str | None = None
    batch_no: str | None = None
    amount: Decimal | None = None
    unit: str | None = None
    storage_condition: str | None = None
    status: SampleStatus
    priority: str
    received_at: datetime | None = None
    due_date: date | None = None
    notes: str | None = None
    is_deleted: bool
    created_by: int | None = None
    created_at: datetime
    updated_by: int | None = None
    updated_at: datetime | None = None


class SamplePage(PageBase):
    items: list[SampleRead]


class TestMethodCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=50)
    version: str | None = Field(default=None, max_length=30)
    description: str | None = None
    is_active: bool = True


class TestMethodUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, min_length=1, max_length=40)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=50)
    version: str | None = Field(default=None, max_length=30)
    description: str | None = None


class TestMethodActivation(BaseModel):
    is_active: bool


class TestMethodRead(BaseModel):
    id: int
    code: str
    name: str
    category: str | None = None
    version: str | None = None
    description: str | None = None
    is_active: bool
    created_by: int | None = None
    created_at: datetime
    updated_by: int | None = None
    updated_at: datetime | None = None


class TestMethodPage(PageBase):
    items: list[TestMethodRead]


class TaskSampleBrief(BaseModel):
    id: int
    project_id: int
    sample_no: str
    name: str
    status: str


class TaskMethodBrief(BaseModel):
    id: int
    code: str
    name: str
    category: str | None = None
    version: str | None = None


class TestTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_id: int
    method_id: int
    assigned_to: int
    priority: str = Field(default="normal", max_length=10)
    due_date: date | None = None


class TestTaskAssigneeUpdate(BaseModel):
    assigned_to: int


class TestTaskStatusChange(BaseModel):
    status: TaskStatus


class TestTaskRead(BaseModel):
    id: int
    sample_id: int
    method_id: int
    test_method_id: int
    assigned_to: int | None = None
    status: TaskStatus
    priority: str
    due_date: date | None = None
    sample: TaskSampleBrief
    method: TaskMethodBrief
    result_id: int | None = None
    result_status: ReviewStatus | None = None
    created_by: int | None = None
    created_at: datetime
    updated_by: int | None = None
    updated_at: datetime | None = None


class TestTaskPage(PageBase):
    items: list[TestTaskRead]


class TestResultCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: int
    result_data: Any
    conclusion: str | None = None


class TestResultUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_data: Any | None = None
    conclusion: str | None = None


class ReviewComment(BaseModel):
    comment: str | None = None


class RejectComment(BaseModel):
    comment: str = Field(min_length=1)

    @field_validator("comment")
    @classmethod
    def comment_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Reject comment is required")
        return value


class TestResultRead(BaseModel):
    id: int
    task_id: int
    sample_test_id: int
    result_data: Any
    conclusion: str | None = None
    status: ReviewStatus
    submitted_by: int | None = None
    submitted_at: datetime | None = None
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    review_comment: str | None = None
    task: TestTaskRead
    created_by: int | None = None
    created_at: datetime
    updated_by: int | None = None
    updated_at: datetime | None = None


class TestResultPage(PageBase):
    items: list[TestResultRead]
