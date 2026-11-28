from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response
from sqlmodel import select

try:
    from backend.core.audit import audit
    from backend.core.dependencies import ADMIN, DB
    from backend.models.activity import ActivityLog
    from backend.models.member import Member
    from backend.models.trainer import Trainer
    from backend.models.trainer_progress import WorkoutProgress
    from backend.models.user import AppUser
    from backend.models.workout import WorkoutAssignment, WorkoutPlan
    from backend.models.resources import (
        AuthSession, Membership, Attendance, GymGroup, GymGroupMember, GymGroupTask,
    )
    from backend.schemas.trainer import RoleChangeBody
    from backend.schemas.admin import BulkUserAction, BulkContentDelete
    from backend.services import admin_service
    from backend.services.auth_service import public_user
except ModuleNotFoundError:
    from core.audit import audit
    from core.dependencies import ADMIN, DB
    from models.activity import ActivityLog
    from models.member import Member
    from models.trainer import Trainer
    from models.trainer_progress import WorkoutProgress
    from models.user import AppUser
    from models.workout import WorkoutAssignment, WorkoutPlan
    from models.resources import (
        AuthSession, Membership, Attendance, GymGroup, GymGroupMember, GymGroupTask,
    )
    from schemas.trainer import RoleChangeBody
    from schemas.admin import BulkUserAction, BulkContentDelete
    from services import admin_service
    from services.auth_service import public_user


router = APIRouter(tags=["administration"])


@router.get("/api/admin/stats")
def admin_stats(user: ADMIN, db: DB):
    return admin_service.get_admin_stats(db)


@router.get("/api/admin/users")
def admin_users(
    user: ADMIN,
    db: DB,
    q: str = "",
    role: str = "",
    status: str = "",
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    return admin_service.list_admin_users(db, q, role, status, offset, limit)


@router.get("/api/admin/users/{target_id}")
def admin_user_detail(target_id: int, user: ADMIN, db: DB):
    return admin_service.get_admin_user_detail(db, target_id)


@router.patch("/api/admin/users/{target_id}/role")
def change_role(
    target_id: int,
    data: RoleChangeBody,
    user: ADMIN,
    db: DB,
    request: Request,
):
    target = admin_service.change_user_role(db, target_id, user.id, data.role)
    audit(db, request, "role_changed", user, "user", target_id, f"{target.email} -> {data.role}")
    return public_user(target)


@router.post("/api/admin/users/bulk-ban")
def bulk_ban_users(data: BulkUserAction, user: ADMIN, db: DB, request: Request):
    targets = admin_service.bulk_ban_users(db, user.id, data.user_ids, data.reason)
    for target in targets:
        audit(db, request, "user_banned", user, "user", target.id, data.reason[:200])
    return {"count": len(targets), "users": [public_user(target) for target in targets]}


@router.post("/api/admin/users/bulk-unban")
def bulk_unban_users(data: BulkUserAction, user: ADMIN, db: DB, request: Request):
    targets = admin_service.bulk_unban_users(db, data.user_ids)
    for target in targets:
        audit(db, request, "user_unbanned", user, "user", target.id)
    return {"count": len(targets), "users": [public_user(target) for target in targets]}


@router.post("/api/admin/users/{target_id}/ban")
def ban_user(target_id: int, data: dict, user: ADMIN, db: DB, request: Request):
    target = admin_service.ban_user(
        db,
        target_id,
        user.id,
        str(data.get("reason", ""))[:200],
    )
    audit(db, request, "user_banned", user, "user", target_id, str(data.get("reason", ""))[:200])
    return public_user(target)


@router.post("/api/admin/users/{target_id}/unban")
def unban_user(target_id: int, user: ADMIN, db: DB, request: Request):
    target = admin_service.unban_user(db, target_id)
    audit(db, request, "user_unbanned", user, "user", target_id)
    return public_user(target)


@router.post("/api/admin/users/{target_id}/revoke-sessions", status_code=204)
def admin_revoke_sessions(target_id: int, user: ADMIN, db: DB, request: Request):
    admin_service.revoke_user_sessions(db, target_id)
    audit(db, request, "admin_sessions_revoked", user, "user", target_id)
    return Response(status_code=204)


@router.get("/api/admin/activity")
def admin_activity(
    user: ADMIN,
    db: DB,
    q: str = "",
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    return admin_service.list_activity(db, q, offset, limit)


@router.get("/api/admin/security")
def admin_security(user: ADMIN, db: DB):
    return admin_service.security_summary(db)


@router.get("/api/admin/content")
def admin_content(
    user: ADMIN,
    db: DB,
    content_type: Literal["memberships", "attendance", "workout_plans", "assignments", "groups", "trainer_progress"] = Query("memberships", alias="type"),
    q: str = "",
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    items, total = admin_service._admin_content_query(db, content_type, q)
    return {
        "items": items[offset:offset + limit],
        "total": total,
        "offset": offset,
        "limit": limit,
        "type": content_type,
    }


@router.delete("/api/admin/content/{content_type}/{record_id}", status_code=204)
def delete_admin_content(
    content_type: Literal["memberships", "attendance", "workout_plans", "assignments", "groups", "trainer_progress"],
    record_id: int,
    user: ADMIN,
    db: DB,
    request: Request,
):
    admin_service._delete_admin_content_record(db, content_type, record_id)
    db.commit()
    audit(db, request, "content_deleted", user, content_type, record_id)
    return Response(status_code=204)


@router.post("/api/admin/content/{content_type}/bulk-delete")
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
            admin_service._delete_admin_content_record(db, content_type, record_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    for record_id in record_ids:
        audit(db, request, "content_deleted", user, content_type, record_id, "Bulk moderation")
    return {"count": len(record_ids), "deleted_ids": record_ids}


@router.get("/api/admin/export/users")
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
    return admin_service.csv_response("gymtrack-users.csv", ["id", "full_name", "email", "role", "is_banned", "created_at"],
        [[u.id, u.full_name, u.email, u.role, u.is_banned, u.created_at.isoformat()] for u in rows])


@router.get("/api/admin/export/members")
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
    return admin_service.csv_response("gymtrack-members.csv", ["id", "full_name", "email", "phone", "join_date", "is_active"],
        [[m.id, m.full_name, m.email, m.phone, m.join_date, m.is_active] for m in rows])


@router.get("/api/admin/export/activity")
def export_activity(user: ADMIN, db: DB, request: Request, q: str = ""):
    query = select(ActivityLog)
    if q:
        query = query.where(
            ActivityLog.action.ilike(f"%{q}%") | ActivityLog.email.ilike(f"%{q}%")
        )
    rows = db.exec(query.order_by(ActivityLog.created_at.desc()).limit(10000)).all()
    audit(db, request, "data_exported", user, "export", "activity")
    return admin_service.csv_response("gymtrack-activity.csv",
        ["id", "email", "action", "entity_type", "entity_id", "ip_address", "user_agent", "created_at"],
        [[a.id, a.email, a.action, a.entity_type, a.entity_id, a.ip_address, a.user_agent, a.created_at] for a in rows])


@router.get("/api/admin/export/trainers")
def export_trainers(user: ADMIN, db: DB, request: Request):
    rows = db.exec(select(Trainer).order_by(Trainer.full_name)).all()
    audit(db, request, "data_exported", user, "export", "trainers")
    return admin_service.csv_response("gymtrack-trainers.csv",
        ["id", "full_name", "email", "phone", "specialization", "is_active"],
        [[t.id, t.full_name, t.email, t.phone, t.specialization, t.is_active] for t in rows])


@router.get("/api/admin/export/memberships")
def export_memberships(user: ADMIN, db: DB, request: Request):
    rows = db.exec(select(Membership).order_by(Membership.created_at.desc())).all()
    audit(db, request, "data_exported", user, "export", "memberships")
    return admin_service.csv_response("gymtrack-memberships.csv",
        ["id", "member_id", "plan_name", "start_date", "end_date", "price", "status"],
        [[m.id, m.member_id, m.plan_name, m.start_date, m.end_date, m.price, m.status] for m in rows])


@router.get("/api/admin/export/attendance")
def export_attendance(user: ADMIN, db: DB, request: Request):
    rows = db.exec(select(Attendance).order_by(Attendance.check_in.desc()).limit(50000)).all()
    audit(db, request, "data_exported", user, "export", "attendance")
    return admin_service.csv_response("gymtrack-attendance.csv",
        ["id", "member_id", "check_in", "check_out", "notes", "recorded_by"],
        [[a.id, a.member_id, a.check_in, a.check_out, a.notes, a.recorded_by] for a in rows])


@router.get("/api/admin/export/workouts")
def export_workouts(user: ADMIN, db: DB, request: Request):
    rows = db.exec(select(WorkoutPlan).order_by(WorkoutPlan.created_at.desc())).all()
    audit(db, request, "data_exported", user, "export", "workout_plans")
    return admin_service.csv_response("gymtrack-workout-plans.csv",
        ["id", "title", "description", "level", "duration_weeks", "created_by"],
        [[p.id, p.title, p.description, p.level, p.duration_weeks, p.created_by] for p in rows])


@router.get("/api/admin/export/assignments")
def export_workout_assignments(user: ADMIN, db: DB, request: Request):
    rows = db.exec(select(WorkoutAssignment).order_by(WorkoutAssignment.created_at.desc())).all()
    audit(db, request, "data_exported", user, "export", "workout_assignments")
    return admin_service.csv_response("gymtrack-workout-assignments.csv",
        ["id", "plan_id", "member_id", "trainer_id", "start_date", "end_date", "status"],
        [[a.id, a.plan_id, a.member_id, a.trainer_id, a.start_date, a.end_date, a.status] for a in rows])


@router.get("/api/admin/export/groups")
def export_groups(user: ADMIN, db: DB, request: Request):
    rows = db.exec(select(GymGroup).order_by(GymGroup.created_at.desc())).all()
    audit(db, request, "data_exported", user, "export", "groups")
    return admin_service.csv_response("gymtrack-groups.csv", ["id", "name", "created_by", "created_at"],
        [[g.id, g.name, g.created_by, g.created_at] for g in rows])


