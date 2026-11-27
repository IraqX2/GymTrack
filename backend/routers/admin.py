"""Domain API controllers. HTTP concerns live here; shared models/dependencies live in gymtrack_api."""
from fastapi import APIRouter

try:
    from backend.gymtrack_api import *
except ModuleNotFoundError:
    from gymtrack_api import *

router = APIRouter()


# Admin overview, user management, activity/security views and CSV export.
@router.get("/api/admin/stats")
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


@router.get("/api/admin/users")
def admin_users(user: ADMIN, db: DB, q: str = "", role: str = "", status: str = "",
                offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    query = select(AppUser).order_by(AppUser.created_at.desc())
    if q: query = query.where(AppUser.full_name.ilike(f"%{q}%") | AppUser.email.ilike(f"%{q}%"))
    if role in {"admin", "user"}: query = query.where(AppUser.role == role)
    if status == "banned": query = query.where(AppUser.is_banned.is_(True))
    if status == "active": query = query.where(AppUser.is_banned.is_(False))
    rows = db.exec(query.offset(offset).limit(limit)).all()
    return [public_user(row, db) for row in rows]


@router.patch("/api/admin/users/{target_id}/role")
def change_role(target_id: int, data: dict, user: ADMIN, db: DB, request: Request):
    if target_id == user.id: raise HTTPException(400, "You cannot change your own role")
    role = data.get("role")
    if role not in {"user", "admin"}: raise HTTPException(422, "Role must be user or admin")
    target = db.get(AppUser, target_id)
    if not target: raise HTTPException(404, "User not found")
    target.role = role; target.updated_at = now(); db.add(target); db.commit()
    audit(db, request, "role_changed", user, "user", target_id, f"{target.email} -> {role}")
    return public_user(target, db)


@router.post("/api/admin/users/{target_id}/ban")
def ban_user(target_id: int, data: dict, user: ADMIN, db: DB, request: Request):
    if target_id == user.id: raise HTTPException(400, "You cannot ban yourself")
    target = db.get(AppUser, target_id)
    if not target: raise HTTPException(404, "User not found")
    if target.role == "admin": raise HTTPException(400, "You cannot ban another admin")
    target.is_banned = True; db.add(target)
    for s in db.exec(select(AuthSession).where(AuthSession.user_id == target_id, AuthSession.revoked_at.is_(None))).all():
        s.revoked_at = now(); db.add(s)
    db.commit(); audit(db, request, "user_banned", user, "user", target_id, str(data.get("reason", ""))[:200])
    return public_user(target, db)


@router.post("/api/admin/users/{target_id}/unban")
def unban_user(target_id: int, user: ADMIN, db: DB, request: Request):
    target = db.get(AppUser, target_id)
    if not target: raise HTTPException(404, "User not found")
    target.is_banned = False; db.add(target); db.commit()
    audit(db, request, "user_unbanned", user, "user", target_id)
    return public_user(target, db)


@router.post("/api/admin/users/{target_id}/revoke-sessions", status_code=204)
def admin_revoke_sessions(target_id: int, user: ADMIN, db: DB, request: Request):
    target = db.get(AppUser, target_id)
    if not target: raise HTTPException(404, "User not found")
    for s in db.exec(select(AuthSession).where(AuthSession.user_id == target_id, AuthSession.revoked_at.is_(None))).all():
        s.revoked_at = now(); db.add(s)
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
    start = now() - timedelta(hours=24)
    rows = db.exec(select(ActivityLog).where(ActivityLog.created_at >= start,
        ActivityLog.action.in_(["login_failed", "login_locked", "login_blocked"]))
        .order_by(ActivityLog.created_at.desc()).limit(200)).all()
    return {"failed_logins_24h": len(rows), "events": rows}


@router.get("/api/admin/export/users")
def export_users(user: ADMIN, db: DB):
    rows = db.exec(select(AppUser).order_by(AppUser.id)).all()
    return csv_response("gymtrack-users.csv", ["id", "full_name", "email", "role", "is_banned", "created_at"],
        [[u.id, u.full_name, u.email, u.role, u.is_banned, u.created_at.isoformat()] for u in rows])


@router.get("/api/admin/export/members")
def export_members(user: ADMIN, db: DB):
    rows = db.exec(select(Member).order_by(Member.id)).all()
    return csv_response("gymtrack-members.csv", ["id", "full_name", "email", "phone", "join_date", "is_active"],
        [[m.id, m.full_name, m.email, m.phone, m.join_date, m.is_active] for m in rows])


@router.get("/api/admin/export/activity")
def export_activity(user: ADMIN, db: DB):
    rows = db.exec(select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(10000)).all()
    return csv_response("gymtrack-activity.csv",
        ["id", "email", "action", "entity_type", "entity_id", "ip_address", "user_agent", "created_at"],
        [[a.id, a.email, a.action, a.entity_type, a.entity_id, a.ip_address, a.user_agent, a.created_at] for a in rows])


try:
    from backend.trainers.router import router as trainer_router
except ModuleNotFoundError:
    from trainers.router import router as trainer_router

app.include_router(trainer_router)
