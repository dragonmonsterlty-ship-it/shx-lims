import json
from pathlib import Path
import subprocess
import sys

from app.core.config import Settings
from app.models.user import User
from scripts import seed_demo


def test_settings_support_app_env_and_local_vite_origins(monkeypatch):
    monkeypatch.setenv("APP_ENV", "integration")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    configured = Settings(_env_file=None)

    assert configured.app_env == "integration"
    assert configured.cors_origin_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_seed_demo_is_idempotent_and_uses_documented_accounts(db_session):
    seed_demo.seed_database(db_session)
    seed_demo.seed_database(db_session)

    users = {item.username: item.role for item in db_session.query(User).all()}
    assert users == {
        "admin": "admin",
        "pm": "pm",
        "project_manager": "project_manager",
        "researcher": "researcher",
        "operator": "operator",
        "analyst": "analyst",
    }


def test_export_openapi_script_writes_generated_schema(tmp_path):
    output_path = tmp_path / "openapi.json"
    backend_root = Path(__file__).resolve().parents[1]

    completed = subprocess.run(
        [sys.executable, "scripts/export_openapi.py", "--output", str(output_path)],
        cwd=backend_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    schema = json.loads(output_path.read_text(encoding="utf-8"))
    assert schema["info"]["title"] == "LIMS"
    assert "/api/health" in schema["paths"]
