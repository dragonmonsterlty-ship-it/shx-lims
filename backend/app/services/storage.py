from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.config import settings


@dataclass(frozen=True)
class StoredObject:
    storage_key: str
    content: bytes
    content_type: str | None = None


class StorageService:
    def generate_storage_key(self) -> str:
        return str(uuid4())

    def upload_bytes(self, storage_key: str, content: bytes, content_type: str | None = None) -> None:
        try:
            from minio import Minio
        except ImportError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="MinIO client is not installed") from exc

        client = Minio(
            settings.minio_endpoint.removeprefix("http://").removeprefix("https://"),
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure,
        )
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
        client.put_object(
            settings.minio_bucket,
            storage_key,
            BytesIO(content),
            length=len(content),
            content_type=content_type or "application/octet-stream",
        )

    def download_bytes(self, storage_key: str) -> bytes:
        try:
            from minio import Minio
        except ImportError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="MinIO client is not installed") from exc

        client = Minio(
            settings.minio_endpoint.removeprefix("http://").removeprefix("https://"),
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure,
        )
        response = client.get_object(settings.minio_bucket, storage_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_object(self, storage_key: str) -> None:
        try:
            from minio import Minio
        except ImportError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="MinIO client is not installed") from exc

        client = Minio(
            settings.minio_endpoint.removeprefix("http://").removeprefix("https://"),
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure,
        )
        client.remove_object(settings.minio_bucket, storage_key)


storage_service = StorageService()
