import csv, hashlib, hmac, io, os, secrets, uuid
from datetime import date, datetime, timedelta, timezone
from typing import Literal

import jwt
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field as PField
from sqlmodel import Field, Session, SQLModel, select

try:
    from backend.database import engine
    from backend.models.member import Member
    from backend.models.trainer import Trainer
    from backend.models.workout import WorkoutAssignment, WorkoutPlan
    from backend.models.trainer_progress import WorkoutProgress
    from backend.models.user import AppUser
    from backend.models.activity import ActivityLog
    from backend.schemas.trainer import RoleChangeBody
    from backend.schemas.admin import BulkUserAction, BulkContentDelete
    from backend.core.audit import audit, client_ip
    from backend.core.dependencies import ADMIN, CURRENT, DB, TRAINER
except ModuleNotFoundError:
    from database import engine
    from models.member import Member
    from models.trainer import Trainer
    from models.workout import WorkoutAssignment, WorkoutPlan
    from models.trainer_progress import WorkoutProgress
    from models.user import AppUser
    from models.activity import ActivityLog
    from schemas.trainer import RoleChangeBody
    from schemas.admin import BulkUserAction, BulkContentDelete
    from core.audit import audit, client_ip
    from core.dependencies import ADMIN, CURRENT, DB, TRAINER




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
def now():
    return datetime.now(timezone.utc)

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
    if user.role not in {"user", "trainer"}:
        raise HTTPException(403, "Member dashboard is only available to member and trainer accounts")
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
    if user.role not in {"user", "trainer"}:
        raise HTTPException(403, "Attendance requests are for member and trainer accounts.")
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
def create_group(data: GroupBody, user: ADMIN, db: DB, request: Request):
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
    query = select(AppUser)
    if q:
        query = query.where(AppUser.full_name.ilike(f"%{q}%") | AppUser.email.ilike(f"%{q}%"))
    if role in {"admin", "user", "trainer"}:
        query = query.where(AppUser.role == role)
    if status == "banned":
        query = query.where(AppUser.is_banned.is_(True))
    if status == "active":
        query = query.where(AppUser.is_banned.is_(False))

    from sqlalchemy import func
    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    rows = db.exec(query.order_by(AppUser.created_at.desc()).offset(offset).limit(limit)).all()
    return {
        "items": [public_user(row) for row in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@app.get("/api/admin/users/{target_id}")
def admin_user_detail(target_id: int, user: ADMIN, db: DB):
    target = db.get(AppUser, target_id)
    if target is None:
        raise HTTPException(404, "User not found")

    member = db.exec(select(Member).where(Member.user_id == target_id)).first()
    trainer = db.exec(select(Trainer).where(Trainer.email == target.email)).first()

    memberships = []
    attendance = []
    workouts = []
    if member is not None:
        memberships = db.exec(
            select(Membership)
            .where(Membership.member_id == member.id)
            .order_by(Membership.created_at.desc())
        ).all()
        attendance = db.exec(
            select(Attendance)
            .where(Attendance.member_id == member.id)
            .order_by(Attendance.check_in.desc())
            .limit(100)
        ).all()
        assignment_rows = db.exec(
            select(WorkoutAssignment, WorkoutPlan)
            .join(WorkoutPlan, WorkoutPlan.id == WorkoutAssignment.plan_id)
            .where(WorkoutAssignment.member_id == member.id)
            .order_by(WorkoutAssignment.created_at.desc())
        ).all()
        workouts = [
            {"assignment": assignment, "plan": plan}
            for assignment, plan in assignment_rows
        ]

    group_rows = db.exec(
        select(GymGroupMember, GymGroup)
        .join(GymGroup, GymGroup.id == GymGroupMember.group_id)
        .where(GymGroupMember.user_id == target_id)
    ).all()
    session_rows = db.exec(
        select(AuthSession)
        .where(AuthSession.user_id == target_id)
        .order_by(AuthSession.last_used_at.desc())
        .limit(50)
    ).all()
    activity_rows = db.exec(
        select(ActivityLog)
        .where(ActivityLog.user_id == target_id)
        .order_by(ActivityLog.created_at.desc())
        .limit(50)
    ).all()

    return {
        "user": public_user(target),
        "member": member,
        "trainer": trainer,
        "memberships": memberships,
        "attendance": attendance,
        "workouts": workouts,
        "groups": [
            {
                "group": group,
                "membership": {
                    "role": membership.role,
                    "can_create": membership.can_create,
                    "can_edit": membership.can_edit,
                    "can_assign": membership.can_assign,
                    "joined_at": membership.joined_at,
                },
            }
            for membership, group in group_rows
        ],
        "sessions": [
            {
                "id": session.id,
                "created_at": session.created_at,
                "last_used_at": session.last_used_at,
                "expires_at": session.expires_at,
                "revoked_at": session.revoked_at,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "is_active": session.revoked_at is None and session.expires_at > now(),
            }
            for session in session_rows
        ],
        "recent_activity": activity_rows,
    }


@app.patch("/api/admin/users/{target_id}/role")
def change_role(target_id: int, data: RoleChangeBody, user: ADMIN, db: DB, request: Request):
    if target_id == user.id:
        raise HTTPException(400, "You cannot change your own role")
    target = db.get(AppUser, target_id)
    if not target:
        raise HTTPException(404, "User not found")

    previous_role = target.role
    if data.role == "trainer":
        from backend.services.trainer_service import ensure_trainer_profile
        ensure_trainer_profile(db, target)
    elif previous_role == "trainer":
        from backend.services.trainer_service import deactivate_trainer_profile
        deactivate_trainer_profile(db, target.email)

    target.role = data.role
    target.updated_at = now()
    db.add(target)
    db.commit()
    audit(db, request, "role_changed", user, "user", target_id, f"{target.email} -> {data.role}")
    return public_user(target)


@app.post("/api/admin/users/bulk-ban")
def bulk_ban_users(data: BulkUserAction, user: ADMIN, db: DB, request: Request):
    user_ids = list(dict.fromkeys(data.user_ids))
    if user.id in user_ids:
        raise HTTPException(400, "You cannot ban your own account")
    targets = db.exec(select(AppUser).where(AppUser.id.in_(user_ids))).all()
    if len(targets) != len(user_ids):
        raise HTTPException(404, "One or more users were not found")
    if any(target.role == "admin" for target in targets):
        raise HTTPException(400, "Bulk ban cannot include administrator accounts")

    for target in targets:
        target.is_banned = True
        db.add(target)
        for session in db.exec(
            select(AuthSession).where(
                AuthSession.user_id == target.id,
                AuthSession.revoked_at.is_(None),
            )
        ).all():
            session.revoked_at = now()
            db.add(session)
    db.commit()

    for target in targets:
        audit(db, request, "user_banned", user, "user", target.id, data.reason[:200])
    return {"count": len(targets), "users": [public_user(target) for target in targets]}


@app.post("/api/admin/users/bulk-unban")
def bulk_unban_users(data: BulkUserAction, user: ADMIN, db: DB, request: Request):
    user_ids = list(dict.fromkeys(data.user_ids))
    targets = db.exec(select(AppUser).where(AppUser.id.in_(user_ids))).all()
    if len(targets) != len(user_ids):
        raise HTTPException(404, "One or more users were not found")

    for target in targets:
        target.is_banned = False
        db.add(target)
    db.commit()

    for target in targets:
        audit(db, request, "user_unbanned", user, "user", target.id)
    return {"count": len(targets), "users": [public_user(target) for target in targets]}


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

    by_ip: dict[str, int] = {}
    by_account: dict[str, int] = {}
    for event in rows:
        ip = event.ip_address or "Unknown IP"
        account = event.email or "Unknown account"
        by_ip[ip] = by_ip.get(ip, 0) + 1
        by_account[account] = by_account.get(account, 0) + 1

    return {
        "failed_logins_24h": len(rows),
        "events": rows,
        "by_ip": [
            {"ip_address": ip, "count": count}
            for ip, count in sorted(by_ip.items(), key=lambda item: item[1], reverse=True)
        ],
        "by_account": [
            {"email": email, "count": count}
            for email, count in sorted(by_account.items(), key=lambda item: item[1], reverse=True)
        ],
    }


def _admin_content_query(db: Session, content_type: str, q: str):
    from sqlalchemy import func

    if content_type == "memberships":
        statement = select(Membership)
        if q:
            statement = statement.where(Membership.plan_name.ilike(f"%{q}%"))
        total = db.exec(select(func.count()).select_from(statement.subquery())).one()
        rows = db.exec(statement.order_by(Membership.created_at.desc()).limit(10000)).all()
        items = [
            {"id": row.id, "label": row.plan_name, "details": f"Member #{row.member_id} · {row.status}",
             "created_at": row.created_at}
            for row in rows
        ]
    elif content_type == "attendance":
        statement = select(Attendance)
        if q and q.isdigit():
            statement = statement.where(
                (Attendance.member_id == int(q)) | (Attendance.id == int(q))
            )
        total = db.exec(select(func.count()).select_from(statement.subquery())).one()
        rows = db.exec(statement.order_by(Attendance.check_in.desc()).limit(10000)).all()
        items = [
            {"id": row.id, "label": f"Attendance #{row.id}",
             "details": f"Member #{row.member_id} · {row.check_in} · "
                        f"{'Checked out' if row.check_out else 'Currently checked in'}",
             "created_at": row.check_in}
            for row in rows
        ]
    elif content_type == "workout_plans":
        statement = select(WorkoutPlan)
        if q:
            statement = statement.where(
                WorkoutPlan.title.ilike(f"%{q}%") | WorkoutPlan.description.ilike(f"%{q}%")
            )
        total = db.exec(select(func.count()).select_from(statement.subquery())).one()
        rows = db.exec(statement.order_by(WorkoutPlan.created_at.desc()).limit(10000)).all()
        items = [
            {"id": row.id, "label": row.title,
             "details": f"{row.level} · {row.duration_weeks} weeks", "created_at": row.created_at}
            for row in rows
        ]
    elif content_type == "assignments":
        statement = (
            select(WorkoutAssignment, WorkoutPlan, Member)
            .join(WorkoutPlan, WorkoutPlan.id == WorkoutAssignment.plan_id)
            .join(Member, Member.id == WorkoutAssignment.member_id)
        )
        if q:
            statement = statement.where(
                WorkoutPlan.title.ilike(f"%{q}%")
                | Member.full_name.ilike(f"%{q}%")
                | Member.email.ilike(f"%{q}%")
            )
        total = db.exec(select(func.count()).select_from(statement.subquery())).one()
        rows = db.exec(
            statement.order_by(WorkoutAssignment.created_at.desc()).limit(10000)
        ).all()
        items = [
            {"id": assignment.id, "label": f"{plan.title} → {member.full_name}",
             "details": f"{assignment.status} · Trainer #{assignment.trainer_id or 'unassigned'}",
             "created_at": assignment.created_at}
            for assignment, plan, member in rows
        ]
    elif content_type == "groups":
        statement = select(GymGroup)
        if q:
            statement = statement.where(GymGroup.name.ilike(f"%{q}%"))
        total = db.exec(select(func.count()).select_from(statement.subquery())).one()
        rows = db.exec(statement.order_by(GymGroup.created_at.desc()).limit(10000)).all()
        items = [
            {"id": row.id, "label": row.name,
             "details": f"Owner account #{row.created_by}", "created_at": row.created_at}
            for row in rows
        ]
    elif content_type == "trainer_progress":
        statement = select(WorkoutProgress)
        if q:
            statement = statement.where(WorkoutProgress.notes.ilike(f"%{q}%"))
        total = db.exec(select(func.count()).select_from(statement.subquery())).one()
        rows = db.exec(
            statement.order_by(WorkoutProgress.created_at.desc()).limit(10000)
        ).all()
        items = [
            {"id": row.id, "label": f"Progress #{row.id}",
             "details": f"Assignment #{row.assignment_id} · Member #{row.member_id} · Trainer #{row.trainer_id} · {row.completion_percent}% complete",
             "created_at": row.created_at}
            for row in rows
        ]
    else:
        raise HTTPException(422, "Unsupported content type")
    return items, total


def _delete_admin_content_record(db: Session, content_type: str, record_id: int) -> None:
    if content_type == "memberships":
        row = db.get(Membership, record_id)
        if row is None:
            raise HTTPException(404, "Membership record not found")
        db.delete(row)
    elif content_type == "attendance":
        row = db.get(Attendance, record_id)
        if row is None:
            raise HTTPException(404, "Attendance record not found")
        db.delete(row)
    elif content_type == "trainer_progress":
        row = db.get(WorkoutProgress, record_id)
        if row is None:
            raise HTTPException(404, "Progress record not found")
        db.delete(row)
    elif content_type == "assignments":
        row = db.get(WorkoutAssignment, record_id)
        if row is None:
            raise HTTPException(404, "Workout assignment not found")
        for progress in db.exec(
            select(WorkoutProgress).where(WorkoutProgress.assignment_id == record_id)
        ).all():
            db.delete(progress)
        db.delete(row)
    elif content_type == "workout_plans":
        row = db.get(WorkoutPlan, record_id)
        if row is None:
            raise HTTPException(404, "Workout plan not found")
        assignments = db.exec(
            select(WorkoutAssignment).where(WorkoutAssignment.plan_id == record_id)
        ).all()
        for assignment in assignments:
            for progress in db.exec(
                select(WorkoutProgress).where(WorkoutProgress.assignment_id == assignment.id)
            ).all():
                db.delete(progress)
            db.delete(assignment)
        db.delete(row)
    elif content_type == "groups":
        row = db.get(GymGroup, record_id)
        if row is None:
            raise HTTPException(404, "Group not found")
        for task in db.exec(
            select(GymGroupTask).where(GymGroupTask.group_id == record_id)
        ).all():
            db.delete(task)
        for membership in db.exec(
            select(GymGroupMember).where(GymGroupMember.group_id == record_id)
        ).all():
            db.delete(membership)
        db.delete(row)
    else:
        raise HTTPException(422, "Unsupported content type")


@app.get("/api/admin/content")
def admin_content(
    user: ADMIN,
    db: DB,
    content_type: Literal["memberships", "attendance", "workout_plans", "assignments", "groups", "trainer_progress"] = Query("memberships", alias="type"),
    q: str = "",
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    items, total = _admin_content_query(db, content_type, q)
    return {
        "items": items[offset:offset + limit],
        "total": total,
        "offset": offset,
        "limit": limit,
        "type": content_type,
    }


@app.delete("/api/admin/content/{content_type}/{record_id}", status_code=204)
def delete_admin_content(
    content_type: Literal["memberships", "attendance", "workout_plans", "assignments", "groups", "trainer_progress"],
    record_id: int,
    user: ADMIN,
    db: DB,
    request: Request,
):
    _delete_admin_content_record(db, content_type, record_id)
    db.commit()
    audit(db, request, "content_deleted", user, content_type, record_id)
    return Response(status_code=204)


@app.post("/api/admin/content/{content_type}/bulk-delete")
def bulk_delete_admin_content(
    content_type: Literal["memberships", "attendance", "workout_plans", "assignments", "groups", "trainer_progress"],
    data: BulkContentDelete,
    user: ADMIN,
    db: DB,
    request: Request,
):
    record_ids = list(dict.fromkeys(data.ids))
    try:
        for record_id in record_ids:
            _delete_admin_content_record(db, content_type, record_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    for record_id in record_ids:
        audit(db, request, "content_deleted", user, content_type, record_id, "Bulk moderation")
    return {"count": len(record_ids), "deleted_ids": record_ids}


@app.get("/api/admin/export/users")
def export_users(user: ADMIN, db: DB, request: Request, q: str = "", role: str = "", status: str = ""):
    query = select(AppUser)
    if q:
        query = query.where(AppUser.full_name.ilike(f"%{q}%") | AppUser.email.ilike(f"%{q}%"))
    if role in {"admin", "user", "trainer"}:
        query = query.where(AppUser.role == role)
    if status == "banned":
        query = query.where(AppUser.is_banned.is_(True))
    if status == "active":
        query = query.where(AppUser.is_banned.is_(False))
    rows = db.exec(query.order_by(AppUser.id)).all()
    audit(db, request, "data_exported", user, "export", "users")
    return csv_response("gymtrack-users.csv", ["id", "full_name", "email", "role", "is_banned", "created_at"],
        [[u.id, u.full_name, u.email, u.role, u.is_banned, u.created_at.isoformat()] for u in rows])


@app.get("/api/admin/export/members")
def export_members(user: ADMIN, db: DB, request: Request, q: str = "", status: str = ""):
    query = select(Member)
    if q:
        query = query.where(Member.full_name.ilike(f"%{q}%") | Member.email.ilike(f"%{q}%"))
    if status == "active":
        query = query.where(Member.is_active.is_(True))
    if status == "inactive":
        query = query.where(Member.is_active.is_(False))
    rows = db.exec(query.order_by(Member.id)).all()
    audit(db, request, "data_exported", user, "export", "members")
    return csv_response("gymtrack-members.csv", ["id", "full_name", "email", "phone", "join_date", "is_active"],
        [[m.id, m.full_name, m.email, m.phone, m.join_date, m.is_active] for m in rows])


@app.get("/api/admin/export/activity")
def export_activity(user: ADMIN, db: DB, request: Request, q: str = ""):
    query = select(ActivityLog)
    if q:
        query = query.where(
            ActivityLog.action.ilike(f"%{q}%") | ActivityLog.email.ilike(f"%{q}%")
        )
    rows = db.exec(query.order_by(ActivityLog.created_at.desc()).limit(10000)).all()
    audit(db, request, "data_exported", user, "export", "activity")
    return csv_response("gymtrack-activity.csv",
        ["id", "email", "action", "entity_type", "entity_id", "ip_address", "user_agent", "created_at"],
        [[a.id, a.email, a.action, a.entity_type, a.entity_id, a.ip_address, a.user_agent, a.created_at] for a in rows])


@app.get("/api/admin/export/trainers")
def export_trainers(user: ADMIN, db: DB, request: Request):
    rows = db.exec(select(Trainer).order_by(Trainer.full_name)).all()
    audit(db, request, "data_exported", user, "export", "trainers")
    return csv_response("gymtrack-trainers.csv",
        ["id", "full_name", "email", "phone", "specialization", "is_active"],
        [[t.id, t.full_name, t.email, t.phone, t.specialization, t.is_active] for t in rows])


@app.get("/api/admin/export/memberships")
def export_memberships(user: ADMIN, db: DB, request: Request):
    rows = db.exec(select(Membership).order_by(Membership.created_at.desc())).all()
    audit(db, request, "data_exported", user, "export", "memberships")
    return csv_response("gymtrack-memberships.csv",
        ["id", "member_id", "plan_name", "start_date", "end_date", "price", "status"],
        [[m.id, m.member_id, m.plan_name, m.start_date, m.end_date, m.price, m.status] for m in rows])


@app.get("/api/admin/export/attendance")
def export_attendance(user: ADMIN, db: DB, request: Request):
    rows = db.exec(select(Attendance).order_by(Attendance.check_in.desc()).limit(50000)).all()
    audit(db, request, "data_exported", user, "export", "attendance")
    return csv_response("gymtrack-attendance.csv",
        ["id", "member_id", "check_in", "check_out", "notes", "recorded_by"],
        [[a.id, a.member_id, a.check_in, a.check_out, a.notes, a.recorded_by] for a in rows])


@app.get("/api/admin/export/workouts")
def export_workouts(user: ADMIN, db: DB, request: Request):
    rows = db.exec(select(WorkoutPlan).order_by(WorkoutPlan.created_at.desc())).all()
    audit(db, request, "data_exported", user, "export", "workout_plans")
    return csv_response("gymtrack-workout-plans.csv",
        ["id", "title", "description", "level", "duration_weeks", "created_by"],
        [[p.id, p.title, p.description, p.level, p.duration_weeks, p.created_by] for p in rows])


@app.get("/api/admin/export/assignments")
def export_workout_assignments(user: ADMIN, db: DB, request: Request):
    rows = db.exec(select(WorkoutAssignment).order_by(WorkoutAssignment.created_at.desc())).all()
    audit(db, request, "data_exported", user, "export", "workout_assignments")
    return csv_response("gymtrack-workout-assignments.csv",
        ["id", "plan_id", "member_id", "trainer_id", "start_date", "end_date", "status"],
        [[a.id, a.plan_id, a.member_id, a.trainer_id, a.start_date, a.end_date, a.status] for a in rows])


@app.get("/api/admin/export/groups")
def export_groups(user: ADMIN, db: DB, request: Request):
    rows = db.exec(select(GymGroup).order_by(GymGroup.created_at.desc())).all()
    audit(db, request, "data_exported", user, "export", "groups")
    return csv_response("gymtrack-groups.csv", ["id", "name", "created_by", "created_at"],
        [[g.id, g.name, g.created_by, g.created_at] for g in rows])


@app.on_event("startup")
def startup():
    if os.getenv("VERCEL") == "1" and (not JWT_SECRET or not PEPPER):
        raise RuntimeError("JWT_SECRET_KEY and PASSWORD_PEPPER must be set in Vercel.")
    # In local SQLite only, create tables for models. Supabase uses explicit migrations.
    if os.getenv("VERCEL") != "1":
        SQLModel.metadata.create_all(engine)


try:
    from backend.routers.trainers import router as trainers_router
except ModuleNotFoundError:
    from routers.trainers import router as trainers_router

app.include_router(trainers_router)


@app.get("/")
def root():
    return {"message": "GymTrack API is running", "docs": "/api/docs"}
