from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


AUDIT_ACTIONS = {
    "create",
    "update",
    "delete",
    "submit",
    "approve",
    "reject",
    "archive",
    "upload",
    "download",
    "enable_user",
    "disable_user",
    "change_role",
    "reset_password",
}

AUDIT_ENTITY_TYPES = {
    "experiment",
    "daily_report",
    "sample",
    "test_task",
    "test_result",
    "attachment",
    "user",
}


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: int | None = None
    actor_role: str | None = None
    action: str
    entity_type: str
    entity_id: int
    project_id: int | None = None
    target_user_id: int | None = None
    before_data: Any = None
    after_data: Any = None
    metadata: Any = None
    created_at: datetime


class AuditLogPage(BaseModel):
    items: list[AuditLogRead]
    total: int
    page: int
    page_size: int


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserRoleUpdate(BaseModel):
    role: str = Field(min_length=1, max_length=20)


class UserPasswordReset(BaseModel):
    new_password: str = Field(min_length=8, max_length=255)


class PasswordResetResult(BaseModel):
    id: int
    must_change_password: bool
