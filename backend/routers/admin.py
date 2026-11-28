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
    week = admin_service.now() - timedelta(days=7)
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


@router.get("/api/admin/users")
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


@router.get("/api/admin/users/{target_id}")
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
                "is_active": session.revoked_at is None and session.expires_at > admin_service.now(),
            }
            for session in session_rows
        ],
        "recent_activity": activity_rows,
    }


@router.patch("/api/admin/users/{target_id}/role")
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
    target.updated_at = admin_service.now()
    db.add(target)
    db.commit()
    audit(db, request, "role_changed", user, "user", target_id, f"{target.email} -> {data.role}")
    return public_user(target)


@router.post("/api/admin/users/bulk-ban")
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
            session.revoked_at = admin_service.now()
            db.add(session)
    db.commit()

    for target in targets:
        audit(db, request, "user_banned", user, "user", target.id, data.reason[:200])
    return {"count": len(targets), "users": [public_user(target) for target in targets]}


@router.post("/api/admin/users/bulk-unban")
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


@router.post("/api/admin/users/{target_id}/ban")
def ban_user(target_id: int, data: dict, user: ADMIN, db: DB, request: Request):
    if target_id == user.id: raise HTTPException(400, "You cannot ban yourself")
    target = db.get(AppUser, target_id)
    if not target: raise HTTPException(404, "User not found")
    if target.role == "admin": raise HTTPException(400, "You cannot ban another admin")
    target.is_banned = True; db.add(target)
    for s in db.exec(select(AuthSession).where(AuthSession.user_id == target_id, AuthSession.revoked_at.is_(None))).all():
        s.revoked_at = admin_service.now(); db.add(s)
    db.commit(); audit(db, request, "user_banned", user, "user", target_id, str(data.get("reason", ""))[:200])
    return public_user(target)


@router.post("/api/admin/users/{target_id}/unban")
def unban_user(target_id: int, user: ADMIN, db: DB, request: Request):
    target = db.get(AppUser, target_id)
    if not target: raise HTTPException(404, "User not found")
    target.is_banned = False; db.add(target); db.commit()
    audit(db, request, "user_unbanned", user, "user", target_id)
    return public_user(target)


@router.post("/api/admin/users/{target_id}/revoke-sessions", status_code=204)
def admin_revoke_sessions(target_id: int, user: ADMIN, db: DB, request: Request):
    target = db.get(AppUser, target_id)
    if not target: raise HTTPException(404, "User not found")
    for s in db.exec(select(AuthSession).where(AuthSession.user_id == target_id, AuthSession.revoked_at.is_(None))).all():
        s.revoked_at = admin_service.now(); db.add(s)
    db.commit(); audit(db, request, "admin_sessions_revoked", user, "user", target_id)
    return Response(status_code=204)


@router.get("/api/admin/activity")
def admin_activity(user: ADMIN, db: DB, q: str = "", offset: int = Query(0, ge=0),
                   limit: int = Query(50, ge=1, le=200)):
    query = select(ActivityLog).order_by(ActivityLog.created_at.desc())
    if q: query = query.where(ActivityLog.action.ilike(f"%{q}%") | ActivityLog.email.ilike(f"%{q}%"))
    return db.exec(query.offset(offset).limit(limit)).all()


@router.get("/api/admin/security")
def admin_security(user: ADMIN, db: DB):
    start = admin_service.now() - timedelta(hours=24)
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


