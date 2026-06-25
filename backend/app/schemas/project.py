from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserRead


PROJECT_STATUSES = {"active", "paused", "completed", "cancelled"}
PROJECT_MEMBER_ROLES = {"manager", "member"}
PROJECT_OWNER_ROLES = {"admin", "project_manager"}
PROJECT_WRITE_ROLES = {"admin", "project_manager"}


class ProjectBase(BaseModel):
    project_code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=100)
    project_type: str | None = Field(default=None, max_length=50)
    status: str = Field(default="active", max_length=20)
    priority: str = Field(default="normal", max_length=10)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    current_stage: str | None = Field(default=None, max_length=100)
    progress: int = Field(default=0, ge=0, le=100)
    recent_update: str | None = None
    risk_summary: str | None = None
    next_plan: str | None = None
    remark: str | None = None


class ProjectCreate(ProjectBase):
    lead_user_id: int


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_code: str | None = Field(default=None, min_length=1, max_length=40)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    project_type: str | None = Field(default=None, max_length=50)
    lead_user_id: int | None = None
    status: str | None = Field(default=None, max_length=20)
    priority: str | None = Field(default=None, max_length=10)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    current_stage: str | None = Field(default=None, max_length=100)
    progress: int | None = Field(default=None, ge=0, le=100)
    recent_update: str | None = None
    risk_summary: str | None = None
    next_plan: str | None = None
    remark: str | None = None


class ProjectUserBrief(BaseModel):
    id: int
    name: str
    username: str
    role: str
    email: str | None = None
    department: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_code: str
    name: str
    project_type: str | None = None
    lead_user_id: int | None = None
    status: str
    priority: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    current_stage: str | None = None
    progress: int
    recent_update: str | None = None
    risk_summary: str | None = None
    next_plan: str | None = None
    remark: str | None = None
    is_deleted: bool
    created_by: int | None = None
    created_at: datetime
    updated_by: int | None = None
    updated_at: datetime | None = None
    code: str | None = None
    type: str | None = None
    expected_end_date: date | None = None
    owner: ProjectUserBrief | None = None
    manager: ProjectUserBrief | None = None
    principal: ProjectUserBrief | None = None
    member_count: int = 0
    next_plan_summary: str | None = None


class ProjectListItem(BaseModel):
    id: int
    code: str
    name: str
    type: str | None = None
    status: str
    owner: ProjectUserBrief | None = None
    manager: ProjectUserBrief | None = None
    priority: str
    start_date: date | None = None
    expected_end_date: date | None = None
    member_count: int
    current_stage: str | None = None
    progress: int
    updated_at: datetime | None = None
    risk_summary: str | None = None
    next_plan_summary: str | None = None


class ProjectDetail(ProjectListItem):
    project_code: str
    project_type: str | None = None
    lead_user_id: int | None = None
    description: str | None = None
    principal: ProjectUserBrief | None = None
    members: list[ProjectUserBrief] = Field(default_factory=list)
    recent_update: str | None = None
    experiment_record_count: int = 0
    attachment_count: int = 0
    inventory_item_count: int = 0
    next_plan: str | None = None
    remark: str | None = None
    created_by: int | None = None
    created_at: datetime
    is_deleted: bool


class ProjectPage(BaseModel):
    items: list[ProjectListItem]
    total: int
    page: int
    page_size: int


class ProjectSummary(BaseModel):
    type: str | None = None
    owner: ProjectUserBrief | None = None
    manager: ProjectUserBrief | None = None
    member_count: int
    current_stage: str | None = None
    updated_at: datetime | None = None
    next_plan_summary: str | None = None
    risk_summary: str | None = None


class ProjectMemberCreate(BaseModel):
    user_id: int
    role_in_project: str = Field(default="member", max_length=20)


class ProjectMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    role_in_project: str
    created_by: int | None = None
    created_at: datetime
    updated_by: int | None = None
    updated_at: datetime | None = None
    user: UserRead | None = None
