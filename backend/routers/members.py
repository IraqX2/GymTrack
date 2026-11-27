"""Domain API controllers. HTTP concerns live here; shared models/dependencies live in gymtrack_api."""
from fastapi import APIRouter

try:
    from backend.gymtrack_api import *
except ModuleNotFoundError:
    from gymtrack_api import *

router = APIRouter()


# Members
@router.get("/api/members")
def members(user: CURRENT, db: DB, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    query = select(Member).order_by(Member.id.desc()).offset(offset).limit(limit)
    if user.role != "admin": query = query.where(Member.user_id == user.id)
    return db.exec(query).all()


@router.post("/api/members", status_code=201)
def add_member(data: MemberBody, user: ADMIN, db: DB, request: Request):
    email = str(data.email).lower()
    if db.exec(select(Member).where(Member.email == email)).first():
        raise HTTPException(409, "Member email already exists")
    row = Member(**data.model_dump(exclude={"email"}), email=email, created_by=user.id)
    db.add(row); db.commit(); db.refresh(row); audit(db, request, "member_created", user, "member", row.id)
    return row


@router.get("/api/members/{member_id}")
def member_detail(member_id: int, user: CURRENT, db: DB):
    row = db.get(Member, member_id)
    if not row or (user.role != "admin" and row.user_id != user.id):
        raise HTTPException(404, "Member not found")
    return row


@router.put("/api/members/{member_id}")
def edit_member(member_id: int, data: MemberBody, user: ADMIN, db: DB, request: Request):
    row = db.get(Member, member_id)
    if not row: raise HTTPException(404, "Member not found")
    for key, value in data.model_dump().items(): setattr(row, key, str(value).lower() if key == "email" else value)
    db.add(row); db.commit(); audit(db, request, "member_updated", user, "member", row.id)
    return row


@router.delete("/api/members/{member_id}", status_code=204)
def remove_member(member_id: int, user: ADMIN, db: DB, request: Request):
    row = db.get(Member, member_id)
    if not row:
        raise HTTPException(404, "Member not found")
    has_membership = db.exec(select(Membership).where(Membership.member_id == member_id)).first()
    has_attendance = db.exec(select(Attendance).where(Attendance.member_id == member_id)).first()
    has_workout = db.exec(select(WorkoutAssignment).where(WorkoutAssignment.member_id == member_id)).first()
    if has_membership or has_attendance or has_workout:
        raise HTTPException(
            409,
            "This member has gym history. Mark the member inactive instead of deleting their records.",
        )
    db.delete(row)
    db.commit()
    audit(db, request, "member_deleted", user, "member", member_id)
    return Response(status_code=204)
