from fastapi import APIRouter, Request, Response

try:
    from backend.core.audit import audit
    from backend.core.dependencies import ADMIN, CURRENT, DB
    from backend.schemas.resources import MembershipBody
    from backend.services import membership_service
except ModuleNotFoundError:
    from core.audit import audit
    from core.dependencies import ADMIN, CURRENT, DB
    from schemas.resources import MembershipBody
    from services import membership_service


router = APIRouter(prefix="/api/memberships", tags=["memberships"])


@router.get("")
def list_memberships(user: CURRENT, db: DB):
    return membership_service.list_membership_records(db, user)


@router.post("", status_code=201)
def create_membership(
    payload: MembershipBody,
    user: ADMIN,
    db: DB,
    request: Request,
):
    membership = membership_service.create_membership(db, payload)
    audit(db, request, "membership_created", user, "membership", membership.id)
    return membership


@router.patch("/{membership_id}")
def update_membership(
    membership_id: int,
    payload: MembershipBody,
    user: ADMIN,
    db: DB,
    request: Request,
):
    membership = membership_service.update_membership(db, membership_id, payload)
    audit(db, request, "membership_updated", user, "membership", membership.id)
    return membership


@router.delete("/{membership_id}", status_code=204)
def delete_membership(
    membership_id: int,
    user: ADMIN,
    db: DB,
    request: Request,
):
    membership_service.delete_membership(db, membership_id)
    audit(db, request, "membership_deleted", user, "membership", membership_id)
    return Response(status_code=204)
