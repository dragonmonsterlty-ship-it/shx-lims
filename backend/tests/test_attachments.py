from app.models.business import Attachment
from app.services.storage import StorageService


OBJECTS: dict[str, bytes] = {}


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


def setup_attachment_context(client, create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    create_user(username="director", role="director", must_change_password=False)
    manager = create_user(username="manager", role="project_manager", must_change_password=False)
    operator = create_user(username="operator", role="operator", must_change_password=False)
    other_operator = create_user(username="other_operator", role="operator", must_change_password=False)
    admin_headers = auth_headers(client, "admin")
    project = create_project(client, admin_headers, "P001", manager.id)
    add_member(client, admin_headers, project["id"], operator.id)
    daily_log = client.post(
        "/api/daily-logs",
        headers=auth_headers(client, "operator"),
        json={"project_id": project["id"], "log_date": "2026-06-22", "content": "with file"},
    ).json()["data"]
    return project, daily_log


def install_fake_storage(monkeypatch):
    OBJECTS.clear()
    counter = {"value": 0}

    def generate_storage_key(self):
        counter["value"] += 1
        return f"uuid-{counter['value']}"

    def upload_bytes(self, storage_key, content, content_type=None):
        OBJECTS[storage_key] = content

    def download_bytes(self, storage_key):
        return OBJECTS[storage_key]

    monkeypatch.setattr(StorageService, "generate_storage_key", generate_storage_key)
    monkeypatch.setattr(StorageService, "upload_bytes", upload_bytes)
    monkeypatch.setattr(StorageService, "download_bytes", download_bytes)


def upload_file(client, headers, daily_log_id: int, name: str = "report.pdf", content: bytes = b"%PDF-1.4\nbody"):
    return client.post(
        "/api/attachments/upload",
        headers=headers,
        data={"entity_type": "daily_log", "entity_id": str(daily_log_id)},
        files={"file": (name, content, "application/pdf")},
    )


def test_author_can_upload_attachment_to_own_draft_log(client, create_user, monkeypatch):
    install_fake_storage(monkeypatch)
    _, daily_log = setup_attachment_context(client, create_user)

    response = upload_file(client, auth_headers(client, "operator"), daily_log["id"])

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["sha256"]
    assert data["storage_key"] == "uuid-1"
    assert "report.pdf" not in data["storage_key"]
    assert data["content_type_detected"] == "application/pdf"
    assert data["file_size"] == len(b"%PDF-1.4\nbody")


def test_unauthorized_user_and_director_cannot_upload_attachment(client, create_user, monkeypatch):
    install_fake_storage(monkeypatch)
    _, daily_log = setup_attachment_context(client, create_user)

    other = upload_file(client, auth_headers(client, "other_operator"), daily_log["id"])
    director = upload_file(client, auth_headers(client, "director"), daily_log["id"])

    assert other.status_code == 404
    assert director.status_code == 403


def test_non_daily_log_entity_type_is_rejected(client, create_user, monkeypatch):
    install_fake_storage(monkeypatch)
    _, daily_log = setup_attachment_context(client, create_user)

    response = client.post(
        "/api/attachments/upload",
        headers=auth_headers(client, "operator"),
        data={"entity_type": "sample", "entity_id": str(daily_log["id"])},
        files={"file": ("report.pdf", b"%PDF-1.4\nbody", "application/pdf")},
    )

    assert response.status_code == 400


def test_upload_size_and_extension_are_rejected(client, create_user, monkeypatch):
    install_fake_storage(monkeypatch)
    monkeypatch.setattr("app.services.attachments.settings.upload_max_size_bytes", 4)
    _, daily_log = setup_attachment_context(client, create_user)
    headers = auth_headers(client, "operator")

    too_large = upload_file(client, headers, daily_log["id"], content=b"12345")
    bad_extension = upload_file(client, headers, daily_log["id"], name="script.exe", content=b"123")

    assert too_large.status_code == 413
    assert bad_extension.status_code == 400


def test_download_attachment_requires_daily_log_access(client, create_user, monkeypatch):
    install_fake_storage(monkeypatch)
    _, daily_log = setup_attachment_context(client, create_user)
    upload = upload_file(client, auth_headers(client, "operator"), daily_log["id"])
    attachment_id = upload.json()["data"]["id"]

    ok = client.get(f"/api/attachments/{attachment_id}/download", headers=auth_headers(client, "operator"))
    denied = client.get(f"/api/attachments/{attachment_id}/download", headers=auth_headers(client, "other_operator"))

    assert ok.status_code == 200
    assert ok.content == b"%PDF-1.4\nbody"
    assert denied.status_code == 404


def test_daily_log_attachment_list_and_record(client, create_user, db_session, monkeypatch):
    install_fake_storage(monkeypatch)
    _, daily_log = setup_attachment_context(client, create_user)
    upload = upload_file(client, auth_headers(client, "operator"), daily_log["id"])

    list_response = client.get(f"/api/daily-logs/{daily_log['id']}/attachments", headers=auth_headers(client, "operator"))

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["data"]] == [upload.json()["data"]["id"]]
    db_session.expire_all()
    attachment = db_session.get(Attachment, upload.json()["data"]["id"])
    assert attachment.entity_type == "daily_log"
    assert attachment.preview_status == "not_generated"
