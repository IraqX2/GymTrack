"""Domain API controllers. HTTP concerns live here; shared models/dependencies live in gymtrack_api."""
from fastapi import APIRouter

try:
    from backend.gymtrack_api import *
except ModuleNotFoundError:
    from gymtrack_api import *

router = APIRouter()


# Shared groups with server-side create/edit/assign checks. Only owners manage membership and delete.
@router.get("/api/groups")
def list_groups(user: CURRENT, db: DB):
    ids = select(GymGroupMember.group_id).where(GymGroupMember.user_id == user.id)
    rows = db.exec(select(GymGroup).where(GymGroup.id.in_(ids))).all()
    return [{"id": g.id, "name": g.name, "created_by": g.created_by,
             "my_role": get_group_member(db, g.id, user.id).role} for g in rows]


@router.post("/api/groups", status_code=201)
def create_group(data: GroupBody, user: ADMIN, db: DB, request: Request):
    row = GymGroup(name=data.name, created_by=user.id)
    db.add(row); db.commit(); db.refresh(row)
    db.add(GymGroupMember(group_id=row.id, user_id=user.id, role="owner", can_create=True, can_edit=True, can_assign=True))
    db.commit(); audit(db, request, "group_created", user, "group", row.id)
    return {"id": row.id, "name": row.name, "my_role": "owner"}


@router.patch("/api/groups/{group_id}")
def rename_group(group_id: int, data: GroupBody, user: CURRENT, db: DB, request: Request):
    membership = get_group_member(db, group_id, user.id)
    if membership.role != "owner":
        raise HTTPException(403, "Only the group owner can rename this group")
    group = db.get(GymGroup, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    group.name = data.name.strip()
    db.add(group)
    db.commit()
    audit(db, request, "group_renamed", user, "group", group_id, group.name)
    return {"id": group.id, "name": group.name, "my_role": membership.role}


@router.delete("/api/groups/{group_id}", status_code=204)
def delete_group(group_id: int, user: CURRENT, db: DB, request: Request):
    membership = get_group_member(db, group_id, user.id)
    if membership.role != "owner":
        raise HTTPException(403, "Only the group owner can delete this group")
    group = db.get(GymGroup, group_id)
    if not group:
        raise HTTPException(404, "Group not found")
    for task in db.exec(select(GymGroupTask).where(GymGroupTask.group_id == group_id)).all():
        db.delete(task)
    for group_member in db.exec(select(GymGroupMember).where(GymGroupMember.group_id == group_id)).all():
        db.delete(group_member)
    db.delete(group)
    db.commit()
    audit(db, request, "group_deleted", user, "group", group_id, group.name)
    return Response(status_code=204)


@router.get("/api/groups/{group_id}/members")
def group_members(group_id: int, user: CURRENT, db: DB):
    get_group_member(db, group_id, user.id)
    rows = db.exec(select(GymGroupMember, AppUser).join(AppUser, AppUser.id == GymGroupMember.user_id)
                   .where(GymGroupMember.group_id == group_id)).all()
    return [{"user_id": m.user_id, "full_name": u.full_name, "email": u.email, "role": m.role,
             "can_create": m.can_create, "can_edit": m.can_edit, "can_assign": m.can_assign} for m, u in rows]


@router.post("/api/groups/{group_id}/members", status_code=201)
def add_group_member(group_id: int, data: GroupMemberBody, user: CURRENT, db: DB, request: Request):
    owner = get_group_member(db, group_id, user.id)
    if owner.role != "owner": raise HTTPException(403, "Only the group owner can add members")
    target = db.exec(select(AppUser).where(AppUser.email == str(data.email).lower())).first()
    if not target: raise HTTPException(404, "No GymTrack account exists for this email")
    if db.get(GymGroupMember, (group_id, target.id)): raise HTTPException(409, "Already a group member")
    row = GymGroupMember(group_id=group_id, user_id=target.id, role="member",
                         can_create=data.can_create, can_edit=data.can_edit, can_assign=data.can_assign)
    db.add(row); db.commit(); audit(db, request, "group_member_added", user, "group", group_id, target.email)
    return {"user_id": target.id, "full_name": target.full_name, "email": target.email, "role": "member",
            "can_create": row.can_create, "can_edit": row.can_edit, "can_assign": row.can_assign}


@router.patch("/api/groups/{group_id}/members/{target_id}")
def group_permissions(group_id: int, target_id: int, data: GroupPermissions,
                      user: CURRENT, db: DB, request: Request):
    owner = get_group_member(db, group_id, user.id)
    if owner.role != "owner": raise HTTPException(403, "Only the group owner manages permissions")
    target = get_group_member(db, group_id, target_id)
    if target.role == "owner": raise HTTPException(400, "Owner permissions cannot be changed")
    for key, value in data.model_dump().items(): setattr(target, key, value)
    db.add(target); db.commit(); audit(db, request, "group_permissions_changed", user, "group", group_id)
    return {"user_id": target_id, **data.model_dump()}


@router.delete("/api/groups/{group_id}/members/{target_id}", status_code=204)
def remove_group_member(group_id: int, target_id: int, user: CURRENT, db: DB, request: Request):
    actor = get_group_member(db, group_id, user.id)
    target = get_group_member(db, group_id, target_id)
    if actor.role != "owner" and target_id != user.id: raise HTTPException(403, "Only owner can remove others")
    if target.role == "owner": raise HTTPException(400, "Owner cannot leave; delete the group instead")
    db.delete(target); db.commit(); audit(db, request, "group_member_removed", user, "group", group_id, str(target_id))
    return Response(status_code=204)


@router.get("/api/groups/{group_id}/work")
def list_group_work(group_id: int, user: CURRENT, db: DB):
    get_group_member(db, group_id, user.id)
    return db.exec(select(GymGroupTask).where(GymGroupTask.group_id == group_id)
                   .order_by(GymGroupTask.created_at.desc())).all()


@router.post("/api/groups/{group_id}/work", status_code=201)
def create_group_work(group_id: int, data: GroupWorkBody, user: CURRENT, db: DB, request: Request):
    member = get_group_member(db, group_id, user.id); group_allow(member, "create")
    if data.assigned_to is not None:
        group_allow(member, "assign")
        if not db.get(GymGroupMember, (group_id, data.assigned_to)): raise HTTPException(422, "Assignee is not a group member")
    row = GymGroupTask(**data.model_dump(), group_id=group_id, created_by=user.id)
    db.add(row); db.commit(); db.refresh(row); audit(db, request, "group_work_created", user, "group_work", row.id)
    return row


@router.patch("/api/groups/{group_id}/work/{work_id}")
def edit_group_work(group_id: int, work_id: int, data: GroupWorkPatch,
                    user: CURRENT, db: DB, request: Request):
    member = get_group_member(db, group_id, user.id)
    row = db.get(GymGroupTask, work_id)
    if not row or row.group_id != group_id: raise HTTPException(404, "Group work not found")
    changes = data.model_dump(exclude_unset=True)
    if "assigned_to" in changes:
        group_allow(member, "assign")
        if changes["assigned_to"] is not None and not db.get(GymGroupMember, (group_id, changes["assigned_to"])):
            raise HTTPException(422, "Assignee is not a group member")
    if member.role != "owner" and row.created_by != user.id: group_allow(member, "edit")
    for key, value in changes.items(): setattr(row, key, value)
    row.updated_at = now(); db.add(row); db.commit()
    audit(db, request, "group_work_updated", user, "group_work", row.id)
    return row


@router.delete("/api/groups/{group_id}/work/{work_id}", status_code=204)
def delete_group_work(group_id: int, work_id: int, user: CURRENT, db: DB, request: Request):
    member = get_group_member(db, group_id, user.id)
    if member.role != "owner": raise HTTPException(403, "Only owner can delete group work")
    row = db.get(GymGroupTask, work_id)
    if not row or row.group_id != group_id: raise HTTPException(404, "Group work not found")
    db.delete(row); db.commit(); audit(db, request, "group_work_deleted", user, "group_work", work_id)
    return Response(status_code=204)
