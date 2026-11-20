from fastapi import HTTPException
from sqlmodel import Session, select

try:
    from backend.models.member import Member
    from backend.schemas.member import MemberCreate, MemberUpdate
except ModuleNotFoundError:
    from models.member import Member
    from schemas.member import MemberCreate, MemberUpdate


def create_member_record(session: Session, payload: MemberCreate) -> Member:
    existing = session.exec(
        select(Member).where(Member.email == str(payload.email))
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A member with this email already exists.",
        )

    member = Member(**payload.model_dump())
    session.add(member)
    session.commit()
    session.refresh(member)
    return member


def list_member_records(session: Session, offset: int = 0, limit: int = 100) -> list[Member]:
    statement = (
        select(Member)
        .order_by(Member.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(statement).all())


def get_member_record(session: Session, member_id: int) -> Member:
    member = session.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found.")
    return member


def update_member_record(
    session: Session,
    member_id: int,
    payload: MemberUpdate,
) -> Member:
    member = get_member_record(session, member_id)
    changes = payload.model_dump(exclude_unset=True)

    if "email" in changes:
        changes["email"] = str(changes["email"])
        duplicate = session.exec(
            select(Member).where(
                Member.email == changes["email"],
                Member.id != member_id,
            )
        ).first()
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="A member with this email already exists.",
            )

    for key, value in changes.items():
        setattr(member, key, value)

    session.add(member)
    session.commit()
    session.refresh(member)
    return member


def delete_member_record(session: Session, member_id: int) -> None:
    member = get_member_record(session, member_id)
    session.delete(member)
    session.commit()
