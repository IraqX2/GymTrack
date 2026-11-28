"""Database queries for member subscriptions."""

from sqlmodel import Session, select

try:
    from backend.models.member import Member
    from backend.models.resources import Membership
except ModuleNotFoundError:
    from models.member import Member
    from models.resources import Membership


def member_for_account(session: Session, user_id: int) -> Member | None:
    return session.exec(select(Member).where(Member.user_id == user_id)).first()


def get_member(session: Session, member_id: int) -> Member | None:
    return session.get(Member, member_id)


def list_memberships(session: Session, member_id: int | None):
    statement = select(Membership, Member).join(Member, Member.id == Membership.member_id)
    if member_id is not None:
        statement = statement.where(Membership.member_id == member_id)
    return list(session.exec(statement.order_by(Membership.created_at.desc())).all())


def get_membership(session: Session, membership_id: int) -> Membership | None:
    return session.get(Membership, membership_id)


def save_membership(session: Session, membership: Membership) -> Membership:
    session.add(membership)
    session.commit()
    session.refresh(membership)
    return membership


def delete_membership(session: Session, membership: Membership) -> None:
    session.delete(membership)
    session.commit()
