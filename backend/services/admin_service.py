"""Shared admin data operations and export helpers."""

import csv
import io
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Response
from sqlmodel import Session, select

try:
    from backend.models.member import Member
    from backend.models.activity import ActivityLog
    from backend.models.user import AppUser
    from backend.models.resources import AuthSession
    from backend.repositories import admin_repository as repository
    from backend.services.auth_service import public_user
    from backend.models.trainer_progress import WorkoutProgress
    from backend.models.workout import WorkoutAssignment, WorkoutPlan
    from backend.models.resources import (
        Membership, Attendance, GymGroup, GymGroupMember, GymGroupTask,
    )
except ModuleNotFoundError:
    from models.member import Member
    from models.activity import ActivityLog
    from models.user import AppUser
    from models.resources import AuthSession
    from repositories import admin_repository as repository
    from services.auth_service import public_user
    from models.trainer_progress import WorkoutProgress
    from models.workout import WorkoutAssignment, WorkoutPlan
    from models.resources import (
        Membership, Attendance, GymGroup, GymGroupMember, GymGroupTask,
    )


def now():
    return datetime.now(timezone.utc)


def csv_response(filename: str, headers: list[str], rows: list[list]):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([
            "'" + str(value)
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@"))
            else value
            for value in row
        ])
    return Response(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


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





def get_admin_stats(session: Session) -> dict:
    current = now()
    today_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = current - timedelta(days=7)
    return repository.dashboard_stats(session, today_start, week_start)


def list_admin_users(
    session: Session,
    q: str = "",
    role: str = "",
    status: str = "",
    offset: int = 0,
    limit: int = 20,
) -> dict:
    rows, total = repository.list_users(session, q, role, status, offset, limit)
    return {
        "items": [public_user(row) for row in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


def get_admin_user_detail(session: Session, target_id: int) -> dict:
    target = repository.get_user(session, target_id)
    if target is None:
        raise HTTPException(404, "User not found")
    records = repository.user_detail_records(session, target)
    return {
        "user": public_user(target),
        "member": records["member"],
        "trainer": records["trainer"],
        "memberships": records["memberships"],
        "attendance": records["attendance"],
        "workouts": [
            {"assignment": assignment, "plan": plan}
            for assignment, plan in records["workouts"]
        ],
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
            for membership, group in records["group_rows"]
        ],
        "sessions": [
            {
                "id": row.id,
                "created_at": row.created_at,
                "last_used_at": row.last_used_at,
                "expires_at": row.expires_at,
                "revoked_at": row.revoked_at,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "is_active": row.revoked_at is None and row.expires_at > now(),
            }
            for row in records["session_rows"]
        ],
        "recent_activity": records["activity_rows"],
    }


def change_user_role(session: Session, target_id: int, actor_id: int, role: str) -> AppUser:
    if target_id == actor_id:
        raise HTTPException(400, "You cannot change your own role")
    target = repository.get_user(session, target_id)
    if target is None:
        raise HTTPException(404, "User not found")
    previous_role = target.role
    try:
        from backend.services.trainer_service import ensure_trainer_profile, deactivate_trainer_profile
    except ModuleNotFoundError:
        from services.trainer_service import ensure_trainer_profile, deactivate_trainer_profile
    if role == "trainer":
        ensure_trainer_profile(session, target)
    elif previous_role == "trainer":
        deactivate_trainer_profile(session, target.email)
    target.role = role
    target.updated_at = now()
    return repository.save_user(session, target)


def bulk_ban_users(session: Session, actor_id: int, user_ids: list[int], reason: str) -> list[AppUser]:
    unique_ids = list(dict.fromkeys(user_ids))
    if actor_id in unique_ids:
        raise HTTPException(400, "You cannot ban your own account")
    targets = repository.get_users_by_ids(session, unique_ids)
    if len(targets) != len(unique_ids):
        raise HTTPException(404, "One or more users were not found")
    if any(target.role == "admin" for target in targets):
        raise HTTPException(400, "Bulk ban cannot include administrator accounts")
    for target in targets:
        target.is_banned = True
        session.add(target)
        repository.revoke_open_sessions(session, target.id, now())
    session.commit()
    return targets


def bulk_unban_users(session: Session, user_ids: list[int]) -> list[AppUser]:
    unique_ids = list(dict.fromkeys(user_ids))
    targets = repository.get_users_by_ids(session, unique_ids)
    if len(targets) != len(unique_ids):
        raise HTTPException(404, "One or more users were not found")
    for target in targets:
        target.is_banned = False
        session.add(target)
    session.commit()
    return targets


def ban_user(session: Session, target_id: int, actor_id: int, reason: str = "") -> AppUser:
    if target_id == actor_id:
        raise HTTPException(400, "You cannot ban yourself")
    target = repository.get_user(session, target_id)
    if target is None:
        raise HTTPException(404, "User not found")
    if target.role == "admin":
        raise HTTPException(400, "You cannot ban another admin")
    target.is_banned = True
    session.add(target)
    repository.revoke_open_sessions(session, target_id, now())
    session.commit()
    return target


def unban_user(session: Session, target_id: int) -> AppUser:
    target = repository.get_user(session, target_id)
    if target is None:
        raise HTTPException(404, "User not found")
    target.is_banned = False
    return repository.save_user(session, target)


def revoke_user_sessions(session: Session, target_id: int) -> None:
    if repository.get_user(session, target_id) is None:
        raise HTTPException(404, "User not found")
    repository.revoke_open_sessions(session, target_id, now())
    session.commit()


def list_activity(session: Session, q: str = "", offset: int = 0, limit: int = 50):
    return repository.get_user_activity(session, q, offset, limit)


def security_summary(session: Session) -> dict:
    events = repository.get_security_events(session, now() - timedelta(hours=24))
    by_ip: dict[str, int] = {}
    by_account: dict[str, int] = {}
    for event in events:
        ip = event.ip_address or "Unknown IP"
        account = event.email or "Unknown account"
        by_ip[ip] = by_ip.get(ip, 0) + 1
        by_account[account] = by_account.get(account, 0) + 1
    return {
        "failed_logins_24h": len(events),
        "events": events,
        "by_ip": [
            {"ip_address": ip, "count": count}
            for ip, count in sorted(by_ip.items(), key=lambda item: item[1], reverse=True)
        ],
        "by_account": [
            {"email": email, "count": count}
            for email, count in sorted(by_account.items(), key=lambda item: item[1], reverse=True)
        ],
    }


def export_users_csv(session: Session, q: str = "", role: str = "", status: str = ""):
    rows = repository.export_users(session, q, role, status)
    return csv_response(
        "gymtrack-users.csv",
        ["id", "full_name", "email", "role", "is_banned", "created_at"],
        [[u.id, u.full_name, u.email, u.role, u.is_banned, u.created_at.isoformat()] for u in rows],
    )


def export_members_csv(session: Session, q: str = "", status: str = ""):
    rows = repository.export_members(session, q, status)
    return csv_response(
        "gymtrack-members.csv",
        ["id", "full_name", "email", "phone", "join_date", "is_active"],
        [[m.id, m.full_name, m.email, m.phone, m.join_date, m.is_active] for m in rows],
    )


def export_activity_csv(session: Session, q: str = ""):
    rows = repository.export_activity(session, q)
    return csv_response(
        "gymtrack-activity.csv",
        ["id", "email", "action", "entity_type", "entity_id", "ip_address", "user_agent", "created_at"],
        [[a.id, a.email, a.action, a.entity_type, a.entity_id, a.ip_address, a.user_agent, a.created_at] for a in rows],
    )


def export_trainers_csv(session: Session):
    rows = repository.export_trainers(session)
    return csv_response(
        "gymtrack-trainers.csv",
        ["id", "full_name", "email", "phone", "specialization", "is_active"],
        [[t.id, t.full_name, t.email, t.phone, t.specialization, t.is_active] for t in rows],
    )


def export_memberships_csv(session: Session):
    rows = repository.export_memberships(session)
    return csv_response(
        "gymtrack-memberships.csv",
        ["id", "member_id", "plan_name", "start_date", "end_date", "price", "status"],
        [[m.id, m.member_id, m.plan_name, m.start_date, m.end_date, m.price, m.status] for m in rows],
    )


def export_attendance_csv(session: Session):
    rows = repository.export_attendance(session)
    return csv_response(
        "gymtrack-attendance.csv",
        ["id", "member_id", "check_in", "check_out", "notes", "recorded_by"],
        [[a.id, a.member_id, a.check_in, a.check_out, a.notes, a.recorded_by] for a in rows],
    )


def export_workouts_csv(session: Session):
    rows = repository.export_workouts(session)
    return csv_response(
        "gymtrack-workout-plans.csv",
        ["id", "title", "description", "level", "duration_weeks", "created_by"],
        [[p.id, p.title, p.description, p.level, p.duration_weeks, p.created_by] for p in rows],
    )


def export_assignments_csv(session: Session):
    rows = repository.export_assignments(session)
    return csv_response(
        "gymtrack-workout-assignments.csv",
        ["id", "plan_id", "member_id", "trainer_id", "start_date", "end_date", "status"],
        [[a.id, a.plan_id, a.member_id, a.trainer_id, a.start_date, a.end_date, a.status] for a in rows],
    )


def export_groups_csv(session: Session):
    rows = repository.export_groups(session)
    return csv_response(
        "gymtrack-groups.csv",
        ["id", "name", "created_by", "created_at"],
        [[g.id, g.name, g.created_by, g.created_at] for g in rows],
    )
