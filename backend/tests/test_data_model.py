import os
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import inspect

from app.core.config import settings
from app.db.base import Base
from app.models.business import (
    Attachment,
    AuditLog,
    DailyLog,
    Experiment,
    ExperimentMaterial,
    InventoryTxn,
    Project,
    ProjectMember,
    RefStandard,
    Reagent,
    ReagentLot,
    Result,
    Sample,
    SampleTest,
    TestMethod as LimsTestMethod,
)


DATA_MODEL_TABLES = {
    "project",
    "project_member",
    "sample",
    "test_method",
    "sample_test",
    "result",
    "experiment",
    "experiment_material",
    "reagent",
    "reagent_lot",
    "inventory_txn",
    "daily_log",
    "attachment",
    "audit_log",
    "ref_standard",
    "ref_standard_code_counter",
}


def test_data_model_tables_are_registered():
    assert DATA_MODEL_TABLES.issubset(Base.metadata.tables)
    assert Base.metadata.tables["project_member"].constraints
    assert Base.metadata.tables["sample_test"].constraints
    assert Base.metadata.tables["result"].c.sample_test_id.unique is True
    assert {"amount", "unit", "storage_condition"}.issubset(Base.metadata.tables["sample"].c.keys())
    assert {"category", "version", "description"}.issubset(Base.metadata.tables["test_method"].c.keys())
    assert {"priority", "due_date"}.issubset(Base.metadata.tables["sample_test"].c.keys())
    assert {
        "result_data",
        "conclusion",
        "status",
        "submitted_by",
        "submitted_at",
    }.issubset(Base.metadata.tables["result"].c.keys())


def test_attachment_model_uses_t1_6a_canonical_contract():
    attachment_columns = set(Base.metadata.tables["attachment"].c.keys())

    assert {
        "id",
        "entity_type",
        "entity_id",
        "project_id",
        "original_filename",
        "storage_key",
        "content_type",
        "file_size",
        "checksum_sha256",
        "storage_backend",
        "uploaded_by",
        "uploaded_at",
        "deleted_at",
    }.issubset(attachment_columns)
    assert "file_name" not in attachment_columns
    assert "sha256" not in attachment_columns
    assert "content_type_detected" not in attachment_columns
    assert Base.metadata.tables["attachment"].c.project_id.nullable is True


def test_ref_standard_model_contract(db_session, create_user):
    user = create_user(username="refstd_model", role="operator", modules="refstd", must_change_password=False)
    table = Base.metadata.tables["ref_standard"]
    assert {
        "id",
        "code",
        "name",
        "batch_no",
        "source",
        "spec",
        "assigned_value",
        "initial_amount",
        "current_amount",
        "unit",
        "storage_condition",
        "expires_at",
        "status",
        "notes",
        "created_by",
        "created_at",
        "updated_at",
        "is_deleted",
    }.issubset(table.c.keys())

    standard = RefStandard(
        code="RS-2026-0001",
        name="Reference A",
        source="self_made",
        initial_amount=Decimal("10.0000"),
        current_amount=Decimal("10.0000"),
        created_by=user.id,
    )
    db_session.add(standard)
    db_session.commit()
    db_session.refresh(standard)
    assert standard.status == "in_stock"
    assert standard.current_amount == Decimal("10.0000")


def test_attachment_settings_default_to_local_storage_contract():
    assert settings.attachment_max_size_bytes == 20 * 1024 * 1024
    assert settings.attachment_storage_backend == "local"
    assert settings.attachment_storage_root
    assert "exe" in settings.attachment_blocked_extension_set


def test_data_model_minimal_insert_graph(db_session, create_user):
    user = create_user(username="manager", role="project_manager", must_change_password=False)

    project = Project(project_code="P001", name="Project One", lead_user_id=user.id, created_by=user.id)
    reagent = Reagent(name="Methanol", default_unit="mL", min_stock=Decimal("10.0000"), created_by=user.id)
    method = LimsTestMethod(code="HPLC-ASSAY", name="Assay", method="HPLC", unit="%", created_by=user.id)
    db_session.add_all([project, reagent, method])
    db_session.flush()

    member = ProjectMember(project_id=project.id, user_id=user.id, role_in_project="manager", created_by=user.id)
    sample = Sample(
        sample_code="P001-20260622-01",
        project_id=project.id,
        compound_name="Compound A",
        name="Sample A",
        status="registered",
        created_by=user.id,
    )
    lot = ReagentLot(reagent_id=reagent.id, lot_no="LOT-1", quantity=Decimal("50.0000"), created_by=user.id)
    db_session.add_all([member, sample, lot])
    db_session.flush()

    sample_test = SampleTest(sample_id=sample.id, test_method_id=method.id, assigned_to=user.id, status="pending", created_by=user.id)
    experiment = Experiment(
        project_id=project.id,
        experiment_no="EXP-001",
        title="Screening",
        author_id=user.id,
        related_sample_id=sample.id,
        created_by=user.id,
    )
    daily_log = DailyLog(user_id=user.id, project_id=project.id, log_date=date(2026, 6, 22), content="Work log", created_by=user.id)
    db_session.add_all([sample_test, experiment, daily_log])
    db_session.flush()

    result = Result(sample_test_id=sample_test.id, value_num=Decimal("99.500000"), entered_by=user.id, created_by=user.id)
    material = ExperimentMaterial(experiment_id=experiment.id, material_name="Methanol", reagent_lot_id=lot.id, created_by=user.id)
    txn = InventoryTxn(reagent_lot_id=lot.id, txn_type="in", quantity=Decimal("50.0000"), balance_after=Decimal("50.0000"), operator_id=user.id)
    attachment = Attachment(
        entity_type="sample",
        entity_id=sample.id,
        project_id=project.id,
        original_filename="spectrum.png",
        storage_key="uuid/spectrum.png",
        content_type="image/png",
        file_size=12,
        checksum_sha256="0" * 64,
        storage_backend="local",
        uploaded_by=user.id,
    )
    audit_log = AuditLog(
        actor_user_id=user.id,
        actor_role=user.role,
        action="create",
        entity_type="sample",
        entity_id=sample.id,
        project_id=project.id,
        after_data={"sample_code": sample.sample_code},
    )
    db_session.add_all([result, material, txn, attachment, audit_log])
    db_session.commit()

    assert db_session.get(Project, project.id).members[0].role_in_project == "manager"
    assert db_session.get(SampleTest, sample_test.id).result.review_status == "pending"
    assert db_session.get(ReagentLot, lot.id).inventory_txns[0].txn_type == "in"


def test_alembic_upgrade_head_creates_data_model_tables(tmp_path):
    db_path = tmp_path / "migration.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    env.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough")

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

    from sqlalchemy import create_engine

    engine = create_engine(env["DATABASE_URL"])
    try:
        table_names = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert DATA_MODEL_TABLES.issubset(table_names)


def test_user_modules_migration_backfills_existing_users(tmp_path):
    db_path = tmp_path / "modules-migration.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    env.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough")
    backend_dir = Path(__file__).resolve().parents[1]

    before = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "202606290001"],
        cwd=backend_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert before.returncode == 0, before.stderr

    from sqlalchemy import create_engine, text

    engine = create_engine(env["DATABASE_URL"])
    with engine.begin() as connection:
        connection.execute(
            text(
                'INSERT INTO "user" '
                "(username, full_name, password_hash, role, is_active, must_change_password) "
                "VALUES ('legacy-user', 'Legacy User', 'hash', 'operator', 1, 0)"
            )
        )
    engine.dispose()

    after = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert after.returncode == 0, after.stderr

    engine = create_engine(env["DATABASE_URL"])
    try:
        with engine.connect() as connection:
            modules = connection.execute(
                text('SELECT modules FROM "user" WHERE username = \'legacy-user\'')
            ).scalar_one()
    finally:
        engine.dispose()
    assert modules == "lims"


def test_ref_standard_migration_upgrades_legacy_database_and_round_trips(tmp_path):
    db_path = tmp_path / "ref-standard-migration.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    env.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough")
    backend_dir = Path(__file__).resolve().parents[1]

    def run_alembic(*args: str) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=backend_dir,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    run_alembic("upgrade", "202607130001")

    from sqlalchemy import create_engine, text

    engine = create_engine(env["DATABASE_URL"])
    with engine.begin() as connection:
        connection.execute(
            text(
                'INSERT INTO "user" '
                "(id, username, full_name, password_hash, role, modules, is_active, must_change_password) "
                "VALUES (1, 'legacy-refstd', 'Legacy Refstd', 'hash', 'operator', 'refstd', 1, 0)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO project (id, project_code, name, created_by) "
                "VALUES (1, 'LEGACY-P', 'Legacy Project', 1)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO attachment "
                "(id, entity_type, entity_id, project_id, original_filename, storage_key, content_type, "
                "file_size, checksum_sha256, storage_backend, uploaded_by) "
                "VALUES (1, 'sample', 1, 1, 'legacy.pdf', 'legacy-key', 'application/pdf', 3, :checksum, 'local', 1)"
            ),
            {"checksum": "a" * 64},
        )
    engine.dispose()

    run_alembic("upgrade", "head")
    engine = create_engine(env["DATABASE_URL"])
    try:
        inspector = inspect(engine)
        assert {"ref_standard", "ref_standard_code_counter"}.issubset(inspector.get_table_names())
        project_id_column = next(
            column for column in inspector.get_columns("attachment") if column["name"] == "project_id"
        )
        assert project_id_column["nullable"] is True
        with engine.begin() as connection:
            assert connection.execute(text("SELECT original_filename FROM attachment WHERE id = 1")).scalar_one() == "legacy.pdf"
            connection.execute(
                text(
                    "INSERT INTO ref_standard "
                    "(id, code, name, source, initial_amount, current_amount, status, created_by) "
                    "VALUES (1, 'RS-2030-0001', 'Migrated Standard', 'self_made', 1, 1, 'in_stock', 1)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO attachment "
                    "(id, entity_type, entity_id, project_id, original_filename, storage_key, content_type, "
                    "file_size, checksum_sha256, storage_backend, uploaded_by) "
                    "VALUES (2, 'ref_standard', 1, NULL, 'coa.pdf', 'coa-key', 'application/pdf', 3, :checksum, 'local', 1)"
                ),
                {"checksum": "b" * 64},
            )
    finally:
        engine.dispose()

    run_alembic("downgrade", "202607130001")
    engine = create_engine(env["DATABASE_URL"])
    try:
        inspector = inspect(engine)
        assert "ref_standard" not in inspector.get_table_names()
        assert "ref_standard_code_counter" not in inspector.get_table_names()
        project_id_column = next(
            column for column in inspector.get_columns("attachment") if column["name"] == "project_id"
        )
        assert project_id_column["nullable"] is False
        with engine.connect() as connection:
            attachments = connection.execute(text("SELECT id, entity_type FROM attachment ORDER BY id")).all()
        assert attachments == [(1, "sample")]
    finally:
        engine.dispose()

    run_alembic("upgrade", "head")
    engine = create_engine(env["DATABASE_URL"])
    try:
        assert {"ref_standard", "ref_standard_code_counter"}.issubset(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert connection.execute(text("SELECT original_filename FROM attachment WHERE id = 1")).scalar_one() == "legacy.pdf"
    finally:
        engine.dispose()
