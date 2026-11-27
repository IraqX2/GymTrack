from sqlmodel import Session, select

from backend.models.member import Member
from backend.models.trainer import Trainer
from backend.models.trainer_progress import WorkoutProgress
from backend.models.workout import WorkoutAssignment, WorkoutPlan


def list_trainers(session: Session) -> list[Trainer]:
    statement = select(Trainer).order_by(Trainer.full_name)
    return list(session.exec(statement).all())


def find_trainer_by_email(session: Session, email: str) -> Trainer | None:
    return session.exec(
        select(Trainer).where(Trainer.email == email.strip().lower())
    ).first()


def find_trainer_by_id(session: Session, trainer_id: int) -> Trainer | None:
    return session.get(Trainer, trainer_id)


def add_trainer(session: Session, trainer: Trainer) -> Trainer:
    session.add(trainer)
    session.flush()
    session.refresh(trainer)
    return trainer


def list_assignments_for_trainer(session: Session, trainer_id: int):
    statement = (
        select(WorkoutAssignment, WorkoutPlan, Member)
        .join(WorkoutPlan, WorkoutPlan.id == WorkoutAssignment.plan_id)
        .join(Member, Member.id == WorkoutAssignment.member_id)
        .where(WorkoutAssignment.trainer_id == trainer_id)
        .order_by(WorkoutAssignment.created_at.desc())
    )
    return list(session.exec(statement).all())


def find_assignment(session: Session, assignment_id: int) -> WorkoutAssignment | None:
    return session.get(WorkoutAssignment, assignment_id)


def list_progress_for_assignment(
    session: Session,
    assignment_id: int,
    limit: int = 20,
) -> list[WorkoutProgress]:
    statement = (
        select(WorkoutProgress)
        .where(WorkoutProgress.assignment_id == assignment_id)
        .order_by(WorkoutProgress.recorded_at.desc())
        .limit(limit)
    )
    return list(session.exec(statement).all())


def add_progress(session: Session, progress: WorkoutProgress) -> WorkoutProgress:
    session.add(progress)
    session.commit()
    session.refresh(progress)
    return progress


def delete_trainer(session: Session, trainer: Trainer) -> None:
    session.delete(trainer)
    session.commit()
