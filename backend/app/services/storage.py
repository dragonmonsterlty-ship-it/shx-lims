from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Protocol
from uuid import uuid4

from app.core.config import settings


class AttachmentStorage(Protocol):
    def save(self, content: bytes, suffix: str) -> str: ...

    def read(self, storage_key: str) -> bytes: ...

    def exists(self, storage_key: str) -> bool: ...

    def delete(self, storage_key: str) -> None: ...


class LocalAttachmentStorage:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, content: bytes, suffix: str) -> str:
        safe_suffix = self._safe_suffix(suffix)
        for _ in range(10):
            object_id = uuid4().hex
            storage_key = f"{object_id[:2]}/{object_id}{safe_suffix}"
            path = self._resolve_key(storage_key)
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with path.open("xb") as handle:
                    handle.write(content)
            except FileExistsError:
                continue
            return storage_key
        raise RuntimeError("Unable to allocate unique attachment storage key")

    def read(self, storage_key: str) -> bytes:
        return self._resolve_key(storage_key).read_bytes()

    def exists(self, storage_key: str) -> bool:
        return self._resolve_key(storage_key).is_file()

    def delete(self, storage_key: str) -> None:
        path = self._resolve_key(storage_key)
        if path.exists():
            path.unlink()

    def _resolve_key(self, storage_key: str) -> Path:
        key = PurePosixPath(storage_key)
        if key.is_absolute() or ".." in key.parts or any(part in {"", "."} for part in key.parts):
            raise ValueError("Invalid attachment storage key")
        if "\\" in storage_key or ":" in storage_key:
            raise ValueError("Invalid attachment storage key")
        path = (self.root / Path(*key.parts)).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Invalid attachment storage key") from exc
        return path

    @staticmethod
    def _safe_suffix(suffix: str) -> str:
        if not suffix:
            return ""
        normalized = suffix if suffix.startswith(".") else f".{suffix}"
        normalized = normalized.lower()
        if "/" in normalized or "\\" in normalized or ":" in normalized or ".." in normalized:
            raise ValueError("Invalid attachment storage suffix")
        return normalized


def get_attachment_storage() -> AttachmentStorage:
    return LocalAttachmentStorage(settings.attachment_storage_root)


class StorageService(LocalAttachmentStorage):
    """Compatibility shim until the old attachment service is replaced in T1.6A."""

    def __init__(self) -> None:
        super().__init__(settings.attachment_storage_root)

    def generate_storage_key(self) -> str:
        return uuid4().hex

    def upload_bytes(self, storage_key: str, content: bytes, content_type: str | None = None) -> None:
        path = self._resolve_key(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(content)

    def download_bytes(self, storage_key: str) -> bytes:
        return self.read(storage_key)

    def delete_object(self, storage_key: str) -> None:
        self.delete(storage_key)


storage_service = StorageService()
