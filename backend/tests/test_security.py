import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-that-is-at-least-32-characters")
os.environ.setdefault("PASSWORD_PEPPER", "test-password-pepper-that-is-at-least-32-characters")

from backend.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_is_hashed_and_verifies():
    password = "StrongGymTrackPassword!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("incorrect-password", hashed)


def test_signed_access_token_contains_id_role_and_session():
    user = SimpleNamespace(id=12, role="admin")
    token = create_access_token(user, "session-123")

    claims = decode_access_token(token)
    assert claims["sub"] == "12"
    assert claims["role"] == "admin"
    assert claims["sid"] == "session-123"


def test_expired_access_token_is_rejected():
    expired = datetime.now(timezone.utc) - timedelta(minutes=2)
    token = jwt.encode(
        {
            "sub": "12",
            "role": "user",
            "sid": "session-123",
            "iat": expired - timedelta(minutes=1),
            "exp": expired,
        },
        os.environ["JWT_SECRET_KEY"],
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as error:
        decode_access_token(token)

    assert error.value.status_code == 401


def test_tampered_access_token_is_rejected():
    user = SimpleNamespace(id=12, role="user")
    token = create_access_token(user, "session-123")

    with pytest.raises(HTTPException) as error:
        decode_access_token(token + "tampered")

    assert error.value.status_code == 401
