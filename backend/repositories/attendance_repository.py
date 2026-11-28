"""Persistence queries for attendance and attendance requests."""

from sqlmodel import Session, select

try:
    from backend.models.activity import ActivityLog
    from backend.models.member import Member
    from backend.models.resources import Attendance, AttendanceRequest
    from backend.models.user import AppUser
except ModuleNotFoundError:
    from models.activity import ActivityLog
    from models.member import Member
    from models.resources import Attendance, AttendanceRequest
    from models.user import AppUser


def member_for_account(session: Session, user_id: int) -> Member | None:
    return session.exec(select(Member).where(Member.user_id == user_id)).first()


def get_member(session: Session, member_id: int) -> Member | None:
    return session.get(Member, member_id)


def list_attendance(session: Session, member_id: int | None, limit: int):
    statement = select(Attendance, Member).join(Member, Member.id == Attendance.member_id)
    if member_id is not None:
        statement = statement.where(Attendance.member_id == member_id)
    return list(session.exec(statement.order_by(Attendance.check_in.desc()).limit(limit)).all())


def get_open_visit(session: Session, member_id: int) -> Attendance | None:
    statement = select(Attendance).where(
        Attendance.member_id == member_id,
        Attendance.check_out.is_(None),
    )
    return session.exec(statement).first()


def get_attendance(session: Session, attendance_id: int) -> Attendance | None:
    return session.get(Attendance, attendance_id)


def add_attendance(session: Session, visit: Attendance, commit: bool = True) -> Attendance:
    session.add(visit)
    if commit:
        session.commit()
        session.refresh(visit)
    else:
        session.flush()
    return visit


def save_attendance(session: Session, visit: Attendance) -> Attendance:
    session.add(visit)
    session.commit()
    session.refresh(visit)
    return visit


def list_attendance_requests(
    session: Session,
    user_id: int | None,
    status: str,
):
    statement = (
        select(AttendanceRequest, Member, AppUser)
        .join(Member, Member.id == AttendanceRequest.member_id)
        .join(AppUser, AppUser.id == AttendanceRequest.user_id)
    )
    if user_id is not None:
        statement = statement.where(AttendanceRequest.user_id == user_id)
    if status in {"pending", "approved", "rejected"}:
        statement = statement.where(AttendanceRequest.status == status)
    statement = statement.order_by(AttendanceRequest.created_at.desc()).limit(100)
    return list(session.exec(statement).all())


def find_pending_request(
    session: Session,
    user_id: int,
    requested_check_in,
) -> AttendanceRequest | None:
    statement = select(AttendanceRequest).where(
        AttendanceRequest.user_id == user_id,
        AttendanceRequest.requested_check_in == requested_check_in,
        AttendanceRequest.status == "pending",
    )
    return session.exec(statement).first()


def add_attendance_request(session: Session, request_row: AttendanceRequest) -> AttendanceRequest:
    session.add(request_row)
    session.commit()
    session.refresh(request_row)
    return request_row


def get_attendance_request(session: Session, request_id: int) -> AttendanceRequest | None:
    return session.get(AttendanceRequest, request_id)


def save_attendance_request(session: Session, request_row: AttendanceRequest) -> AttendanceRequest:
    session.add(request_row)
    session.commit()
    session.refresh(request_row)
    return request_row


def delete_attendance_request(session: Session, request_row: AttendanceRequest) -> None:
    session.delete(request_row)
    session.commit()
