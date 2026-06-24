from app.models.business import DailyLog


def login(client, username: str, password: str = "password123") -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def auth_headers(client, username: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {login(client, username)}"}


def create_project(client, admin_headers: dict[str, str], code: str, manager_id: int) -> dict:
    response = client.post(
        "/api/projects",
        headers=admin_headers,
        json={
            "project_code": code,
            "name": f"Project {code}",
            "project_type": "assay",
            "lead_user_id": manager_id,
            "status": "active",
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


def daily_log_payload(project_id: int, content: str = "Daily work") -> dict:
    return {"project_id": project_id, "log_date": "2026-06-22", "content": content}


def setup_users_and_projects(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    create_user(username="director", role="director", must_change_password=False)
    manager_1 = create_user(username="manager1", role="project_manager", must_change_password=False)
    manager_2 = create_user(username="manager2", role="project_manager", must_change_password=False)
    operator_1 = create_user(username="operator1", role="operator", must_change_password=False)
    operator_2 = create_user(username="operator2", role="operator", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project_1 = create_project(client, admin_headers, "P001", manager_1.id)
    project_2 = create_project(client, admin_headers, "P002", manager_2.id)
    add_member(client, admin_headers, project_1["id"], operator_1.id)
    add_member(client, admin_headers, project_2["id"], operator_2.id)
    return admin_headers, project_1, project_2


def test_operator_can_create_daily_log_in_own_project_but_not_other_project(client, create_user):
    _, project_1, project_2 = setup_users_and_projects(client, create_user)
    headers = auth_headers(client, "operator1")

    ok = client.post("/api/daily-logs", headers=headers, json=daily_log_payload(project_1["id"]))
    denied = client.post("/api/daily-logs", headers=headers, json=daily_log_payload(project_2["id"]))

    assert ok.status_code == 201
    assert ok.json()["data"]["status"] == "draft"
    assert denied.status_code == 403


def test_operator_only_views_own_daily_logs_and_manager_views_own_project(client, create_user):
    admin_headers, project_1, project_2 = setup_users_and_projects(client, create_user)
    op1_headers = auth_headers(client, "operator1")
    op2_headers = auth_headers(client, "operator2")
    manager_headers = auth_headers(client, "manager1")
    log_1 = client.post("/api/daily-logs", headers=op1_headers, json=daily_log_payload(project_1["id"], "op1")).json()["data"]
    log_2 = client.post("/api/daily-logs", headers=op2_headers, json=daily_log_payload(project_2["id"], "op2")).json()["data"]

    operator_list = client.get("/api/daily-logs", headers=op1_headers)
    manager_list = client.get("/api/daily-logs", headers=manager_headers)
    manager_denied_project = client.get(f"/api/daily-logs?project_id={project_2['id']}", headers=manager_headers)
    admin_list = client.get("/api/daily-logs", headers=admin_headers)

    assert [item["id"] for item in operator_list.json()["data"]] == [log_1["id"]]
    assert [item["id"] for item in manager_list.json()["data"]] == [log_1["id"]]
    assert manager_denied_project.status_code == 403
    assert {item["id"] for item in admin_list.json()["data"]} == {log_1["id"], log_2["id"]}


def test_director_can_read_all_daily_logs_but_cannot_write(client, create_user):
    _, project_1, _ = setup_users_and_projects(client, create_user)
    operator_headers = auth_headers(client, "operator1")
    daily_log = client.post("/api/daily-logs", headers=operator_headers, json=daily_log_payload(project_1["id"])).json()["data"]
    director_headers = auth_headers(client, "director")

    assert client.get("/api/daily-logs", headers=director_headers).status_code == 200
    assert client.post("/api/daily-logs", headers=director_headers, json=daily_log_payload(project_1["id"])).status_code == 403
    assert client.patch(f"/api/daily-logs/{daily_log['id']}", headers=director_headers, json={"content": "x"}).status_code == 403
    assert client.post(f"/api/daily-logs/{daily_log['id']}/submit", headers=director_headers).status_code == 403
    assert client.post(f"/api/daily-logs/{daily_log['id']}/review", headers=director_headers, json={}).status_code == 403
    assert client.post(f"/api/daily-logs/{daily_log['id']}/return", headers=director_headers, json={"review_comment": "fix"}).status_code == 403


def test_author_can_edit_draft_submit_and_cannot_edit_submitted_content(client, create_user):
    _, project_1, _ = setup_users_and_projects(client, create_user)
    headers = auth_headers(client, "operator1")
    daily_log = client.post("/api/daily-logs", headers=headers, json=daily_log_payload(project_1["id"])).json()["data"]

    edit = client.patch(f"/api/daily-logs/{daily_log['id']}", headers=headers, json={"content": "updated"})
    submit = client.post(f"/api/daily-logs/{daily_log['id']}/submit", headers=headers)
    edit_submitted = client.patch(f"/api/daily-logs/{daily_log['id']}", headers=headers, json={"content": "after submit"})

    assert edit.status_code == 200
    assert edit.json()["data"]["content"] == "updated"
    assert submit.status_code == 200
    assert submit.json()["data"]["status"] == "submitted"
    assert edit_submitted.status_code == 400


def test_project_manager_can_review_others_submitted_log_but_author_cannot_review_own(client, create_user):
    _, project_1, _ = setup_users_and_projects(client, create_user)
    op_headers = auth_headers(client, "operator1")
    manager_headers = auth_headers(client, "manager1")
    daily_log = client.post("/api/daily-logs", headers=op_headers, json=daily_log_payload(project_1["id"])).json()["data"]
    client.post(f"/api/daily-logs/{daily_log['id']}/submit", headers=op_headers)

    author_review = client.post(f"/api/daily-logs/{daily_log['id']}/review", headers=op_headers, json={})
    manager_review = client.post(f"/api/daily-logs/{daily_log['id']}/review", headers=manager_headers, json={"review_comment": "ok"})

    assert author_review.status_code == 403
    assert manager_review.status_code == 200
    assert manager_review.json()["data"]["status"] == "reviewed"


def test_return_requires_comment_and_delete_is_soft_delete(client, create_user, db_session):
    _, project_1, _ = setup_users_and_projects(client, create_user)
    op_headers = auth_headers(client, "operator1")
    manager_headers = auth_headers(client, "manager1")
    draft = client.post("/api/daily-logs", headers=op_headers, json=daily_log_payload(project_1["id"], "draft")).json()["data"]
    submitted = client.post("/api/daily-logs", headers=op_headers, json=daily_log_payload(project_1["id"], "submitted")).json()["data"]
    client.post(f"/api/daily-logs/{submitted['id']}/submit", headers=op_headers)

    missing_comment = client.post(f"/api/daily-logs/{submitted['id']}/return", headers=manager_headers, json={})
    returned = client.post(f"/api/daily-logs/{submitted['id']}/return", headers=manager_headers, json={"review_comment": "please revise"})
    delete_draft = client.delete(f"/api/daily-logs/{draft['id']}", headers=op_headers)

    assert missing_comment.status_code == 422
    assert returned.status_code == 200
    assert returned.json()["data"]["status"] == "returned"
    assert delete_draft.status_code == 200
    db_session.expire_all()
    assert db_session.get(DailyLog, draft["id"]).is_deleted is True


def test_reviewed_daily_log_cannot_be_deleted_by_non_admin(client, create_user):
    _, project_1, _ = setup_users_and_projects(client, create_user)
    op_headers = auth_headers(client, "operator1")
    manager_headers = auth_headers(client, "manager1")
    daily_log = client.post("/api/daily-logs", headers=op_headers, json=daily_log_payload(project_1["id"])).json()["data"]
    client.post(f"/api/daily-logs/{daily_log['id']}/submit", headers=op_headers)
    client.post(f"/api/daily-logs/{daily_log['id']}/review", headers=manager_headers, json={})

    response = client.delete(f"/api/daily-logs/{daily_log['id']}", headers=manager_headers)

    assert response.status_code == 403
