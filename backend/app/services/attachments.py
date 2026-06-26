from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import mimetypes
from pathlib import PurePath

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.business import Attachment
from app.models.user import User
from app.schemas.attachment import AttachmentDeleteResult
from app.services.attachment_entities import resolve_attachment_entity
from app.services.storage import AttachmentStorage, get_attachment_storage


@dataclass(frozen=True)
class ValidatedUpload:
    original_filename: str
    suffix: str
    content_type: str
    file_size: int
    checksum_sha256: str
    content: bytes


def sanitize_original_filename(filename: str) -> str:
    cleaned = (filename or "").strip()
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required")
    if len(cleaned) > 255:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is too long")
    if "/" in cleaned or "\\" in cleaned or ":" in cleaned or ".." in cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is invalid")
    if PurePath(cleaned).is_absolute():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is invalid")
    if any(ord(char) < 32 or ord(char) == 127 for char in cleaned):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is invalid")
    return cleaned


def detect_content_type(filename: str, content: bytes) -> str:
    stripped = content.lstrip().lower()
    if stripped.startswith((b"<!doctype html", b"<html", b"<script")):
        return "text/html"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"%PDF"):
        return "application/pdf"
    if content.startswith(b"PK\x03\x04"):
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/zip"
    if b"\x00" not in content:
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            return "text/plain"
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def validate_upload(filename: str, declared_type: str | None, content: bytes) -> ValidatedUpload:
    if len(content) > settings.attachment_max_size_bytes:
        raise HTTPException(status_code=413, detail="File exceeds upload size limit")

    original_filename = sanitize_original_filename(filename)
    suffix = PurePath(original_filename).suffix.lower()
    extension = suffix.lstrip(".")
    if not extension:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File extension is required")
    if extension in settings.attachment_blocked_extension_set:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File extension is not allowed")
    if extension not in settings.attachment_allowed_extension_set:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File extension is not allowed")

    declared = (declared_type or "").split(";")[0].strip().lower()
    if declared and declared in settings.attachment_blocked_mime_type_set:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File MIME type is not allowed")

    detected = detect_content_type(original_filename, content)
    if detected in settings.attachment_blocked_mime_type_set:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File MIME type is not allowed")

    content_type = detected if detected != "application/octet-stream" else declared or detected
    return ValidatedUpload(
        original_filename=original_filename,
        suffix=suffix,
        content_type=content_type,
        file_size=len(content),
        checksum_sha256=hashlib.sha256(content).hexdigest(),
        content=content,
    )


async def upload_attachment(
    db: Session,
    current_user: User,
    entity_type: str,
    entity_id: int,
    file: UploadFile,
    storage: AttachmentStorage | None = None,
) -> Attachment:
    resolved = resolve_attachment_entity(db, current_user, entity_type, entity_id, action="upload")
    content = await file.read()
    validated = validate_upload(file.filename or "upload", file.content_type, content)
    attachment_storage = storage or get_attachment_storage()
    storage_key = attachment_storage.save(validated.content, validated.suffix)

    attachment = Attachment(
        entity_type=resolved.entity_type,
        entity_id=resolved.entity_id,
        project_id=resolved.project_id,
        original_filename=validated.original_filename,
        storage_key=storage_key,
        content_type=validated.content_type,
        file_size=validated.file_size,
        checksum_sha256=validated.checksum_sha256,
        storage_backend=settings.attachment_storage_backend,
        uploaded_by=current_user.id,
    )
    db.add(attachment)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        attachment_storage.delete(storage_key)
        raise
    db.refresh(attachment)
    return attachment


def list_attachments(db: Session, current_user: User, entity_type: str, entity_id: int) -> list[Attachment]:
    resolved = resolve_attachment_entity(db, current_user, entity_type, entity_id, action="read")
    stmt = (
        select(Attachment)
        .where(
            Attachment.entity_type == resolved.entity_type,
            Attachment.entity_id == resolved.entity_id,
            Attachment.project_id == resolved.project_id,
            Attachment.deleted_at.is_(None),
        )
        .order_by(Attachment.id)
    )
    return list(db.scalars(stmt).all())


def get_attachment(db: Session, current_user: User, attachment_id: int) -> Attachment:
    attachment = _get_active_attachment(db, attachment_id)
    _resolve_and_check_project(db, current_user, attachment, "read")
    return attachment


def download_attachment(
    db: Session,
    current_user: User,
    attachment_id: int,
    storage: AttachmentStorage | None = None,
) -> tuple[Attachment, bytes]:
    attachment = get_attachment(db, current_user, attachment_id)
    attachment_storage = storage or get_attachment_storage()
    return attachment, attachment_storage.read(attachment.storage_key)


def delete_attachment(db: Session, current_user: User, attachment_id: int) -> AttachmentDeleteResult:
    attachment = _get_active_attachment(db, attachment_id)
    _resolve_and_check_project(db, current_user, attachment, "delete")
    if current_user.role == "operator" and attachment.uploaded_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operators can delete only their own attachments")
    attachment.deleted_at = datetime.now(UTC)
    db.commit()
    return AttachmentDeleteResult(id=attachment.id, deleted=True)


def _get_active_attachment(db: Session, attachment_id: int) -> Attachment:
    attachment = db.scalar(select(Attachment).where(Attachment.id == attachment_id, Attachment.deleted_at.is_(None)))
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return attachment


def _resolve_and_check_project(db: Session, current_user: User, attachment: Attachment, action: str) -> None:
    resolved = resolve_attachment_entity(
        db,
        current_user,
        attachment.entity_type,
        attachment.entity_id,
        action=action,
    )
    if resolved.project_id != attachment.project_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Attachment project mismatch")
