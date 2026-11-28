"""Business rules for member CRUD and ownership."""

from fastapi import HTTPException
from sqlmodel import Session

try:
    from backend.models.member import Member
    from backend.repositories import member_repository as repository
    from backend.schemas.member import MemberCreate, MemberUpdate
except ModuleNotFoundError:
    from models.member import Member
    from repositories import member_repository as repository
    from schemas.member import MemberCreate, MemberUpdate


def list_member_records(session: Session, account, offset: int = 0, limit: int = 50) -> list[Member]:
    return repository.list_members(session, account, offset, limit)


def create_member_record(session: Session, payload: MemberCreate, created_by: int) -> Member:
    email = str(payload.email).strip().lower()
    if repository.find_member_by_email(session, email):
        raise HTTPException(status_code=409, detail="Member email already exists")

    member = Member(
        **payload.model_dump(exclude={"email"}),
        email=email,
        created_by=created_by,
    )
    return repository.add_member(session, member)


def get_member_record(session: Session, member_id: int, account) -> Member:
    member = repository.find_member_by_id(session, member_id)
    if member is None or (account.role != "admin" and member.user_id != account.id):
        raise HTTPException(status_code=404, detail="Member not found")
    return member


def update_member_record(
    session: Session,
    member_id: int,
    payload: MemberUpdate,
) -> Member:
    member = repository.find_member_by_id(session, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    changes = payload.model_dump(exclude_unset=True)
    if "email" in changes and changes["email"] is not None:
        email = str(changes["email"]).strip().lower()
        duplicate = repository.find_member_by_email(session, email)
        if duplicate and duplicate.id != member_id:
            raise HTTPException(status_code=409, detail="Member email already exists")
        changes["email"] = email

    for key, value in changes.items():
        setattr(member, key, value)
    return repository.save_member(session, member)


def delete_member_record(session: Session, member_id: int) -> None:
    member = repository.find_member_by_id(session, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if repository.member_has_gym_history(session, member_id):
        raise HTTPException(
            status_code=409,
            detail="This member has gym history. Mark the member inactive instead of deleting their records.",
        )
    repository.remove_member(session, member)
