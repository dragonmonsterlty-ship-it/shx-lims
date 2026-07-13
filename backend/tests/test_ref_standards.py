from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import create_engine_for_url
from app.models.business import AuditLog, RefStandard
from app.models.user import User
from app.schemas.ref_standard import RefStandardCreate
from app.services import ref_standards as ref_standard_service


def auth_headers(client, username: str, password: str = "password123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def create_payload(**overrides) -> dict:
    payload = {
        "name": "Reference Standard A",
        "batch_no": "BATCH-001",
        "source": "self_made",
        "spec": "10 mg",
        "assigned_value": "99.50%",
        "initial_amount": "12.3400",
        "unit": "mg",
        "storage_condition": "2-8 C",
        "expires_at": "2027-07-13",
        "notes": None,
    }
    payload.update(overrides)
    return payload


def setup_users(create_user):
    users = {
        "writer": create_user(
            username="refstd_writer", role="operator", modules="refstd", must_change_password=False
        ),
        "viewer": create_user(
            username="refstd_viewer", role="viewer", modules="refstd", must_change_password=False
        ),
        "no_module": create_user(
            username="refstd_no_module", role="operator", modules="lims", must_change_password=False
        ),
        "admin": create_user(
            username="refstd_admin", role="admin", modules="lims", must_change_password=False
        ),
    }
    return users


def test_create_auto_and_manual_codes_and_response_formats(client, create_user, db_session, monkeypatch):
    setup_users(create_user)
    monkeypatch.setattr(ref_standard_service, "current_year", lambda: 2031)
    headers = auth_headers(client, "refstd_writer")

    automatic = client.post("/api/ref-standards", headers=headers, json=create_payload())
    assert automatic.status_code == 201, automatic.text
    auto_data = automatic.json()["data"]
    assert auto_data == {
        "id": auto_data["id"],
        "code": "RS-2031-0001",
        "name": "Reference Standard A",
        "batch_no": "BATCH-001",
        "source": "self_made",
        "spec": "10 mg",
        "assigned_value": "99.50%",
        "initial_amount": "12.3400",
        "current_amount": "12.3400",
        "unit": "mg",
        "storage_condition": "2-8 C",
        "expires_at": "2027-07-13",
        "status": "in_stock",
        "notes": None,
        "created_by": auto_data["created_by"],
        "created_at": auto_data["created_at"],
        "updated_at": None,
        "is_deleted": False,
    }
    assert auto_data["created_at"].endswith("Z") or "+00:00" in auto_data["created_at"]

    manual = client.post(
        "/api/ref-standards",
        headers=headers,
        json=create_payload(code="  rs-2031-0042  ", name="Manual"),
    )
    assert manual.status_code == 201, manual.text
    assert manual.json()["data"]["code"] == "RS-2031-0042"

    next_auto = client.post("/api/ref-standards", headers=headers, json=create_payload(name="Next"))
    assert next_auto.status_code == 201, next_auto.text
    assert next_auto.json()["data"]["code"] == "RS-2031-0043"

    logs = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.entity_type == "ref_standard", AuditLog.action == "create")
        ).all()
    )
    assert len(logs) == 3


def test_duplicate_code_and_payload_validation_return_expected_errors(client, create_user):
    setup_users(create_user)
    headers = auth_headers(client, "refstd_writer")
    first = client.post(
        "/api/ref-standards", headers=headers, json=create_payload(code="manual-001")
    )
    assert first.status_code == 201, first.text

    duplicate = client.post(
        "/api/ref-standards", headers=headers, json=create_payload(code=" MANUAL-001 ")
    )
    assert duplicate.status_code == 409
    assert duplicate.json() == {
        "code": 409,
        "message": "Reference standard code already exists",
        "data": None,
    }

    for payload in (
        create_payload(source="other"),
        create_payload(initial_amount="0"),
        create_payload(initial_amount="-1"),
        create_payload(code="   "),
    ):
        response = client.post("/api/ref-standards", headers=headers, json=payload)
        assert response.status_code == 422, response.text


def test_module_and_viewer_permissions_cover_all_ledger_routes(client, create_user):
    users = setup_users(create_user)
    admin_headers = auth_headers(client, "refstd_admin")
    created = client.post(
        "/api/ref-standards", headers=admin_headers, json=create_payload(code="PERM-001")
    ).json()["data"]
    standard_id = created["id"]
    no_module_headers = auth_headers(client, "refstd_no_module")
    viewer_headers = auth_headers(client, "refstd_viewer")

    no_module_requests = (
        client.get("/api/ref-standards", headers=no_module_headers),
        client.post("/api/ref-standards", headers=no_module_headers, json=create_payload()),
        client.get(f"/api/ref-standards/{standard_id}", headers=no_module_headers),
        client.patch(f"/api/ref-standards/{standard_id}", headers=no_module_headers, json={"name": "Denied"}),
        client.post(f"/api/ref-standards/{standard_id}/dispose", headers=no_module_headers),
    )
    assert all(response.status_code == 403 for response in no_module_requests)

    assert client.get("/api/ref-standards", headers=viewer_headers).status_code == 200
    assert client.get(f"/api/ref-standards/{standard_id}", headers=viewer_headers).status_code == 200
    assert client.post("/api/ref-standards", headers=viewer_headers, json=create_payload()).status_code == 403
    assert (
        client.patch(f"/api/ref-standards/{standard_id}", headers=viewer_headers, json={"name": "Denied"}).status_code
        == 403
    )
    assert client.post(f"/api/ref-standards/{standard_id}/dispose", headers=viewer_headers).status_code == 403
    assert users["admin"].modules == "lims"


def test_list_filters_pagination_and_soft_delete_exclusion(client, create_user, db_session):
    setup_users(create_user)
    headers = auth_headers(client, "refstd_writer")
    today = date.today()
    records = [
        create_payload(code="FILTER-001", name="Alpha", batch_no="LOT-A", source="self_made", expires_at=str(today + timedelta(days=5))),
        create_payload(code="FILTER-002", name="Beta", batch_no="LOT-B", source="purchased", expires_at=str(today + timedelta(days=40))),
        create_payload(code="FILTER-003", name="Gamma", batch_no="LOT-C", source="purchased", expires_at=str(today - timedelta(days=1))),
    ]
    ids = []
    for payload in records:
        response = client.post("/api/ref-standards", headers=headers, json=payload)
        assert response.status_code == 201, response.text
        ids.append(response.json()["data"]["id"])
    deleted = db_session.get(RefStandard, ids[2])
    deleted.is_deleted = True
    db_session.commit()

    cases = (
        ({"keyword": "lOt-a"}, ["FILTER-001"]),
        ({"code": "002"}, ["FILTER-002"]),
        ({"name": "alp"}, ["FILTER-001"]),
        ({"batch_no": "lot-b"}, ["FILTER-002"]),
        ({"source": "purchased"}, ["FILTER-002"]),
        ({"status": "in_stock", "expiring_within_days": 10}, ["FILTER-001"]),
    )
    for params, expected_codes in cases:
        response = client.get("/api/ref-standards", headers=headers, params=params)
        assert response.status_code == 200, response.text
        assert [item["code"] for item in response.json()["data"]["items"]] == expected_codes

    page = client.get("/api/ref-standards", headers=headers, params={"page": 1, "page_size": 1})
    assert page.json()["data"]["total"] == 2
    assert page.json()["data"]["page"] == 1
    assert page.json()["data"]["page_size"] == 1
    assert client.get(f"/api/ref-standards/{ids[2]}", headers=headers).status_code == 404
    assert client.get("/api/ref-standards", headers=headers, params={"source": "invalid"}).status_code == 422
    assert client.get("/api/ref-standards", headers=headers, params={"status": "invalid"}).status_code == 422
    assert client.get("/api/ref-standards", headers=headers, params={"expiring_within_days": -1}).status_code == 422


def test_patch_forbids_read_only_fields_and_records_only_actual_changes(client, create_user, db_session):
    setup_users(create_user)
    headers = auth_headers(client, "refstd_writer")
    created = client.post(
        "/api/ref-standards", headers=headers, json=create_payload(code="PATCH-001", notes="old")
    ).json()["data"]
    standard_id = created["id"]

    for field, value in (
        ("code", "PATCH-002"),
        ("initial_amount", "99"),
        ("current_amount", "1"),
        ("status", "depleted"),
        ("created_by", 999),
        ("created_at", "2026-01-01T00:00:00Z"),
    ):
        response = client.patch(f"/api/ref-standards/{standard_id}", headers=headers, json={field: value})
        assert response.status_code == 422, (field, response.text)

    updated = client.patch(
        f"/api/ref-standards/{standard_id}",
        headers=headers,
        json={"name": "Reference Standard A", "notes": "new", "spec": None},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["notes"] == "new"
    assert updated.json()["data"]["spec"] is None

    log = db_session.scalar(
        select(AuditLog)
        .where(AuditLog.entity_type == "ref_standard", AuditLog.entity_id == standard_id, AuditLog.action == "update")
        .order_by(AuditLog.id.desc())
    )
    assert log.before_data == {"notes": "old", "spec": "10 mg"}
    assert log.after_data == {"notes": "new", "spec": None}
    assert log.metadata_ == {"changed_fields": ["spec", "notes"]}


def test_dispose_is_audited_and_blocks_repeat_and_edit(client, create_user, db_session):
    setup_users(create_user)
    headers = auth_headers(client, "refstd_writer")
    standard_id = client.post(
        "/api/ref-standards", headers=headers, json=create_payload(code="DISPOSE-001")
    ).json()["data"]["id"]

    disposed = client.post(f"/api/ref-standards/{standard_id}/dispose", headers=headers)
    assert disposed.status_code == 200, disposed.text
    assert disposed.json()["data"]["status"] == "disposed"
    assert disposed.json()["data"]["current_amount"] == "12.3400"
    assert client.post(f"/api/ref-standards/{standard_id}/dispose", headers=headers).status_code == 422
    assert client.patch(f"/api/ref-standards/{standard_id}", headers=headers, json={"notes": "x"}).status_code == 422

    log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "ref_standard",
            AuditLog.entity_id == standard_id,
            AuditLog.action == "dispose",
        )
    )
    assert log.before_data == {"status": "in_stock"}
    assert log.after_data == {"status": "disposed"}
    assert log.metadata_ == {"changed_fields": ["status"]}


def test_atomic_counter_generates_unique_codes_concurrently(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'counter.db').as_posix()}"
    engine = create_engine_for_url(database_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    with SessionLocal() as db:
        user = User(
            username="counter_writer",
            full_name="Counter Writer",
            password_hash=hash_password("password123"),
            role="operator",
            modules="refstd",
            is_active=True,
            must_change_password=False,
        )
        db.add(user)
        db.commit()
        user_id = user.id

    monkeypatch.setattr(ref_standard_service, "current_year", lambda: 2032)

    def create_one(index: int) -> str:
        with SessionLocal() as db:
            user = db.get(User, user_id)
            standard = ref_standard_service.create_ref_standard(
                db,
                user,
                RefStandardCreate(
                    name=f"Concurrent {index}",
                    source="purchased",
                    initial_amount=Decimal("1.0000"),
                ),
            )
            return standard.code

    with ThreadPoolExecutor(max_workers=8) as executor:
        codes = list(executor.map(create_one, range(8)))
    engine.dispose()

    assert len(set(codes)) == 8
    assert sorted(codes) == [f"RS-2032-{value:04d}" for value in range(1, 9)]
