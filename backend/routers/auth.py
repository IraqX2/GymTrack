import hashlib
import os
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

try:
    from backend.database import get_session
    from backend.models.auth_session import AuthSession
    from backend.models.user import User
    from backend.schemas.auth import (
        AuthSessionRead,
        LoginRequest,
        PasswordChangeRequest,
        ProfileUpdateRequest,
        RegisterRequest,
        TokenResponse,
        UserRead,
    )
    from backend.security import (
        REFRESH_TOKEN_DAYS,
        as_utc,
        create_access_token,
        ensure_auth_configuration,
        get_current_user,
        hash_password,
        utc_now,
        verify_password,
    )
except ModuleNotFoundError:
    from database import get_session
    from models.auth_session import AuthSession
    from models.user import User
    from schemas.auth import (
        AuthSessionRead,
        LoginRequest,
        PasswordChangeRequest,
        ProfileUpdateRequest,
        RegisterRequest,
        TokenResponse,
        UserRead,
    )
    from security import (
        REFRESH_TOKEN_DAYS,
        as_utc,
        create_access_token,
        ensure_auth_configuration,
        get_current_user,
        hash_password,
        utc_now,
        verify_password,
    )


router = APIRouter(prefix="/api/auth", tags=["authentication"])
REFRESH_COOKIE_NAME = "gymtrack_refresh"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _set_refresh_cookie(response: Response, request: Request, token: str) -> None:
    secure = os.getenv("VERCEL") == "1" or request.url.scheme == "https"
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=REFRESH_TOKEN_DAYS * 24 * 60 * 60,
        path="/api/auth",
    )


def _issue_session(
    user: User,
    session: Session,
    request: Request,
    response: Response,
) -> TokenResponse:
    refresh_token = secrets.token_urlsafe(48)
    now = utc_now()
    auth_session = AuthSession(
        user_id=user.id,
        refresh_token_hash=_token_hash(refresh_token),
        created_at=now,
        last_used_at=now,
        expires_at=now + timedelta(days=REFRESH_TOKEN_DAYS),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    session.add(auth_session)
    session.commit()
    session.refresh(auth_session)

    _set_refresh_cookie(response, request, refresh_token)
    return TokenResponse(
        access_token=create_access_token(user, auth_session.id),
        user=UserRead.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    ensure_auth_configuration()
    email = str(payload.email).strip().lower()
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = User(
        full_name=payload.full_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role="user",
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    session.refresh(user)
    return _issue_session(user, session, request, response)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    ensure_auth_configuration()
    email = str(payload.email).strip().lower()
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")

    if user.is_banned:
        raise HTTPException(status_code=403, detail="This account has been banned.")

    return _issue_session(user, session, request, response)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    ensure_auth_configuration()
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(status_code=401, detail="No refresh session was found.")

    auth_session = session.exec(
        select(AuthSession).where(AuthSession.refresh_token_hash == _token_hash(raw_token))
    ).first()
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or as_utc(auth_session.expires_at) <= utc_now()
    ):
        raise HTTPException(status_code=401, detail="Refresh session is invalid or expired.")

    user = session.get(User, auth_session.user_id)
    if user is None or user.is_banned:
        auth_session.revoked_at = utc_now()
        session.add(auth_session)
        session.commit()
        raise HTTPException(status_code=403, detail="This account is not allowed to sign in.")

    # Rotate the opaque refresh token so a copied token cannot be reused.
    new_refresh_token = secrets.token_urlsafe(48)
    auth_session.refresh_token_hash = _token_hash(new_refresh_token)
    auth_session.last_used_at = utc_now()
    session.add(auth_session)
    session.commit()

    _set_refresh_cookie(response, request, new_refresh_token)
    return TokenResponse(
        access_token=create_access_token(user, auth_session.id),
        user=UserRead.model_validate(user),
    )


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_token:
        auth_session = session.exec(
            select(AuthSession).where(AuthSession.refresh_token_hash == _token_hash(raw_token))
        ).first()
        if auth_session and auth_session.revoked_at is None:
            auth_session.revoked_at = utc_now()
            session.add(auth_session)
            session.commit()

    secure = os.getenv("VERCEL") == "1" or request.url.scheme == "https"
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/auth",
        secure=secure,
        httponly=True,
        samesite="lax",
    )
    response.status_code = 204
    return response


@router.get("/me", response_model=UserRead)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserRead)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    current_user.full_name = payload.full_name.strip()
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.post("/change-password", response_model=TokenResponse)
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    current_user.password_hash = hash_password(payload.new_password)
    now = utc_now()

    # Revoke every previous session, then issue one fresh session for this browser.
    old_sessions = session.exec(
        select(AuthSession).where(
            AuthSession.user_id == current_user.id,
            AuthSession.revoked_at.is_(None),
        )
    ).all()
    for old_session in old_sessions:
        old_session.revoked_at = now
        session.add(old_session)

    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return _issue_session(current_user, session, request, response)


@router.get("/sessions", response_model=list[AuthSessionRead])
def list_sessions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return session.exec(
        select(AuthSession)
        .where(AuthSession.user_id == current_user.id)
        .order_by(AuthSession.created_at.desc())
    ).all()


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_session(
    session_id: str,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    auth_session = session.get(AuthSession, session_id)
    if auth_session is None or auth_session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found.")

    if auth_session.revoked_at is None:
        auth_session.revoked_at = utc_now()
        session.add(auth_session)
        session.commit()

    response.status_code = 204
    return response
