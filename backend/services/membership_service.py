"""Membership lifecycle and member-ownership rules."""

from datetime import date
from fastapi import HTTPException
from sqlmodel import Session

try:
    from backend.models.resources import Membership
    from backend.repositories import membership_repository as repository
    from backend.schemas.resources import MembershipBody
except ModuleNotFoundError:
    from models.resources import Membership
    from repositories import membership_repository as repository
    from schemas.resources import MembershipBody


VALID_STATUSES = {"active", "expired", "cancelled"}


def list_membership_records(session: Session, account):
    member_id = None
    if account.role != "admin":
        member = repository.member_for_account(session, account.id)
        if member is None:
            raise HTTPException(404, "No gym profile is linked to this account")
        member_id = member.id
    rows = repository.list_memberships(session, member_id)
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


def _validate_membership(session: Session, payload: MembershipBody) -> None:
    if repository.get_member(session, payload.member_id) is None:
        raise HTTPException(404, "Member not found")
    if payload.end_date < payload.start_date:
        raise HTTPException(422, "End date cannot be before start date")
    if payload.status not in VALID_STATUSES:
        raise HTTPException(422, "Invalid membership status")


def create_membership(session: Session, payload: MembershipBody) -> Membership:
    _validate_membership(session, payload)
    return repository.save_membership(session, Membership(**payload.model_dump()))


def update_membership(session: Session, membership_id: int, payload: MembershipBody) -> Membership:
    membership = repository.get_membership(session, membership_id)
    if membership is None:
        raise HTTPException(404, "Membership not found")
    _validate_membership(session, payload)
    for key, value in payload.model_dump().items():
        setattr(membership, key, value)
    return repository.save_membership(session, membership)


def delete_membership(session: Session, membership_id: int) -> None:
    membership = repository.get_membership(session, membership_id)
    if membership is None:
        raise HTTPException(404, "Membership not found")
    repository.delete_membership(session, membership)
