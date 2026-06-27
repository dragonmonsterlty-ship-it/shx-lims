from pathlib import Path

from app.models.business import (
    AuditLog,
    DailyReport,
    ExperimentRecord,
    Project,
    Result,
    Sample,
    SampleTest,
)
from app.models.user import User
from scripts import seed_demo


def test_demo_seed_builds_stable_browser_walkthrough_data(db_session):
    seed_demo.seed_database(db_session)

    users = {item.username: item for item in db_session.query(User).all()}
    assert {"admin", "project_manager", "analyst", "operator"} <= users.keys()

    projects = db_session.query(Project).order_by(Project.project_code).all()
    assert [(item.project_code, item.name) for item in projects] == [
        ("DEMO-001", "MVP Demo Project A"),
        ("DEMO-002", "MVP Demo Project B"),
    ]

    samples = {item.sample_code: item for item in db_session.query(Sample).all()}
    assert samples["DEMO-SAMPLE-PENDING"].status == "in_testing"
    assert samples["DEMO-SAMPLE-COMPLETE"].status == "completed"

    tasks = db_session.query(SampleTest).all()
    assert {item.status for item in tasks} >= {"pending", "completed"}
    assert db_session.query(Result).filter(Result.status == "approved").count() == 1

    reports = db_session.query(DailyReport).all()
    assert any(len(item.items) >= 2 for item in reports)
    assert {item.status for item in reports} >= {"draft", "confirmed"}
    assert {item.status for item in db_session.query(ExperimentRecord).all()} >= {"draft", "submitted"}

    audited_types = {item.entity_type for item in db_session.query(AuditLog).all()}
    assert {"experiment", "daily_report", "sample"} <= audited_types


def test_demo_reset_entrypoint_has_destructive_local_guards():
    script = Path(__file__).resolve().parents[2] / "scripts" / "seed-demo.ps1"
    content = script.read_text(encoding="utf-8")

    assert "[switch]$Force" in content
    assert "localhost" in content
    assert "127.0.0.1" in content
    assert "15432" in content
    assert "demo/dev" in content
    assert "alembic downgrade base" in content
    assert "alembic upgrade head" in content


def test_demo_walkthrough_documents_commands_accounts_and_roles():
    root = Path(__file__).resolve().parents[2]
    content = (root / "docs" / "demo-walkthrough.md").read_text(encoding="utf-8")

    for marker in [
        "seed-demo.ps1 -Force",
        "start-backend.ps1",
        "start-frontend.ps1",
        "admin",
        "project_manager",
        "analyst",
        "operator",
        "附件",
        "verify:api",
        "仅用于本地 demo/dev",
    ]:
        assert marker in content
