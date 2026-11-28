"""Group ownership and fine-grained permission rules."""

from fastapi import HTTPException
from sqlmodel import Session

try:
    from backend.models.resources import GymGroup, GymGroupMember, GymGroupTask
    from backend.repositories import group_repository as repository
    from backend.schemas.resources import GroupBody, GroupMemberBody, GroupPermissions, GroupWorkBody, GroupWorkPatch
except ModuleNotFoundError:
    from models.resources import GymGroup, GymGroupMember, GymGroupTask
    from repositories import group_repository as repository
    from schemas.resources import GroupBody, GroupMemberBody, GroupPermissions, GroupWorkBody, GroupWorkPatch


def _membership(session: Session, group_id: int, user_id: int) -> GymGroupMember:
    membership = repository.get_membership(session, group_id, user_id)
    if membership is None:
        raise HTTPException(404, "Group not found")
    return membership


def _allow(membership: GymGroupMember, permission: str) -> None:
    if membership.role == "owner":
        return
    enabled = {
        "create": membership.can_create,
        "edit": membership.can_edit,
        "assign": membership.can_assign,
    }.get(permission, False)
    if not enabled:
        raise HTTPException(403, f"Group permission denied: {permission}")


def list_groups(session: Session, user_id: int):
    rows = repository.list_groups_for_user(session, user_id)
    return [
        {"id": group.id, "name": group.name, "created_by": group.created_by, "my_role": membership.role}
        for group, membership in rows
    ]


def create_group(session: Session, user_id: int, payload: GroupBody):
    group = GymGroup(name=payload.name.strip(), created_by=user_id)
    session.add(group)
    session.commit()
    session.refresh(group)
    membership = GymGroupMember(
        group_id=group.id, user_id=user_id, role="owner",
        can_create=True, can_edit=True, can_assign=True,
    )
    session.add(membership)
    session.commit()
    return {"id": group.id, "name": group.name, "my_role": "owner"}


def rename_group(session: Session, group_id: int, user_id: int, payload: GroupBody):
    membership = _membership(session, group_id, user_id)
    if membership.role != "owner":
        raise HTTPException(403, "Only the group owner can rename this group")
    group = repository.get_group(session, group_id)
    if group is None:
        raise HTTPException(404, "Group not found")
    group.name = payload.name.strip()
    repository.save(session, group)
    return {"id": group.id, "name": group.name, "my_role": membership.role}


def delete_group(session: Session, group_id: int, user_id: int) -> str:
    membership = _membership(session, group_id, user_id)
    if membership.role != "owner":
        raise HTTPException(403, "Only the group owner can delete this group")
    group = repository.get_group(session, group_id)
    if group is None:
        raise HTTPException(404, "Group not found")
    group_name = group.name
    repository.delete_group_records(session, group_id, group)
    return group_name


def list_members(session: Session, group_id: int, user_id: int):
    _membership(session, group_id, user_id)
    rows = repository.list_group_members(session, group_id)
    return [
        {
            "user_id": member.user_id, "full_name": account.full_name, "email": account.email,
            "role": member.role, "can_create": member.can_create,
            "can_edit": member.can_edit, "can_assign": member.can_assign,
        }
        for member, account in rows
    ]


def add_member(session: Session, group_id: int, user_id: int, payload: GroupMemberBody):
    owner = _membership(session, group_id, user_id)
    if owner.role != "owner":
        raise HTTPException(403, "Only the group owner can add members")
    target = repository.find_user_by_email(session, str(payload.email).lower())
    if target is None:
        raise HTTPException(404, "No GymTrack account exists for this email")
    if repository.get_membership(session, group_id, target.id):
        raise HTTPException(409, "Already a group member")
    row = GymGroupMember(
        group_id=group_id, user_id=target.id, role="member",
        can_create=payload.can_create, can_edit=payload.can_edit, can_assign=payload.can_assign,
    )
    session.add(row)
    session.commit()
    return {
        "user_id": target.id, "full_name": target.full_name, "email": target.email, "role": "member",
        "can_create": row.can_create, "can_edit": row.can_edit, "can_assign": row.can_assign,
    }


def update_permissions(session: Session, group_id: int, actor_id: int, target_id: int, payload: GroupPermissions):
    owner = _membership(session, group_id, actor_id)
    if owner.role != "owner":
        raise HTTPException(403, "Only the group owner manages permissions")
    target = _membership(session, group_id, target_id)
    if target.role == "owner":
        raise HTTPException(400, "Owner permissions cannot be changed")
    for key, value in payload.model_dump().items():
        setattr(target, key, value)
    repository.save(session, target)
    return {"user_id": target_id, **payload.model_dump()}


def remove_member(session: Session, group_id: int, actor_id: int, target_id: int) -> None:
    actor = _membership(session, group_id, actor_id)
    target = _membership(session, group_id, target_id)
    if actor.role != "owner" and target_id != actor_id:
        raise HTTPException(403, "Only owner can remove others")
    if target.role == "owner":
        raise HTTPException(400, "Owner cannot leave; delete the group instead")
    session.delete(target)
    session.commit()


def list_work(session: Session, group_id: int, user_id: int):
    _membership(session, group_id, user_id)
    return repository.list_group_tasks(session, group_id)


def create_work(session: Session, group_id: int, user_id: int, payload: GroupWorkBody):
    membership = _membership(session, group_id, user_id)
    _allow(membership, "create")
    if payload.assigned_to is not None:
        _allow(membership, "assign")
        if repository.get_membership(session, group_id, payload.assigned_to) is None:
            raise HTTPException(422, "Assignee is not a group member")
    task = GymGroupTask(**payload.model_dump(), group_id=group_id, created_by=user_id)
    return repository.save(session, task)


def edit_work(session: Session, group_id: int, work_id: int, user_id: int, payload: GroupWorkPatch):
    membership = _membership(session, group_id, user_id)
    task = repository.get_group_task(session, group_id, work_id)
    if task is None:
        raise HTTPException(404, "Group work not found")
    changes = payload.model_dump(exclude_unset=True)
    if "assigned_to" in changes:
        _allow(membership, "assign")
        if changes["assigned_to"] is not None and repository.get_membership(
            session, group_id, changes["assigned_to"]
        ) is None:
            raise HTTPException(422, "Assignee is not a group member")
    if membership.role != "owner" and task.created_by != user_id:
        _allow(membership, "edit")
    for key, value in changes.items():
        setattr(task, key, value)
    return repository.save(session, task)


def delete_work(session: Session, group_id: int, work_id: int, user_id: int) -> None:
    membership = _membership(session, group_id, user_id)
    if membership.role != "owner":
        raise HTTPException(403, "Only owner can delete group work")
    task = repository.get_group_task(session, group_id, work_id)
    if task is None:
        raise HTTPException(404, "Group work not found")
    session.delete(task)
    session.commit()
