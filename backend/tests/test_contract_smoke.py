from app.main import app


def login(client, username: str, password: str = "password123") -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def auth_headers(client, username: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {login(client, username)}"}


def assert_page_shape(data: dict) -> None:
    assert {"items", "total", "page", "page_size"}.issubset(data)
    assert isinstance(data["items"], list)


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


def create_reagent_and_lot(client, headers: dict[str, str]) -> tuple[dict, dict]:
    reagent = client.post(
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
    assert reagent.status_code == 201
    reagent_data = reagent.json()["data"]
    lot = client.post(
        "/api/reagent-lots",
        headers=headers,
        json={
            "reagent_id": reagent_data["id"],
            "lot_no": "LOT-SMOKE",
            "quantity": "0",
            "unit": "mL",
            "location": "Cabinet A",
            "status": "in_stock",
        },
    )
    assert lot.status_code == 201
    return reagent_data, lot.json()["data"]


def create_experiment_record(client, headers: dict[str, str], project_id: int, code: str = "EXP-SMOKE") -> dict:
    response = client.post(
        "/api/experiment-records",
        headers=headers,
        json={
            "project_id": project_id,
            "code": code,
            "title": "Smoke experiment",
            "record_type": "analysis",
            "status": "draft",
            "experiment_date": "2026-06-23",
            "result_summary": "Smoke result",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_health_contract_includes_status_and_app(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["data"] == {"status": "ok", "app": "LIMS"}


def test_main_routers_are_registered():
    route_paths = {
        path
        for route in app.routes
        if (path := getattr(route, "path", None)) is not None
    }
    route_paths.update(app.openapi()["paths"])

    assert "/api/health" in route_paths
    assert "/api/users/project-owner-candidates" in route_paths
    assert "/api/projects" in route_paths
    assert "/api/reagents" in route_paths
    assert "/api/reagent-lots" in route_paths
    assert "/api/inventory-transactions" in route_paths
    assert "/api/experiment-records" in route_paths
    assert "/api/daily-reports" in route_paths
    assert "/api/samples" in route_paths
    assert "/api/test-methods" in route_paths
    assert "/api/test-tasks" in route_paths
    assert "/api/test-results" in route_paths


def test_contract_smoke_lists_permissions_and_pagination(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    create_user(username="director", role="director", must_change_password=False)
    manager = create_user(username="manager", role="project_manager", must_change_password=False)
    researcher = create_user(username="researcher", role="researcher", must_change_password=False)
    operator = create_user(username="operator", role="operator", must_change_password=False)

    admin_headers = auth_headers(client, "admin")
    project = create_project(client, admin_headers, "SMOKE-001", manager.id)
    add_member(client, admin_headers, project["id"], researcher.id)
    add_member(client, admin_headers, project["id"], operator.id)
    _, lot = create_reagent_and_lot(client, admin_headers)
    record = create_experiment_record(client, admin_headers, project["id"])
    report = client.post(
        "/api/daily-reports",
        headers=auth_headers(client, "researcher"),
        json={
            "report_date": "2026-06-23",
            "summary": "Smoke daily report",
            "items": [
                {
                    "project_id": project["id"],
                    "experiment_record_id": record["id"],
                    "work_type": "analysis",
                    "content": "Smoke contract work",
                }
            ],
        },
    )
    assert report.status_code == 201

    for path, headers in [
        ("/api/projects", admin_headers),
        ("/api/reagents", auth_headers(client, "director")),
        ("/api/reagent-lots", auth_headers(client, "director")),
        ("/api/inventory-transactions", auth_headers(client, "director")),
        ("/api/experiment-records", auth_headers(client, "researcher")),
        ("/api/daily-reports", auth_headers(client, "researcher")),
    ]:
        response = client.get(path, headers=headers, params={"page": 1, "page_size": 10})
        assert response.status_code == 200
        assert_page_shape(response.json()["data"])

    owner_candidates = client.get("/api/users/project-owner-candidates", headers=admin_headers)
    assert owner_candidates.status_code == 200
    assert {user["role"] for user in owner_candidates.json()["data"]} == {"admin", "project_manager"}

    operator_txn = client.post(
        "/api/inventory-transactions",
        headers=auth_headers(client, "operator"),
        json={"reagent_lot_id": lot["id"], "txn_type": "in", "quantity": "1.0000"},
    )
    director_txn = client.post(
        "/api/inventory-transactions",
        headers=auth_headers(client, "director"),
        json={"reagent_lot_id": lot["id"], "txn_type": "in", "quantity": "1.0000"},
    )
    anonymous_projects = client.get("/api/projects")

    assert operator_txn.status_code == 403
    assert director_txn.status_code == 201
    assert anonymous_projects.status_code == 401
