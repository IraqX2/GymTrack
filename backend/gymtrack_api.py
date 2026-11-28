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
    from backend.models.resources import (
        AuthSession, Membership, Attendance, AttendanceRequest,
        GymGroup, GymGroupMember, GymGroupTask,
    )
    from backend.schemas.trainer import RoleChangeBody
    from backend.schemas.admin import BulkUserAction, BulkContentDelete
    from backend.schemas.resources import (
        Signup, Login, ProfilePatch, PasswordPatch, MemberBody,
        MembershipBody, AttendanceBody, AttendanceRequestBody,
        AttendanceRequestReview, PlanBody, AssignmentBody, GroupBody,
        GroupMemberBody, GroupPermissions, GroupWorkBody, GroupWorkPatch,
    )
    from backend.core.audit import audit, client_ip
    from backend.core.dependencies import ADMIN, CURRENT, DB, TRAINER
    from backend.services.auth_service import hash_password, check_password, public_user
    from backend.routers.auth import router as auth_router
    from backend.routers.admin import router as admin_router
except ModuleNotFoundError:
    from database import engine
    from models.member import Member
    from models.trainer import Trainer
    from models.workout import WorkoutAssignment, WorkoutPlan
    from models.trainer_progress import WorkoutProgress
    from models.user import AppUser
    from models.activity import ActivityLog
    from models.resources import (
        AuthSession, Membership, Attendance, AttendanceRequest,
        GymGroup, GymGroupMember, GymGroupTask,
    )
    from schemas.trainer import RoleChangeBody
    from schemas.admin import BulkUserAction, BulkContentDelete
    from schemas.resources import (
        Signup, Login, ProfilePatch, PasswordPatch, MemberBody,
        MembershipBody, AttendanceBody, AttendanceRequestBody,
        AttendanceRequestReview, PlanBody, AssignmentBody, GroupBody,
        GroupMemberBody, GroupPermissions, GroupWorkBody, GroupWorkPatch,
    )
    from core.audit import audit, client_ip
    from core.dependencies import ADMIN, CURRENT, DB, TRAINER
    from services.auth_service import hash_password, check_password, public_user
    from routers.auth import router as auth_router
    from routers.admin import router as admin_router




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


@app.on_event("startup")
def startup():
    if os.getenv("VERCEL") == "1" and (not JWT_SECRET or not PEPPER):
        raise RuntimeError("JWT_SECRET_KEY and PASSWORD_PEPPER must be set in Vercel.")
    # In local SQLite only, create tables for models. Supabase uses explicit migrations.
    if os.getenv("VERCEL") != "1":
        SQLModel.metadata.create_all(engine)


try:
    from backend.routers.trainers import router as trainers_router
    from backend.routers.members import router as members_router
    from backend.routers.groups import router as groups_router
    from backend.routers.memberships import router as memberships_router
    from backend.routers.workouts import router as workouts_router
    from backend.routers.attendance import router as attendance_router
except ModuleNotFoundError:
    from routers.trainers import router as trainers_router
    from routers.members import router as members_router
    from routers.groups import router as groups_router
    from routers.memberships import router as memberships_router
    from routers.workouts import router as workouts_router
    from routers.attendance import router as attendance_router

app.include_router(trainers_router)
app.include_router(members_router)
app.include_router(groups_router)
app.include_router(memberships_router)
app.include_router(workouts_router)
app.include_router(attendance_router)
app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return {"message": "GymTrack API is running", "docs": "/api/docs"}
