from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


UserRoleValue = Literal["admin", "director", "project_manager", "researcher", "operator", "viewer"]


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    display_name: str = Field(min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=8, max_length=255)
    role: UserRoleValue
    is_active: bool = True

    @field_validator("username", "display_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        local, separator, domain = value.rpartition("@")
        if not separator or not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError("invalid email address")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    email: str | None = None
    role: str
    department: str | None = None
    is_active: bool
    must_change_password: bool
