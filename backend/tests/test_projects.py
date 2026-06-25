from app.models.business import Project, ProjectMember


def login(client, username: str, password: str = "password123") -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def auth_headers(client, username: str) -> dict[str, str]:
    token = login(client, username)
    return {"Authorization": f"Bearer {token}"}


def project_payload(code: str, lead_user_id: int, name: str | None = None) -> dict:
    return {
        "project_code": code,
        "name": name or f"Project {code}",
        "project_type": "assay",
        "lead_user_id": lead_user_id,
        "status": "active",
        "priority": "normal",
        "description": "MVP project",
    }


def create_project_via_api(client, admin_headers: dict[str, str], code: str, lead_user_id: int) -> dict:
    response = client.post("/api/projects", headers=admin_headers, json=project_payload(code, lead_user_id))
    assert response.status_code == 201
    return response.json()["data"]


def test_admin_can_create_project_and_manager_member_is_created(client, create_user, db_session):
    create_user(username="admin", role="admin", must_change_password=False)
    create_user(username="director_user", role="director", must_change_password=False)
    manager = create_user(username="manager", role="project_manager", must_change_password=False)

    response = client.post("/api/projects", headers=auth_headers(client, "admin"), json=project_payload("P001", manager.id))

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["project_code"] == "P001"
    assert body["lead_user_id"] == manager.id

    db_session.expire_all()
    project = db_session.get(Project, body["id"])
    assert project is not None
    member = (
        db_session.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == manager.id)
        .one()
    )
    assert member.role_in_project == "manager"


def test_duplicate_project_code_fails(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    manager = create_user(username="manager", role="project_manager", must_change_password=False)
    headers = auth_headers(client, "admin")
    create_project_via_api(client, headers, "P001", manager.id)

    response = client.post("/api/projects", headers=headers, json=project_payload("P001", manager.id, name="Duplicate"))

    assert response.status_code == 409


def test_admin_and_director_can_view_all_projects_but_director_cannot_write(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    create_user(username="director", role="director", must_change_password=False)
    manager_1 = create_user(username="manager1", role="project_manager", must_change_password=False)
    manager_2 = create_user(username="manager2", role="project_manager", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project_1 = create_project_via_api(client, admin_headers, "P001", manager_1.id)
    project_2 = create_project_via_api(client, admin_headers, "P002", manager_2.id)

    admin_list = client.get("/api/projects", headers=admin_headers)
    director_headers = auth_headers(client, "director")
    director_list = client.get("/api/projects", headers=director_headers)

    assert admin_list.status_code == 200
    assert {item["id"] for item in admin_list.json()["data"]["items"]} == {project_1["id"], project_2["id"]}
    assert director_list.status_code == 200
    assert {item["id"] for item in director_list.json()["data"]["items"]} == {project_1["id"], project_2["id"]}

    assert client.post("/api/projects", headers=director_headers, json=project_payload("P003", manager_1.id)).status_code == 403
    assert client.patch("/api/projects/1", headers=director_headers, json={"name": "Nope"}).status_code == 403
    assert client.delete("/api/projects/1", headers=director_headers).status_code == 403


def test_admin_can_patch_any_project(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    manager_1 = create_user(username="manager1", role="project_manager", must_change_password=False)
    manager_2 = create_user(username="manager2", role="project_manager", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project = create_project_via_api(client, admin_headers, "P001", manager_1.id)

    response = client.patch(
        f"/api/projects/{project['id']}",
        headers=admin_headers,
        json={"project_code": "P001A", "name": "Admin Updated", "lead_user_id": manager_2.id, "status": "paused"},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["project_code"] == "P001A"
    assert body["name"] == "Admin Updated"
    assert body["lead_user_id"] == manager_2.id
    assert body["status"] == "paused"


def test_admin_patch_duplicate_project_code_fails(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    manager_1 = create_user(username="manager1", role="project_manager", must_change_password=False)
    manager_2 = create_user(username="manager2", role="project_manager", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project_1 = create_project_via_api(client, admin_headers, "P001", manager_1.id)
    create_project_via_api(client, admin_headers, "P002", manager_2.id)

    response = client.patch(f"/api/projects/{project_1['id']}", headers=admin_headers, json={"project_code": "P002"})

    assert response.status_code == 409


def test_project_manager_can_patch_own_project_business_fields(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    manager = create_user(username="manager", role="project_manager", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project = create_project_via_api(client, admin_headers, "P001", manager.id)

    response = client.patch(
        f"/api/projects/{project['id']}",
        headers=auth_headers(client, "manager"),
        json={"name": "Manager Updated", "description": "Updated by manager", "status": "paused"},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["name"] == "Manager Updated"
    assert body["description"] == "Updated by manager"
    assert body["status"] == "paused"
    assert body["project_code"] == "P001"
    assert body["lead_user_id"] == manager.id


def test_project_manager_cannot_patch_non_owned_project(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    manager_1 = create_user(username="manager1", role="project_manager", must_change_password=False)
    manager_2 = create_user(username="manager2", role="project_manager", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    create_project_via_api(client, admin_headers, "P001", manager_1.id)
    project_2 = create_project_via_api(client, admin_headers, "P002", manager_2.id)

    response = client.patch(
        f"/api/projects/{project_2['id']}",
        headers=auth_headers(client, "manager1"),
        json={"name": "Not allowed"},
    )

    assert response.status_code == 403


def test_project_manager_cannot_patch_protected_project_fields(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    manager = create_user(username="manager", role="project_manager", must_change_password=False)
    other_manager = create_user(username="other_manager", role="project_manager", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project = create_project_via_api(client, admin_headers, "P001", manager.id)
    manager_headers = auth_headers(client, "manager")

    code_response = client.patch(f"/api/projects/{project['id']}", headers=manager_headers, json={"project_code": "P001X"})
    lead_response = client.patch(f"/api/projects/{project['id']}", headers=manager_headers, json={"lead_user_id": other_manager.id})

    assert code_response.status_code == 403
    assert lead_response.status_code == 403


def test_project_manager_can_archive_own_project(client, create_user, db_session):
    create_user(username="admin", role="admin", must_change_password=False)
    manager = create_user(username="manager", role="project_manager", must_change_password=False)
    project = create_project_via_api(client, auth_headers(client, "admin"), "P001", manager.id)

    response = client.delete(f"/api/projects/{project['id']}", headers=auth_headers(client, "manager"))

    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.get(Project, project["id"]).is_deleted is True


def test_director_and_operator_cannot_patch_project(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    create_user(username="director", role="director", must_change_password=False)
    manager = create_user(username="manager", role="project_manager", must_change_password=False)
    operator = create_user(username="operator", role="operator", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project = create_project_via_api(client, admin_headers, "P001", manager.id)
    assert (
        client.post(
            f"/api/projects/{project['id']}/members",
            headers=admin_headers,
            json={"user_id": operator.id, "role_in_project": "member"},
        ).status_code
        == 201
    )

    director_response = client.patch(
        f"/api/projects/{project['id']}",
        headers=auth_headers(client, "director"),
        json={"name": "Director denied"},
    )
    operator_response = client.patch(
        f"/api/projects/{project['id']}",
        headers=auth_headers(client, "operator"),
        json={"name": "Operator denied"},
    )

    assert director_response.status_code == 403
    assert operator_response.status_code == 403


def test_project_manager_and_operator_only_view_own_projects(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    manager_1 = create_user(username="manager1", role="project_manager", must_change_password=False)
    manager_2 = create_user(username="manager2", role="project_manager", must_change_password=False)
    operator = create_user(username="operator", role="operator", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project_1 = create_project_via_api(client, admin_headers, "P001", manager_1.id)
    project_2 = create_project_via_api(client, admin_headers, "P002", manager_2.id)
    add_operator = client.post(
        f"/api/projects/{project_1['id']}/members",
        headers=admin_headers,
        json={"user_id": operator.id, "role_in_project": "member"},
    )
    assert add_operator.status_code == 201

    manager_list = client.get("/api/projects", headers=auth_headers(client, "manager1"))
    operator_list = client.get("/api/projects", headers=auth_headers(client, "operator"))
    manager_forbidden_detail = client.get(f"/api/projects/{project_2['id']}", headers=auth_headers(client, "manager1"))

    assert manager_list.status_code == 200
    assert [item["id"] for item in manager_list.json()["data"]["items"]] == [project_1["id"]]
    assert operator_list.status_code == 200
    assert [item["id"] for item in operator_list.json()["data"]["items"]] == [project_1["id"]]
    assert manager_forbidden_detail.status_code == 404


def test_project_manager_can_manage_own_project_members_only(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    manager_1 = create_user(username="manager1", role="project_manager", must_change_password=False)
    manager_2 = create_user(username="manager2", role="project_manager", must_change_password=False)
    operator = create_user(username="operator", role="operator", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project_1 = create_project_via_api(client, admin_headers, "P001", manager_1.id)
    project_2 = create_project_via_api(client, admin_headers, "P002", manager_2.id)
    manager_headers = auth_headers(client, "manager1")

    add_response = client.post(
        f"/api/projects/{project_1['id']}/members",
        headers=manager_headers,
        json={"user_id": operator.id, "role_in_project": "member"},
    )
    add_manager_response = client.post(
        f"/api/projects/{project_1['id']}/members",
        headers=manager_headers,
        json={"user_id": manager_2.id, "role_in_project": "manager"},
    )
    non_own_response = client.post(
        f"/api/projects/{project_2['id']}/members",
        headers=manager_headers,
        json={"user_id": operator.id, "role_in_project": "member"},
    )
    remove_manager_response = client.delete(f"/api/projects/{project_1['id']}/members/{manager_1.id}", headers=manager_headers)
    delete_response = client.delete(f"/api/projects/{project_1['id']}/members/{operator.id}", headers=manager_headers)

    assert add_response.status_code == 201
    assert add_response.json()["data"]["role_in_project"] == "member"
    assert add_manager_response.status_code == 403
    assert non_own_response.status_code == 403
    assert remove_manager_response.status_code == 403
    assert delete_response.status_code == 200


def test_operator_cannot_add_or_delete_members(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    manager = create_user(username="manager", role="project_manager", must_change_password=False)
    operator = create_user(username="operator", role="operator", must_change_password=False)
    other_operator = create_user(username="other_operator", role="operator", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project = create_project_via_api(client, admin_headers, "P001", manager.id)
    assert (
        client.post(
            f"/api/projects/{project['id']}/members",
            headers=admin_headers,
            json={"user_id": operator.id, "role_in_project": "member"},
        ).status_code
        == 201
    )
    operator_headers = auth_headers(client, "operator")

    add_response = client.post(
        f"/api/projects/{project['id']}/members",
        headers=operator_headers,
        json={"user_id": other_operator.id, "role_in_project": "member"},
    )
    delete_response = client.delete(f"/api/projects/{project['id']}/members/{manager.id}", headers=operator_headers)

    assert add_response.status_code == 403
    assert delete_response.status_code == 403


def test_delete_project_is_soft_delete(client, create_user, db_session):
    create_user(username="admin", role="admin", must_change_password=False)
    manager = create_user(username="manager", role="project_manager", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project = create_project_via_api(client, admin_headers, "P001", manager.id)

    response = client.delete(f"/api/projects/{project['id']}", headers=admin_headers)

    assert response.status_code == 200
    db_session.expire_all()
    deleted_project = db_session.get(Project, project["id"])
    assert deleted_project.is_deleted is True

    list_response = client.get("/api/projects", headers=admin_headers)
    assert list_response.status_code == 200
    assert list_response.json()["data"]["items"] == []


def test_project_owner_must_have_owner_level_role(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    operator = create_user(username="operator", role="operator", must_change_password=False)

    response = client.post("/api/projects", headers=auth_headers(client, "admin"), json=project_payload("P001", operator.id))

    assert response.status_code == 400
    assert response.json()["message"] == "Project owner must have an owner-level role"


def test_project_list_supports_filters_pagination_and_summary_fields(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    create_user(username="director", role="director", must_change_password=False)
    manager_1 = create_user(username="manager1", role="project_manager", must_change_password=False)
    manager_2 = create_user(username="manager2", role="project_manager", must_change_password=False)
    operator = create_user(username="operator", role="operator", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project_1 = create_project_via_api(client, admin_headers, "CHEM-001", manager_1.id)
    create_project_via_api(client, admin_headers, "BIO-002", manager_2.id)
    patch_response = client.patch(
        f"/api/projects/{project_1['id']}",
        headers=admin_headers,
        json={
            "priority": "high",
            "current_stage": "method validation",
            "progress": 35,
            "risk_summary": "Instrument queue risk",
            "next_plan": "Finish validation batch and review chromatograms",
        },
    )
    assert patch_response.status_code == 200
    assert client.post(
        f"/api/projects/{project_1['id']}/members",
        headers=admin_headers,
        json={"user_id": operator.id, "role_in_project": "member"},
    ).status_code == 201

    response = client.get(
        "/api/projects",
        headers=auth_headers(client, "director"),
        params={"keyword": "manager1", "status": "active", "type": "assay", "manager_id": manager_1.id, "priority": "high", "page": 1, "page_size": 1},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 1
    item = data["items"][0]
    assert item["id"] == project_1["id"]
    assert item["code"] == "CHEM-001"
    assert item["owner"]["role"] == "project_manager"
    assert item["member_count"] == 1
    assert item["current_stage"] == "method validation"
    assert item["progress"] == 35
    assert item["risk_summary"] == "Instrument queue risk"
    assert item["next_plan_summary"].startswith("Finish validation")


def test_project_detail_separates_owner_from_members_and_summary_endpoint(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    create_user(username="director", role="director", must_change_password=False)
    manager = create_user(username="manager", role="project_manager", must_change_password=False)
    analyst = create_user(username="analyst", role="analyst", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project = create_project_via_api(client, admin_headers, "P001", manager.id)
    assert client.post(
        f"/api/projects/{project['id']}/members",
        headers=admin_headers,
        json={"user_id": analyst.id, "role_in_project": "member"},
    ).status_code == 201

    detail = client.get(f"/api/projects/{project['id']}", headers=auth_headers(client, "director"))
    summary = client.get(f"/api/projects/{project['id']}/summary", headers=auth_headers(client, "director"))

    assert detail.status_code == 200
    body = detail.json()["data"]
    assert body["owner"]["id"] == manager.id
    assert body["manager"]["id"] == manager.id
    assert body["principal"]["id"] == manager.id
    assert [member["id"] for member in body["members"]] == [analyst.id]
    assert body["experiment_record_count"] == 0
    assert body["attachment_count"] == 0
    assert body["inventory_item_count"] == 0
    assert summary.status_code == 200
    assert summary.json()["data"]["member_count"] == 1


def test_project_owner_candidates_exclude_regular_members(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    create_user(username="director_user", role="director", must_change_password=False)
    create_user(username="pm_user", role="project_manager", must_change_password=False)
    create_user(username="project_manager_user", role="project_manager", must_change_password=False)
    create_user(username="pi_user", role="principal_investigator", must_change_password=False)
    create_user(username="researcher_user", role="researcher", must_change_password=False)
    create_user(username="analyst_user", role="analyst", must_change_password=False)
    create_user(username="operator_user", role="operator", must_change_password=False)
    create_user(username="qa_user", role="qa", must_change_password=False)

    response = client.get("/api/users/project-owner-candidates", headers=auth_headers(client, "admin"))
    role_group_response = client.get("/api/users", headers=auth_headers(client, "admin"), params={"role_group": "project_owner", "keyword": "user"})

    assert response.status_code == 200
    assert {user["role"] for user in response.json()["data"]} == {"admin", "project_manager"}
    assert role_group_response.status_code == 200
    assert {user["role"] for user in role_group_response.json()["data"]} == {"project_manager"}
