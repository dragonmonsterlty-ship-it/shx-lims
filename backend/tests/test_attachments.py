from app.models.business import Attachment, Project
from app.services import storage as storage_module


def test_attachment_persists_t1_6a_project_scoped_contract(db_session, create_user):
    user = create_user(username="attachment-manager", role="project_manager", must_change_password=False)
    project = Project(project_code="ATT-P001", name="Attachment Project", lead_user_id=user.id, created_by=user.id)
    db_session.add(project)
    db_session.flush()

    attachment = Attachment(
        entity_type="sample",
        entity_id=123,
        project_id=project.id,
        original_filename="report.pdf",
        storage_key="2026/opaque-key.pdf",
        content_type="application/pdf",
        file_size=17,
        checksum_sha256="a" * 64,
        storage_backend="local",
        uploaded_by=user.id,
    )
    db_session.add(attachment)
    db_session.commit()

    saved = db_session.get(Attachment, attachment.id)
    assert saved is not None
    assert saved.project_id == project.id
    assert saved.original_filename == "report.pdf"
    assert saved.checksum_sha256 == "a" * 64
    assert saved.storage_backend == "local"
    assert saved.deleted_at is None


def test_local_storage_generates_unique_opaque_keys(tmp_path):
    assert hasattr(storage_module, "LocalAttachmentStorage")
    LocalAttachmentStorage = storage_module.LocalAttachmentStorage
    storage = LocalAttachmentStorage(tmp_path)

    first_key = storage.save(b"first", ".pdf")
    second_key = storage.save(b"second", ".pdf")

    assert first_key != second_key
    assert "report.pdf" not in first_key
    assert storage.read(first_key) == b"first"
    assert storage.read(second_key) == b"second"


def test_local_storage_rejects_key_outside_root(tmp_path):
    assert hasattr(storage_module, "LocalAttachmentStorage")
    LocalAttachmentStorage = storage_module.LocalAttachmentStorage
    storage = LocalAttachmentStorage(tmp_path)

    for key in ["../secret.txt", "/tmp/secret.txt", "safe/../../secret.txt"]:
        try:
            storage.read(key)
        except ValueError as exc:
            assert "Invalid attachment storage key" in str(exc)
        else:
            raise AssertionError(f"{key} should be rejected")


def test_local_storage_round_trip_does_not_expose_real_path(tmp_path):
    assert hasattr(storage_module, "LocalAttachmentStorage")
    LocalAttachmentStorage = storage_module.LocalAttachmentStorage
    storage = LocalAttachmentStorage(tmp_path)

    storage_key = storage.save(b"hello", ".txt")

    assert str(tmp_path) not in storage_key
    assert "\\" not in storage_key
    assert storage.exists(storage_key) is True
    assert storage.read(storage_key) == b"hello"
    storage.delete(storage_key)
    assert storage.exists(storage_key) is False
