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


def create_experiment_record(client, headers: dict[str, str], project_id: int, code: str = "EXP-DR-001") -> dict:
    response = client.post(
        "/api/experiment-records",
        headers=headers,
        json={
            "project_id": project_id,
            "code": code,
            "title": "Daily report linked record",
            "record_type": "analysis",
            "status": "draft",
            "experiment_date": "2026-06-23",
            "result_summary": "Assay completed",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def report_payload(project_id: int | None = None, experiment_record_id: int | None = None, summary: str = "Daily summary") -> dict:
    return {
        "report_date": "2026-06-23",
        "summary": summary,
        "issues": "No blocking issue",
        "next_plan": "Continue analysis",
        "items": [
            {
                "project_id": project_id,
                "experiment_record_id": experiment_record_id,
                "work_type": "analysis",
                "content": "Reviewed chromatogram and wrote conclusion",
                "progress_note": "80%",
                "hours_spent": "2.50",
                "problem_note": "Column pressure increased",
                "next_step": "Flush column",
                "sort_order": 1,
            }
        ],
        "attachments": [
            {
                "file_name": "chromatogram.pdf",
                "file_type": "pdf",
                "file_size": 2048,
                "storage_key": "daily-reports/chromatogram.pdf",
                "description": "Metadata only",
            }
        ],
    }


def setup_users_projects_and_record(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    create_user(username="pm", role="project_manager", must_change_password=False)
    create_user(username="director", role="director", must_change_password=False)
    manager = create_user(username="manager", role="project_manager", must_change_password=False)
    researcher = create_user(username="researcher", role="researcher", must_change_password=False)
    operator = create_user(username="operator", role="operator", must_change_password=False)
    other = create_user(username="other", role="operator", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project = create_project(client, admin_headers, "DR001", manager.id)
    other_project = create_project(client, admin_headers, "DR002", manager.id)
    add_member(client, admin_headers, project["id"], researcher.id)
    add_member(client, admin_headers, project["id"], operator.id)
    record = create_experiment_record(client, admin_headers, project["id"])
    return admin_headers, project, other_project, record


def test_create_daily_report_success(client, create_user):
    _, project, _, record = setup_users_projects_and_record(client, create_user)

    response = client.post("/api/daily-reports", headers=auth_headers(client, "researcher"), json=report_payload(project["id"], record["id"]))

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "draft"
    assert data["summary"] == "Daily summary"
    assert data["item_count"] == 1
    assert data["project_count"] == 1
    assert data["experiment_record_count"] == 1


def test_create_daily_report_with_multiple_items_success(client, create_user):
    _, project, _, record = setup_users_projects_and_record(client, create_user)
    payload = report_payload(project["id"], record["id"])
    payload["items"].append(
        {
            "project_id": None,
            "experiment_record_id": None,
            "work_type": "meeting",
            "content": "Project sync meeting",
            "sort_order": 2,
        }
    )

    response = client.post("/api/daily-reports", headers=auth_headers(client, "operator"), json=payload)

    assert response.status_code == 201
    assert response.json()["data"]["item_count"] == 2


def test_daily_report_list_pagination_success(client, create_user):
    _, project, _, record = setup_users_projects_and_record(client, create_user)
    headers = auth_headers(client, "researcher")
    client.post("/api/daily-reports", headers=headers, json=report_payload(project["id"], record["id"], "First"))
    second_payload = {**report_payload(project["id"], record["id"], "Second"), "report_date": "2026-06-24"}
    client.post("/api/daily-reports", headers=headers, json=second_payload)

    response = client.get("/api/daily-reports", headers=headers, params={"page": 1, "page_size": 1})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert len(data["items"]) == 1


def test_daily_report_filters_by_user_status_date_and_project(client, create_user):
    _, project, _, record = setup_users_projects_and_record(client, create_user)
    researcher_headers = auth_headers(client, "researcher")
    report = client.post("/api/daily-reports", headers=researcher_headers, json=report_payload(project["id"], record["id"])).json()["data"]
    client.post(f"/api/daily-reports/{report['id']}/submit", headers=researcher_headers)

    response = client.get(
        "/api/daily-reports",
        headers=auth_headers(client, "admin"),
        params={
            "user_id": report["user_id"],
            "status": "submitted",
            "date_from": "2026-06-23",
            "date_to": "2026-06-23",
            "project_id": project["id"],
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["id"] == report["id"]


def test_daily_report_detail_returns_items_attachments_and_experiment_record_summary(client, create_user):
    _, project, _, record = setup_users_projects_and_record(client, create_user)
    created = client.post(
        "/api/daily-reports",
        headers=auth_headers(client, "researcher"),
        json=report_payload(project["id"], record["id"]),
    ).json()["data"]

    response = client.get(f"/api/daily-reports/{created['id']}", headers=auth_headers(client, "researcher"))

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["items"]) == 1
    assert len(data["attachments"]) == 1
    assert data["items"][0]["experiment_record"]["code"] == "EXP-DR-001"
    assert data["attachments"][0]["file_name"] == "chromatogram.pdf"


def test_daily_report_submit_review_return_state_transitions_success(client, create_user):
    _, project, _, record = setup_users_projects_and_record(client, create_user)
    researcher_headers = auth_headers(client, "researcher")
    manager_headers = auth_headers(client, "manager")
    report = client.post("/api/daily-reports", headers=researcher_headers, json=report_payload(project["id"], record["id"])).json()["data"]

    submitted = client.post(f"/api/daily-reports/{report['id']}/submit", headers=researcher_headers)
    reviewed = client.post(f"/api/daily-reports/{report['id']}/review", headers=manager_headers, json={"review_comment": "ok"})

    assert submitted.status_code == 200
    assert submitted.json()["data"]["status"] == "submitted"
    assert reviewed.status_code == 200
    assert reviewed.json()["data"]["status"] == "confirmed"

    second = client.post("/api/daily-reports", headers=researcher_headers, json=report_payload(project["id"], record["id"], "Needs return")).json()["data"]
    client.post(f"/api/daily-reports/{second['id']}/submit", headers=researcher_headers)
    returned = client.post(f"/api/daily-reports/{second['id']}/return", headers=manager_headers, json={"review_comment": "revise"})
    assert returned.status_code == 200
    assert returned.json()["data"]["status"] == "returned"


def test_regular_user_only_views_own_daily_reports(client, create_user):
    _, project, _, record = setup_users_projects_and_record(client, create_user)
    own = client.post("/api/daily-reports", headers=auth_headers(client, "researcher"), json=report_payload(project["id"], record["id"])).json()["data"]
    hidden = client.post("/api/daily-reports", headers=auth_headers(client, "operator"), json=report_payload(project["id"], record["id"], "hidden")).json()["data"]

    own_list = client.get("/api/daily-reports", headers=auth_headers(client, "researcher"))
    hidden_detail = client.get(f"/api/daily-reports/{hidden['id']}", headers=auth_headers(client, "researcher"))

    assert own_list.status_code == 200
    assert {item["id"] for item in own_list.json()["data"]["items"]} == {own["id"]}
    assert hidden_detail.status_code == 404


def test_regular_user_cannot_review_or_archive(client, create_user):
    _, project, _, record = setup_users_projects_and_record(client, create_user)
    researcher_headers = auth_headers(client, "researcher")
    report = client.post("/api/daily-reports", headers=researcher_headers, json=report_payload(project["id"], record["id"])).json()["data"]
    client.post(f"/api/daily-reports/{report['id']}/submit", headers=researcher_headers)

    review = client.post(f"/api/daily-reports/{report['id']}/review", headers=auth_headers(client, "operator"), json={"review_comment": "no"})
    archive = client.post(f"/api/daily-reports/{report['id']}/archive", headers=auth_headers(client, "operator"))

    assert review.status_code in {403, 404}
    assert archive.status_code in {403, 404, 405}


def test_admin_pm_project_manager_can_view_and_review(client, create_user):
    _, project, _, record = setup_users_projects_and_record(client, create_user)
    researcher_headers = auth_headers(client, "researcher")
    report = client.post("/api/daily-reports", headers=researcher_headers, json=report_payload(project["id"], record["id"])).json()["data"]
    client.post(f"/api/daily-reports/{report['id']}/submit", headers=researcher_headers)

    pm_list = client.get("/api/daily-reports", headers=auth_headers(client, "manager"))
    manager_review = client.post(f"/api/daily-reports/{report['id']}/review", headers=auth_headers(client, "manager"), json={"review_comment": "ok"})

    assert pm_list.status_code == 200
    assert pm_list.json()["data"]["total"] == 1
    assert manager_review.status_code == 200
    assert manager_review.json()["data"]["status"] == "confirmed"


def test_project_manager_only_reviews_reports_for_managed_projects(client, create_user):
    admin_headers, project, _, record = setup_users_projects_and_record(client, create_user)
    other_manager = create_user(username="other_manager", role="project_manager", must_change_password=False)
    other_operator = create_user(username="other_team_operator", role="operator", must_change_password=False)
    other_project = create_project(client, admin_headers, "DR003", other_manager.id)
    add_member(client, admin_headers, other_project["id"], other_operator.id)
    other_record = create_experiment_record(client, admin_headers, other_project["id"], "EXP-DR-OTHER")
    report = client.post(
        "/api/daily-reports",
        headers=auth_headers(client, "other_team_operator"),
        json=report_payload(other_project["id"], other_record["id"]),
    ).json()["data"]
    client.post(f"/api/daily-reports/{report['id']}/submit", headers=auth_headers(client, "other_team_operator"))

    manager_list = client.get("/api/daily-reports", headers=auth_headers(client, "manager"))
    manager_review = client.post(
        f"/api/daily-reports/{report['id']}/review",
        headers=auth_headers(client, "manager"),
        json={"review_comment": "should not pass"},
    )
    assert report["id"] not in {item["id"] for item in manager_list.json()["data"]["items"]}
    assert manager_review.status_code == 404


def test_daily_report_archive_is_admin_only_for_t1_6b(client, create_user):
    _, project, _, record = setup_users_projects_and_record(client, create_user)
    report = client.post("/api/daily-reports", headers=auth_headers(client, "researcher"), json=report_payload(project["id"], record["id"])).json()["data"]
    client.post(f"/api/daily-reports/{report['id']}/submit", headers=auth_headers(client, "researcher"))

    response = client.post(f"/api/daily-reports/{report['id']}/archive", headers=auth_headers(client, "admin"))

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "archived"
