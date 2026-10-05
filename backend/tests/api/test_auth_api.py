PREFIX = "/api/v1/auth"


def register(client, email="new@example.com", password="secret123"):
    return client.post(f"{PREFIX}/register", json={"email": email, "password": password})


def login(client, email="new@example.com", password="secret123"):
    return client.post(f"{PREFIX}/login", json={"email": email, "password": password})


def test_register_returns_user_without_password(client):
    res = register(client)

    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "new@example.com"
    assert body["role"] == "user"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email_is_400(client):
    register(client)

    assert register(client).status_code == 400


def test_login_returns_bearer_token(client):
    register(client)

    res = login(client)

    assert res.status_code == 200
    assert res.json()["token_type"] == "bearer"
    assert res.json()["access_token"]


def test_login_wrong_password_is_401(client):
    register(client)

    assert login(client, password="wrong-password").status_code == 401


def test_login_unknown_email_is_401(client):
    assert login(client, email="nobody@example.com").status_code == 401


def test_me_with_valid_token(client):
    register(client)
    token = login(client).json()["access_token"]

    res = client.get(f"{PREFIX}/me", headers={"Authorization": f"Bearer {token}"})

    assert res.status_code == 200
    assert res.json()["email"] == "new@example.com"


def test_me_without_token_is_rejected(client):
    # 403 on FastAPI 0.115 (pinned), 401 on newer versions: either way, not allowed in
    assert client.get(f"{PREFIX}/me").status_code in (401, 403)


def test_me_with_garbage_token_is_401(client):
    res = client.get(f"{PREFIX}/me", headers={"Authorization": "Bearer not-a-jwt"})

    assert res.status_code == 401


def test_me_with_token_of_deleted_user_is_401(client, db):
    from app.features.auth.models import User

    register(client)
    token = login(client).json()["access_token"]
    db.query(User).delete()
    db.commit()

    res = client.get(f"{PREFIX}/me", headers={"Authorization": f"Bearer {token}"})

    assert res.status_code == 401
