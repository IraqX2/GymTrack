from fastapi import APIRouter, Query, Request, Response

try:
    from backend.core.audit import audit
    from backend.core.dependencies import ADMIN, CURRENT, DB
    from backend.schemas.resources import AttendanceBody, AttendanceRequestBody, AttendanceRequestReview
    from backend.services import attendance_service
except ModuleNotFoundError:
    from core.audit import audit
    from core.dependencies import ADMIN, CURRENT, DB
    from schemas.resources import AttendanceBody, AttendanceRequestBody, AttendanceRequestReview
    from services import attendance_service


router = APIRouter(tags=["attendance"])


@router.get("/api/attendance")
def list_attendance(
    user: CURRENT,
    db: DB,
    limit: int = Query(100, ge=1, le=200),
):
    return attendance_service.list_attendance_records(db, user, limit)


@router.post("/api/attendance", status_code=201)
def record_attendance(
    payload: AttendanceBody,
    user: ADMIN,
    db: DB,
    request: Request,
):
    visit = attendance_service.record_attendance(db, payload, user.id)
    audit(db, request, "attendance_recorded", user, "attendance", visit.id)
    return visit


@router.patch("/api/attendance/{attendance_id}/checkout")
def checkout_attendance(
    attendance_id: int,
    user: ADMIN,
    db: DB,
    request: Request,
):
    visit = attendance_service.checkout_attendance(db, attendance_id)
    audit(db, request, "attendance_checkout", user, "attendance", visit.id)
    return visit


@router.get("/api/attendance/requests")
def list_attendance_requests(user: CURRENT, db: DB, status: str = ""):
    return attendance_service.list_attendance_request_records(db, user, status)


@router.post("/api/attendance/requests", status_code=201)
def create_attendance_request(
    payload: AttendanceRequestBody,
    user: CURRENT,
    db: DB,
    request: Request,
):
    result = attendance_service.create_attendance_request(db, user, payload)
    audit(db, request, "attendance_request_created", user, "attendance_request", result["id"])
    return result


@router.patch("/api/attendance/requests/{request_id}")
def review_attendance_request(
    request_id: int,
    payload: AttendanceRequestReview,
    user: ADMIN,
    db: DB,
    request: Request,
):
    result = attendance_service.review_attendance_request(db, request_id, payload, user.id)
    audit(
        db,
        request,
        "attendance_request_" + payload.status,
        user,
        "attendance_request",
        request_id,
        payload.review_note,
    )
    return result


@router.delete("/api/attendance/requests/{request_id}", status_code=204)
def delete_attendance_request(
    request_id: int,
    user: CURRENT,
    db: DB,
    request: Request,
):
    attendance_service.delete_attendance_request(db, request_id, user)
    audit(db, request, "attendance_request_removed", user, "attendance_request", request_id)
    return Response(status_code=204)
