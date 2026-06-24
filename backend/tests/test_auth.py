from app.models.auth import RefreshToken
from app.models.user import User


def login(client, username="admin", password="password123"):
    return client.post("/api/auth/login", json={"username": username, "password": password})


def test_login_success(client, create_user):
    create_user(must_change_password=True)

    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["access_token"]
    assert body["data"]["refresh_token"]
    assert body["data"]["must_change_password"] is True
    assert body["data"]["user"]["username"] == "admin"


def test_login_wrong_password_fails(client, create_user):
    create_user()

    response = login(client, password="wrong-password")

    assert response.status_code == 401
    assert response.json()["code"] == 401


def test_refresh_token_rotates_and_old_token_fails(client, create_user):
    create_user()
    login_body = login(client).json()["data"]

    response = client.post("/api/auth/refresh", json={"refresh_token": login_body["refresh_token"]})

    assert response.status_code == 200
    new_body = response.json()["data"]
    assert new_body["access_token"]
    assert new_body["refresh_token"]
    assert new_body["refresh_token"] != login_body["refresh_token"]

    old_response = client.post("/api/auth/refresh", json={"refresh_token": login_body["refresh_token"]})
    assert old_response.status_code == 401


def test_logout_revokes_refresh_token(client, create_user):
    create_user()
    refresh_token = login(client).json()["data"]["refresh_token"]

    response = client.post("/api/auth/logout", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    assert response.json()["data"] == {"logged_out": True}

    refresh_response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 401


def test_change_password_clears_must_change_password_and_revokes_refresh_tokens(client, create_user, db_session):
    user = create_user(must_change_password=True)
    login_body = login(client).json()["data"]

    response = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {login_body['access_token']}"},
        json={"old_password": "password123", "new_password": "new-password123"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"must_change_password": False}
    db_session.expire_all()
    updated_user = db_session.get(User, user.id)
    assert updated_user.must_change_password is False
    assert db_session.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)).count() == 0

    old_refresh_response = client.post("/api/auth/refresh", json={"refresh_token": login_body["refresh_token"]})
    assert old_refresh_response.status_code == 401

    new_login_response = login(client, password="new-password123")
    assert new_login_response.status_code == 200
    assert new_login_response.json()["data"]["must_change_password"] is False


def test_users_me_requires_login(client):
    response = client.get("/api/users/me")

    assert response.status_code == 401
    assert response.json()["code"] == 401


def test_users_me_returns_current_user(client, create_user):
    create_user(username="operator", password="password123", role="operator", must_change_password=False)
    login_body = login(client, username="operator").json()["data"]

    response = client.get("/api/users/me", headers={"Authorization": f"Bearer {login_body['access_token']}"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["username"] == "operator"
    assert body["data"]["role"] == "operator"
