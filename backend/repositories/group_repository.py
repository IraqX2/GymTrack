"""Database access for shared groups and group work."""

from sqlmodel import Session, select

try:
    from backend.models.resources import GymGroup, GymGroupMember, GymGroupTask
    from backend.models.user import AppUser
except ModuleNotFoundError:
    from models.resources import GymGroup, GymGroupMember, GymGroupTask
    from models.user import AppUser


def get_membership(session: Session, group_id: int, user_id: int) -> GymGroupMember | None:
    return session.get(GymGroupMember, (group_id, user_id))


def get_group(session: Session, group_id: int) -> GymGroup | None:
    return session.get(GymGroup, group_id)


def get_group_task(session: Session, group_id: int, work_id: int) -> GymGroupTask | None:
    task = session.get(GymGroupTask, work_id)
    return task if task and task.group_id == group_id else None


def find_user_by_email(session: Session, email: str) -> AppUser | None:
    return session.exec(select(AppUser).where(AppUser.email == email)).first()


def list_groups_for_user(session: Session, user_id: int):
    statement = (
        select(GymGroup, GymGroupMember)
        .join(GymGroupMember, GymGroupMember.group_id == GymGroup.id)
        .where(GymGroupMember.user_id == user_id)
        .order_by(GymGroup.created_at.desc())
    )
    return list(session.exec(statement).all())


def list_group_members(session: Session, group_id: int):
    statement = (
        select(GymGroupMember, AppUser)
        .join(AppUser, AppUser.id == GymGroupMember.user_id)
        .where(GymGroupMember.group_id == group_id)
        .order_by(GymGroupMember.joined_at)
    )
    return list(session.exec(statement).all())


def list_group_tasks(session: Session, group_id: int) -> list[GymGroupTask]:
    statement = (
        select(GymGroupTask)
        .where(GymGroupTask.group_id == group_id)
        .order_by(GymGroupTask.created_at.desc())
    )
    return list(session.exec(statement).all())


def save(session: Session, record):
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def delete_group_records(session: Session, group_id: int, group: GymGroup) -> None:
    for task in session.exec(select(GymGroupTask).where(GymGroupTask.group_id == group_id)).all():
        session.delete(task)
    for member in session.exec(select(GymGroupMember).where(GymGroupMember.group_id == group_id)).all():
        session.delete(member)
    session.delete(group)
    session.commit()
