from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "LIMS"
    app_env: str = "development"
    api_prefix: str = "/api"

    database_url: str = "postgresql+psycopg://lims:lims@localhost:5432/lims"
    test_database_url: str | None = None

    secret_key: str = Field(default="change-this-development-secret", min_length=16)
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    minio_endpoint: str = "http://localhost:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket: str = "lims-dev"
    minio_secure: bool = False
    upload_max_size_bytes: int = 20 * 1024 * 1024
    upload_allowed_extensions: str = "jpg,jpeg,png,pdf,csv,xlsx,xls"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_allowed_extension_set(self) -> set[str]:
        return {extension.strip().lower().lstrip(".") for extension in self.upload_allowed_extensions.split(",") if extension.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
