from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.project import ProjectUserBrief


EXPERIMENT_RECORD_STATUSES = {"draft", "in_progress", "submitted", "reviewed", "archived"}
EXPERIMENT_RECORD_TYPES = {"synthesis", "analysis", "purification", "formulation", "stability", "other"}
EXPERIMENT_ATTACHMENT_TYPES = {"hplc", "lcms", "nmr", "ms", "ir", "image", "pdf", "other"}
EXPERIMENT_RECORD_CREATE_ROLES = {"admin", "project_manager", "operator"}
EXPERIMENT_RECORD_ADMIN_ROLES = {"admin"}
EXPERIMENT_RECORD_VIEW_ALL_ROLES = {"admin", "director"}


class ExperimentProjectBrief(BaseModel):
    id: int
    code: str
    name: str


class ExperimentReagentUsageBase(BaseModel):
    reagent_id: int | None = None
    lot_id: int | None = None
    reagent_name_snapshot: str | None = Field(default=None, max_length=200)
    lot_code_snapshot: str | None = Field(default=None, max_length=80)
    quantity: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    unit: str | None = Field(default=None, max_length=30)
    purpose: str | None = Field(default=None, max_length=200)
    remark: str | None = None


class ExperimentReagentUsageCreate(ExperimentReagentUsageBase):
    pass


class ExperimentReagentUsageRead(ExperimentReagentUsageBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_record_id: int
    created_by: int | None = None
    created_at: datetime
    updated_by: int | None = None
    updated_at: datetime | None = None
    outbound_status: str
    shortage_qty: Decimal | None = None
    stock_available: Decimal | None = None
    dispensed_by: int | None = None
    dispensed_at: datetime | None = None


class ExperimentAttachmentBase(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_type: str = Field(max_length=50)
    file_size: int | None = Field(default=None, ge=0)
    storage_key: str | None = Field(default=None, max_length=500)
    description: str | None = None


class ExperimentAttachmentCreate(ExperimentAttachmentBase):
    pass


class ExperimentAttachmentRead(ExperimentAttachmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    experiment_record_id: int
    uploaded_by: int | None = None
    created_by: int | None = None
    created_at: datetime
    updated_by: int | None = None
    updated_at: datetime | None = None


class ExperimentRecordBase(BaseModel):
    project_id: int
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    record_type: str = Field(max_length=50)
    status: str = Field(default="draft", max_length=20)
    owner_id: int | None = None
    experiment_date: date | None = None
    objective: str | None = None
    procedure: str | None = None
    result_summary: str | None = None
    conclusion: str | None = None
    next_step: str | None = None
    risk_note: str | None = None


class ExperimentRecordCreate(ExperimentRecordBase):
    participant_ids: list[int] = Field(default_factory=list)
    reagent_usages: list[ExperimentReagentUsageCreate] = Field(default_factory=list)
    attachments: list[ExperimentAttachmentCreate] = Field(default_factory=list)


class ExperimentRecordUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, min_length=1, max_length=80)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    record_type: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=20)
    owner_id: int | None = None
    experiment_date: date | None = None
    objective: str | None = None
    procedure: str | None = None
    result_summary: str | None = None
    conclusion: str | None = None
    next_step: str | None = None
    risk_note: str | None = None
    participant_ids: list[int] | None = None
    reagent_usages: list[ExperimentReagentUsageCreate] | None = None
    attachments: list[ExperimentAttachmentCreate] | None = None


class ExperimentRecordListItem(BaseModel):
    id: int
    code: str
    title: str
    project_id: int
    project_code: str
    project_name: str
    record_type: str
    status: str
    creator: ProjectUserBrief
    owner: ProjectUserBrief | None = None
    experiment_date: date | None = None
    updated_at: datetime | None = None
    attachment_count: int
    reagent_usage_count: int


class ExperimentRecordDetail(ExperimentRecordListItem):
    project: ExperimentProjectBrief
    creator_id: int
    owner_id: int | None = None
    objective: str | None = None
    procedure: str | None = None
    result_summary: str | None = None
    conclusion: str | None = None
    next_step: str | None = None
    risk_note: str | None = None
    participant_ids: list[int] = Field(default_factory=list)
    reagent_usages: list[ExperimentReagentUsageRead] = Field(default_factory=list)
    attachments: list[ExperimentAttachmentRead] = Field(default_factory=list)
    created_at: datetime


class ExperimentRecordPage(BaseModel):
    items: list[ExperimentRecordListItem]
    total: int
    page: int
    page_size: int
