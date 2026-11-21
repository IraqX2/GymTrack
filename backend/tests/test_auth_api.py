import os

os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-that-is-at-least-32-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-password-pepper-that-is-at-least-32-characters")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.database import get_session
from backend.main import app
from backend.models.user import User
from backend.security import hash_password


@pytest.fixture
def test_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        yield engine
    finally:
        app.dependency_overrides.pop(get_session, None)
        engine.dispose()


@pytest.fixture
def client(test_database):
    # Avoid the application's production startup hook; this test uses its own
    # isolated in-memory database through the dependency override above.
    with TestClient(app) as test_client:
        yield test_client


def register_user(client: TestClient, email: str = "member@example.com") -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "GymTrack Member",
            "email": email,
            "password": "StrongPassword123!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_signup_login_and_role_based_member_access(client: TestClient):
    registered = register_user(client)
    assert registered["user"]["role"] == "user"
    assert registered["access_token"]

    # Member records are protected even if a user manually calls the API.
    assert client.get("/api/members").status_code == 401

    user_response = client.get(
        "/api/members",
        headers={"Authorization": "Bearer " + registered["access_token"]},
    )
    assert user_response.status_code == 403

    login_response = client.post(
        "/api/auth/login",
        json={"email": "member@example.com", "password": "StrongPassword123!"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["role"] == "user"


def test_administrator_can_access_member_management(client: TestClient, test_database):
    with Session(test_database) as session:
        admin = User(
            full_name="GymTrack Admin",
            email="admin@example.com",
            password_hash=hash_password("AdminPassword123!"),
            role="admin",
        )
        session.add(admin)
        session.commit()

    login_response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "AdminPassword123!"},
    )
    assert login_response.status_code == 200

    response = client.get(
        "/api/members",
        headers={"Authorization": "Bearer " + login_response.json()["access_token"]},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_refresh_rotates_cookie_and_logout_revokes_access(client: TestClient):
    registered = register_user(client, "refresh@example.com")
    old_refresh_token = client.cookies.get("gymtrack_refresh")
    assert old_refresh_token

    refresh_response = client.post("/api/auth/refresh")
    assert refresh_response.status_code == 200
    new_refresh_token = client.cookies.get("gymtrack_refresh")
    assert new_refresh_token
    assert new_refresh_token != old_refresh_token

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204

    after_logout = client.get(
        "/api/members",
        headers={"Authorization": "Bearer " + registered["access_token"]},
    )
    assert after_logout.status_code == 401
