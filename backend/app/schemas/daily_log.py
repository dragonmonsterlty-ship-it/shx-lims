from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


DAILY_LOG_STATUSES = {"draft", "submitted", "reviewed", "returned"}


class DailyLogCreate(BaseModel):
    project_id: int | None = None
    log_date: date
    content: str = Field(min_length=1)
    related_sample_id: int | None = None


class DailyLogUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: int | None = None
    log_date: date | None = None
    content: str | None = Field(default=None, min_length=1)
    related_sample_id: int | None = None


class DailyLogReview(BaseModel):
    review_comment: str | None = None


class DailyLogReturn(BaseModel):
    review_comment: str = Field(min_length=1)


class DailyLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    project_id: int | None = None
    log_date: date
    content: str
    related_sample_id: int | None = None
    status: str
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    review_comment: str | None = None
    is_deleted: bool
    created_by: int | None = None
    created_at: datetime
    updated_by: int | None = None
    updated_at: datetime | None = None
