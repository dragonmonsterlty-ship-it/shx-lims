from urllib.parse import quote

from fastapi import APIRouter, File, Form, Query, UploadFile, status
from fastapi.responses import Response

from app.core.deps import CurrentUser, DbSession
from app.schemas.attachment import (
    AttachmentDeleteResponse,
    AttachmentEntityType,
    AttachmentListResponse,
    AttachmentRead,
    AttachmentResponse,
)
from app.schemas.common import api_response
from app.services import attachments as attachment_service


router = APIRouter()


@router.post("", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    db: DbSession,
    current_user: CurrentUser,
    entity_type: AttachmentEntityType = Form(...),
    entity_id: int = Form(...),
    file: UploadFile = File(...),
) -> dict:
    attachment = await attachment_service.upload_attachment(db, current_user, entity_type.value, entity_id, file)
    return api_response(AttachmentRead.model_validate(attachment))


@router.get("", response_model=AttachmentListResponse)
def list_attachments(
    db: DbSession,
    current_user: CurrentUser,
    entity_type: AttachmentEntityType = Query(...),
    entity_id: int = Query(...),
) -> dict:
    attachments = attachment_service.list_attachments(db, current_user, entity_type.value, entity_id)
    return api_response([AttachmentRead.model_validate(attachment) for attachment in attachments])


@router.get("/{attachment_id}", response_model=AttachmentResponse)
def read_attachment(attachment_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    attachment = attachment_service.get_attachment(db, current_user, attachment_id)
    return api_response(AttachmentRead.model_validate(attachment))


@router.get("/{attachment_id}/download", response_class=Response)
def download_attachment(attachment_id: int, db: DbSession, current_user: CurrentUser) -> Response:
    attachment, content = attachment_service.download_attachment(db, current_user, attachment_id)
    quoted_name = quote(attachment.original_filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quoted_name}",
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=content, media_type=attachment.content_type, headers=headers)


@router.delete("/{attachment_id}", response_model=AttachmentDeleteResponse)
def delete_attachment(attachment_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    result = attachment_service.delete_attachment(db, current_user, attachment_id)
    return api_response(result)
