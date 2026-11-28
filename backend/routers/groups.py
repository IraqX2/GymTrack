from fastapi import APIRouter, Request, Response

try:
    from backend.core.audit import audit
    from backend.core.dependencies import ADMIN, CURRENT, DB
    from backend.schemas.resources import GroupBody, GroupMemberBody, GroupPermissions, GroupWorkBody, GroupWorkPatch
    from backend.services import group_service
except ModuleNotFoundError:
    from core.audit import audit
    from core.dependencies import ADMIN, CURRENT, DB
    from schemas.resources import GroupBody, GroupMemberBody, GroupPermissions, GroupWorkBody, GroupWorkPatch
    from services import group_service


router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("")
def list_groups(user: CURRENT, db: DB):
    return group_service.list_groups(db, user.id)


@router.post("", status_code=201)
def create_group(payload: GroupBody, user: ADMIN, db: DB, request: Request):
    group = group_service.create_group(db, user.id, payload)
    audit(db, request, "group_created", user, "group", group["id"])
    return group


@router.patch("/{group_id}")
def rename_group(group_id: int, payload: GroupBody, user: CURRENT, db: DB, request: Request):
    group = group_service.rename_group(db, group_id, user.id, payload)
    audit(db, request, "group_renamed", user, "group", group_id, group["name"])
    return group


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, user: CURRENT, db: DB, request: Request):
    group_name = group_service.delete_group(db, group_id, user.id)
    audit(db, request, "group_deleted", user, "group", group_id, group_name)
    return Response(status_code=204)


@router.get("/{group_id}/members")
def list_group_members(group_id: int, user: CURRENT, db: DB):
    return group_service.list_members(db, group_id, user.id)


@router.post("/{group_id}/members", status_code=201)
def add_group_member(
    group_id: int,
    payload: GroupMemberBody,
    user: CURRENT,
    db: DB,
    request: Request,
):
    member = group_service.add_member(db, group_id, user.id, payload)
    audit(db, request, "group_member_added", user, "group", group_id, member["email"])
    return member


@router.patch("/{group_id}/members/{target_id}")
def update_group_permissions(
    group_id: int,
    target_id: int,
    payload: GroupPermissions,
    user: CURRENT,
    db: DB,
    request: Request,
):
    result = group_service.update_permissions(db, group_id, user.id, target_id, payload)
    audit(db, request, "group_permissions_changed", user, "group", group_id)
    return result


@router.delete("/{group_id}/members/{target_id}", status_code=204)
def remove_group_member(
    group_id: int,
    target_id: int,
    user: CURRENT,
    db: DB,
    request: Request,
):
    group_service.remove_member(db, group_id, user.id, target_id)
    audit(db, request, "group_member_removed", user, "group", group_id, str(target_id))
    return Response(status_code=204)


@router.get("/{group_id}/work")
def list_group_work(group_id: int, user: CURRENT, db: DB):
    return group_service.list_work(db, group_id, user.id)


@router.post("/{group_id}/work", status_code=201)
def create_group_work(
    group_id: int,
    payload: GroupWorkBody,
    user: CURRENT,
    db: DB,
    request: Request,
):
    work = group_service.create_work(db, group_id, user.id, payload)
    audit(db, request, "group_work_created", user, "group_work", work.id)
    return work


@router.patch("/{group_id}/work/{work_id}")
def edit_group_work(
    group_id: int,
    work_id: int,
    payload: GroupWorkPatch,
    user: CURRENT,
    db: DB,
    request: Request,
):
    work = group_service.edit_work(db, group_id, work_id, user.id, payload)
    audit(db, request, "group_work_updated", user, "group_work", work.id)
    return work


@router.delete("/{group_id}/work/{work_id}", status_code=204)
def delete_group_work(
    group_id: int,
    work_id: int,
    user: CURRENT,
    db: DB,
    request: Request,
):
    group_service.delete_work(db, group_id, work_id, user.id)
    audit(db, request, "group_work_deleted", user, "group_work", work_id)
    return Response(status_code=204)
