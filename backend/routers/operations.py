"""Domain API controllers. HTTP concerns live here; shared models/dependencies live in gymtrack_api."""
from fastapi import APIRouter

try:
    from backend.gymtrack_api import *
except ModuleNotFoundError:
    from gymtrack_api import *

router = APIRouter()


# Memberships
@router.get("/api/memberships")
def memberships(user: CURRENT, db: DB):
    query = select(Membership, Member).join(Member, Member.id == Membership.member_id)
    if user.role != "admin":
        query = query.where(Membership.member_id == get_my_member(db, user).id)
    rows = db.exec(query.order_by(Membership.created_at.desc())).all()
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


@router.post("/api/memberships", status_code=201)
def add_membership(data: MembershipBody, user: ADMIN, db: DB, request: Request):
    if not db.get(Member, data.member_id): raise HTTPException(404, "Member not found")
    if data.end_date < data.start_date: raise HTTPException(422, "End date cannot be before start date")
    if data.status not in {"active", "expired", "cancelled"}: raise HTTPException(422, "Invalid membership status")
    row = Membership(**data.model_dump()); db.add(row); db.commit(); db.refresh(row)
    audit(db, request, "membership_created", user, "membership", row.id)
    return row


@router.patch("/api/memberships/{membership_id}")
def edit_membership(membership_id: int, data: MembershipBody, user: ADMIN, db: DB, request: Request):
    row = db.get(Membership, membership_id)
    if not row: raise HTTPException(404, "Membership not found")
    if not db.get(Member, data.member_id): raise HTTPException(404, "Member not found")
    if data.end_date < data.start_date: raise HTTPException(422, "End date cannot be before start date")
    if data.status not in {"active", "expired", "cancelled"}: raise HTTPException(422, "Invalid membership status")
    for key, value in data.model_dump().items(): setattr(row, key, value)
    db.add(row); db.commit(); audit(db, request, "membership_updated", user, "membership", row.id)
    return row


@router.delete("/api/memberships/{membership_id}", status_code=204)
def remove_membership(membership_id: int, user: ADMIN, db: DB, request: Request):
    row = db.get(Membership, membership_id)
    if not row: raise HTTPException(404, "Membership not found")
    db.delete(row); db.commit(); audit(db, request, "membership_deleted", user, "membership", membership_id)
    return Response(status_code=204)


# Attendance
def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@router.get("/api/attendance")
def attendance(user: CURRENT, db: DB, limit: int = Query(100, ge=1, le=200)):
    query = select(Attendance, Member).join(Member, Member.id == Attendance.member_id)
    if user.role != "admin":
        query = query.where(Attendance.member_id == get_my_member(db, user).id)
    rows = db.exec(query.order_by(Attendance.check_in.desc()).limit(limit)).all()
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


@router.post("/api/attendance", status_code=201)
def record_attendance(data: AttendanceBody, user: ADMIN, db: DB, request: Request):
    member = db.get(Member, data.member_id)
    if not member:
        raise HTTPException(404, "Member not found")
    if not member.is_active:
        raise HTTPException(409, "This member is inactive.")
    check_in = as_utc(data.check_in) or now()
    check_out = as_utc(data.check_out)
    if check_out and check_out <= check_in:
        raise HTTPException(422, "Check-out time must be after check-in time.")
    if check_out is None:
        open_visit = db.exec(
            select(Attendance).where(
                Attendance.member_id == data.member_id,
                Attendance.check_out.is_(None),
            )
        ).first()
        if open_visit:
            raise HTTPException(409, "This member is already checked in.")
    row = Attendance(
        member_id=data.member_id,
        check_in=check_in,
        check_out=check_out,
        notes=data.notes,
        recorded_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    audit(db, request, "attendance_recorded", user, "attendance", row.id)
    return row


@router.patch("/api/attendance/{attendance_id}/checkout")
def attendance_checkout(attendance_id: int, user: ADMIN, db: DB, request: Request):
    row = db.get(Attendance, attendance_id)
    if not row:
        raise HTTPException(404, "Attendance record not found")
    if row.check_out is not None:
        raise HTTPException(409, "This attendance visit is already checked out.")
    row.check_out = now()
    db.add(row)
    db.commit()
    audit(db, request, "attendance_checkout", user, "attendance", row.id)
    return row


# Member attendance correction requests, reviewed by an administrator.
def attendance_request_view(request_row: AttendanceRequest, member: Member, account: AppUser):
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


@router.get("/api/attendance/requests")
def list_attendance_requests(user: CURRENT, db: DB, status: str = ""):
    query = (
        select(AttendanceRequest, Member, AppUser)
        .join(Member, Member.id == AttendanceRequest.member_id)
        .join(AppUser, AppUser.id == AttendanceRequest.user_id)
    )
    if user.role != "admin":
        query = query.where(AttendanceRequest.user_id == user.id)
    if status in {"pending", "approved", "rejected"}:
        query = query.where(AttendanceRequest.status == status)
    rows = db.exec(query.order_by(AttendanceRequest.created_at.desc()).limit(100)).all()
    return [attendance_request_view(request_row, member, account) for request_row, member, account in rows]


@router.post("/api/attendance/requests", status_code=201)
def create_attendance_request(
    data: AttendanceRequestBody,
    user: CURRENT,
    db: DB,
    request: Request,
):
    if user.role != "user":
        raise HTTPException(403, "Attendance requests are for member accounts.")
    member = get_my_member(db, user)
    check_in = as_utc(data.requested_check_in)
    check_out = as_utc(data.requested_check_out)
    if check_out and check_out <= check_in:
        raise HTTPException(422, "Check-out time must be after check-in time.")
    duplicate = db.exec(
        select(AttendanceRequest).where(
            AttendanceRequest.user_id == user.id,
            AttendanceRequest.requested_check_in == check_in,
            AttendanceRequest.status == "pending",
        )
    ).first()
    if duplicate:
        raise HTTPException(409, "You already have a pending request for this check-in time.")
    row = AttendanceRequest(
        user_id=user.id,
        member_id=member.id,
        requested_check_in=check_in,
        requested_check_out=check_out,
        notes=data.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    audit(db, request, "attendance_request_created", user, "attendance_request", row.id)
    return {"id": row.id, "status": row.status, "requested_check_in": row.requested_check_in}


@router.patch("/api/attendance/requests/{request_id}")
def review_attendance_request(
    request_id: int,
    data: AttendanceRequestReview,
    user: ADMIN,
    db: DB,
    request: Request,
):
    request_row = db.get(AttendanceRequest, request_id)
    if not request_row:
        raise HTTPException(404, "Attendance request not found")
    if request_row.status != "pending":
        raise HTTPException(409, "This attendance request has already been reviewed.")
    if data.status == "approved":
        member = db.get(Member, request_row.member_id)
        if not member or not member.is_active:
            raise HTTPException(409, "The linked member is missing or inactive.")
        if request_row.requested_check_out is None:
            open_visit = db.exec(
                select(Attendance).where(
                    Attendance.member_id == request_row.member_id,
                    Attendance.check_out.is_(None),
                )
            ).first()
            if open_visit:
                raise HTTPException(409, "This member already has an open attendance visit.")
        visit = Attendance(
            member_id=request_row.member_id,
            check_in=request_row.requested_check_in,
            check_out=request_row.requested_check_out,
            notes=("Member request: " + request_row.notes).strip()[:500],
            recorded_by=user.id,
        )
        db.add(visit)
        db.flush()
        request_row.attendance_id = visit.id
    request_row.status = data.status
    request_row.reviewed_by = user.id
    request_row.reviewed_at = now()
    request_row.review_note = data.review_note.strip()
    db.add(request_row)
    db.commit()
    db.refresh(request_row)
    audit(
        db, request, "attendance_request_" + data.status,
        user, "attendance_request", request_row.id, data.review_note,
    )
    return {"id": request_row.id, "status": request_row.status, "attendance_id": request_row.attendance_id}


@router.delete("/api/attendance/requests/{request_id}", status_code=204)
def remove_attendance_request(request_id: int, user: CURRENT, db: DB, request: Request):
    request_row = db.get(AttendanceRequest, request_id)
    if not request_row:
        raise HTTPException(404, "Attendance request not found")
    if user.role != "admin" and (
        request_row.user_id != user.id or request_row.status != "pending"
    ):
        raise HTTPException(403, "You can only cancel your own pending request.")
    db.delete(request_row)
    db.commit()
    audit(db, request, "attendance_request_removed", user, "attendance_request", request_id)
    return Response(status_code=204)


# Workout plans and assignments
@router.get("/api/workout-plans")
def workout_plans(user: CURRENT, db: DB):
    if user.role == "admin": return db.exec(select(WorkoutPlan).order_by(WorkoutPlan.created_at.desc())).all()
    my_id = get_my_member(db, user).id
    plan_ids = select(WorkoutAssignment.plan_id).where(WorkoutAssignment.member_id == my_id)
    return db.exec(select(WorkoutPlan).where(WorkoutPlan.id.in_(plan_ids))).all()


@router.post("/api/workout-plans", status_code=201)
def add_workout_plan(data: PlanBody, user: ADMIN, db: DB, request: Request):
    if data.level not in {"beginner", "intermediate", "advanced"}: raise HTTPException(422, "Invalid plan level")
    row = WorkoutPlan(**data.model_dump(), created_by=user.id)
    db.add(row); db.commit(); db.refresh(row); audit(db, request, "workout_plan_created", user, "workout_plan", row.id)
    return row


@router.put("/api/workout-plans/{plan_id}")
def edit_workout_plan(plan_id: int, data: PlanBody, user: ADMIN, db: DB, request: Request):
    row = db.get(WorkoutPlan, plan_id)
    if not row: raise HTTPException(404, "Workout plan not found")
    if data.level not in {"beginner", "intermediate", "advanced"}: raise HTTPException(422, "Invalid plan level")
    for key, value in data.model_dump().items(): setattr(row, key, value)
    db.add(row); db.commit(); audit(db, request, "workout_plan_updated", user, "workout_plan", row.id)
    return row


@router.delete("/api/workout-plans/{plan_id}", status_code=204)
def remove_workout_plan(plan_id: int, user: ADMIN, db: DB, request: Request):
    row = db.get(WorkoutPlan, plan_id)
    if not row:
        raise HTTPException(404, "Workout plan not found")
    assigned_work = db.exec(
        select(WorkoutAssignment).where(WorkoutAssignment.plan_id == plan_id)
    ).first()
    if assigned_work:
        raise HTTPException(409, "This workout plan has member assignments. Remove those assignments first.")
    db.delete(row)
    db.commit()
    audit(db, request, "workout_plan_deleted", user, "workout_plan", plan_id)
    return Response(status_code=204)


@router.get("/api/workout-assignments")
def workout_assignments(user: CURRENT, db: DB):
    query = select(WorkoutAssignment).order_by(WorkoutAssignment.created_at.desc())
    if user.role != "admin": query = query.where(WorkoutAssignment.member_id == get_my_member(db, user).id)
    return db.exec(query).all()


@router.post("/api/workout-assignments", status_code=201)
def create_workout_assignment(data: AssignmentBody, user: ADMIN, db: DB, request: Request):
    if not db.get(WorkoutPlan, data.plan_id) or not db.get(Member, data.member_id):
        raise HTTPException(404, "Plan or member not found")
    if data.trainer_id and not db.get(Trainer, data.trainer_id): raise HTTPException(404, "Trainer not found")
    duplicate_query = select(WorkoutAssignment).where(
        WorkoutAssignment.member_id == data.member_id,
        WorkoutAssignment.plan_id == data.plan_id,
        WorkoutAssignment.status == data.status,
    )
    if data.trainer_id is None:
        duplicate_query = duplicate_query.where(WorkoutAssignment.trainer_id.is_(None))
    else:
        duplicate_query = duplicate_query.where(WorkoutAssignment.trainer_id == data.trainer_id)
    if db.exec(duplicate_query).first():
        raise HTTPException(409, "This workout plan is already assigned to this member and trainer.")
    row = WorkoutAssignment(**data.model_dump(), assigned_by=user.id)
    db.add(row); db.commit(); db.refresh(row)
    audit(db, request, "workout_assigned", user, "workout_assignment", row.id)
    return row


@router.delete("/api/workout-assignments/{assignment_id}", status_code=204)
def remove_workout_assignment(assignment_id: int, user: ADMIN, db: DB, request: Request):
    row = db.get(WorkoutAssignment, assignment_id)
    if not row: raise HTTPException(404, "Assignment not found")
    db.delete(row); db.commit(); audit(db, request, "workout_assignment_deleted", user, "workout_assignment", assignment_id)
    return Response(status_code=204)
