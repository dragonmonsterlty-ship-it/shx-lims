from decimal import Decimal

from app.models.business import InventoryTxn, Project, ReagentLot


def login(client, username: str, password: str = "password123") -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def auth_headers(client, username: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {login(client, username)}"}


def project_payload(code: str, lead_user_id: int) -> dict:
    return {
        "project_code": code,
        "name": f"Project {code}",
        "project_type": "assay",
        "lead_user_id": lead_user_id,
        "status": "active",
        "priority": "normal",
        "description": "Experiment record project",
    }


def create_project(client, headers: dict[str, str], code: str, lead_user_id: int) -> dict:
    response = client.post("/api/projects", headers=headers, json=project_payload(code, lead_user_id))
    assert response.status_code == 201
    return response.json()["data"]


def add_member(client, headers: dict[str, str], project_id: int, user_id: int) -> None:
    response = client.post(
        f"/api/projects/{project_id}/members",
        headers=headers,
        json={"user_id": user_id, "role_in_project": "member"},
    )
    assert response.status_code == 201


def create_reagent_and_lot(client, headers: dict[str, str]) -> tuple[dict, dict]:
    reagent_response = client.post(
        "/api/reagents",
        headers=headers,
        json={
            "name": "Methanol",
            "cas_no": "67-56-1",
            "catalog_no": "M-001",
            "manufacturer": "Vendor",
            "grade": "HPLC",
            "default_unit": "mL",
            "min_stock": "10.0000",
        },
    )
    assert reagent_response.status_code == 201
    reagent = reagent_response.json()["data"]
    lot_response = client.post(
        "/api/reagent-lots",
        headers=headers,
        json={
            "reagent_id": reagent["id"],
            "lot_no": "LOT-001",
            "quantity": "0",
            "unit": "mL",
            "location": "Cabinet A",
            "status": "in_stock",
        },
    )
    assert lot_response.status_code == 201
    return reagent, lot_response.json()["data"]


def record_payload(project_id: int, reagent_id: int | None = None, lot_id: int | None = None, code: str = "EXP-001") -> dict:
    return {
        "project_id": project_id,
        "code": code,
        "title": "Route screening",
        "record_type": "synthesis",
        "status": "draft",
        "experiment_date": "2026-06-23",
        "objective": "Screen route A",
        "procedure": "Charge solvent and substrate",
        "result_summary": "LCMS showed desired mass",
        "conclusion": "Proceed to purification",
        "next_step": "Scale to 1 g",
        "risk_note": "Moisture sensitive",
        "reagent_usages": [
            {
                "reagent_id": reagent_id,
                "lot_id": lot_id,
                "quantity": "1.2500",
                "unit": "mL",
                "purpose": "solvent",
            }
        ],
        "attachments": [
            {
                "file_name": "lcms.pdf",
                "file_type": "lcms",
                "file_size": 1024,
                "storage_key": "experiments/EXP-001/lcms.pdf",
                "description": "LCMS report metadata",
            }
        ],
    }


def setup_users_and_project(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    manager = create_user(username="manager", role="project_manager", must_change_password=False)
    operator = create_user(username="operator", role="operator", must_change_password=False)
    other_operator = create_user(username="other_operator", role="operator", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project = create_project(client, admin_headers, "P001", manager.id)
    other_project = create_project(client, admin_headers, "P002", manager.id)
    add_member(client, admin_headers, project["id"], operator.id)
    return admin_headers, manager, operator, other_operator, project, other_project


def test_create_experiment_record_success_with_usage_and_attachment_metadata(client, create_user, db_session):
    admin_headers, _, _, _, project, _ = setup_users_and_project(client, create_user)
    reagent, lot = create_reagent_and_lot(client, admin_headers)

    response = client.post(
        "/api/experiment-records",
        headers=admin_headers,
        json=record_payload(project["id"], reagent["id"], lot["id"]),
    )

    assert response.status_code == 201
    body = response.json()["data"]
    assert body["code"] == "EXP-001"
    assert body["project"]["code"] == "P001"
    assert body["reagent_usage_count"] == 1
    assert body["attachment_count"] == 1
    assert body["reagent_usages"][0]["reagent_name_snapshot"] == "Methanol"
    assert body["reagent_usages"][0]["lot_code_snapshot"] == "LOT-001"
    db_session.expire_all()
    assert db_session.get(ReagentLot, lot["id"]).quantity == Decimal("0.0000")
    assert db_session.query(InventoryTxn).count() == 0


def test_list_pagination_and_filters_by_project_status_and_type(client, create_user):
    admin_headers, _, _, _, project, other_project = setup_users_and_project(client, create_user)
    client.post("/api/experiment-records", headers=admin_headers, json=record_payload(project["id"], code="EXP-001"))
    client.post(
        "/api/experiment-records",
        headers=admin_headers,
        json={**record_payload(other_project["id"], code="EXP-002"), "record_type": "analysis", "status": "in_progress"},
    )

    response = client.get(
        "/api/experiment-records",
        headers=admin_headers,
        params={"project_id": project["id"], "status": "draft", "type": "synthesis", "page": 1, "page_size": 1},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["items"][0]["code"] == "EXP-001"


def test_detail_returns_reagent_usages_and_attachments(client, create_user):
    admin_headers, _, _, _, project, _ = setup_users_and_project(client, create_user)
    create_response = client.post("/api/experiment-records", headers=admin_headers, json=record_payload(project["id"]))
    record_id = create_response.json()["data"]["id"]

    response = client.get(f"/api/experiment-records/{record_id}", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["objective"] == "Screen route A"
    assert len(data["reagent_usages"]) == 1
    assert len(data["attachments"]) == 1
    assert data["attachments"][0]["file_type"] == "lcms"


def test_submit_state_transition_success_for_creator(client, create_user):
    admin_headers, _, _, _, project, _ = setup_users_and_project(client, create_user)
    create_response = client.post("/api/experiment-records", headers=admin_headers, json=record_payload(project["id"]))
    record_id = create_response.json()["data"]["id"]

    response = client.post(f"/api/experiment-records/{record_id}/submit", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "submitted"


def test_regular_user_scope_is_limited_to_member_projects_or_created_records(client, create_user):
    admin_headers, _, operator, other_operator, project, other_project = setup_users_and_project(client, create_user)
    own_project_record = client.post(
        "/api/experiment-records",
        headers=admin_headers,
        json=record_payload(project["id"], code="EXP-001"),
    ).json()["data"]
    hidden_record = client.post(
        "/api/experiment-records",
        headers=admin_headers,
        json=record_payload(other_project["id"], code="EXP-002"),
    ).json()["data"]
    created_by_operator = client.post(
        "/api/experiment-records",
        headers=auth_headers(client, "operator"),
        json=record_payload(project["id"], code="EXP-003"),
    ).json()["data"]

    operator_list = client.get("/api/experiment-records", headers=auth_headers(client, "operator"))
    other_operator_detail = client.get(f"/api/experiment-records/{own_project_record['id']}", headers=auth_headers(client, "other_operator"))
    hidden_detail = client.get(f"/api/experiment-records/{hidden_record['id']}", headers=auth_headers(client, "operator"))

    assert operator_list.status_code == 200
    assert {item["id"] for item in operator_list.json()["data"]["items"]} == {own_project_record["id"], created_by_operator["id"]}
    assert hidden_detail.status_code == 404
    assert other_operator_detail.status_code == 404
    assert operator.id != other_operator.id


def test_admin_pm_project_manager_can_archive(client, create_user):
    admin_headers, _, _, _, project, _ = setup_users_and_project(client, create_user)
    create_response = client.post("/api/experiment-records", headers=admin_headers, json=record_payload(project["id"]))
    record_id = create_response.json()["data"]["id"]

    response = client.post(f"/api/experiment-records/{record_id}/archive", headers=auth_headers(client, "manager"))

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "archived"


def test_project_detail_experiment_record_count_uses_real_records(client, create_user, db_session):
    admin_headers, _, _, _, project, _ = setup_users_and_project(client, create_user)
    client.post("/api/experiment-records", headers=admin_headers, json=record_payload(project["id"], code="EXP-001"))
    client.post("/api/experiment-records", headers=admin_headers, json=record_payload(project["id"], code="EXP-002"))

    response = client.get(f"/api/projects/{project['id']}", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["data"]["experiment_record_count"] == 2
    db_session.expire_all()
    assert db_session.get(Project, project["id"]).project_code == "P001"
