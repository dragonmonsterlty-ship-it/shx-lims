from decimal import Decimal

from app.models.business import ExperimentReagentUsage, InventoryTxn, Project, ReagentLot


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
        "participant_ids": [],
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


def test_participants_and_extended_fields_round_trip(client, create_user):
    admin_headers, _, operator, _, project, _ = setup_users_and_project(client, create_user)
    payload = record_payload(project["id"])
    payload["participant_ids"] = [operator.id]

    created = client.post("/api/experiment-records", headers=admin_headers, json=payload)
    assert created.status_code == 201
    assert created.json()["data"]["participant_ids"] == [operator.id]
    assert created.json()["data"]["conclusion"] == "Proceed to purification"
    assert created.json()["data"]["next_step"] == "Scale to 1 g"
    assert created.json()["data"]["risk_note"] == "Moisture sensitive"

    updated = client.patch(
        f"/api/experiment-records/{created.json()['data']['id']}",
        headers=admin_headers,
        json={
            "participant_ids": [],
            "conclusion": "Updated conclusion",
            "next_step": "Updated next step",
            "risk_note": "Updated risk",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["participant_ids"] == []
    assert updated.json()["data"]["conclusion"] == "Updated conclusion"
    assert updated.json()["data"]["next_step"] == "Updated next step"
    assert updated.json()["data"]["risk_note"] == "Updated risk"


def test_confirm_dispense_deducts_once_records_shortage_and_links_transaction(client, create_user, db_session):
    admin_headers, manager, _, _, project, _ = setup_users_and_project(client, create_user)
    reagent, lot = create_reagent_and_lot(client, admin_headers)
    client.post(
        "/api/inventory-transactions",
        headers=admin_headers,
        json={"reagent_lot_id": lot["id"], "txn_type": "in", "quantity": "1.0000"},
    )
    payload = record_payload(project["id"], reagent["id"], lot["id"])
    payload["reagent_usages"][0]["quantity"] = "1.2500"
    record = client.post("/api/experiment-records", headers=admin_headers, json=payload).json()["data"]

    dispensed = client.post(
        f"/api/experiment-records/{record['id']}/dispense",
        headers=auth_headers(client, "manager"),
    )
    assert dispensed.status_code == 200
    usage = dispensed.json()["data"]["reagent_usages"][0]
    assert usage["outbound_status"] == "insufficient"
    assert Decimal(str(usage["shortage_qty"])) == Decimal("0.2500")
    assert Decimal(str(usage["stock_available"])) == Decimal("0")

    updated = client.patch(
        f"/api/experiment-records/{record['id']}",
        headers=admin_headers,
        json={"conclusion": "Saved after dispensing", "reagent_usages": []},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["reagent_usages"][0]["outbound_status"] == "insufficient"

    repeated = client.post(
        f"/api/experiment-records/{record['id']}/dispense",
        headers=auth_headers(client, "manager"),
    )
    assert repeated.status_code == 200

    db_session.expire_all()
    stored_lot = db_session.get(ReagentLot, lot["id"])
    stored_usage = db_session.query(ExperimentReagentUsage).filter_by(experiment_record_id=record["id"]).one()
    txns = db_session.query(InventoryTxn).filter_by(source_type="experiment", source_id=record["id"]).all()
    assert stored_lot.quantity == Decimal("0.0000")
    assert stored_usage.shortage_qty == Decimal("0.2500")
    assert len(txns) == 1
    assert txns[0].quantity == Decimal("1.0000")


def test_operator_cannot_dispense_and_project_manager_cannot_dispense_other_project(client, create_user):
    admin_headers, manager, _, _, project, _ = setup_users_and_project(client, create_user)
    other_manager = create_user(username="other_manager", role="project_manager", must_change_password=False)
    other_project = create_project(client, admin_headers, "P003", other_manager.id)
    record = client.post(
        "/api/experiment-records",
        headers=admin_headers,
        json=record_payload(other_project["id"], code="EXP-OTHER"),
    ).json()["data"]

    operator_response = client.post(
        f"/api/experiment-records/{record['id']}/dispense",
        headers=auth_headers(client, "operator"),
    )
    manager_response = client.post(
        f"/api/experiment-records/{record['id']}/dispense",
        headers=auth_headers(client, "manager"),
    )
    assert operator_response.status_code == 403
    assert manager_response.status_code == 403
    assert manager.id != other_manager.id


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
    assert {item["id"] for item in operator_list.json()["data"]["items"]} == {created_by_operator["id"]}
    assert hidden_detail.status_code == 404
    assert other_operator_detail.status_code == 404
    assert operator.id != other_operator.id


def test_project_manager_cannot_archive(client, create_user):
    admin_headers, _, _, _, project, _ = setup_users_and_project(client, create_user)
    create_response = client.post("/api/experiment-records", headers=admin_headers, json=record_payload(project["id"]))
    record_id = create_response.json()["data"]["id"]

    response = client.post(f"/api/experiment-records/{record_id}/archive", headers=auth_headers(client, "manager"))

    assert response.status_code == 403


def test_project_detail_experiment_record_count_uses_real_records(client, create_user, db_session):
    admin_headers, _, _, _, project, _ = setup_users_and_project(client, create_user)
    client.post("/api/experiment-records", headers=admin_headers, json=record_payload(project["id"], code="EXP-001"))
    client.post("/api/experiment-records", headers=admin_headers, json=record_payload(project["id"], code="EXP-002"))

    response = client.get(f"/api/projects/{project['id']}", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["data"]["experiment_record_count"] == 2
    db_session.expire_all()
    assert db_session.get(Project, project["id"]).project_code == "P001"
