from app.models.business import ProjectMember


def login(client, username: str, password: str = "password123") -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def headers(client, username: str) -> dict[str, str]:
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
            "priority": "normal",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def add_member(client, admin_headers: dict[str, str], project_id: int, user_id: int) -> None:
    response = client.post(
        f"/api/projects/{project_id}/members",
        headers=admin_headers,
        json={"user_id": user_id, "role_in_project": "member"},
    )
    assert response.status_code == 201


def setup_users_and_projects(client, create_user):
    admin = create_user(username="admin", role="admin", must_change_password=False)
    director = create_user(username="director", role="director", must_change_password=False)
    manager_a = create_user(username="manager_a", role="project_manager", must_change_password=False)
    manager_b = create_user(username="manager_b", role="project_manager", must_change_password=False)
    analyst_a = create_user(username="analyst_a", role="operator", must_change_password=False)
    analyst_c = create_user(username="analyst_c", role="operator", must_change_password=False)
    analyst_b = create_user(username="analyst_b", role="operator", must_change_password=False)
    viewer = director
    admin_headers = headers(client, "admin")
    project_a = create_project(client, admin_headers, "T15-A", manager_a.id)
    project_b = create_project(client, admin_headers, "T15-B", manager_b.id)
    add_member(client, admin_headers, project_a["id"], analyst_a.id)
    add_member(client, admin_headers, project_a["id"], analyst_c.id)
    add_member(client, admin_headers, project_b["id"], analyst_b.id)
    return {
        "admin": admin,
        "viewer": viewer,
        "manager_a": manager_a,
        "manager_b": manager_b,
        "analyst_a": analyst_a,
        "analyst_c": analyst_c,
        "analyst_b": analyst_b,
        "project_a": project_a,
        "project_b": project_b,
        "admin_headers": admin_headers,
    }


def create_method(client, admin_headers: dict[str, str], code: str = "HPLC-T15") -> dict:
    response = client.post(
        "/api/test-methods",
        headers=admin_headers,
        json={
            "code": code,
            "name": "HPLC Assay",
            "category": "assay",
            "version": "1.0",
            "description": "T1.5 method",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def create_sample(client, actor_headers: dict[str, str], project_id: int, sample_no: str = "S-T15-001") -> dict:
    response = client.post(
        "/api/samples",
        headers=actor_headers,
        json={
            "project_id": project_id,
            "sample_no": sample_no,
            "name": "Assay sample",
            "type": "compound",
            "source": "synthesis",
            "batch_no": "B-001",
            "amount": "10.5000",
            "unit": "mg",
            "storage_condition": "2-8 C",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def create_task(
    client,
    actor_headers: dict[str, str],
    sample_id: int,
    method_id: int,
    assignee_id: int,
) -> dict:
    response = client.post(
        "/api/test-tasks",
        headers=actor_headers,
        json={
            "sample_id": sample_id,
            "method_id": method_id,
            "assigned_to": assignee_id,
            "priority": "high",
            "due_date": "2026-06-30",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_sample_and_method_crud_and_activation(client, create_user):
    ctx = setup_users_and_projects(client, create_user)
    manager_headers = headers(client, "manager_a")

    sample = create_sample(client, manager_headers, ctx["project_a"]["id"])
    assert sample["sample_no"] == "S-T15-001"
    assert sample["sample_code"] == "S-T15-001"
    assert sample["type"] == "compound"
    assert sample["amount"] == "10.5000"
    assert sample["status"] == "registered"
    sample_list = client.get("/api/samples", headers=manager_headers)
    sample_detail = client.get(f"/api/samples/{sample['id']}", headers=manager_headers)
    assert sample_list.status_code == 200
    assert [item["id"] for item in sample_list.json()["data"]["items"]] == [sample["id"]]
    assert sample_detail.status_code == 200

    update = client.patch(
        f"/api/samples/{sample['id']}",
        headers=manager_headers,
        json={"name": "Updated sample", "storage_condition": "room temperature"},
    )
    assert update.status_code == 200
    assert update.json()["data"]["name"] == "Updated sample"

    status_change = client.post(
        f"/api/samples/{sample['id']}/status",
        headers=manager_headers,
        json={"status": "cancelled"},
    )
    assert status_change.status_code == 200
    assert status_change.json()["data"]["status"] == "cancelled"

    method = create_method(client, ctx["admin_headers"])
    assert method["category"] == "assay"
    method_list = client.get("/api/test-methods", headers=manager_headers)
    method_detail = client.get(f"/api/test-methods/{method['id']}", headers=manager_headers)
    assert method_list.status_code == 200
    assert [item["id"] for item in method_list.json()["data"]["items"]] == [method["id"]]
    assert method_detail.status_code == 200
    patch = client.patch(
        f"/api/test-methods/{method['id']}",
        headers=ctx["admin_headers"],
        json={"version": "1.1", "description": "Updated"},
    )
    assert patch.status_code == 200
    assert patch.json()["data"]["version"] == "1.1"
    deactivate = client.post(
        f"/api/test-methods/{method['id']}/activation",
        headers=ctx["admin_headers"],
        json={"is_active": False},
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["data"]["is_active"] is False

    deleted = client.delete(f"/api/samples/{sample['id']}", headers=manager_headers)
    assert deleted.status_code == 200
    assert client.get(f"/api/samples/{sample['id']}", headers=manager_headers).status_code == 404


def test_happy_path_task_result_submit_and_approve(client, create_user):
    ctx = setup_users_and_projects(client, create_user)
    manager_headers = headers(client, "manager_a")
    analyst_headers = headers(client, "analyst_a")
    method = create_method(client, ctx["admin_headers"])
    sample = create_sample(client, manager_headers, ctx["project_a"]["id"])
    task = create_task(client, manager_headers, sample["id"], method["id"], ctx["analyst_a"].id)

    assert task["status"] == "pending"
    assert task["method_id"] == method["id"]
    assert task["sample"]["sample_no"] == sample["sample_no"]

    started = client.post(
        f"/api/test-tasks/{task['id']}/status",
        headers=analyst_headers,
        json={"status": "in_progress"},
    )
    assert started.status_code == 200

    result = client.post(
        "/api/test-results",
        headers=analyst_headers,
        json={
            "task_id": task["id"],
            "result_data": {"assay": 99.4, "unit": "%"},
            "conclusion": "Meets specification",
        },
    )
    assert result.status_code == 201
    result_data = result.json()["data"]
    assert result_data["status"] == "draft"
    assert result_data["result_data"]["assay"] == 99.4

    submitted = client.post(
        f"/api/test-results/{result_data['id']}/submit",
        headers=analyst_headers,
    )
    assert submitted.status_code == 200
    assert submitted.json()["data"]["status"] == "submitted"
    assert submitted.json()["data"]["submitted_by"] == ctx["analyst_a"].id

    queue = client.get(
        "/api/test-results",
        headers=manager_headers,
        params={"status": "submitted", "project_id": ctx["project_a"]["id"]},
    )
    assert queue.status_code == 200
    assert [item["id"] for item in queue.json()["data"]["items"]] == [result_data["id"]]

    approved = client.post(
        f"/api/test-results/{result_data['id']}/approve",
        headers=manager_headers,
        json={"comment": "Approved"},
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "approved"
    assert approved.json()["data"]["reviewed_by"] == ctx["manager_a"].id

    final_task = client.get(f"/api/test-tasks/{task['id']}", headers=analyst_headers)
    final_sample = client.get(f"/api/samples/{sample['id']}", headers=manager_headers)
    assert final_task.json()["data"]["status"] == "completed"
    assert final_sample.json()["data"]["status"] == "completed"


def test_rejected_result_returns_to_draft_on_edit_and_can_resubmit(client, create_user):
    ctx = setup_users_and_projects(client, create_user)
    manager_headers = headers(client, "manager_a")
    analyst_headers = headers(client, "analyst_a")
    method = create_method(client, ctx["admin_headers"], "LCMS-T15")
    sample = create_sample(client, manager_headers, ctx["project_a"]["id"], "S-T15-REJECT")
    task = create_task(client, manager_headers, sample["id"], method["id"], ctx["analyst_a"].id)
    client.post(f"/api/test-tasks/{task['id']}/status", headers=analyst_headers, json={"status": "in_progress"})
    created = client.post(
        "/api/test-results",
        headers=analyst_headers,
        json={"task_id": task["id"], "result_data": {"identity": "match"}, "conclusion": "Initial"},
    ).json()["data"]
    client.post(f"/api/test-results/{created['id']}/submit", headers=analyst_headers)

    missing_comment = client.post(
        f"/api/test-results/{created['id']}/reject",
        headers=manager_headers,
        json={"comment": " "},
    )
    assert missing_comment.status_code == 422

    rejected = client.post(
        f"/api/test-results/{created['id']}/reject",
        headers=manager_headers,
        json={"comment": "Repeat integration"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["data"]["status"] == "rejected"

    edited = client.patch(
        f"/api/test-results/{created['id']}",
        headers=analyst_headers,
        json={"result_data": {"identity": "match", "repeat": True}, "conclusion": "Repeated"},
    )
    assert edited.status_code == 200
    assert edited.json()["data"]["status"] == "draft"
    assert edited.json()["data"]["review_comment"] is None

    resubmitted = client.post(f"/api/test-results/{created['id']}/submit", headers=analyst_headers)
    assert resubmitted.status_code == 200
    assert resubmitted.json()["data"]["status"] == "submitted"


def test_four_role_permissions_and_cross_project_denials(client, create_user, db_session):
    ctx = setup_users_and_projects(client, create_user)
    manager_a_headers = headers(client, "manager_a")
    manager_b_headers = headers(client, "manager_b")
    analyst_a_headers = headers(client, "analyst_a")
    analyst_b_headers = headers(client, "analyst_b")
    viewer_headers = headers(client, "director")
    method = create_method(client, ctx["admin_headers"], "PERM-T15")
    sample_a = create_sample(client, manager_a_headers, ctx["project_a"]["id"], "S-PERM-A")
    sample_b = create_sample(client, manager_b_headers, ctx["project_b"]["id"], "S-PERM-B")
    task_a = create_task(client, manager_a_headers, sample_a["id"], method["id"], ctx["analyst_a"].id)

    assert client.get(f"/api/samples/{sample_b['id']}", headers=manager_a_headers).status_code == 404
    assert client.patch(
        f"/api/samples/{sample_b['id']}",
        headers=manager_a_headers,
        json={"name": "Forbidden"},
    ).status_code in {403, 404}
    assert client.get(f"/api/test-tasks/{task_a['id']}", headers=analyst_b_headers).status_code == 404
    assert client.post(
        f"/api/test-tasks/{task_a['id']}/status",
        headers=analyst_b_headers,
        json={"status": "in_progress"},
    ).status_code in {403, 404}

    assert client.get("/api/samples", headers=viewer_headers).status_code == 200
    assert client.post(
        "/api/samples",
        headers=viewer_headers,
        json={"project_id": ctx["project_a"]["id"], "sample_no": "DENIED", "name": "Denied"},
    ).status_code == 403
    assert client.post(
        "/api/test-methods",
        headers=manager_a_headers,
        json={"code": "DENIED", "name": "Denied"},
    ).status_code == 403

    unassigned = create_task(
        client,
        manager_a_headers,
        sample_a["id"],
        create_method(client, ctx["admin_headers"], "PERM-T15-2")["id"],
        ctx["analyst_a"].id,
    )
    reassign = client.patch(
        f"/api/test-tasks/{unassigned['id']}/assignee",
        headers=manager_a_headers,
        json={"assigned_to": ctx["analyst_c"].id},
    )
    assert reassign.status_code == 200
    assert reassign.json()["data"]["assigned_to"] == ctx["analyst_c"].id
    cross_project_reassign = client.patch(
        f"/api/test-tasks/{unassigned['id']}/assignee",
        headers=manager_a_headers,
        json={"assigned_to": ctx["analyst_b"].id},
    )
    assert cross_project_reassign.status_code == 400

    started = client.post(
        f"/api/test-tasks/{task_a['id']}/status",
        headers=analyst_a_headers,
        json={"status": "in_progress"},
    )
    assert started.status_code == 200
    result = client.post(
        "/api/test-results",
        headers=analyst_a_headers,
        json={"task_id": task_a["id"], "result_data": {"value": 1}, "conclusion": "Scoped"},
    ).json()["data"]
    assert client.get(f"/api/test-results/{result['id']}", headers=analyst_b_headers).status_code == 404
    assert client.post(
        f"/api/test-results/{result['id']}/submit",
        headers=analyst_a_headers,
    ).status_code == 200
    assert client.post(
        f"/api/test-results/{result['id']}/approve",
        headers=manager_b_headers,
        json={"comment": "Cross project"},
    ).status_code == 403

    membership = (
        db_session.query(ProjectMember)
        .filter(
            ProjectMember.project_id == ctx["project_a"]["id"],
            ProjectMember.user_id == ctx["analyst_a"].id,
        )
        .one()
    )
    assert membership.role_in_project == "member"


def test_closed_result_and_task_cannot_be_modified_or_rolled_back(client, create_user):
    ctx = setup_users_and_projects(client, create_user)
    manager_headers = headers(client, "manager_a")
    analyst_headers = headers(client, "analyst_a")
    director_headers = headers(client, "director")
    method = create_method(client, ctx["admin_headers"], "CLOSED-T15")
    sample = create_sample(client, manager_headers, ctx["project_a"]["id"], "S-CLOSED-T15")
    task = create_task(client, manager_headers, sample["id"], method["id"], ctx["analyst_a"].id)

    assert client.post(
        f"/api/test-tasks/{task['id']}/status",
        headers=director_headers,
        json={"status": "in_progress"},
    ).status_code == 403
    assert client.post(
        "/api/test-tasks",
        headers=director_headers,
        json={
            "sample_id": sample["id"],
            "method_id": method["id"],
            "assigned_to": ctx["analyst_a"].id,
        },
    ).status_code == 403

    assert client.post(
        f"/api/test-tasks/{task['id']}/status",
        headers=analyst_headers,
        json={"status": "in_progress"},
    ).status_code == 200
    result = client.post(
        "/api/test-results",
        headers=analyst_headers,
        json={"task_id": task["id"], "result_data": {"assay": 99.8}, "conclusion": "Pass"},
    ).json()["data"]
    assert client.post(
        f"/api/test-results/{result['id']}/submit",
        headers=analyst_headers,
    ).status_code == 200

    assert client.post(
        f"/api/test-results/{result['id']}/approve",
        headers=analyst_headers,
        json={"comment": "Self approve"},
    ).status_code == 403
    assert client.post(
        f"/api/test-results/{result['id']}/reject",
        headers=director_headers,
        json={"comment": "Read-only user"},
    ).status_code == 403

    approved = client.post(
        f"/api/test-results/{result['id']}/approve",
        headers=manager_headers,
        json={"comment": "Approved"},
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "approved"

    assert client.patch(
        f"/api/test-results/{result['id']}",
        headers=analyst_headers,
        json={"result_data": {"assay": 100.1}},
    ).status_code == 400
    assert client.post(
        f"/api/test-tasks/{task['id']}/status",
        headers=analyst_headers,
        json={"status": "in_progress"},
    ).status_code == 400
    assert client.post(
        f"/api/test-tasks/{task['id']}/status",
        headers=manager_headers,
        json={"status": "cancelled"},
    ).status_code == 400
