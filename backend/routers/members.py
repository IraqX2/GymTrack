from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session

from backend.database import get_session
from backend.schemas.member import MemberCreate, MemberRead, MemberUpdate
from backend.services.member_service import (
    create_member_record,
    delete_member_record,
    get_member_record,
    list_member_records,
    update_member_record,
)

router = APIRouter(prefix="/api/members", tags=["members"])


@router.post("", response_model=MemberRead, status_code=201)
def create_member(
    payload: MemberCreate,
    session: Session = Depends(get_session),
):
    return create_member_record(session, payload)


@router.get("", response_model=list[MemberRead])
def list_members(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    session: Session = Depends(get_session),
):
    return list_member_records(session, offset=offset, limit=limit)


@router.get("/{member_id}", response_model=MemberRead)
def get_member(
    member_id: int,
    session: Session = Depends(get_session),
):
    return get_member_record(session, member_id)


@router.put("/{member_id}", response_model=MemberRead)
def update_member(
    member_id: int,
    payload: MemberUpdate,
    session: Session = Depends(get_session),
):
    return update_member_record(session, member_id, payload)


@router.delete("/{member_id}", status_code=204)
def delete_member(
    member_id: int,
    session: Session = Depends(get_session),
):
    delete_member_record(session, member_id)
    return Response(status_code=204)
