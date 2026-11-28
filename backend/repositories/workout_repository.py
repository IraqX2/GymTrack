"""Database queries for workout plans and assignments."""

from sqlmodel import Session, select

try:
    from backend.models.member import Member
    from backend.models.trainer import Trainer
    from backend.models.workout import WorkoutAssignment, WorkoutPlan
except ModuleNotFoundError:
    from models.member import Member
    from models.trainer import Trainer
    from models.workout import WorkoutAssignment, WorkoutPlan


def member_for_account(session: Session, user_id: int) -> Member | None:
    return session.exec(select(Member).where(Member.user_id == user_id)).first()


def list_all_plans(session: Session):
    return list(session.exec(select(WorkoutPlan).order_by(WorkoutPlan.created_at.desc())).all())


def list_plans_for_member(session: Session, member_id: int):
    plan_ids = select(WorkoutAssignment.plan_id).where(WorkoutAssignment.member_id == member_id)
    return list(session.exec(select(WorkoutPlan).where(WorkoutPlan.id.in_(plan_ids))).all())


def get_plan(session: Session, plan_id: int) -> WorkoutPlan | None:
    return session.get(WorkoutPlan, plan_id)


def get_member(session: Session, member_id: int) -> Member | None:
    return session.get(Member, member_id)


def get_trainer(session: Session, trainer_id: int) -> Trainer | None:
    return session.get(Trainer, trainer_id)


def save_plan(session: Session, plan: WorkoutPlan) -> WorkoutPlan:
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def delete_plan(session: Session, plan: WorkoutPlan) -> None:
    session.delete(plan)
    session.commit()


def has_plan_assignments(session: Session, plan_id: int) -> bool:
    return session.exec(
        select(WorkoutAssignment.id).where(WorkoutAssignment.plan_id == plan_id)
    ).first() is not None


def list_assignments(session: Session, member_id: int | None):
    statement = select(WorkoutAssignment).order_by(WorkoutAssignment.created_at.desc())
    if member_id is not None:
        statement = statement.where(WorkoutAssignment.member_id == member_id)
    return list(session.exec(statement).all())


def find_duplicate_assignment(
    session: Session,
    member_id: int,
    plan_id: int,
    trainer_id: int | None,
    status: str,
) -> WorkoutAssignment | None:
    statement = select(WorkoutAssignment).where(
        WorkoutAssignment.member_id == member_id,
        WorkoutAssignment.plan_id == plan_id,
        WorkoutAssignment.status == status,
    )
    if trainer_id is None:
        statement = statement.where(WorkoutAssignment.trainer_id.is_(None))
    else:
        statement = statement.where(WorkoutAssignment.trainer_id == trainer_id)
    return session.exec(statement).first()


def get_assignment(session: Session, assignment_id: int) -> WorkoutAssignment | None:
    return session.get(WorkoutAssignment, assignment_id)


def save_assignment(session: Session, assignment: WorkoutAssignment) -> WorkoutAssignment:
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    return assignment


def delete_assignment(session: Session, assignment: WorkoutAssignment) -> None:
    session.delete(assignment)
    session.commit()
