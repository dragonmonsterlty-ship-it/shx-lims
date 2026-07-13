import pytest
from sqlalchemy import inspect, select

from app.core.security import verify_password
from app.models.business import AuditLog
from app.models.user import User


def login(client, username: str, password: str = "password123") -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def auth_headers(client, username: str, password: str = "password123") -> dict[str, str]:
    return {"Authorization": f"Bearer {login(client, username, password)}"}


def create_project(client, headers: dict[str, str], code: str, lead_user_id: int) -> dict:
    response = client.post(
        "/api/projects",
        headers=headers,
        json={
            "project_code": code,
            "name": f"Project {code}",
            "project_type": "assay",
            "lead_user_id": lead_user_id,
            "status": "active",
            "priority": "normal",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def add_member(client, headers: dict[str, str], project_id: int, user_id: int) -> None:
    response = client.post(
        f"/api/projects/{project_id}/members",
        headers=headers,
        json={"user_id": user_id, "role_in_project": "member"},
    )
    assert response.status_code == 201


def create_method(client, headers: dict[str, str], code: str) -> dict:
    response = client.post(
        "/api/test-methods",
        headers=headers,
        json={"code": code, "name": f"Method {code}", "category": "assay", "version": "1.0"},
    )
    assert response.status_code == 201
    return response.json()["data"]


def create_sample(client, headers: dict[str, str], project_id: int, sample_no: str) -> dict:
    response = client.post(
        "/api/samples",
        headers=headers,
        json={"project_id": project_id, "sample_no": sample_no, "name": sample_no, "type": "compound"},
    )
    assert response.status_code == 201
    return response.json()["data"]


def create_task(client, headers: dict[str, str], sample_id: int, method_id: int, assignee_id: int) -> dict:
    response = client.post(
        "/api/test-tasks",
        headers=headers,
        json={"sample_id": sample_id, "method_id": method_id, "assigned_to": assignee_id},
    )
    assert response.status_code == 201
    return response.json()["data"]


def setup_audit_context(client, create_user):
    admin = create_user(username="audit_admin", role="admin", must_change_password=False)
    manager_a = create_user(username="audit_manager_a", role="project_manager", must_change_password=False)
    manager_b = create_user(username="audit_manager_b", role="project_manager", must_change_password=False)
    operator_a = create_user(username="audit_operator_a", role="operator", must_change_password=False)
    operator_b = create_user(username="audit_operator_b", role="operator", must_change_password=False)
    viewer = create_user(username="audit_viewer", role="viewer", must_change_password=False)
    target = create_user(username="audit_target", role="operator", must_change_password=False)

    admin_headers = auth_headers(client, "audit_admin")
    project_a = create_project(client, admin_headers, "AUD-A", manager_a.id)
    project_b = create_project(client, admin_headers, "AUD-B", manager_b.id)
    add_member(client, admin_headers, project_a["id"], operator_a.id)
    add_member(client, admin_headers, project_a["id"], viewer.id)
    add_member(client, admin_headers, project_b["id"], operator_b.id)

    method = create_method(client, admin_headers, "AUD-METHOD")
    return {
        "admin": admin,
        "manager_a": manager_a,
        "manager_b": manager_b,
        "operator_a": operator_a,
        "operator_b": operator_b,
        "viewer": viewer,
        "target": target,
        "admin_headers": admin_headers,
        "project_a": project_a,
        "project_b": project_b,
        "method": method,
    }


def test_audit_log_model_has_t1_6b_columns(db_session):
    columns = {column["name"] for column in inspect(db_session.bind).get_columns("audit_log")}
    assert {
        "id",
        "actor_user_id",
        "actor_role",
        "action",
        "entity_type",
        "entity_id",
        "project_id",
        "target_user_id",
        "before_data",
        "after_data",
        "metadata",
        "created_at",
    } <= columns


def test_sample_task_result_and_attachment_audit_timeline_and_project_scope(client, create_user):
    ctx = setup_audit_context(client, create_user)
    manager_headers = auth_headers(client, "audit_manager_a")
    operator_headers = auth_headers(client, "audit_operator_a")
    viewer_headers = auth_headers(client, "audit_viewer")
    sample = create_sample(client, manager_headers, ctx["project_a"]["id"], "AUD-SAMPLE-A")
    client.patch(f"/api/samples/{sample['id']}", headers=manager_headers, json={"name": "AUD-SAMPLE-A2"})
    task = create_task(client, manager_headers, sample["id"], ctx["method"]["id"], ctx["operator_a"].id)
    client.post(f"/api/test-tasks/{task['id']}/status", headers=operator_headers, json={"status": "in_progress"})
    result = client.post(
        "/api/test-results",
        headers=operator_headers,
        json={"task_id": task["id"], "result_data": {"value": 1}, "conclusion": "ok"},
    ).json()["data"]
    client.patch(f"/api/test-results/{result['id']}", headers=operator_headers, json={"conclusion": "ok2"})
    upload = client.post(
        "/api/attachments",
        headers=manager_headers,
        data={"entity_type": "sample", "entity_id": str(sample["id"])},
        files={"file": ("audit.pdf", b"%PDF-1.4\naudit attachment", "application/pdf")},
    )
    assert upload.status_code == 201
    attachment = upload.json()["data"]
    download = client.get(f"/api/attachments/{attachment['id']}/download", headers=manager_headers)
    delete = client.delete(f"/api/attachments/{attachment['id']}", headers=manager_headers)
    assert download.status_code == 200
    assert delete.status_code == 200
    client.post(f"/api/test-results/{result['id']}/submit", headers=operator_headers)
    client.post(f"/api/test-results/{result['id']}/approve", headers=manager_headers, json={"comment": "approved"})

    sample_timeline = client.get(f"/api/samples/{sample['id']}/timeline", headers=viewer_headers)
    task_timeline = client.get(f"/api/test-tasks/{task['id']}/timeline", headers=operator_headers)
    result_timeline = client.get(f"/api/test-results/{result['id']}/timeline", headers=operator_headers)
    attachment_timeline = client.get(f"/api/attachments/{attachment['id']}/timeline", headers=manager_headers)
    assert sample_timeline.status_code == 200
    assert [item["action"] for item in sample_timeline.json()["data"]] == ["create", "update"]
    assert {item["metadata"]["task_event"] for item in task_timeline.json()["data"] if item["metadata"]} >= {"start", "complete"}
    assert {item["action"] for item in result_timeline.json()["data"]} >= {"create", "update", "submit", "approve"}
    assert [item["action"] for item in attachment_timeline.json()["data"]] == ["upload", "download", "delete"]

    project_b_sample = create_sample(
        client,
        auth_headers(client, "audit_manager_b"),
        ctx["project_b"]["id"],
        "AUD-SAMPLE-B",
    )
    manager_list = client.get("/api/audit-logs", headers=manager_headers, params={"project_id": ctx["project_a"]["id"]})
    manager_cross = client.get(f"/api/samples/{project_b_sample['id']}/timeline", headers=manager_headers)
    member_list = client.get("/api/audit-logs", headers=operator_headers)
    viewer_write = client.patch(f"/api/samples/{sample['id']}", headers=viewer_headers, json={"name": "nope"})
    viewer_cross = client.get(f"/api/samples/{project_b_sample['id']}/timeline", headers=viewer_headers)
    assert manager_list.status_code == 200
    assert {item["project_id"] for item in manager_list.json()["data"]["items"]} == {ctx["project_a"]["id"]}
    assert manager_cross.status_code == 404
    assert member_list.status_code == 403
    assert viewer_write.status_code == 403
    assert viewer_cross.status_code == 404


def test_experiment_and_daily_report_audit_cover_create_update_submit_archive(client, create_user):
    ctx = setup_audit_context(client, create_user)
    admin_headers = ctx["admin_headers"]
    record = client.post(
        "/api/experiment-records",
        headers=admin_headers,
        json={
            "project_id": ctx["project_a"]["id"],
            "code": "AUD-EXP",
            "title": "Audit experiment",
            "record_type": "analysis",
            "status": "draft",
        },
    ).json()["data"]
    client.patch(f"/api/experiment-records/{record['id']}", headers=admin_headers, json={"title": "Audit experiment 2"})
    client.post(f"/api/experiment-records/{record['id']}/submit", headers=admin_headers)
    client.post(f"/api/experiment-records/{record['id']}/archive", headers=admin_headers)

    report = client.post(
        "/api/daily-reports",
        headers=auth_headers(client, "audit_operator_a"),
        json={
            "report_date": "2026-06-26",
            "summary": "Audit report",
            "items": [{"project_id": ctx["project_a"]["id"], "work_type": "analysis", "content": "audit"}],
        },
    ).json()["data"]
    client.patch(f"/api/daily-reports/{report['id']}", headers=auth_headers(client, "audit_operator_a"), json={"summary": "Audit report 2"})
    client.post(f"/api/daily-reports/{report['id']}/submit", headers=auth_headers(client, "audit_operator_a"))
    client.post(f"/api/daily-reports/{report['id']}/archive", headers=admin_headers)

    experiment_timeline = client.get(f"/api/experiment-records/{record['id']}/timeline", headers=admin_headers)
    daily_timeline = client.get(f"/api/daily-reports/{report['id']}/timeline", headers=admin_headers)
    assert [item["action"] for item in experiment_timeline.json()["data"]] == ["create", "update", "submit", "archive"]
    assert [item["action"] for item in daily_timeline.json()["data"]] == ["create", "update", "submit", "archive"]


def test_admin_user_management_writes_audit_and_enforces_admin_only(client, create_user, db_session):
    ctx = setup_audit_context(client, create_user)
    admin_headers = ctx["admin_headers"]
    manager_headers = auth_headers(client, "audit_manager_a")
    target_id = ctx["target"].id

    assert client.get("/api/admin/users", headers=manager_headers).status_code == 403
    assert client.patch(f"/api/admin/users/{target_id}/status", headers=manager_headers, json={"is_active": False}).status_code == 403

    disabled = client.patch(f"/api/admin/users/{target_id}/status", headers=admin_headers, json={"is_active": False})
    enabled = client.patch(f"/api/admin/users/{target_id}/status", headers=admin_headers, json={"is_active": True})
    role = client.patch(f"/api/admin/users/{target_id}/role", headers=admin_headers, json={"role": "viewer"})
    reset = client.post(f"/api/admin/users/{target_id}/reset-password", headers=admin_headers, json={"new_password": "newpass123"})
    assert disabled.status_code == 200
    assert enabled.status_code == 200
    assert role.status_code == 200
    assert role.json()["data"]["role"] == "viewer"
    assert reset.status_code == 200
    assert reset.json()["data"]["must_change_password"] is True
    assert client.post("/api/auth/login", json={"username": "audit_target", "password": "newpass123"}).status_code == 200
    assert client.patch(f"/api/admin/users/{ctx['admin'].id}/status", headers=admin_headers, json={"is_active": False}).status_code == 400
    assert client.patch(f"/api/admin/users/{ctx['admin'].id}/role", headers=admin_headers, json={"role": "viewer"}).status_code == 400

    logs = db_session.query(AuditLog).filter(AuditLog.entity_type == "user", AuditLog.entity_id == target_id).all()
    assert [log.action for log in logs] == ["disable_user", "enable_user", "change_role", "reset_password"]


def test_admin_can_create_user_with_hashed_password_audit_and_login(client, create_user, db_session):
    create_user(username="creator_admin", role="admin", must_change_password=False)
    headers = auth_headers(client, "creator_admin")

    response = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "username": "new_operator",
            "display_name": "New Operator",
            "email": "new.operator@example.com",
            "password": "initial-pass-123",
            "role": "operator",
            "is_active": True,
        },
    )

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["username"] == "new_operator"
    assert body["full_name"] == "New Operator"
    assert body["email"] == "new.operator@example.com"
    assert body["role"] == "operator"
    assert body["is_active"] is True
    assert body["must_change_password"] is True
    assert "password" not in body
    assert "password_hash" not in body

    created = db_session.scalar(select(User).where(User.username == "new_operator"))
    assert created is not None
    assert created.password_hash != "initial-pass-123"
    assert verify_password("initial-pass-123", created.password_hash) is True

    log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "create",
            AuditLog.entity_type == "user",
            AuditLog.entity_id == created.id,
        )
    )
    assert log is not None
    assert log.actor_user_id is not None
    assert log.target_user_id == created.id
    assert log.after_data == {
        "username": "new_operator",
        "role": "operator",
        "is_active": True,
    }
    assert log.created_at is not None

    login_response = client.post(
        "/api/auth/login",
        json={"username": "new_operator", "password": "initial-pass-123"},
    )
    assert login_response.status_code == 200


@pytest.mark.parametrize(
    "role",
    ["director", "project_manager", "researcher", "operator", "viewer", "analyst", "auditor"],
)
def test_non_admin_cannot_create_user(client, create_user, role):
    username = f"create_denied_{role}"
    create_user(username=username, role=role, must_change_password=False)

    response = client.post(
        "/api/admin/users",
        headers=auth_headers(client, username),
        json={
            "username": f"forbidden_{role}",
            "display_name": "Forbidden User",
            "password": "initial-pass-123",
            "role": "viewer",
            "is_active": True,
        },
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Administrator permission required"


def test_admin_create_user_rejects_duplicate_username(client, create_user):
    create_user(username="duplicate_admin", role="admin", must_change_password=False)
    create_user(username="existing_user", role="viewer", must_change_password=False)

    response = client.post(
        "/api/admin/users",
        headers=auth_headers(client, "duplicate_admin"),
        json={
            "username": "existing_user",
            "display_name": "Duplicate User",
            "password": "initial-pass-123",
            "role": "viewer",
            "is_active": True,
        },
    )

    assert response.status_code == 409
    assert response.json()["message"] == "Username already exists"


def test_cancel_and_reject_audit_events(client, create_user):
    ctx = setup_audit_context(client, create_user)
    manager_headers = auth_headers(client, "audit_manager_a")
    operator_headers = auth_headers(client, "audit_operator_a")
    sample = create_sample(client, manager_headers, ctx["project_a"]["id"], "AUD-CANCEL")
    cancel_task = create_task(client, manager_headers, sample["id"], ctx["method"]["id"], ctx["operator_a"].id)
    cancel = client.post(f"/api/test-tasks/{cancel_task['id']}/status", headers=manager_headers, json={"status": "cancelled"})
    assert cancel.status_code == 200
    cancel_timeline = client.get(f"/api/test-tasks/{cancel_task['id']}/timeline", headers=manager_headers).json()["data"]
    assert cancel_timeline[-1]["metadata"]["task_event"] == "cancel"

    result_sample = create_sample(client, manager_headers, ctx["project_a"]["id"], "AUD-REJECT")
    result_task = create_task(client, manager_headers, result_sample["id"], ctx["method"]["id"], ctx["operator_a"].id)
    client.post(f"/api/test-tasks/{result_task['id']}/status", headers=operator_headers, json={"status": "in_progress"})
    result = client.post(
        "/api/test-results",
        headers=operator_headers,
        json={"task_id": result_task["id"], "result_data": {"value": 2}, "conclusion": "needs review"},
    ).json()["data"]
    client.post(f"/api/test-results/{result['id']}/submit", headers=operator_headers)
    rejected = client.post(f"/api/test-results/{result['id']}/reject", headers=manager_headers, json={"comment": "repeat"})
    assert rejected.status_code == 200
    result_timeline = client.get(f"/api/test-results/{result['id']}/timeline", headers=operator_headers).json()["data"]
    assert result_timeline[-1]["action"] == "reject"
