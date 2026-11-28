"""Persistence queries for the member domain."""

from sqlmodel import Session, select

try:
    from backend.models.member import Member
    from backend.models.resources import Attendance, Membership
    from backend.models.workout import WorkoutAssignment, WorkoutPlan
    from backend.models.trainer import Trainer
except ModuleNotFoundError:
    from models.member import Member
    from models.resources import Attendance, Membership
    from models.workout import WorkoutAssignment, WorkoutPlan
    from models.trainer import Trainer


def find_member_by_email(session: Session, email: str) -> Member | None:
    return session.exec(select(Member).where(Member.email == email)).first()


def find_member_by_id(session: Session, member_id: int) -> Member | None:
    return session.get(Member, member_id)


def list_members(session: Session, account, offset: int, limit: int) -> list[Member]:
    statement = select(Member).order_by(Member.id.desc())
    if account.role != "admin":
        statement = statement.where(Member.user_id == account.id)
    return list(session.exec(statement.offset(offset).limit(limit)).all())


def add_member(session: Session, member: Member) -> Member:
    session.add(member)
    session.commit()
    session.refresh(member)
    return member


def save_member(session: Session, member: Member) -> Member:
    session.add(member)
    session.commit()
    session.refresh(member)
    return member


def member_has_gym_history(session: Session, member_id: int) -> bool:
    checks = (
        select(Membership.id).where(Membership.member_id == member_id),
        select(Attendance.id).where(Attendance.member_id == member_id),
        select(WorkoutAssignment.id).where(WorkoutAssignment.member_id == member_id),
    )
    return any(session.exec(statement).first() is not None for statement in checks)


def remove_member(session: Session, member: Member) -> None:
    session.delete(member)
    session.commit()

def find_member_by_user_id(session: Session, user_id: int) -> Member | None:
    return session.exec(select(Member).where(Member.user_id == user_id)).first()


def get_member_dashboard_records(session: Session, member_id: int):
    memberships = session.exec(
        select(Membership)
        .where(Membership.member_id == member_id)
        .order_by(Membership.created_at.desc())
    ).all()
    attendance = session.exec(
        select(Attendance)
        .where(Attendance.member_id == member_id)
        .order_by(Attendance.check_in.desc())
        .limit(100)
    ).all()
    assignments = session.exec(
        select(WorkoutAssignment, WorkoutPlan, Trainer)
        .join(WorkoutPlan, WorkoutPlan.id == WorkoutAssignment.plan_id)
        .outerjoin(Trainer, Trainer.id == WorkoutAssignment.trainer_id)
        .where(WorkoutAssignment.member_id == member_id)
        .order_by(WorkoutAssignment.created_at.desc())
    ).all()
    return memberships, attendance, assignments

