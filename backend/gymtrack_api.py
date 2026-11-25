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

class TrainerBody(BaseModel):
    full_name: str = PField(min_length=2, max_length=100)
    email: EmailStr
    phone: str = PField(default="", max_length=30)
    specialization: str = PField(default="", max_length=120)
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

def public_user(user: AppUser):
    return {"id": user.id, "full_name": user.full_name, "email": user.email, "role": user.role,
            "is_banned": user.is_banned, "created_at": user.created_at}

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


# Authentication
@app.post("/api/auth/signup", status_code=201)
def signup(data: Signup, request: Request, response: Response, db: DB):
    email = str(data.email).lower()
    if db.exec(select(AppUser).where(AppUser.email == email)).first():
        raise HTTPException(409, "An account with this email already exists")
    bootstrap_email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").lower()
    user = AppUser(full_name=data.full_name.strip(), email=email, password_hash=hash_password(data.password),
                   role="admin" if bootstrap_email and bootstrap_email == email else "user")
    db.add(user); db.commit(); db.refresh(user)
    # Automatically link the signup to a personal gym member record.
    db.add(Member(full_name=user.full_name, email=user.email, phone="", is_active=True,
                  created_by=user.id, user_id=user.id))
    db.commit()
    refresh = secrets.token_urlsafe(48)
    db.add(AuthSession(id=str(uuid.uuid4()), user_id=user.id, refresh_token_hash=hash_refresh(refresh),
                       expires_at=now()+timedelta(days=REFRESH_DAYS), ip_address=client_ip(request),
                       user_agent=(request.headers.get("user-agent") or "")[:250]))
    db.commit(); set_cookie(response, refresh)
    audit(db, request, "signup", user, "user", user.id)
    return {"user": public_user(user), "access_token": issue_access(user), "token_type": "bearer",
            "expires_in": ACCESS_MINUTES*60}


@app.post("/api/auth/login")
def login(data: Login, request: Request, response: Response, db: DB):
    email = str(data.email).lower()
    user = db.exec(select(AppUser).where(AppUser.email == email)).first()
    if not user:
        audit(db, request, "login_failed", email=email, details="Unknown email")
        raise HTTPException(401, "Invalid email or password")
    if user.is_banned:
        audit(db, request, "login_blocked", user, details="Banned account")
        raise HTTPException(403, "Account is banned")
    if user.locked_until and user.locked_until > now():
        raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
    if not check_password(data.password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= 5:
            user.failed_login_count = 0
            user.locked_until = now() + timedelta(minutes=15)
            audit(db, request, "login_locked", user, details="Five failed attempts")
        else:
            audit(db, request, "login_failed", user)
        db.add(user); db.commit()
        raise HTTPException(401, "Invalid email or password")
    user.failed_login_count, user.locked_until = 0, None
    user.updated_at = now(); db.add(user); db.commit()
    refresh = secrets.token_urlsafe(48)
    db.add(AuthSession(id=str(uuid.uuid4()), user_id=user.id, refresh_token_hash=hash_refresh(refresh),
                       expires_at=now()+timedelta(days=REFRESH_DAYS), ip_address=client_ip(request),
                       user_agent=(request.headers.get("user-agent") or "")[:250]))
    db.commit(); set_cookie(response, refresh); audit(db, request, "login", user)
    return {"user": public_user(user), "access_token": issue_access(user), "token_type": "bearer",
            "expires_in": ACCESS_MINUTES*60}


@app.post("/api/auth/refresh")
def refresh(request: Request, response: Response, db: DB):
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        raise HTTPException(401, "Refresh cookie missing")
    token_row = db.exec(select(AuthSession).where(AuthSession.refresh_token_hash == hash_refresh(raw))).first()
    if not token_row or token_row.revoked_at or token_row.expires_at <= now():
        clear_cookie(response)
        raise HTTPException(401, "Refresh session expired or revoked")
    user = db.get(AppUser, token_row.user_id)
    if not user or user.is_banned:
        token_row.revoked_at = now(); db.add(token_row); db.commit(); clear_cookie(response)
        raise HTTPException(403, "Account is banned or unavailable")
    new_refresh = secrets.token_urlsafe(48)
    token_row.refresh_token_hash = hash_refresh(new_refresh)
    token_row.last_used_at = now(); token_row.ip_address = client_ip(request)
    db.add(token_row); db.commit(); set_cookie(response, new_refresh)
    return {"user": public_user(user), "access_token": issue_access(user), "token_type": "bearer",
            "expires_in": ACCESS_MINUTES*60}


@app.post("/api/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: DB):
    raw = request.cookies.get(COOKIE_NAME)
    if raw:
        row = db.exec(select(AuthSession).where(AuthSession.refresh_token_hash == hash_refresh(raw))).first()
        if row and not row.revoked_at:
            row.revoked_at = now(); db.add(row); db.commit()
            user = db.get(AppUser, row.user_id); audit(db, request, "logout", user)
    clear_cookie(response)
    return Response(status_code=204)


@app.get("/api/me")
def me(user: CURRENT, db: DB):
    member = db.exec(select(Member).where(Member.user_id == user.id)).first()
    return {**public_user(user), "member_id": member.id if member else None, "phone": member.phone if member else ""}


@app.patch("/api/me")
def update_me(data: ProfilePatch, user: CURRENT, db: DB, request: Request):
    user.full_name = data.full_name.strip(); user.updated_at = now()
    db.add(user)
    member = db.exec(select(Member).where(Member.user_id == user.id)).first()
    if member:
        member.full_name = user.full_name; db.add(member)
    db.commit(); audit(db, request, "profile_updated", user)
    return public_user(user)


@app.post("/api/me/password", status_code=204)
def change_password(data: PasswordPatch, user: CURRENT, db: DB, request: Request, response: Response):
    if not check_password(data.current_password, user.password_hash):
        audit(db, request, "password_change_failed", user)
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(data.new_password); user.updated_at = now(); db.add(user)
    for row in db.exec(select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))).all():
        row.revoked_at = now(); db.add(row)
    db.commit(); clear_cookie(response); audit(db, request, "password_changed", user)
    return Response(status_code=204)


@app.get("/api/auth/sessions")
def sessions(user: CURRENT, db: DB, request: Request):
    active = db.exec(select(AuthSession).where(AuthSession.user_id == user.id,
                    AuthSession.revoked_at.is_(None), AuthSession.expires_at > now())).all()
    current_hash = hash_refresh(request.cookies[COOKIE_NAME]) if request.cookies.get(COOKIE_NAME) else None
    return [{"id": row.id, "created_at": row.created_at, "last_used_at": row.last_used_at,
             "expires_at": row.expires_at, "ip_address": row.ip_address, "user_agent": row.user_agent,
             "current": row.refresh_token_hash == current_hash} for row in active]


@app.delete("/api/auth/sessions/{session_id}", status_code=204)
def revoke_session(session_id: str, user: CURRENT, db: DB, request: Request, response: Response):
    row = db.get(AuthSession, session_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Session not found")
    was_current = request.cookies.get(COOKIE_NAME) and row.refresh_token_hash == hash_refresh(request.cookies[COOKIE_NAME])
    row.revoked_at = now(); db.add(row); db.commit()
    if was_current: clear_cookie(response)
    audit(db, request, "session_revoked", user, "session", session_id)
    return Response(status_code=204)


@app.get("/api/member/dashboard")
def member_dashboard(user: CURRENT, db: DB):
    # A regular login represents one member profile. Members only receive
    # their own records; administrators use the management modules instead.
    if user.role != "user":
        raise HTTPException(403, "Member dashboard is only available to member accounts")
    member = get_my_member(db, user)
    my_memberships = db.exec(
        select(Membership).where(Membership.member_id == member.id)
        .order_by(Membership.created_at.desc())
    ).all()
    my_attendance = db.exec(
        select(Attendance).where(Attendance.member_id == member.id)
        .order_by(Attendance.check_in.desc()).limit(100)
    ).all()
    assignment_rows = db.exec(
        select(WorkoutAssignment, WorkoutPlan, Trainer)
        .join(WorkoutPlan, WorkoutPlan.id == WorkoutAssignment.plan_id)
        .outerjoin(Trainer, Trainer.id == WorkoutAssignment.trainer_id)
        .where(WorkoutAssignment.member_id == member.id)
        .order_by(WorkoutAssignment.created_at.desc())
    ).all()
    workouts = [
        {
            "assignment": assignment,
            "plan": plan,
            "trainer": trainer,
        }
        for assignment, plan, trainer in assignment_rows
    ]
    return {
        "member": member,
        "memberships": my_memberships,
        "attendance": my_attendance,
        "workouts": workouts,
    }


# Members
@app.get("/api/members")
def members(user: CURRENT, db: DB, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    query = select(Member).order_by(Member.id.desc()).offset(offset).limit(limit)
    if user.role != "admin": query = query.where(Member.user_id == user.id)
    return db.exec(query).all()


@app.post("/api/members", status_code=201)
def add_member(data: MemberBody, user: ADMIN, db: DB, request: Request):
    email = str(data.email).lower()
    if db.exec(select(Member).where(Member.email == email)).first():
        raise HTTPException(409, "Member email already exists")
    row = Member(**data.model_dump(exclude={"email"}), email=email, created_by=user.id)
    db.add(row); db.commit(); db.refresh(row); audit(db, request, "member_created", user, "member", row.id)
    return row


@app.get("/api/members/{member_id}")
def member_detail(member_id: int, user: CURRENT, db: DB):
    row = db.get(Member, member_id)
    if not row or (user.role != "admin" and row.user_id != user.id):
        raise HTTPException(404, "Member not found")
    return row


@app.put("/api/members/{member_id}")
def edit_member(member_id: int, data: MemberBody, user: ADMIN, db: DB, request: Request):
    row = db.get(Member, member_id)
    if not row: raise HTTPException(404, "Member not found")
    for key, value in data.model_dump().items(): setattr(row, key, str(value).lower() if key == "email" else value)
    db.add(row); db.commit(); audit(db, request, "member_updated", user, "member", row.id)
    return row


@app.delete("/api/members/{member_id}", status_code=204)
def remove_member(member_id: int, user: ADMIN, db: DB, request: Request):
    row = db.get(Member, member_id)
    if not row:
        raise HTTPException(404, "Member not found")
    has_membership = db.exec(select(Membership).where(Membership.member_id == member_id)).first()
    has_attendance = db.exec(select(Attendance).where(Attendance.member_id == member_id)).first()
    has_workout = db.exec(select(WorkoutAssignment).where(WorkoutAssignment.member_id == member_id)).first()
    if has_membership or has_attendance or has_workout:
        raise HTTPException(
            409,
            "This member has gym history. Mark the member inactive instead of deleting their records.",
        )
    db.delete(row)
    db.commit()
    audit(db, request, "member_deleted", user, "member", member_id)
    return Response(status_code=204)


# Trainers
@app.get("/api/trainers")
def trainers(user: CURRENT, db: DB):
    return db.exec(select(Trainer).order_by(Trainer.full_name)).all()


@app.post("/api/trainers", status_code=201)
def add_trainer(data: TrainerBody, user: ADMIN, db: DB, request: Request):
    email = str(data.email).lower()
    if db.exec(select(Trainer).where(Trainer.email == email)).first():
        raise HTTPException(409, "Trainer email already exists")
    row = Trainer(**data.model_dump(exclude={"email"}), email=email)
    db.add(row); db.commit(); db.refresh(row); audit(db, request, "trainer_created", user, "trainer", row.id)
    return row


@app.put("/api/trainers/{trainer_id}")
def edit_trainer(trainer_id: int, data: TrainerBody, user: ADMIN, db: DB, request: Request):
    row = db.get(Trainer, trainer_id)
    if not row: raise HTTPException(404, "Trainer not found")
    for key, value in data.model_dump().items(): setattr(row, key, str(value).lower() if key == "email" else value)
    db.add(row); db.commit(); audit(db, request, "trainer_updated", user, "trainer", row.id)
    return row


@app.delete("/api/trainers/{trainer_id}", status_code=204)
def remove_trainer(trainer_id: int, user: ADMIN, db: DB, request: Request):
    row = db.get(Trainer, trainer_id)
    if not row:
        raise HTTPException(404, "Trainer not found")
    assigned_work = db.exec(
        select(WorkoutAssignment).where(WorkoutAssignment.trainer_id == trainer_id)
    ).first()
    if assigned_work:
        raise HTTPException(409, "This trainer has assigned workouts. Mark the trainer inactive instead.")
    db.delete(row)
    db.commit()
    audit(db, request, "trainer_deleted", user, "trainer", trainer_id)
    return Response(status_code=204)


# Memberships
@app.get("/api/memberships")
def memberships(user: CURRENT, db: DB):
    query = select(Membership, Member).join(Member, Member.id == Membership.member_id)
    if user.role != "admin":
        query = query.where(Membership.member_id == get_my_member(db, user).id)
    rows = db.exec(query.order_by(Membership.created_at.desc())).all()
    return [
        {
            "id": membership.id,
            "member_id": membership.member_id,
            "member_name": member.full_name,
            "member_email": member.email,
            "plan_name": membership.plan_name,
            "start_date": membership.start_date,
            "end_date": membership.end_date,
            "price": membership.price,
            "status": membership.status,
            "created_at": membership.created_at,
        }
        for membership, member in rows
    ]


@app.post("/api/memberships", status_code=201)
def add_membership(data: MembershipBody, user: ADMIN, db: DB, request: Request):
    if not db.get(Member, data.member_id): raise HTTPException(404, "Member not found")
    if data.end_date < data.start_date: raise HTTPException(422, "End date cannot be before start date")
    if data.status not in {"active", "expired", "cancelled"}: raise HTTPException(422, "Invalid membership status")
    row = Membership(**data.model_dump()); db.add(row); db.commit(); db.refresh(row)
    audit(db, request, "membership_created", user, "membership", row.id)
    return row


@app.patch("/api/memberships/{membership_id}")
def edit_membership(membership_id: int, data: MembershipBody, user: ADMIN, db: DB, request: Request):
    row = db.get(Membership, membership_id)
    if not row: raise HTTPException(404, "Membership not found")
    if not db.get(Member, data.member_id): raise HTTPException(404, "Member not found")
    if data.end_date < data.start_date: raise HTTPException(422, "End date cannot be before start date")
    if data.status not in {"active", "expired", "cancelled"}: raise HTTPException(422, "Invalid membership status")
    for key, value in data.model_dump().items(): setattr(row, key, value)
    db.add(row); db.commit(); audit(db, request, "membership_updated", user, "membership", row.id)
    return row


@app.delete("/api/memberships/{membership_id}", status_code=204)
def remove_membership(membership_id: int, user: ADMIN, db: DB, request: Request):
    row = db.get(Membership, membership_id)
    if not row: raise HTTPException(404, "Membership not found")
    db.delete(row); db.commit(); audit(db, request, "membership_deleted", user, "membership", membership_id)
    return Response(status_code=204)


# Attendance
def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@app.get("/api/attendance")
def attendance(user: CURRENT, db: DB, limit: int = Query(100, ge=1, le=200)):
    query = select(Attendance, Member).join(Member, Member.id == Attendance.member_id)
    if user.role != "admin":
        query = query.where(Attendance.member_id == get_my_member(db, user).id)
    rows = db.exec(query.order_by(Attendance.check_in.desc()).limit(limit)).all()
    return [
        {
            "id": visit.id,
            "member_id": visit.member_id,
            "member_name": member.full_name,
            "member_email": member.email,
            "check_in": visit.check_in,
            "check_out": visit.check_out,
            "notes": visit.notes,
            "recorded_by": visit.recorded_by,
        }
        for visit, member in rows
    ]


@app.post("/api/attendance", status_code=201)
def record_attendance(data: AttendanceBody, user: ADMIN, db: DB, request: Request):
    member = db.get(Member, data.member_id)
    if not member:
        raise HTTPException(404, "Member not found")
    if not member.is_active:
        raise HTTPException(409, "This member is inactive.")
    check_in = as_utc(data.check_in) or now()
    check_out = as_utc(data.check_out)
    if check_out and check_out <= check_in:
        raise HTTPException(422, "Check-out time must be after check-in time.")
    if check_out is None:
        open_visit = db.exec(
            select(Attendance).where(
                Attendance.member_id == data.member_id,
                Attendance.check_out.is_(None),
            )
        ).first()
        if open_visit:
            raise HTTPException(409, "This member is already checked in.")
    row = Attendance(
        member_id=data.member_id,
        check_in=check_in,
        check_out=check_out,
        notes=data.notes,
        recorded_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    audit(db, request, "attendance_recorded", user, "attendance", row.id)
    return row


@app.patch("/api/attendance/{attendance_id}/checkout")
def attendance_checkout(attendance_id: int, user: ADMIN, db: DB, request: Request):
    row = db.get(Attendance, attendance_id)
    if not row:
        raise HTTPException(404, "Attendance record not found")
    if row.check_out is not None:
        raise HTTPException(409, "This attendance visit is already checked out.")
    row.check_out = now()
    db.add(row)
    db.commit()
    audit(db, request, "attendance_checkout", user, "attendance", row.id)
    return row


# Member attendance correction requests, reviewed by an administrator.
def attendance_request_view(request_row: AttendanceRequest, member: Member, account: AppUser):
    return {
        "id": request_row.id,
        "user_id": request_row.user_id,
        "member_id": request_row.member_id,
        "member_name": member.full_name,
        "member_email": member.email,
        "requested_check_in": request_row.requested_check_in,
        "requested_check_out": request_row.requested_check_out,
        "notes": request_row.notes,
        "status": request_row.status,
        "reviewed_by": request_row.reviewed_by,
        "reviewed_at": request_row.reviewed_at,
        "review_note": request_row.review_note,
        "attendance_id": request_row.attendance_id,
        "created_at": request_row.created_at,
    }


@app.get("/api/attendance/requests")
def list_attendance_requests(user: CURRENT, db: DB, status: str = ""):
    query = (
        select(AttendanceRequest, Member, AppUser)
        .join(Member, Member.id == AttendanceRequest.member_id)
        .join(AppUser, AppUser.id == AttendanceRequest.user_id)
    )
    if user.role != "admin":
        query = query.where(AttendanceRequest.user_id == user.id)
    if status in {"pending", "approved", "rejected"}:
        query = query.where(AttendanceRequest.status == status)
    rows = db.exec(query.order_by(AttendanceRequest.created_at.desc()).limit(100)).all()
    return [attendance_request_view(request_row, member, account) for request_row, member, account in rows]


@app.post("/api/attendance/requests", status_code=201)
def create_attendance_request(
    data: AttendanceRequestBody,
    user: CURRENT,
    db: DB,
    request: Request,
):
    if user.role != "user":
        raise HTTPException(403, "Attendance requests are for member accounts.")
    member = get_my_member(db, user)
    check_in = as_utc(data.requested_check_in)
    check_out = as_utc(data.requested_check_out)
    if check_out and check_out <= check_in:
        raise HTTPException(422, "Check-out time must be after check-in time.")
    duplicate = db.exec(
        select(AttendanceRequest).where(
            AttendanceRequest.user_id == user.id,
            AttendanceRequest.requested_check_in == check_in,
            AttendanceRequest.status == "pending",
        )
    ).first()
    if duplicate:
        raise HTTPException(409, "You already have a pending request for this check-in time.")
    row = AttendanceRequest(
        user_id=user.id,
        member_id=member.id,
        requested_check_in=check_in,
        requested_check_out=check_out,
        notes=data.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    audit(db, request, "attendance_request_created", user, "attendance_request", row.id)
    return {"id": row.id, "status": row.status, "requested_check_in": row.requested_check_in}


@app.patch("/api/attendance/requests/{request_id}")
def review_attendance_request(
    request_id: int,
    data: AttendanceRequestReview,
    user: ADMIN,
    db: DB,
    request: Request,
):
    request_row = db.get(AttendanceRequest, request_id)
    if not request_row:
        raise HTTPException(404, "Attendance request not found")
    if request_row.status != "pending":
        raise HTTPException(409, "This attendance request has already been reviewed.")
    if data.status == "approved":
        member = db.get(Member, request_row.member_id)
        if not member or not member.is_active:
            raise HTTPException(409, "The linked member is missing or inactive.")
        if request_row.requested_check_out is None:
            open_visit = db.exec(
                select(Attendance).where(
                    Attendance.member_id == request_row.member_id,
                    Attendance.check_out.is_(None),
                )
            ).first()
            if open_visit:
                raise HTTPException(409, "This member already has an open attendance visit.")
        visit = Attendance(
            member_id=request_row.member_id,
            check_in=request_row.requested_check_in,
            check_out=request_row.requested_check_out,
            notes=("Member request: " + request_row.notes).strip()[:500],
            recorded_by=user.id,
        )
        db.add(visit)
        db.flush()
        request_row.attendance_id = visit.id
    request_row.status = data.status
    request_row.reviewed_by = user.id
    request_row.reviewed_at = now()
    request_row.review_note = data.review_note.strip()
    db.add(request_row)
    db.commit()
    db.refresh(request_row)
    audit(
        db, request, "attendance_request_" + data.status,
        user, "attendance_request", request_row.id, data.review_note,
    )
    return {"id": request_row.id, "status": request_row.status, "attendance_id": request_row.attendance_id}


@app.delete("/api/attendance/requests/{request_id}", status_code=204)
def remove_attendance_request(request_id: int, user: CURRENT, db: DB, request: Request):
    request_row = db.get(AttendanceRequest, request_id)
    if not request_row:
        raise HTTPException(404, "Attendance request not found")
    if user.role != "admin" and (
        request_row.user_id != user.id or request_row.status != "pending"
    ):
        raise HTTPException(403, "You can only cancel your own pending request.")
    db.delete(request_row)
    db.commit()
    audit(db, request, "attendance_request_removed", user, "attendance_request", request_id)
    return Response(status_code=204)


# Workout plans and assignments
@app.get("/api/workout-plans")
def workout_plans(user: CURRENT, db: DB):
    if user.role == "admin": return db.exec(select(WorkoutPlan).order_by(WorkoutPlan.created_at.desc())).all()
    my_id = get_my_member(db, user).id
    plan_ids = select(WorkoutAssignment.plan_id).where(WorkoutAssignment.member_id == my_id)
    return db.exec(select(WorkoutPlan).where(WorkoutPlan.id.in_(plan_ids))).all()


@app.post("/api/workout-plans", status_code=201)
def add_workout_plan(data: PlanBody, user: ADMIN, db: DB, request: Request):
    if data.level not in {"beginner", "intermediate", "advanced"}: raise HTTPException(422, "Invalid plan level")
    row = WorkoutPlan(**data.model_dump(), created_by=user.id)
    db.add(row); db.commit(); db.refresh(row); audit(db, request, "workout_plan_created", user, "workout_plan", row.id)
    return row


@app.put("/api/workout-plans/{plan_id}")
def edit_workout_plan(plan_id: int, data: PlanBody, user: ADMIN, db: DB, request: Request):
    row = db.get(WorkoutPlan, plan_id)
    if not row: raise HTTPException(404, "Workout plan not found")
    if data.level not in {"beginner", "intermediate", "advanced"}: raise HTTPException(422, "Invalid plan level")
    for key, value in data.model_dump().items(): setattr(row, key, value)
    db.add(row); db.commit(); audit(db, request, "workout_plan_updated", user, "workout_plan", row.id)
    return row


@app.delete("/api/workout-plans/{plan_id}", status_code=204)
def remove_workout_plan(plan_id: int, user: ADMIN, db: DB, request: Request):
    row = db.get(WorkoutPlan, plan_id)
    if not row:
        raise HTTPException(404, "Workout plan not found")
    assigned_work = db.exec(
        select(WorkoutAssignment).where(WorkoutAssignment.plan_id == plan_id)
    ).first()
    if assigned_work:
        raise HTTPException(409, "This workout plan has member assignments. Remove those assignments first.")
    db.delete(row)
    db.commit()
    audit(db, request, "workout_plan_deleted", user, "workout_plan", plan_id)
    return Response(status_code=204)


@app.get("/api/workout-assignments")
def workout_assignments(user: CURRENT, db: DB):
    query = select(WorkoutAssignment).order_by(WorkoutAssignment.created_at.desc())
    if user.role != "admin": query = query.where(WorkoutAssignment.member_id == get_my_member(db, user).id)
    return db.exec(query).all()


@app.post("/api/workout-assignments", status_code=201)
def create_workout_assignment(data: AssignmentBody, user: ADMIN, db: DB, request: Request):
    if not db.get(WorkoutPlan, data.plan_id) or not db.get(Member, data.member_id):
        raise HTTPException(404, "Plan or member not found")
    if data.trainer_id and not db.get(Trainer, data.trainer_id): raise HTTPException(404, "Trainer not found")
    duplicate_query = select(WorkoutAssignment).where(
        WorkoutAssignment.member_id == data.member_id,
        WorkoutAssignment.plan_id == data.plan_id,
        WorkoutAssignment.status == data.status,
    )
    if data.trainer_id is None:
        duplicate_query = duplicate_query.where(WorkoutAssignment.trainer_id.is_(None))
    else:
        duplicate_query = duplicate_query.where(WorkoutAssignment.trainer_id == data.trainer_id)
    if db.exec(duplicate_query).first():
        raise HTTPException(409, "This workout plan is already assigned to this member and trainer.")
    row = WorkoutAssignment(**data.model_dump(), assigned_by=user.id)
    db.add(row); db.commit(); db.refresh(row)
    audit(db, request, "workout_assigned", user, "workout_assignment", row.id)
    return row


@app.delete("/api/workout-assignments/{assignment_id}", status_code=204)
def remove_workout_assignment(assignment_id: int, user: ADMIN, db: DB, request: Request):
    row = db.get(WorkoutAssignment, assignment_id)
    if not row: raise HTTPException(404, "Assignment not found")
    db.delete(row); db.commit(); audit(db, request, "workout_assignment_deleted", user, "workout_assignment", assignment_id)
    return Response(status_code=204)


# Shared groups with server-side create/edit/assign checks. Only owners manage membership and delete.
@app.get("/api/groups")
def list_groups(user: CURRENT, db: DB):
    ids = select(GymGroupMember.group_id).where(GymGroupMember.user_id == user.id)
    rows = db.exec(select(GymGroup).where(GymGroup.id.in_(ids))).all()
    return [{"id": g.id, "name": g.name, "created_by": g.created_by,
             "my_role": get_group_member(db, g.id, user.id).role} for g in rows]


@app.post("/api/groups", status_code=201)
def create_group(data: GroupBody, user: CURRENT, db: DB, request: Request):
    row = GymGroup(name=data.name, created_by=user.id)
    db.add(row); db.commit(); db.refresh(row)
    db.add(GymGroupMember(group_id=row.id, user_id=user.id, role="owner", can_create=True, can_edit=True, can_assign=True))
    db.commit(); audit(db, request, "group_created", user, "group", row.id)
    return {"id": row.id, "name": row.name, "my_role": "owner"}


@app.patch("/api/groups/{group_id}")
def rename_group(group_id: int, data: GroupBody, user: CURRENT, db: DB, request: Request):
    membership = get_group_member(db, group_id, user.id)
    if membership.role != "owner":
        raise HTTPException(403, "Only the group owner can rename this group")
    group = db.get(GymGroup, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    group.name = data.name.strip()
    db.add(group)
    db.commit()
    audit(db, request, "group_renamed", user, "group", group_id, group.name)
    return {"id": group.id, "name": group.name, "my_role": membership.role}


@app.delete("/api/groups/{group_id}", status_code=204)
def delete_group(group_id: int, user: CURRENT, db: DB, request: Request):
    membership = get_group_member(db, group_id, user.id)
    if membership.role != "owner":
        raise HTTPException(403, "Only the group owner can delete this group")
    group = db.get(GymGroup, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    for task in db.exec(select(GymGroupTask).where(GymGroupTask.group_id == group_id)).all():
        db.delete(task)
    for group_member in db.exec(select(GymGroupMember).where(GymGroupMember.group_id == group_id)).all():
        db.delete(group_member)
    db.delete(group)
    db.commit()
    audit(db, request, "group_deleted", user, "group", group_id, group.name)
    return Response(status_code=204)


@app.get("/api/groups/{group_id}/members")
def group_members(group_id: int, user: CURRENT, db: DB):
    get_group_member(db, group_id, user.id)
    rows = db.exec(select(GymGroupMember, AppUser).join(AppUser, AppUser.id == GymGroupMember.user_id)
                   .where(GymGroupMember.group_id == group_id)).all()
    return [{"user_id": m.user_id, "full_name": u.full_name, "email": u.email, "role": m.role,
             "can_create": m.can_create, "can_edit": m.can_edit, "can_assign": m.can_assign} for m, u in rows]


@app.post("/api/groups/{group_id}/members", status_code=201)
def add_group_member(group_id: int, data: GroupMemberBody, user: CURRENT, db: DB, request: Request):
    owner = get_group_member(db, group_id, user.id)
    if owner.role != "owner": raise HTTPException(403, "Only the group owner can add members")
    target = db.exec(select(AppUser).where(AppUser.email == str(data.email).lower())).first()
    if not target: raise HTTPException(404, "No GymTrack account exists for this email")
    if db.get(GymGroupMember, (group_id, target.id)): raise HTTPException(409, "Already a group member")
    row = GymGroupMember(group_id=group_id, user_id=target.id, role="member",
                         can_create=data.can_create, can_edit=data.can_edit, can_assign=data.can_assign)
    db.add(row); db.commit(); audit(db, request, "group_member_added", user, "group", group_id, target.email)
    return {"user_id": target.id, "full_name": target.full_name, "email": target.email, "role": "member",
            "can_create": row.can_create, "can_edit": row.can_edit, "can_assign": row.can_assign}


@app.patch("/api/groups/{group_id}/members/{target_id}")
def group_permissions(group_id: int, target_id: int, data: GroupPermissions,
                      user: CURRENT, db: DB, request: Request):
    owner = get_group_member(db, group_id, user.id)
    if owner.role != "owner": raise HTTPException(403, "Only the group owner manages permissions")
    target = get_group_member(db, group_id, target_id)
    if target.role == "owner": raise HTTPException(400, "Owner permissions cannot be changed")
    for key, value in data.model_dump().items(): setattr(target, key, value)
    db.add(target); db.commit(); audit(db, request, "group_permissions_changed", user, "group", group_id)
    return {"user_id": target_id, **data.model_dump()}


@app.delete("/api/groups/{group_id}/members/{target_id}", status_code=204)
def remove_group_member(group_id: int, target_id: int, user: CURRENT, db: DB, request: Request):
    actor = get_group_member(db, group_id, user.id)
    target = get_group_member(db, group_id, target_id)
    if actor.role != "owner" and target_id != user.id: raise HTTPException(403, "Only owner can remove others")
    if target.role == "owner": raise HTTPException(400, "Owner cannot leave; delete the group instead")
    db.delete(target); db.commit(); audit(db, request, "group_member_removed", user, "group", group_id, str(target_id))
    return Response(status_code=204)


@app.get("/api/groups/{group_id}/work")
def list_group_work(group_id: int, user: CURRENT, db: DB):
    get_group_member(db, group_id, user.id)
    return db.exec(select(GymGroupTask).where(GymGroupTask.group_id == group_id)
                   .order_by(GymGroupTask.created_at.desc())).all()


@app.post("/api/groups/{group_id}/work", status_code=201)
def create_group_work(group_id: int, data: GroupWorkBody, user: CURRENT, db: DB, request: Request):
    member = get_group_member(db, group_id, user.id); group_allow(member, "create")
    if data.assigned_to is not None:
        group_allow(member, "assign")
        if not db.get(GymGroupMember, (group_id, data.assigned_to)): raise HTTPException(422, "Assignee is not a group member")
    row = GymGroupTask(**data.model_dump(), group_id=group_id, created_by=user.id)
    db.add(row); db.commit(); db.refresh(row); audit(db, request, "group_work_created", user, "group_work", row.id)
    return row


@app.patch("/api/groups/{group_id}/work/{work_id}")
def edit_group_work(group_id: int, work_id: int, data: GroupWorkPatch,
                    user: CURRENT, db: DB, request: Request):
    member = get_group_member(db, group_id, user.id)
    row = db.get(GymGroupTask, work_id)
    if not row or row.group_id != group_id: raise HTTPException(404, "Group work not found")
    changes = data.model_dump(exclude_unset=True)
    if "assigned_to" in changes:
        group_allow(member, "assign")
        if changes["assigned_to"] is not None and not db.get(GymGroupMember, (group_id, changes["assigned_to"])):
            raise HTTPException(422, "Assignee is not a group member")
    if member.role != "owner" and row.created_by != user.id: group_allow(member, "edit")
    for key, value in changes.items(): setattr(row, key, value)
    row.updated_at = now(); db.add(row); db.commit()
    audit(db, request, "group_work_updated", user, "group_work", row.id)
    return row


@app.delete("/api/groups/{group_id}/work/{work_id}", status_code=204)
def delete_group_work(group_id: int, work_id: int, user: CURRENT, db: DB, request: Request):
    member = get_group_member(db, group_id, user.id)
    if member.role != "owner": raise HTTPException(403, "Only owner can delete group work")
    row = db.get(GymGroupTask, work_id)
    if not row or row.group_id != group_id: raise HTTPException(404, "Group work not found")
    db.delete(row); db.commit(); audit(db, request, "group_work_deleted", user, "group_work", work_id)
    return Response(status_code=204)


# Admin overview, user management, activity/security views and CSV export.
@app.get("/api/admin/stats")
def admin_stats(user: ADMIN, db: DB):
    week = now() - timedelta(days=7)
    today = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
    count = lambda model, *conditions: len(db.exec(select(model).where(*conditions)).all()) if conditions else len(db.exec(select(model)).all())
    return {
        "users": count(AppUser), "admins": count(AppUser, AppUser.role == "admin"),
        "banned_users": count(AppUser, AppUser.is_banned.is_(True)),
        "new_users_7d": count(AppUser, AppUser.created_at >= week),
        "members": count(Member), "active_members": count(Member, Member.is_active.is_(True)),
        "trainers": count(Trainer), "memberships": count(Membership),
        "attendance_today": count(Attendance, Attendance.check_in >= today),
        "workout_plans": count(WorkoutPlan), "groups": count(GymGroup),
    }


@app.get("/api/admin/users")
def admin_users(user: ADMIN, db: DB, q: str = "", role: str = "", status: str = "",
                offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    query = select(AppUser).order_by(AppUser.created_at.desc())
    if q: query = query.where(AppUser.full_name.ilike(f"%{q}%") | AppUser.email.ilike(f"%{q}%"))
    if role in {"admin", "user"}: query = query.where(AppUser.role == role)
    if status == "banned": query = query.where(AppUser.is_banned.is_(True))
    if status == "active": query = query.where(AppUser.is_banned.is_(False))
    rows = db.exec(query.offset(offset).limit(limit)).all()
    return [public_user(row) for row in rows]


@app.patch("/api/admin/users/{target_id}/role")
def change_role(target_id: int, data: dict, user: ADMIN, db: DB, request: Request):
    if target_id == user.id: raise HTTPException(400, "You cannot change your own role")
    role = data.get("role")
    if role not in {"user", "admin"}: raise HTTPException(422, "Role must be user or admin")
    target = db.get(AppUser, target_id)
    if not target: raise HTTPException(404, "User not found")
    target.role = role; target.updated_at = now(); db.add(target); db.commit()
    audit(db, request, "role_changed", user, "user", target_id, f"{target.email} -> {role}")
    return public_user(target)


@app.post("/api/admin/users/{target_id}/ban")
def ban_user(target_id: int, data: dict, user: ADMIN, db: DB, request: Request):
    if target_id == user.id: raise HTTPException(400, "You cannot ban yourself")
    target = db.get(AppUser, target_id)
    if not target: raise HTTPException(404, "User not found")
    if target.role == "admin": raise HTTPException(400, "You cannot ban another admin")
    target.is_banned = True; db.add(target)
    for s in db.exec(select(AuthSession).where(AuthSession.user_id == target_id, AuthSession.revoked_at.is_(None))).all():
        s.revoked_at = now(); db.add(s)
    db.commit(); audit(db, request, "user_banned", user, "user", target_id, str(data.get("reason", ""))[:200])
    return public_user(target)


@app.post("/api/admin/users/{target_id}/unban")
def unban_user(target_id: int, user: ADMIN, db: DB, request: Request):
    target = db.get(AppUser, target_id)
    if not target: raise HTTPException(404, "User not found")
    target.is_banned = False; db.add(target); db.commit()
    audit(db, request, "user_unbanned", user, "user", target_id)
    return public_user(target)


@app.post("/api/admin/users/{target_id}/revoke-sessions", status_code=204)
def admin_revoke_sessions(target_id: int, user: ADMIN, db: DB, request: Request):
    target = db.get(AppUser, target_id)
    if not target: raise HTTPException(404, "User not found")
    for s in db.exec(select(AuthSession).where(AuthSession.user_id == target_id, AuthSession.revoked_at.is_(None))).all():
        s.revoked_at = now(); db.add(s)
    db.commit(); audit(db, request, "admin_sessions_revoked", user, "user", target_id)
    return Response(status_code=204)


@app.get("/api/admin/activity")
def admin_activity(user: ADMIN, db: DB, q: str = "", offset: int = Query(0, ge=0),
                   limit: int = Query(50, ge=1, le=200)):
    query = select(ActivityLog).order_by(ActivityLog.created_at.desc())
    if q: query = query.where(ActivityLog.action.ilike(f"%{q}%") | ActivityLog.email.ilike(f"%{q}%"))
    return db.exec(query.offset(offset).limit(limit)).all()


@app.get("/api/admin/security")
def admin_security(user: ADMIN, db: DB):
    start = now() - timedelta(hours=24)
    rows = db.exec(select(ActivityLog).where(ActivityLog.created_at >= start,
        ActivityLog.action.in_(["login_failed", "login_locked", "login_blocked"]))
        .order_by(ActivityLog.created_at.desc()).limit(200)).all()
    return {"failed_logins_24h": len(rows), "events": rows}


@app.get("/api/admin/export/users")
def export_users(user: ADMIN, db: DB):
    rows = db.exec(select(AppUser).order_by(AppUser.id)).all()
    return csv_response("gymtrack-users.csv", ["id", "full_name", "email", "role", "is_banned", "created_at"],
        [[u.id, u.full_name, u.email, u.role, u.is_banned, u.created_at.isoformat()] for u in rows])


@app.get("/api/admin/export/members")
def export_members(user: ADMIN, db: DB):
    rows = db.exec(select(Member).order_by(Member.id)).all()
    return csv_response("gymtrack-members.csv", ["id", "full_name", "email", "phone", "join_date", "is_active"],
        [[m.id, m.full_name, m.email, m.phone, m.join_date, m.is_active] for m in rows])


@app.get("/api/admin/export/activity")
def export_activity(user: ADMIN, db: DB):
    rows = db.exec(select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(10000)).all()
    return csv_response("gymtrack-activity.csv",
        ["id", "email", "action", "entity_type", "entity_id", "ip_address", "user_agent", "created_at"],
        [[a.id, a.email, a.action, a.entity_type, a.entity_id, a.ip_address, a.user_agent, a.created_at] for a in rows])


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
