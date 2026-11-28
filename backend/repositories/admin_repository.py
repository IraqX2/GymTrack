"""Read and write queries for administrator workflows."""

from datetime import datetime
from sqlalchemy import func
from sqlmodel import Session, select

try:
    from backend.models.activity import ActivityLog
    from backend.models.member import Member
    from backend.models.trainer import Trainer
    from backend.models.user import AppUser
    from backend.models.resources import (
        AuthSession, Membership, Attendance, GymGroup, GymGroupMember,
    )
    from backend.models.workout import WorkoutAssignment, WorkoutPlan
except ModuleNotFoundError:
    from models.activity import ActivityLog
    from models.member import Member
    from models.trainer import Trainer
    from models.user import AppUser
    from models.resources import (
        AuthSession, Membership, Attendance, GymGroup, GymGroupMember,
    )
    from models.workout import WorkoutAssignment, WorkoutPlan


def _count(session: Session, model, *conditions) -> int:
    statement = select(func.count()).select_from(model)
    if conditions:
        statement = statement.where(*conditions)
    return int(session.exec(statement).one())


def dashboard_stats(session: Session, today_start: datetime, week_start: datetime) -> dict:
    return {
        "users": _count(session, AppUser),
        "admins": _count(session, AppUser, AppUser.role == "admin"),
        "banned_users": _count(session, AppUser, AppUser.is_banned.is_(True)),
        "new_users_7d": _count(session, AppUser, AppUser.created_at >= week_start),
        "members": _count(session, Member),
        "active_members": _count(session, Member, Member.is_active.is_(True)),
        "trainers": _count(session, Trainer),
        "memberships": _count(session, Membership),
        "attendance_today": _count(session, Attendance, Attendance.check_in >= today_start),
        "workout_plans": _count(session, WorkoutPlan),
        "groups": _count(session, GymGroup),
    }


def list_users(
    session: Session,
    q: str = "",
    role: str = "",
    status: str = "",
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[AppUser], int]:
    statement = select(AppUser)
    if q:
        statement = statement.where(
            AppUser.full_name.ilike(f"%{q}%") | AppUser.email.ilike(f"%{q}%")
        )
    if role in {"admin", "user", "trainer"}:
        statement = statement.where(AppUser.role == role)
    if status == "banned":
        statement = statement.where(AppUser.is_banned.is_(True))
    if status == "active":
        statement = statement.where(AppUser.is_banned.is_(False))
    total = int(session.exec(select(func.count()).select_from(statement.subquery())).one())
    rows = list(
        session.exec(
            statement.order_by(AppUser.created_at.desc()).offset(offset).limit(limit)
        ).all()
    )
    return rows, total


def get_user(session: Session, user_id: int) -> AppUser | None:
    return session.get(AppUser, user_id)


def user_detail_records(session: Session, target: AppUser) -> dict:
    target_id = target.id
    member = session.exec(select(Member).where(Member.user_id == target_id)).first()
    trainer = session.exec(select(Trainer).where(Trainer.email == target.email)).first()
    memberships, attendance, workouts = [], [], []
    if member is not None:
        memberships = session.exec(
            select(Membership)
            .where(Membership.member_id == member.id)
            .order_by(Membership.created_at.desc())
        ).all()
        attendance = session.exec(
            select(Attendance)
            .where(Attendance.member_id == member.id)
            .order_by(Attendance.check_in.desc())
            .limit(100)
        ).all()
        workouts = session.exec(
            select(WorkoutAssignment, WorkoutPlan)
            .join(WorkoutPlan, WorkoutPlan.id == WorkoutAssignment.plan_id)
            .where(WorkoutAssignment.member_id == member.id)
            .order_by(WorkoutAssignment.created_at.desc())
        ).all()
    group_rows = session.exec(
        select(GymGroupMember, GymGroup)
        .join(GymGroup, GymGroup.id == GymGroupMember.group_id)
        .where(GymGroupMember.user_id == target_id)
    ).all()
    session_rows = list(
        session.exec(
            select(AuthSession)
            .where(AuthSession.user_id == target_id)
            .order_by(AuthSession.last_used_at.desc())
            .limit(50)
        ).all()
    )
    activity_rows = list(
        session.exec(
            select(ActivityLog)
            .where(ActivityLog.user_id == target_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(50)
        ).all()
    )
    return {
        "member": member,
        "trainer": trainer,
        "memberships": memberships,
        "attendance": attendance,
        "workouts": workouts,
        "group_rows": group_rows,
        "session_rows": session_rows,
        "activity_rows": activity_rows,
    }


def save_user(session: Session, user: AppUser) -> AppUser:
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_users_by_ids(session: Session, user_ids: list[int]) -> list[AppUser]:
    if not user_ids:
        return []
    return list(session.exec(select(AppUser).where(AppUser.id.in_(user_ids))).all())


def revoke_open_sessions(session: Session, user_id: int, revoked_at: datetime) -> None:
    rows = session.exec(
        select(AuthSession).where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
    ).all()
    for row in rows:
        row.revoked_at = revoked_at
        session.add(row)


def get_user_activity(session: Session, q: str = "", offset: int = 0, limit: int = 50):
    statement = select(ActivityLog).order_by(ActivityLog.created_at.desc())
    if q:
        statement = statement.where(
            ActivityLog.action.ilike(f"%{q}%") | ActivityLog.email.ilike(f"%{q}%")
        )
    return list(session.exec(statement.offset(offset).limit(limit)).all())


def get_security_events(session: Session, start_time: datetime):
    return list(
        session.exec(
            select(ActivityLog)
            .where(
                ActivityLog.created_at >= start_time,
                ActivityLog.action.in_(["login_failed", "login_locked", "login_blocked"]),
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(200)
        ).all()
    )


def export_users(session: Session, q: str = "", role: str = "", status: str = ""):
    statement = select(AppUser)
    if q:
        statement = statement.where(
            AppUser.full_name.ilike(f"%{q}%") | AppUser.email.ilike(f"%{q}%")
        )
    if role in {"admin", "user", "trainer"}:
        statement = statement.where(AppUser.role == role)
    if status == "banned":
        statement = statement.where(AppUser.is_banned.is_(True))
    if status == "active":
        statement = statement.where(AppUser.is_banned.is_(False))
    return list(session.exec(statement.order_by(AppUser.id)).all())


def export_members(session: Session, q: str = "", status: str = ""):
    statement = select(Member)
    if q:
        statement = statement.where(
            Member.full_name.ilike(f"%{q}%") | Member.email.ilike(f"%{q}%")
        )
    if status == "active":
        statement = statement.where(Member.is_active.is_(True))
    if status == "inactive":
        statement = statement.where(Member.is_active.is_(False))
    return list(session.exec(statement.order_by(Member.id)).all())


def export_activity(session: Session, q: str = ""):
    statement = select(ActivityLog)
    if q:
        statement = statement.where(
            ActivityLog.action.ilike(f"%{q}%") | ActivityLog.email.ilike(f"%{q}%")
        )
    return list(
        session.exec(statement.order_by(ActivityLog.created_at.desc()).limit(10000)).all()
    )


def export_trainers(session: Session):
    return list(session.exec(select(Trainer).order_by(Trainer.full_name)).all())


def export_memberships(session: Session):
    return list(session.exec(select(Membership).order_by(Membership.created_at.desc())).all())


def export_attendance(session: Session):
    return list(
        session.exec(select(Attendance).order_by(Attendance.check_in.desc()).limit(50000)).all()
    )


def export_workouts(session: Session):
    return list(
        session.exec(select(WorkoutPlan).order_by(WorkoutPlan.created_at.desc())).all()
    )


def export_assignments(session: Session):
    return list(
        session.exec(select(WorkoutAssignment).order_by(WorkoutAssignment.created_at.desc())).all()
    )


def export_groups(session: Session):
    return list(session.exec(select(GymGroup).order_by(GymGroup.created_at.desc())).all())
