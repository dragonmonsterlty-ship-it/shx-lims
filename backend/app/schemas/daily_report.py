from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.project import ProjectUserBrief


DAILY_REPORT_STATUSES = {"draft", "submitted", "returned", "confirmed", "archived"}
DAILY_REPORT_WORK_TYPES = {"experiment", "analysis", "purification", "documentation", "meeting", "inventory", "other"}
DAILY_REPORT_REVIEW_ROLES = {"admin", "project_manager", "director"}
DAILY_REPORT_ORDINARY_ROLES = {"operator"}


class ExperimentRecordBrief(BaseModel):
    id: int
    code: str
    title: str
    status: str
    record_type: str
    experiment_date: date | None = None


class DailyReportAttachmentBase(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_type: str | None = Field(default=None, max_length=50)
    file_size: int | None = Field(default=None, ge=0)
    storage_key: str | None = Field(default=None, max_length=500)
    storage_path: str | None = Field(default=None, max_length=500)
    description: str | None = None


class DailyReportAttachmentCreate(DailyReportAttachmentBase):
    pass


class DailyReportAttachmentRead(DailyReportAttachmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    daily_report_id: int
    uploaded_by: int | None = None
    created_by: int | None = None
    created_at: datetime
    updated_by: int | None = None
    updated_at: datetime | None = None


class DailyReportItemBase(BaseModel):
    project_id: int | None = None
    experiment_record_id: int | None = None
    work_type: str = Field(max_length=30)
    content: str = Field(min_length=1)
    progress_note: str | None = None
    hours_spent: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    problem_note: str | None = None
    next_step: str | None = None
    sort_order: int = 0


class DailyReportItemCreate(DailyReportItemBase):
    pass


class DailyReportItemRead(DailyReportItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    daily_report_id: int
    experiment_record: ExperimentRecordBrief | None = None
    created_by: int | None = None
    created_at: datetime
    updated_by: int | None = None
    updated_at: datetime | None = None


class DailyReportCreate(BaseModel):
    user_id: int | None = None
    report_date: date
    status: str = Field(default="draft", max_length=20)
    summary: str | None = None
    issues: str | None = None
    next_plan: str | None = None
    items: list[DailyReportItemCreate] = Field(default_factory=list)
    attachments: list[DailyReportAttachmentCreate] = Field(default_factory=list)


class DailyReportUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_date: date | None = None
    summary: str | None = None
    issues: str | None = None
    next_plan: str | None = None
    items: list[DailyReportItemCreate] | None = None
    attachments: list[DailyReportAttachmentCreate] | None = None


class DailyReportReview(BaseModel):
    review_comment: str | None = None


class DailyReportReturn(BaseModel):
    review_comment: str = Field(min_length=1)


class DailyReportListItem(BaseModel):
    id: int
    user: ProjectUserBrief
    report_date: date
    status: str
    summary: str | None = None
    item_count: int
    project_count: int
    experiment_record_count: int
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    updated_at: datetime | None = None


class DailyReportDetail(DailyReportListItem):
    user_id: int
    reviewer_id: int | None = None
    reviewer: ProjectUserBrief | None = None
    issues: str | None = None
    next_plan: str | None = None
    review_comment: str | None = None
    items: list[DailyReportItemRead] = Field(default_factory=list)
    attachments: list[DailyReportAttachmentRead] = Field(default_factory=list)
    created_at: datetime


class DailyReportPage(BaseModel):
    items: list[DailyReportListItem]
    total: int
    page: int
    page_size: int
