import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Callable

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

try:
    from backend.database import get_session
    from backend.models.auth_session import AuthSession
    from backend.models.user import User
except ModuleNotFoundError:
    from database import get_session
    from models.auth_session import AuthSession
    from models.user import User


ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 7
password_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
bearer_scheme = HTTPBearer(auto_error=False)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    # SQLite can return a timezone-naive datetime for a column saved as UTC.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _required_secret(name: str) -> str:
    value = os.getenv(name, "")
    if len(value) < 32:
        raise HTTPException(
            status_code=503,
            detail=f"{name} must be configured with at least 32 characters.",
        )
    return value


def ensure_auth_configuration() -> None:
    _required_secret("JWT_SECRET_KEY")
    _required_secret("PASSWORD_PEPPER")


def _peppered_password(password: str) -> str:
    pepper = _required_secret("PASSWORD_PEPPER").encode("utf-8")
    return hmac.new(pepper, password.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_password(password: str) -> str:
    """Argon2id hash of a peppered password. The pepper stays outside the database."""
    ensure_auth_configuration()
    return password_hasher.hash(_peppered_password(password))


def verify_password(password: str, password_hash: str) -> bool:
    ensure_auth_configuration()
    try:
        return password_hasher.verify(password_hash, _peppered_password(password))
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user: User, session_id: str) -> str:
    secret = _required_secret("JWT_SECRET_KEY")
    now = utc_now()
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "sid": session_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            _required_secret("JWT_SECRET_KEY"),
            algorithms=["HS256"],
            options={"require": ["sub", "role", "sid", "iat", "exp"]},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Access token is missing, invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    try:
        user_id = int(payload["sub"])
        session_id = str(payload["sid"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid access token.")

    user = session.get(User, user_id)
    auth_session = session.get(AuthSession, session_id)
    if user is None or auth_session is None or auth_session.user_id != user_id:
        raise HTTPException(status_code=401, detail="Session is no longer valid.")

    if auth_session.revoked_at is not None or as_utc(auth_session.expires_at) <= utc_now():
        raise HTTPException(status_code=401, detail="Session is no longer valid.")

    if user.is_banned:
        raise HTTPException(status_code=403, detail="This account has been banned.")

    # Roles are read from the database on every request. A stale role claim is rejected.
    if payload.get("role") != user.role:
        raise HTTPException(status_code=401, detail="Account permissions changed. Log in again.")

    return user


def require_role(required_role: str) -> Callable:
    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(status_code=403, detail="You do not have permission to do this.")
        return current_user

    return role_dependency
