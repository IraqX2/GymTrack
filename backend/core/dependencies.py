import os
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from backend.database import get_session
from backend.models.user import AppUser

JWT_SECRET = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET")
bearer = HTTPBearer(auto_error=False)
DB = Annotated[Session, Depends(get_session)]


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: DB,
) -> AppUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        claims = jwt.decode(
            credentials.credentials,
            JWT_SECRET or "local-only-secret-change-before-deploy",
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

    user = db.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Account not found")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Account is banned")
    return user


CURRENT = Annotated[AppUser, Depends(current_user)]


def admin_user(user: CURRENT) -> AppUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator permission required")
    return user


ADMIN = Annotated[AppUser, Depends(admin_user)]


def trainer_user(user: CURRENT) -> AppUser:
    if user.role != "trainer":
        raise HTTPException(status_code=403, detail="Trainer permission required")
    return user


TRAINER = Annotated[AppUser, Depends(trainer_user)]
