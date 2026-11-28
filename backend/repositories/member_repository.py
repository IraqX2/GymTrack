"""Persistence queries for the member domain."""

from sqlmodel import Session, select

try:
    from backend.models.member import Member
    from backend.models.resources import Attendance, Membership
    from backend.models.workout import WorkoutAssignment
except ModuleNotFoundError:
    from models.member import Member
    from models.resources import Attendance, Membership
    from models.workout import WorkoutAssignment


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
