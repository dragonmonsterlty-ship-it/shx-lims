import os
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import inspect

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
}


def test_data_model_tables_are_registered():
    assert DATA_MODEL_TABLES.issubset(Base.metadata.tables)
    assert Base.metadata.tables["project_member"].constraints
    assert Base.metadata.tables["sample_test"].constraints
    assert Base.metadata.tables["result"].c.sample_test_id.unique is True


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
    attachment = Attachment(entity_type="sample", entity_id=sample.id, file_name="spectrum.png", storage_key="uuid/spectrum.png", uploaded_by=user.id)
    audit_log = AuditLog(table_name="sample", record_id=sample.id, action="create", changed_by=user.id, new_value={"sample_code": sample.sample_code})
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
