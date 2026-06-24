from datetime import datetime

from pydantic import BaseModel, ConfigDict


ATTACHMENT_ENTITIES = {"sample", "result", "experiment", "daily_log"}
ENABLED_ATTACHMENT_ENTITIES = {"daily_log"}


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    file_name: str
    storage_key: str
    file_type: str | None = None
    content_type_detected: str | None = None
    file_size: int | None = None
    sha256: str | None = None
    thumbnail_key: str | None = None
    upload_status: str
    preview_status: str | None = None
    uploaded_by: int | None = None
    uploaded_at: datetime
