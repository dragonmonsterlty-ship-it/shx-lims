from pathlib import PurePath
import hashlib
import mimetypes

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.business import Attachment
from app.models.user import User
from app.schemas.attachment import ENABLED_ATTACHMENT_ENTITIES
from app.services import daily_logs as daily_log_service
from app.services.storage import StorageService, storage_service


def _extension_for(file_name: str) -> str:
    suffix = PurePath(file_name).suffix.lower().lstrip(".")
    if not suffix:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File extension is required")
    return suffix


def _detect_content_type(file_name: str, content: bytes) -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"%PDF"):
        return "application/pdf"
    if content.startswith(b"PK\x03\x04"):
        guessed, _ = mimetypes.guess_type(file_name)
        return guessed or "application/zip"
    guessed, _ = mimetypes.guess_type(file_name)
    return guessed or "application/octet-stream"


def _validate_upload(entity_type: str, file_name: str, content: bytes) -> None:
    if entity_type not in ENABLED_ATTACHMENT_ENTITIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only daily_log attachments are enabled in this MVP")
    if len(content) > settings.upload_max_size_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File exceeds upload size limit")
    extension = _extension_for(file_name)
    if extension not in settings.upload_allowed_extension_set:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File extension is not allowed")


def _get_attachment(db: Session, current_user: User, attachment_id: int) -> Attachment:
    attachment = db.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    if attachment.entity_type != "daily_log":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    daily_log_service.get_visible_daily_log(db, current_user, attachment.entity_id)
    return attachment


async def upload_attachment(
    db: Session,
    current_user: User,
    entity_type: str,
    entity_id: int,
    file: UploadFile,
    storage: StorageService = storage_service,
) -> Attachment:
    content = await file.read()
    file_name = file.filename or "upload"
    _validate_upload(entity_type, file_name, content)
    daily_log = daily_log_service.get_visible_daily_log(db, current_user, entity_id)
    daily_log_service.ensure_can_upload_daily_log_attachment(db, current_user, daily_log)

    content_type_detected = _detect_content_type(file_name, content)
    storage_key = storage.generate_storage_key()
    sha256 = hashlib.sha256(content).hexdigest()
    storage.upload_bytes(storage_key, content, content_type_detected)

    attachment = Attachment(
        entity_type=entity_type,
        entity_id=entity_id,
        file_name=file_name,
        storage_key=storage_key,
        file_type=file.content_type,
        content_type_detected=content_type_detected,
        file_size=len(content),
        sha256=sha256,
        uploaded_by=current_user.id,
        upload_status="uploaded",
        preview_status="not_generated",
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def get_attachment(db: Session, current_user: User, attachment_id: int) -> Attachment:
    return _get_attachment(db, current_user, attachment_id)


def download_attachment(
    db: Session,
    current_user: User,
    attachment_id: int,
    storage: StorageService = storage_service,
) -> tuple[Attachment, bytes]:
    attachment = _get_attachment(db, current_user, attachment_id)
    return attachment, storage.download_bytes(attachment.storage_key)


def list_daily_log_attachments(db: Session, current_user: User, daily_log_id: int) -> list[Attachment]:
    daily_log_service.get_visible_daily_log(db, current_user, daily_log_id)
    stmt = (
        select(Attachment)
        .where(Attachment.entity_type == "daily_log", Attachment.entity_id == daily_log_id)
        .order_by(Attachment.id)
    )
    return list(db.scalars(stmt).all())
