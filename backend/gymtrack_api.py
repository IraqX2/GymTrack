import csv, hashlib, hmac, io, os, secrets, uuid
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlmodel import Session, SQLModel, select

try:
    from backend.database import engine
    from backend.models.member import Member
    from backend.models.entities import *
    from backend.schemas.api import *
except ModuleNotFoundError:
    from database import engine
    from models.member import Member
    from models.entities import *
    from schemas.api import *

# App setup. In production the frontend and API share one Vercel origin.
app = FastAPI(title="GymTrack API", description="Gym membership, attendance and workout management.", version="2.0.0",
              docs_url="/api/docs" if os.getenv("VERCEL") == "1" else "/docs",
              openapi_url="/api/openapi.json" if os.getenv("VERCEL") == "1" else "/openapi.json")
origins = [x.strip() for x in os.getenv("FRONTEND_URLS", "").split(",") if x.strip()]
if not os.getenv("VERCEL"):
    origins += ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(CORSMiddleware, allow_origins=list(dict.fromkeys(origins)), allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type"])

JWT_SECRET = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET")
PEPPER = os.getenv("PASSWORD_PEPPER")
ACCESS_MINUTES, REFRESH_DAYS = 15, 7
COOKIE_NAME, COOKIE_PATH = "gymtrack_refresh", "/api/auth"
hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


def now():
    return datetime.now(timezone.utc)

def session_dep():
    with Session(engine) as session:
        yield session

DB = Annotated[Session, Depends(session_dep)]

def peppered(value: str) -> str:
    return hmac.new((PEPPER or "local-only-pepper").encode(), value.encode(), hashlib.sha256).hexdigest()

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
    return jwt.encode({"sub": str(user.id), "role": user.role, "iat": issued,
                       "exp": issued + timedelta(minutes=ACCESS_MINUTES)}, secret, algorithm="HS256")

def hash_refresh(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def set_cookie(response: Response, value: str):
    response.set_cookie(COOKIE_NAME, value, max_age=REFRESH_DAYS*86400, path=COOKIE_PATH,
                        httponly=True, secure=os.getenv("VERCEL") == "1", samesite="lax")

def clear_cookie(response: Response):
    response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH, httponly=True,
                           secure=os.getenv("VERCEL") == "1", samesite="lax")

def client_ip(request: Request):
    forwarded = request.headers.get("x-forwarded-for")
    return (forwarded.split(",")[0].strip() if forwarded else
            (request.client.host if request.client else ""))[:45] or None

def audit(db: Session, request: Request, action: str, user: AppUser | None = None,
          entity_type: str | None = None, entity_id=None, details: str | None = None, email: str | None = None):
    try:
        db.add(ActivityLog(user_id=user.id if user else None, email=user.email if user else email,
                           action=action, entity_type=entity_type,
                           entity_id=str(entity_id) if entity_id is not None else None,
                           details=(details or "")[:500] or None, ip_address=client_ip(request),
                           user_agent=(request.headers.get("user-agent") or "")[:250] or None))
        db.commit()
    except Exception:
        db.rollback()

def current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)], db: DB):
    if not credentials:
        raise HTTPException(401, "Not authenticated")
    try:
        claims = jwt.decode(credentials.credentials, JWT_SECRET or "local-only-secret-change-before-deploy",
                            algorithms=["HS256"], options={"require": ["sub", "exp"]})
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise HTTPException(401, "Invalid or expired access token")
    user = db.get(AppUser, user_id)
    if not user:
        raise HTTPException(401, "Account not found")
    if user.is_banned:
        raise HTTPException(403, "Account is banned")
    return user

CURRENT = Annotated[AppUser, Depends(current_user)]

def admin_user(user: CURRENT):
    if user.role != "admin":
        raise HTTPException(403, "Administrator permission required")
    return user

ADMIN = Annotated[AppUser, Depends(admin_user)]

def public_user(user: AppUser, db: Session | None = None):
    trainer = None
    if db is not None and user.role == "user":
        trainer = db.exec(
            select(Trainer).where(Trainer.user_id == user.id, Trainer.is_active.is_(True))
        ).first()
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "is_banned": user.is_banned,
        "is_trainer": trainer is not None,
        "trainer_id": trainer.id if trainer else None,
        "created_at": user.created_at,
    }

def get_my_member(db: Session, user: AppUser):
    member = db.exec(select(Member).where(Member.user_id == user.id)).first()
    if not member:
        raise HTTPException(404, "No gym profile is linked to this account")
    return member

def get_member(db: Session, member_id: int):
    row = db.get(Member, member_id)
    if not row:
        raise HTTPException(404, "Member not found")
    return row

def get_group_member(db: Session, group_id: int, user_id: int):
    row = db.get(GymGroupMember, (group_id, user_id))
    if not row:
        raise HTTPException(404, "Group not found")
    return row

def group_allow(row: GymGroupMember, permission: str):
    if row.role == "owner":
        return
    enabled = {"create": row.can_create, "edit": row.can_edit, "assign": row.can_assign}.get(permission, False)
    if not enabled:
        raise HTTPException(403, f"Group permission denied: {permission}")

def csv_response(filename: str, headers: list[str], rows: list[list]):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        # Prevent spreadsheet formula injection in exported user-controlled text.
        writer.writerow([("'" + str(v) if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v)
                         for v in row])
    return Response(output.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "GymTrack API", "version": "2.0.0"}


# Temporary diagnostic for the preview database connection. It never returns credentials.
@app.get("/api/health/database")
def database_health():
    from sqlalchemy import text
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as error:
        original = getattr(error, "orig", error)
        # Keep database connection details in server logs only; never expose them to the browser.
        sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
        print(
            "GYMTRACK_DB_DIAGNOSTIC",
            type(original).__name__,
            "sqlstate=" + str(sqlstate),
            "message=" + str(original)[:350],
            flush=True,
        )
        raise HTTPException(status_code=503, detail="Database connection is unavailable. Check server logs.")

# Register feature controllers after shared models, security helpers and dependencies exist.
try:
    from backend.routers.auth import router as auth_router
    from backend.routers.members import router as members_router
    from backend.routers.operations import router as operations_router
    from backend.routers.groups import router as groups_router
    from backend.routers.admin import router as admin_router
    from backend.trainers.router import router as trainer_router
except ModuleNotFoundError:
    from routers.auth import router as auth_router
    from routers.members import router as members_router
    from routers.operations import router as operations_router
    from routers.groups import router as groups_router
    from routers.admin import router as admin_router
    from trainers.router import router as trainer_router

app.include_router(auth_router)
app.include_router(members_router)
app.include_router(operations_router)
app.include_router(groups_router)
app.include_router(admin_router)
app.include_router(trainer_router)


@app.on_event("startup")
def startup():
    if os.getenv("VERCEL") == "1" and (not JWT_SECRET or not PEPPER):
        raise RuntimeError("JWT_SECRET_KEY and PASSWORD_PEPPER must be set in Vercel.")
    # In local SQLite only, create tables for models. Supabase uses explicit migrations.
    if os.getenv("VERCEL") != "1":
        SQLModel.metadata.create_all(engine)


@app.get("/")
def root():
    return {"message": "GymTrack API is running", "docs": "/api/docs"}
