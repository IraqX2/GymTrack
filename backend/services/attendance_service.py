"""Attendance check-in/out and correction request business rules."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session

try:
    from backend.models.resources import Attendance, AttendanceRequest
    from backend.repositories import attendance_repository as repository
    from backend.schemas.resources import AttendanceBody, AttendanceRequestBody, AttendanceRequestReview
except ModuleNotFoundError:
    from models.resources import Attendance, AttendanceRequest
    from repositories import attendance_repository as repository
    from schemas.resources import AttendanceBody, AttendanceRequestBody, AttendanceRequestReview


def now():
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def list_attendance_records(session: Session, account, limit: int):
    member_id = None
    if account.role != "admin":
        member = repository.member_for_account(session, account.id)
        if member is None:
            raise HTTPException(404, "No gym profile is linked to this account")
        member_id = member.id
    rows = repository.list_attendance(session, member_id, limit)
    return [
        {
            "id": visit.id,
            "member_id": visit.member_id,
            "member_name": member.full_name,
            "member_email": member.email,
            "check_in": visit.check_in,
            "check_out": visit.check_out,
            "notes": visit.notes,
            "recorded_by": visit.recorded_by,
        }
        for visit, member in rows
    ]


def record_attendance(session: Session, payload: AttendanceBody, recorded_by: int) -> Attendance:
    member = repository.get_member(session, payload.member_id)
    if member is None:
        raise HTTPException(404, "Member not found")
    if not member.is_active:
        raise HTTPException(409, "This member is inactive.")
    check_in = as_utc(payload.check_in) or now()
    check_out = as_utc(payload.check_out)
    if check_out and check_out <= check_in:
        raise HTTPException(422, "Check-out time must be after check-in time.")
    if check_out is None and repository.get_open_visit(session, payload.member_id):
        raise HTTPException(409, "This member is already checked in.")
    visit = Attendance(
        member_id=payload.member_id,
        check_in=check_in,
        check_out=check_out,
        notes=payload.notes,
        recorded_by=recorded_by,
    )
    return repository.add_attendance(session, visit)


def checkout_attendance(session: Session, attendance_id: int) -> Attendance:
    visit = repository.get_attendance(session, attendance_id)
    if visit is None:
        raise HTTPException(404, "Attendance record not found")
    if visit.check_out is not None:
        raise HTTPException(409, "This attendance visit is already checked out.")
    visit.check_out = now()
    return repository.save_attendance(session, visit)


def _attendance_request_view(request_row: AttendanceRequest, member):
    return {
        "id": request_row.id,
        "user_id": request_row.user_id,
        "member_id": request_row.member_id,
        "member_name": member.full_name,
        "member_email": member.email,
        "requested_check_in": request_row.requested_check_in,
        "requested_check_out": request_row.requested_check_out,
        "notes": request_row.notes,
        "status": request_row.status,
        "reviewed_by": request_row.reviewed_by,
        "reviewed_at": request_row.reviewed_at,
        "review_note": request_row.review_note,
        "attendance_id": request_row.attendance_id,
        "created_at": request_row.created_at,
    }


def list_attendance_request_records(session: Session, account, status: str = ""):
    user_id = None if account.role == "admin" else account.id
    rows = repository.list_attendance_requests(session, user_id, status)
    return [
        _attendance_request_view(request_row, member)
        for request_row, member, _account in rows
    ]


def create_attendance_request(
    session: Session,
    account,
    payload: AttendanceRequestBody,
) -> dict:
    if account.role not in {"user", "trainer"}:
        raise HTTPException(403, "Attendance requests are for member and trainer accounts.")
    member = repository.member_for_account(session, account.id)
    if member is None:
        raise HTTPException(404, "No gym profile is linked to this account")
    check_in = as_utc(payload.requested_check_in)
    check_out = as_utc(payload.requested_check_out)
    if check_out and check_out <= check_in:
        raise HTTPException(422, "Check-out time must be after check-in time.")
    if repository.find_pending_request(session, account.id, check_in):
        raise HTTPException(409, "You already have a pending request for this check-in time.")
    row = AttendanceRequest(
        user_id=account.id,
        member_id=member.id,
        requested_check_in=check_in,
        requested_check_out=check_out,
        notes=payload.notes,
    )
    row = repository.add_attendance_request(session, row)
    return {"id": row.id, "status": row.status, "requested_check_in": row.requested_check_in}


def review_attendance_request(
    session: Session,
    request_id: int,
    payload: AttendanceRequestReview,
    reviewed_by: int,
) -> dict:
    request_row = repository.get_attendance_request(session, request_id)
    if request_row is None:
        raise HTTPException(404, "Attendance request not found")
    if request_row.status != "pending":
        raise HTTPException(409, "This attendance request has already been reviewed.")
    if payload.status == "approved":
        member = repository.get_member(session, request_row.member_id)
        if member is None or not member.is_active:
            raise HTTPException(409, "The linked member is missing or inactive.")
        if request_row.requested_check_out is None and repository.get_open_visit(session, request_row.member_id):
            raise HTTPException(409, "This member already has an open attendance visit.")
        visit = Attendance(
            member_id=request_row.member_id,
            check_in=request_row.requested_check_in,
            check_out=request_row.requested_check_out,
            notes=("Member request: " + request_row.notes).strip()[:500],
            recorded_by=reviewed_by,
        )
        repository.add_attendance(session, visit, commit=False)
        request_row.attendance_id = visit.id
    request_row.status = payload.status
    request_row.reviewed_by = reviewed_by
    request_row.reviewed_at = now()
    request_row.review_note = payload.review_note.strip()
    session.add(request_row)
    session.commit()
    session.refresh(request_row)
    return {
        "id": request_row.id,
        "status": request_row.status,
        "attendance_id": request_row.attendance_id,
    }


def delete_attendance_request(session: Session, request_id: int, account) -> None:
    request_row = repository.get_attendance_request(session, request_id)
    if request_row is None:
        raise HTTPException(404, "Attendance request not found")
    if account.role != "admin" and (
        request_row.user_id != account.id or request_row.status != "pending"
    ):
        raise HTTPException(403, "You can only cancel your own pending request.")
    repository.delete_attendance_request(session, request_row)
