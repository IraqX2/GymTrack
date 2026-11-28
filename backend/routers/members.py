from fastapi import APIRouter, Query, Request, Response

try:
    from backend.core.audit import audit
    from backend.core.dependencies import ADMIN, CURRENT, DB
    from backend.schemas.member import MemberCreate, MemberUpdate
    from backend.services import member_service
except ModuleNotFoundError:
    from core.audit import audit
    from core.dependencies import ADMIN, CURRENT, DB
    from schemas.member import MemberCreate, MemberUpdate
    from services import member_service


router = APIRouter(tags=["members"])


@router.get("/api/members")
def list_members(
    user: CURRENT,
    db: DB,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    return member_service.list_member_records(db, user, offset=offset, limit=limit)


@router.post("/api/members", status_code=201)
def create_member(payload: MemberCreate, user: ADMIN, db: DB, request: Request):
    member = member_service.create_member_record(db, payload, created_by=user.id)
    audit(db, request, "member_created", user, "member", member.id)
    return member


@router.get("/api/members/{member_id}")
def get_member(member_id: int, user: CURRENT, db: DB):
    return member_service.get_member_record(db, member_id, user)


@router.put("/api/members/{member_id}")
def update_member(
    member_id: int,
    payload: MemberUpdate,
    user: ADMIN,
    db: DB,
    request: Request,
):
    member = member_service.update_member_record(db, member_id, payload)
    audit(db, request, "member_updated", user, "member", member.id)
    return member


@router.delete("/api/members/{member_id}", status_code=204)
def delete_member(member_id: int, user: ADMIN, db: DB, request: Request):
    member_service.delete_member_record(db, member_id)
    audit(db, request, "member_deleted", user, "member", member_id)
    return Response(status_code=204)

@router.get("/api/member/dashboard")
def member_dashboard(user: CURRENT, db: DB):
    return member_service.get_member_dashboard(db, user)
