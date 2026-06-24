from urllib.parse import quote

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.responses import Response

from app.core.deps import CurrentUser, DbSession
from app.schemas.attachment import AttachmentRead
from app.schemas.common import api_response
from app.services import attachments as attachment_service


router = APIRouter()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    db: DbSession,
    current_user: CurrentUser,
    entity_type: str = Form(...),
    entity_id: int = Form(...),
    file: UploadFile = File(...),
) -> dict:
    attachment = await attachment_service.upload_attachment(db, current_user, entity_type, entity_id, file)
    return api_response(AttachmentRead.model_validate(attachment).model_dump())


@router.get("/{attachment_id}")
def read_attachment(attachment_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    attachment = attachment_service.get_attachment(db, current_user, attachment_id)
    return api_response(AttachmentRead.model_validate(attachment).model_dump())


@router.get("/{attachment_id}/download")
def download_attachment(attachment_id: int, db: DbSession, current_user: CurrentUser) -> Response:
    attachment, content = attachment_service.download_attachment(db, current_user, attachment_id)
    quoted_name = quote(attachment.file_name)
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quoted_name}"}
    return Response(content=content, media_type=attachment.content_type_detected or "application/octet-stream", headers=headers)
