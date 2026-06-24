from decimal import Decimal

from app.models.business import InventoryTxn, ReagentLot


def login(client, username: str, password: str = "password123") -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def auth_headers(client, username: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {login(client, username)}"}


def reagent_payload(name: str = "Methanol", min_stock: str = "10.0000") -> dict:
    return {
        "name": name,
        "cas_no": "67-56-1",
        "catalog_no": "M-001",
        "manufacturer": "Vendor",
        "grade": "HPLC",
        "default_unit": "mL",
        "min_stock": min_stock,
    }


def create_reagent(client, headers: dict[str, str], name: str = "Methanol", min_stock: str = "10.0000") -> dict:
    response = client.post("/api/reagents", headers=headers, json=reagent_payload(name, min_stock))
    assert response.status_code == 201
    return response.json()["data"]


def lot_payload(reagent_id: int, lot_no: str = "LOT-001", quantity: str = "0") -> dict:
    return {
        "reagent_id": reagent_id,
        "lot_no": lot_no,
        "quantity": quantity,
        "unit": "mL",
        "location": "Cabinet A",
        "storage_condition": "room temperature",
        "controlled_flag": False,
        "status": "in_stock",
    }


def create_lot(client, headers: dict[str, str], reagent_id: int, lot_no: str = "LOT-001") -> dict:
    response = client.post("/api/reagent-lots", headers=headers, json=lot_payload(reagent_id, lot_no))
    assert response.status_code == 201
    return response.json()["data"]


def create_txn(client, headers: dict[str, str], lot_id: int, txn_type: str, quantity: str | None = None, target_quantity: str | None = None) -> dict:
    payload = {"reagent_lot_id": lot_id, "txn_type": txn_type, "reference": "test run"}
    if quantity is not None:
        payload["quantity"] = quantity
    if target_quantity is not None:
        payload["target_quantity"] = target_quantity
    response = client.post("/api/inventory-transactions", headers=headers, json=payload)
    assert response.status_code == 201
    return response.json()["data"]


def setup_users(create_user):
    create_user(username="admin", role="admin", must_change_password=False)
    create_user(username="director", role="director", must_change_password=False)
    create_user(username="manager", role="project_manager", must_change_password=False)
    create_user(username="operator", role="operator", must_change_password=False)


def test_admin_can_create_reagent(client, create_user):
    setup_users(create_user)

    response = client.post("/api/reagents", headers=auth_headers(client, "admin"), json=reagent_payload())

    assert response.status_code == 201
    assert response.json()["data"]["name"] == "Methanol"
    assert response.json()["data"]["created_by"] is not None


def test_director_and_operator_can_view_reagents_but_director_cannot_write(client, create_user):
    setup_users(create_user)
    admin_headers = auth_headers(client, "admin")
    reagent = create_reagent(client, admin_headers)

    director_headers = auth_headers(client, "director")
    operator_headers = auth_headers(client, "operator")
    director_list = client.get("/api/reagents", headers=director_headers)
    operator_detail = client.get(f"/api/reagents/{reagent['id']}", headers=operator_headers)
    director_create = client.post("/api/reagents", headers=director_headers, json=reagent_payload("Acetonitrile"))
    director_patch = client.patch(f"/api/reagents/{reagent['id']}", headers=director_headers, json={"name": "Nope"})

    assert director_list.status_code == 200
    assert [item["id"] for item in director_list.json()["data"]["items"]] == [reagent["id"]]
    assert operator_detail.status_code == 200
    assert operator_detail.json()["data"]["id"] == reagent["id"]
    assert director_create.status_code == 403
    assert director_patch.status_code == 403


def test_reagent_list_supports_keyword_is_active_and_pagination(client, create_user):
    setup_users(create_user)
    admin_headers = auth_headers(client, "admin")
    reagent = create_reagent(client, admin_headers, "Methanol", "10.0000")
    inactive = create_reagent(client, admin_headers, "Acetonitrile", "5.0000")
    client.delete(f"/api/reagents/{inactive['id']}", headers=admin_headers)

    response = client.get(
        "/api/reagents",
        headers=auth_headers(client, "director"),
        params={"keyword": "meth", "is_active": True, "page": 1, "page_size": 1},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert [item["id"] for item in data["items"]] == [reagent["id"]]


def test_reagent_lot_duplicate_reagent_and_lot_no_fails(client, create_user):
    setup_users(create_user)
    admin_headers = auth_headers(client, "admin")
    reagent = create_reagent(client, admin_headers)
    create_lot(client, admin_headers, reagent["id"], "LOT-001")

    duplicate = client.post("/api/reagent-lots", headers=admin_headers, json=lot_payload(reagent["id"], "LOT-001"))

    assert duplicate.status_code == 409


def test_reagent_lot_cannot_be_created_with_initial_quantity_or_patched_quantity(client, create_user):
    setup_users(create_user)
    admin_headers = auth_headers(client, "admin")
    reagent = create_reagent(client, admin_headers)

    nonzero_create = client.post("/api/reagent-lots", headers=admin_headers, json=lot_payload(reagent["id"], quantity="5.0000"))
    lot = create_lot(client, admin_headers, reagent["id"])
    patch_quantity = client.patch(f"/api/reagent-lots/{lot['id']}", headers=admin_headers, json={"quantity": "5.0000"})

    assert nonzero_create.status_code == 400
    assert lot["quantity"] in ["0.0000", 0, "0"]
    assert patch_quantity.status_code == 422


def test_inventory_in_increases_lot_quantity_and_records_balance_after(client, create_user, db_session):
    setup_users(create_user)
    admin_headers = auth_headers(client, "admin")
    reagent = create_reagent(client, admin_headers)
    lot = create_lot(client, admin_headers, reagent["id"])

    txn = create_txn(client, auth_headers(client, "operator"), lot["id"], "in", "25.5000")

    assert txn["txn_type"] == "in"
    assert Decimal(str(txn["balance_after"])) == Decimal("25.5000")
    db_session.expire_all()
    assert db_session.get(ReagentLot, lot["id"]).quantity == Decimal("25.5000")


def test_inventory_out_decreases_lot_quantity_and_records_balance_after(client, create_user, db_session):
    setup_users(create_user)
    admin_headers = auth_headers(client, "admin")
    reagent = create_reagent(client, admin_headers)
    lot = create_lot(client, admin_headers, reagent["id"])
    create_txn(client, admin_headers, lot["id"], "in", "25.0000")

    txn = create_txn(client, auth_headers(client, "manager"), lot["id"], "out", "5.0000")

    assert txn["txn_type"] == "out"
    assert Decimal(str(txn["balance_after"])) == Decimal("20.0000")
    db_session.expire_all()
    assert db_session.get(ReagentLot, lot["id"]).quantity == Decimal("20.0000")


def test_inventory_out_rejects_insufficient_quantity_and_leaves_balance_unchanged(client, create_user, db_session):
    setup_users(create_user)
    admin_headers = auth_headers(client, "admin")
    reagent = create_reagent(client, admin_headers)
    lot = create_lot(client, admin_headers, reagent["id"])
    create_txn(client, admin_headers, lot["id"], "in", "3.0000")

    response = client.post(
        "/api/inventory-transactions",
        headers=auth_headers(client, "operator"),
        json={"reagent_lot_id": lot["id"], "txn_type": "out", "quantity": "4.2500"},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Insufficient reagent lot quantity"
    db_session.expire_all()
    stored_lot = db_session.get(ReagentLot, lot["id"])
    txn_count = db_session.query(InventoryTxn).filter(InventoryTxn.reagent_lot_id == lot["id"]).count()
    assert stored_lot.quantity == Decimal("3.0000")
    assert stored_lot.status == "in_stock"
    assert txn_count == 1


def test_inventory_adjust_uses_target_quantity_and_records_balance_after(client, create_user, db_session):
    setup_users(create_user)
    admin_headers = auth_headers(client, "admin")
    reagent = create_reagent(client, admin_headers)
    lot = create_lot(client, admin_headers, reagent["id"])
    create_txn(client, admin_headers, lot["id"], "in", "10.0000")

    txn = create_txn(client, auth_headers(client, "operator"), lot["id"], "adjust", target_quantity="8.5000")

    assert Decimal(str(txn["quantity"])) == Decimal("-1.5000")
    assert Decimal(str(txn["balance_after"])) == Decimal("8.5000")
    db_session.expire_all()
    assert db_session.get(ReagentLot, lot["id"]).quantity == Decimal("8.5000")


def test_inventory_txn_and_balance_update_commit_together(client, create_user, db_session):
    setup_users(create_user)
    admin_headers = auth_headers(client, "admin")
    reagent = create_reagent(client, admin_headers)
    lot = create_lot(client, admin_headers, reagent["id"])

    txn = create_txn(client, admin_headers, lot["id"], "in", "7.0000")

    db_session.expire_all()
    stored_lot = db_session.get(ReagentLot, lot["id"])
    stored_txn = db_session.get(InventoryTxn, txn["id"])
    assert stored_lot.quantity == Decimal("7.0000")
    assert stored_txn.balance_after == stored_lot.quantity


def test_low_stock_returns_lots_below_reagent_min_stock(client, create_user):
    setup_users(create_user)
    admin_headers = auth_headers(client, "admin")
    low_reagent = create_reagent(client, admin_headers, "Methanol", "10.0000")
    ok_reagent = create_reagent(client, admin_headers, "Acetonitrile", "5.0000")
    low_lot = create_lot(client, admin_headers, low_reagent["id"], "LOW")
    ok_lot = create_lot(client, admin_headers, ok_reagent["id"], "OK")
    create_txn(client, admin_headers, low_lot["id"], "in", "3.0000")
    create_txn(client, admin_headers, ok_lot["id"], "in", "6.0000")

    response = client.get("/api/reagent-lots/low-stock", headers=auth_headers(client, "director"))

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]["items"]] == [low_lot["id"]]


def test_lot_and_txn_lists_support_filters_and_pagination(client, create_user):
    setup_users(create_user)
    admin_headers = auth_headers(client, "admin")
    reagent = create_reagent(client, admin_headers)
    controlled_lot = create_lot(client, admin_headers, reagent["id"], "CTRL")
    client.patch(f"/api/reagent-lots/{controlled_lot['id']}", headers=admin_headers, json={"controlled_flag": True})
    other_lot = create_lot(client, admin_headers, reagent["id"], "OTHER")
    txn = create_txn(client, auth_headers(client, "operator"), controlled_lot["id"], "in", "1.2345")
    create_txn(client, auth_headers(client, "operator"), other_lot["id"], "in", "2.0000")

    lot_response = client.get(
        "/api/reagent-lots",
        headers=auth_headers(client, "director"),
        params={"reagent_id": reagent["id"], "keyword": "CTRL", "controlled_flag": True, "page": 1, "page_size": 10},
    )
    txn_response = client.get(
        "/api/inventory-transactions",
        headers=auth_headers(client, "director"),
        params={"reagent_lot_id": controlled_lot["id"], "txn_type": "in", "page": 1, "page_size": 10},
    )

    assert lot_response.status_code == 200
    assert [item["id"] for item in lot_response.json()["data"]["items"]] == [controlled_lot["id"]]
    assert txn_response.status_code == 200
    assert [item["id"] for item in txn_response.json()["data"]["items"]] == [txn["id"]]


def test_director_cannot_create_inventory_transaction(client, create_user):
    setup_users(create_user)
    admin_headers = auth_headers(client, "admin")
    reagent = create_reagent(client, admin_headers)
    lot = create_lot(client, admin_headers, reagent["id"])

    response = client.post(
        "/api/inventory-transactions",
        headers=auth_headers(client, "director"),
        json={"reagent_lot_id": lot["id"], "txn_type": "in", "quantity": "1.0000"},
    )

    assert response.status_code == 403


def test_unauthenticated_reagent_access_fails(client):
    response = client.get("/api/reagents")

    assert response.status_code == 401


def test_decimal_precision_is_preserved_for_inventory(client, create_user, db_session):
    setup_users(create_user)
    admin_headers = auth_headers(client, "admin")
    reagent = create_reagent(client, admin_headers, min_stock="0.0001")
    lot = create_lot(client, admin_headers, reagent["id"])

    txn = create_txn(client, auth_headers(client, "operator"), lot["id"], "in", "0.1234")

    assert Decimal(str(txn["balance_after"])) == Decimal("0.1234")
    db_session.expire_all()
    assert db_session.get(ReagentLot, lot["id"]).quantity == Decimal("0.1234")
