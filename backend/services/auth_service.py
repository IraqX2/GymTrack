"""Authentication, profile and refresh-session business rules."""

import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlmodel import Session, select

try:
    from backend.core.audit import audit, client_ip
    from backend.models.member import Member
    from backend.models.resources import AuthSession
    from backend.models.user import AppUser
    from backend.repositories import auth_repository as repository
    from backend.schemas.resources import Signup, Login, ProfilePatch, PasswordPatch
except ModuleNotFoundError:
    from core.audit import audit, client_ip
    from models.member import Member
    from models.resources import AuthSession
    from models.user import AppUser
    from repositories import auth_repository as repository
    from schemas.resources import Signup, Login, ProfilePatch, PasswordPatch


JWT_SECRET = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET")
PEPPER = os.getenv("PASSWORD_PEPPER")
ACCESS_MINUTES = 15
REFRESH_DAYS = 7
COOKIE_NAME = "gymtrack_refresh"
COOKIE_PATH = "/api/auth"
hasher = PasswordHash.recommended()


def now():
    return datetime.now(timezone.utc)


def peppered(value: str) -> str:
    return hmac.new(
        (PEPPER or "local-only-pepper").encode(),
        value.encode(),
        hashlib.sha256,
    ).hexdigest()


def hash_password(value: str) -> str:
    return hasher.hash(peppered(value))


def check_password(value: str, hashed: str) -> bool:
    try:
        return hasher.verify(peppered(value), hashed)
    except Exception:
        return False


def issue_access(user: AppUser) -> str:
    secret = JWT_SECRET or "local-only-secret-change-before-deploy"
    issued = now()
    return jwt.encode(
        {
            "sub": str(user.id),
            "role": user.role,
            "iat": issued,
            "exp": issued + timedelta(minutes=ACCESS_MINUTES),
        },
        secret,
        algorithm="HS256",
    )


def hash_refresh(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def set_cookie(response: Response, value: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        value,
        max_age=REFRESH_DAYS * 86400,
        path=COOKIE_PATH,
        httponly=True,
        secure=os.getenv("VERCEL") == "1",
        samesite="lax",
    )


def clear_cookie(response: Response) -> None:
    response.delete_cookie(
        COOKIE_NAME,
        path=COOKIE_PATH,
        httponly=True,
        secure=os.getenv("VERCEL") == "1",
        samesite="lax",
    )


def public_user(user: AppUser) -> dict:
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "is_banned": user.is_banned,
        "created_at": user.created_at,
    }


def _create_refresh_session(session: Session, user: AppUser, request: Request) -> str:
    refresh = secrets.token_urlsafe(48)
    repository.add_session(
        session,
        AuthSession(
            id=str(uuid.uuid4()),
            user_id=user.id,
            refresh_token_hash=hash_refresh(refresh),
            expires_at=now() + timedelta(days=REFRESH_DAYS),
            ip_address=client_ip(request),
            user_agent=(request.headers.get("user-agent") or "")[:250],
        ),
    )
    return refresh


def signup(session: Session, payload: Signup, request: Request) -> dict:
    email = str(payload.email).lower()
    if repository.find_user_by_email(session, email):
        raise HTTPException(409, "An account with this email already exists")

    bootstrap_email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").lower()
    user = AppUser(
        full_name=payload.full_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role="admin" if bootstrap_email and bootstrap_email == email else "user",
    )
    repository.save_user(session, user)
    repository.add_member_profile(session, user)
    refresh = _create_refresh_session(session, user, request)
    audit(session, request, "signup", user, "user", user.id)
    return {
        "user": public_user(user),
        "refresh": refresh,
        "access_token": issue_access(user),
        "token_type": "bearer",
        "expires_in": ACCESS_MINUTES * 60,
    }


def login(session: Session, payload: Login, request: Request) -> dict:
    email = str(payload.email).lower()
    user = repository.find_user_by_email(session, email)
    if user is None:
        audit(session, request, "login_failed", email=email, details="Unknown email")
        raise HTTPException(401, "Invalid email or password")
    if user.is_banned:
        audit(session, request, "login_blocked", user, details="Banned account")
        raise HTTPException(403, "Account is banned")
    if user.locked_until and user.locked_until > now():
        raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
    if not check_password(payload.password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= 5:
            user.failed_login_count = 0
            user.locked_until = now() + timedelta(minutes=15)
            repository.save_user(session, user)
            audit(session, request, "login_locked", user, details="Five failed attempts")
        else:
            repository.save_user(session, user)
            audit(session, request, "login_failed", user)
        raise HTTPException(401, "Invalid email or password")

    user.failed_login_count = 0
    user.locked_until = None
    user.updated_at = now()
    repository.save_user(session, user)
    refresh = _create_refresh_session(session, user, request)
    audit(session, request, "login", user)
    return {
        "user": public_user(user),
        "refresh": refresh,
        "access_token": issue_access(user),
        "token_type": "bearer",
        "expires_in": ACCESS_MINUTES * 60,
    }


def refresh_session(session: Session, raw_refresh: str | None, request: Request) -> dict:
    if not raw_refresh:
        raise HTTPException(401, "Refresh cookie missing")
    token_row = repository.find_session_by_refresh_hash(session, hash_refresh(raw_refresh))
    if token_row is None or token_row.revoked_at or token_row.expires_at <= now():
        raise HTTPException(401, "Refresh session expired or revoked")
    user = repository.get_user(session, token_row.user_id)
    if user is None or user.is_banned:
        token_row.revoked_at = now()
        repository.save_session(session, token_row)
        raise HTTPException(403, "Account is banned or unavailable")
    new_refresh = secrets.token_urlsafe(48)
    token_row.refresh_token_hash = hash_refresh(new_refresh)
    token_row.last_used_at = now()
    token_row.ip_address = client_ip(request)
    repository.save_session(session, token_row)
    return {
        "user": public_user(user),
        "refresh": new_refresh,
        "access_token": issue_access(user),
        "token_type": "bearer",
        "expires_in": ACCESS_MINUTES * 60,
    }


def logout(session: Session, raw_refresh: str | None, request: Request) -> None:
    if raw_refresh:
        row = repository.find_session_by_refresh_hash(session, hash_refresh(raw_refresh))
        if row and not row.revoked_at:
            row.revoked_at = now()
            repository.save_session(session, row)
            user = repository.get_user(session, row.user_id)
            audit(session, request, "logout", user)


def get_profile(session: Session, user: AppUser) -> dict:
    member = session.exec(select(Member).where(Member.user_id == user.id)).first()
    return {
        **public_user(user),
        "member_id": member.id if member else None,
        "phone": member.phone if member else "",
    }


def update_profile(session: Session, user: AppUser, payload: ProfilePatch) -> AppUser:
    user.full_name = payload.full_name.strip()
    user.updated_at = now()
    session.add(user)
    member = session.exec(select(Member).where(Member.user_id == user.id)).first()
    if member:
        member.full_name = user.full_name
        session.add(member)
    session.commit()
    session.refresh(user)
    return user


def change_password(
    session: Session,
    user: AppUser,
    payload: PasswordPatch,
    request: Request,
) -> None:
    if not check_password(payload.current_password, user.password_hash):
        audit(session, request, "password_change_failed", user)
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    user.updated_at = now()
    session.add(user)
    for row in repository.list_revocable_sessions(session, user.id):
        row.revoked_at = now()
        session.add(row)
    session.commit()
    audit(session, request, "password_changed", user)


def list_sessions(session: Session, user: AppUser, raw_refresh: str | None):
    active = repository.list_active_sessions(session, user.id, now())
    current_hash = hash_refresh(raw_refresh) if raw_refresh else None
    return [
        {
            "id": row.id,
            "created_at": row.created_at,
            "last_used_at": row.last_used_at,
            "expires_at": row.expires_at,
            "ip_address": row.ip_address,
            "user_agent": row.user_agent,
            "current": row.refresh_token_hash == current_hash,
        }
        for row in active
    ]


def revoke_session(
    session: Session,
    session_id: str,
    user: AppUser,
    raw_refresh: str | None,
    request: Request,
) -> bool:
    row = repository.get_session(session, session_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "Session not found")
    is_current = bool(raw_refresh) and row.refresh_token_hash == hash_refresh(raw_refresh)
    row.revoked_at = now()
    repository.save_session(session, row)
    audit(session, request, "session_revoked", user, "session", session_id)
    return is_current
