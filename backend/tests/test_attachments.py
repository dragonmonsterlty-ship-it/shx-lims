from app.models.business import Attachment, Project


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
