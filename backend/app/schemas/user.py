from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.modules import ALL_MODULES, normalize_modules, parse_modules


UserRoleValue = Literal["admin", "director", "project_manager", "researcher", "operator", "viewer"]
UserModuleValue = Literal["lims", "refstd"]


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    display_name: str = Field(min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=8, max_length=255)
    role: UserRoleValue
    is_active: bool = True
    modules: list[UserModuleValue] = Field(default_factory=lambda: ["lims"], min_length=1, max_length=2)

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

    @field_validator("modules")
    @classmethod
    def validate_modules(cls, value: list[UserModuleValue]) -> list[UserModuleValue]:
        return normalize_modules(value)


class UserModulesUpdate(BaseModel):
    modules: list[UserModuleValue] = Field(min_length=1, max_length=2)

    @field_validator("modules")
    @classmethod
    def validate_modules(cls, value: list[UserModuleValue]) -> list[UserModuleValue]:
        return normalize_modules(value)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    email: str | None = None
    role: str
    modules: list[UserModuleValue]
    department: str | None = None
    is_active: bool
    must_change_password: bool

    @field_validator("modules", mode="before")
    @classmethod
    def deserialize_modules(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return parse_modules(value)
        return normalize_modules(value)

    @model_validator(mode="after")
    def grant_admin_all_modules(self) -> "UserRead":
        if self.role == "admin":
            self.modules = list(ALL_MODULES)
        return self
