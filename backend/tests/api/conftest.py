import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.features.auth.models import User
from app.main import app


@pytest.fixture
def client(db):
    """TestClient whose get_db dependency hands out the in-memory test session."""

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(db, email, role):
    u = User(email=email, password_hash=hash_password("secret123"), role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def bearer(user):
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


@pytest.fixture
def admin_headers(db):
    return bearer(make_user(db, "boss@example.com", "admin"))


@pytest.fixture
def user_headers(db):
    return bearer(make_user(db, "staff@example.com", "user"))
