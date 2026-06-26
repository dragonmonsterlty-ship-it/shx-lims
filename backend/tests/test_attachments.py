from datetime import date

import pytest
from fastapi import HTTPException

from app.models.business import Attachment, Project
from app.models.business import DailyReport, DailyReportItem, ExperimentRecord, ExperimentRecordParticipant
from app.models.business import ProjectMember, Result, Sample, SampleTest, TestMethod as LimsTestMethod
from app.services import storage as storage_module

try:
    from app.services import attachment_entities as attachment_entities_module
except ImportError:
    attachment_entities_module = None


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


def _attachment_context(db_session, create_user):
    admin = create_user(username="att-admin", role="admin", must_change_password=False)
    director = create_user(username="att-director", role="director", must_change_password=False)
    manager = create_user(username="att-manager", role="project_manager", must_change_password=False)
    operator = create_user(username="att-operator", role="operator", must_change_password=False)
    other_operator = create_user(username="att-other-operator", role="operator", must_change_password=False)

    project = Project(project_code="ATT-CTX-1", name="Attachment Context 1", lead_user_id=manager.id, created_by=admin.id)
    other_project = Project(project_code="ATT-CTX-2", name="Attachment Context 2", created_by=admin.id)
    db_session.add_all([project, other_project])
    db_session.flush()
    db_session.add_all(
        [
            ProjectMember(project_id=project.id, user_id=manager.id, role_in_project="manager", created_by=admin.id),
            ProjectMember(project_id=project.id, user_id=operator.id, role_in_project="member", created_by=admin.id),
            ProjectMember(project_id=other_project.id, user_id=other_operator.id, role_in_project="member", created_by=admin.id),
        ]
    )

    method = LimsTestMethod(code="ATT-METHOD", name="Attachment Method", method="HPLC", created_by=admin.id)
    sample = Sample(
        sample_code="ATT-SAMPLE-1",
        project_id=project.id,
        compound_name="Compound",
        name="Sample",
        status="registered",
        created_by=admin.id,
    )
    other_sample = Sample(
        sample_code="ATT-SAMPLE-2",
        project_id=other_project.id,
        compound_name="Other",
        name="Other Sample",
        status="registered",
        created_by=admin.id,
    )
    experiment = ExperimentRecord(
        project_id=project.id,
        code="ATT-EXP-1",
        title="Experiment",
        record_type="synthesis",
        status="draft",
        creator_id=operator.id,
        owner_id=operator.id,
        created_by=operator.id,
    )
    daily_report = DailyReport(user_id=operator.id, report_date=date(2026, 6, 25), status="draft", created_by=operator.id)
    zero_project_report = DailyReport(user_id=operator.id, report_date=date(2026, 6, 26), status="draft", created_by=operator.id)
    multi_project_report = DailyReport(user_id=operator.id, report_date=date(2026, 6, 27), status="draft", created_by=operator.id)
    db_session.add_all([method, sample, other_sample, experiment, daily_report, zero_project_report, multi_project_report])
    db_session.flush()

    experiment.participants = [ExperimentRecordParticipant(user_id=operator.id)]
    daily_report.items = [
        DailyReportItem(project_id=project.id, work_type="experiment", content="one project", created_by=operator.id)
    ]
    multi_project_report.items = [
        DailyReportItem(project_id=project.id, work_type="experiment", content="project one", created_by=operator.id),
        DailyReportItem(project_id=other_project.id, work_type="experiment", content="project two", created_by=operator.id),
    ]
    task = SampleTest(sample_id=sample.id, test_method_id=method.id, assigned_to=operator.id, status="in_progress", created_by=admin.id)
    other_task = SampleTest(sample_id=other_sample.id, test_method_id=method.id, assigned_to=other_operator.id, status="in_progress", created_by=admin.id)
    closed_task = SampleTest(sample_id=sample.id, test_method_id=method.id, assigned_to=operator.id, status="completed", created_by=admin.id)
    db_session.add_all([task, other_task])
    db_session.flush()
    closed_task.test_method_id = method.id
    closed_task.sample_id = sample.id
    result = Result(sample_test_id=task.id, result_data={"value": 1}, conclusion="ok", status="draft", entered_by=operator.id, created_by=operator.id)
    db_session.add(result)
    db_session.commit()

    return {
        "admin": admin,
        "director": director,
        "manager": manager,
        "operator": operator,
        "other_operator": other_operator,
        "project": project,
        "other_project": other_project,
        "experiment": experiment,
        "daily_report": daily_report,
        "zero_project_report": zero_project_report,
        "multi_project_report": multi_project_report,
        "sample": sample,
        "other_sample": other_sample,
        "task": task,
        "other_task": other_task,
        "result": result,
    }


def _resolve(db_session, user, entity_type, entity_id, action="read"):
    assert attachment_entities_module is not None, "attachment entity resolver module is missing"
    return attachment_entities_module.resolve_attachment_entity(db_session, user, entity_type, entity_id, action=action)


def test_attachment_entity_resolver_maps_all_public_types(db_session, create_user):
    context = _attachment_context(db_session, create_user)
    user = context["admin"]

    assert _resolve(db_session, user, "experiment", context["experiment"].id).project_id == context["project"].id
    assert _resolve(db_session, user, "daily_report", context["daily_report"].id).project_id == context["project"].id
    assert _resolve(db_session, user, "sample", context["sample"].id).project_id == context["project"].id
    assert _resolve(db_session, user, "test_task", context["task"].id).project_id == context["project"].id
    assert _resolve(db_session, user, "test_result", context["result"].id).project_id == context["project"].id


def test_daily_report_upload_requires_exactly_one_linked_project(db_session, create_user):
    context = _attachment_context(db_session, create_user)

    for report in [context["zero_project_report"], context["multi_project_report"]]:
        with pytest.raises(HTTPException) as exc_info:
            _resolve(db_session, context["operator"], "daily_report", report.id, action="upload")
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Daily report attachments require exactly one linked project."


def test_attachment_entity_resolver_enforces_role_permissions(db_session, create_user):
    context = _attachment_context(db_session, create_user)

    assert _resolve(db_session, context["director"], "sample", context["sample"].id, action="read").project_id == context["project"].id
    with pytest.raises(HTTPException) as director_upload:
        _resolve(db_session, context["director"], "sample", context["sample"].id, action="upload")
    assert director_upload.value.status_code == 403

    assert _resolve(db_session, context["manager"], "sample", context["sample"].id, action="upload").project_id == context["project"].id
    with pytest.raises(HTTPException) as manager_other_project:
        _resolve(db_session, context["manager"], "sample", context["other_sample"].id, action="upload")
    assert manager_other_project.value.status_code in {403, 404}

    assert _resolve(db_session, context["operator"], "experiment", context["experiment"].id, action="upload").project_id == context["project"].id
    assert _resolve(db_session, context["operator"], "test_task", context["task"].id, action="upload").project_id == context["project"].id
    assert _resolve(db_session, context["operator"], "test_result", context["result"].id, action="upload").project_id == context["project"].id
    with pytest.raises(HTTPException) as operator_other_task:
        _resolve(db_session, context["operator"], "test_task", context["other_task"].id, action="read")
    assert operator_other_task.value.status_code == 404
