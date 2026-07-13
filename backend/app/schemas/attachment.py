from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.schemas.common import ApiResponse


class AttachmentEntityType(StrEnum):
    experiment = "experiment"
    daily_report = "daily_report"
    sample = "sample"
    test_task = "test_task"
    test_result = "test_result"
    ref_standard = "ref_standard"


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: AttachmentEntityType
    entity_id: int
    project_id: int | None = None
    original_filename: str
    storage_key: str
    content_type: str
    file_size: int
    checksum_sha256: str
    storage_backend: str
    uploaded_by: int | None = None
    uploaded_at: datetime
    deleted_at: datetime | None = None


class AttachmentDeleteResult(BaseModel):
    id: int
    deleted: bool = True


AttachmentResponse = ApiResponse[AttachmentRead]
AttachmentListResponse = ApiResponse[list[AttachmentRead]]
AttachmentDeleteResponse = ApiResponse[AttachmentDeleteResult]
