import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models.business import AuditLog
from app.models.user import User
from app.services.module_access import ensure_module


def login(client, username: str, password: str = "password123") -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def auth_headers(client, username: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {login(client, username)}"}


def create_payload(username: str, **overrides) -> dict:
    payload = {
        "username": username,
        "display_name": "Module User",
        "password": "initial-pass-123",
        "role": "operator",
        "is_active": True,
    }
    payload.update(overrides)
    return payload


def test_admin_response_is_normalized_to_all_modules(client, create_user):
    admin = create_user(username="module_admin", role="admin", modules="refstd", must_change_password=False)

    response = client.get("/api/admin/users", headers=auth_headers(client, "module_admin"))

    assert response.status_code == 200
    returned_admin = next(item for item in response.json()["data"] if item["id"] == admin.id)
    assert admin.modules == "refstd"
    assert returned_admin["modules"] == ["lims", "refstd"]


def test_admin_create_user_defaults_to_lims_module(client, create_user, db_session):
    create_user(username="create_modules_admin", role="admin", must_change_password=False)

    response = client.post(
        "/api/admin/users",
        headers=auth_headers(client, "create_modules_admin"),
        json=create_payload("default_modules_user"),
    )

    assert response.status_code == 201
    assert response.json()["data"]["modules"] == ["lims"]
    created = db_session.scalar(select(User).where(User.username == "default_modules_user"))
    assert created is not None
    assert created.modules == "lims"


def test_admin_create_user_accepts_and_canonicalizes_modules(client, create_user, db_session):
    create_user(username="create_both_admin", role="admin", must_change_password=False)

    response = client.post(
        "/api/admin/users",
        headers=auth_headers(client, "create_both_admin"),
        json=create_payload("both_modules_user", modules=["refstd", "lims"]),
    )

    assert response.status_code == 201
    assert response.json()["data"]["modules"] == ["lims", "refstd"]
    created = db_session.scalar(select(User).where(User.username == "both_modules_user"))
    assert created is not None
    assert created.modules == "lims,refstd"


@pytest.mark.parametrize(
    "modules",
    [[], ["unknown"], ["lims", "lims"]],
)
def test_admin_create_user_rejects_invalid_modules(client, create_user, modules):
    create_user(username="invalid_modules_admin", role="admin", must_change_password=False)

    response = client.post(
        "/api/admin/users",
        headers=auth_headers(client, "invalid_modules_admin"),
        json=create_payload(f"invalid_{len(modules)}", modules=modules),
    )

    assert response.status_code == 422


def test_admin_updates_modules_and_records_exact_audit_payload(client, create_user, db_session):
    create_user(username="patch_modules_admin", role="admin", must_change_password=False)
    target = create_user(username="patch_modules_target", role="operator", modules="lims", must_change_password=False)

    response = client.patch(
        f"/api/admin/users/{target.id}/modules",
        headers=auth_headers(client, "patch_modules_admin"),
        json={"modules": ["refstd"]},
    )

    assert response.status_code == 200
    assert response.json()["data"]["modules"] == ["refstd"]
    db_session.expire_all()
    assert db_session.get(User, target.id).modules == "refstd"
    log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "update",
            AuditLog.entity_type == "user",
            AuditLog.entity_id == target.id,
        )
    )
    assert log is not None
    assert log.target_user_id == target.id
    assert log.after_data == {"modules": ["refstd"]}


@pytest.mark.parametrize("modules", [[], ["unknown"], ["refstd", "refstd"]])
def test_admin_update_modules_rejects_invalid_payload(client, create_user, modules):
    create_user(username="patch_invalid_admin", role="admin", must_change_password=False)
    target = create_user(username="patch_invalid_target", role="operator", must_change_password=False)

    response = client.patch(
        f"/api/admin/users/{target.id}/modules",
        headers=auth_headers(client, "patch_invalid_admin"),
        json={"modules": modules},
    )

    assert response.status_code == 422


def test_non_admin_cannot_update_modules(client, create_user):
    create_user(username="non_admin_modules", role="operator", modules="lims,refstd", must_change_password=False)
    target = create_user(username="non_admin_target", role="operator", must_change_password=False)

    response = client.patch(
        f"/api/admin/users/{target.id}/modules",
        headers=auth_headers(client, "non_admin_modules"),
        json={"modules": ["refstd"]},
    )

    assert response.status_code == 403


def test_ensure_module_allows_stored_module_and_admin_override(create_user):
    refstd_user = create_user(username="refstd_access", role="operator", modules="refstd")
    admin = create_user(username="admin_access", role="admin", modules="lims")

    ensure_module(refstd_user, "refstd")
    ensure_module(admin, "refstd")


def test_ensure_module_rejects_missing_module(create_user):
    lims_user = create_user(username="lims_only", role="operator", modules="lims")

    with pytest.raises(HTTPException) as exc_info:
        ensure_module(lims_user, "refstd")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Module access required: refstd"


def test_ensure_module_rejects_unknown_module(create_user):
    user = create_user(username="unknown_module", role="operator", modules="lims")

    with pytest.raises(ValueError, match="Unknown module"):
        ensure_module(user, "other")
