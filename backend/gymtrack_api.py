import csv, hashlib, hmac, io, os, secrets, uuid
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field as PField
from sqlmodel import Field, Session, SQLModel, select

try:
    from backend.database import engine
    from backend.models.member import Member
except ModuleNotFoundError:
    from database import engine
    from models.member import Member


# Existing PostgreSQL tables: public."user", public.authsession, public.member.
class AppUser(SQLModel, table=True):
    __tablename__ = "user"
    id: int | None = Field(default=None, primary_key=True)
    full_name: str
    email: str = Field(index=True)
    password_hash: str
    role: str = "user"
    is_banned: bool = False
    failed_login_count: int = 0
    locked_until: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuthSession(SQLModel, table=True):
    __tablename__ = "authsession"
    id: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    refresh_token_hash: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    revoked_at: datetime | None = None
    ip_address: str | None = None
    user_agent: str | None = None


class Trainer(SQLModel, table=True):
    __tablename__ = "trainer"
    id: int | None = Field(default=None, primary_key=True)
    full_name: str
    email: str = Field(unique=True, index=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    phone: str = ""
    specialization: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Membership(SQLModel, table=True):
    __tablename__ = "membership"
    id: int | None = Field(default=None, primary_key=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    plan_name: str
    start_date: date = Field(default_factory=date.today)
    end_date: date
    price: float = 0
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Attendance(SQLModel, table=True):
    __tablename__ = "attendance"
    id: int | None = Field(default=None, primary_key=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    check_in: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    check_out: datetime | None = None
    notes: str = ""
    recorded_by: int | None = Field(default=None, foreign_key="user.id")


class AttendanceRequest(SQLModel, table=True):
    __tablename__ = "attendance_request"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    requested_check_in: datetime
    requested_check_out: datetime | None = None
    notes: str = ""
    status: str = "pending"
    reviewed_by: int | None = Field(default=None, foreign_key="user.id")
    reviewed_at: datetime | None = None
    review_note: str = ""
    attendance_id: int | None = Field(default=None, foreign_key="attendance.id", unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkoutPlan(SQLModel, table=True):
    __tablename__ = "workout_plan"
    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str = ""
    level: str = "beginner"
    duration_weeks: int = 4
    created_by: int | None = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkoutAssignment(SQLModel, table=True):
    __tablename__ = "workout_assignment"
    id: int | None = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="workout_plan.id")
    member_id: int = Field(foreign_key="member.id", index=True)
    trainer_id: int | None = Field(default=None, foreign_key="trainer.id")
    start_date: date = Field(default_factory=date.today)
    end_date: date | None = None
    status: str = "active"
    assigned_by: int | None = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkoutProgress(SQLModel, table=True):
    __tablename__ = "trainer_progress"
    id: int | None = Field(default=None, primary_key=True)
    assignment_id: int = Field(foreign_key="workout_assignment.id", index=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    trainer_id: int = Field(foreign_key="trainer.id", index=True)
    completion_percent: int = Field(ge=0, le=100)
    notes: str = Field(default="", max_length=1000)
    progress_date: date = Field(default_factory=date.today)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GymGroup(SQLModel, table=True):
    __tablename__ = "gym_group"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    created_by: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GymGroupMember(SQLModel, table=True):
    __tablename__ = "gym_group_member"
    group_id: int = Field(foreign_key="gym_group.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    role: str = "member"
    can_create: bool = False
    can_edit: bool = False
    can_assign: bool = False
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GymGroupTask(SQLModel, table=True):
    __tablename__ = "gym_group_task"
    id: int | None = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="gym_group.id", index=True)
    title: str
    description: str = ""
    due_date: date | None = None
    assigned_to: int | None = Field(default=None, foreign_key="user.id")
    created_by: int = Field(foreign_key="user.id")
    is_completed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActivityLog(SQLModel, table=True):
    __tablename__ = "activity_log"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    email: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    details: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Request/response schemas.
class Signup(BaseModel):
    full_name: str = PField(min_length=2, max_length=100)
    email: EmailStr
    password: str = PField(min_length=8, max_length=128)

class Login(BaseModel):
    email: EmailStr
    password: str = PField(min_length=1, max_length=128)

class ProfilePatch(BaseModel):
    full_name: str = PField(min_length=2, max_length=100)

class PasswordPatch(BaseModel):
    current_password: str
    new_password: str = PField(min_length=8, max_length=128)

class MemberBody(BaseModel):
    full_name: str = PField(min_length=2, max_length=100)
    email: EmailStr
    phone: str = PField(default="", max_length=30)
    join_date: date = Field(default_factory=date.today)
    is_active: bool = True

class MembershipBody(BaseModel):
    member_id: int
    plan_name: str = PField(min_length=2, max_length=100)
    start_date: date = Field(default_factory=date.today)
    end_date: date
    price: float = PField(default=0, ge=0)
    status: str = "active"

class AttendanceBody(BaseModel):
    member_id: int
    check_in: datetime | None = None
    check_out: datetime | None = None
    notes: str = PField(default="", max_length=500)

class AttendanceRequestBody(BaseModel):
    requested_check_in: datetime
    requested_check_out: datetime | None = None
    notes: str = PField(default="", max_length=500)

class AttendanceRequestReview(BaseModel):
    status: Literal["approved", "rejected"]
    review_note: str = PField(default="", max_length=500)

class PlanBody(BaseModel):
    title: str = PField(min_length=2, max_length=120)
    description: str = ""
    level: str = "beginner"
    duration_weeks: int = PField(default=4, ge=1, le=52)

class AssignmentBody(BaseModel):
    plan_id: int
    member_id: int
    trainer_id: int | None = None
    start_date: date = Field(default_factory=date.today)
    end_date: date | None = None
    status: str = "active"

class GroupBody(BaseModel):
    name: str = PField(min_length=2, max_length=100)

class GroupMemberBody(BaseModel):
    email: EmailStr
    can_create: bool = False
    can_edit: bool = False
    can_assign: bool = False

class GroupPermissions(BaseModel):
    can_create: bool = False
    can_edit: bool = False
    can_assign: bool = False

class GroupWorkBody(BaseModel):
    title: str = PField(min_length=2, max_length=140)
    description: str = ""
    due_date: date | None = None
    assigned_to: int | None = None

class GroupWorkPatch(BaseModel):
    title: str | None = PField(default=None, min_length=2, max_length=140)
    description: str | None = None
    due_date: date | None = None
    assigned_to: int | None = None
    is_completed: bool | None = None


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
