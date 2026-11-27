"""Database queries for trainer accounts, assigned workouts and progress."""
from sqlmodel import Session, select

try:
    from backend.gymtrack_api import (
        AppUser,
        Trainer,
        WorkoutAssignment,
        WorkoutPlan,
        WorkoutProgress,
        Member,
    )
except ModuleNotFoundError:
    from gymtrack_api import (
        AppUser,
        Trainer,
        WorkoutAssignment,
        WorkoutPlan,
        WorkoutProgress,
        Member,
    )


def account_by_email(session: Session, email: str) -> AppUser | None:
    return session.exec(select(AppUser).where(AppUser.email == email.lower())).first()


def trainer_by_user_id(session: Session, user_id: int) -> Trainer | None:
    return session.exec(
        select(Trainer).where(Trainer.user_id == user_id, Trainer.is_active.is_(True))
    ).first()


def trainer_by_id(session: Session, trainer_id: int) -> Trainer | None:
    return session.get(Trainer, trainer_id)


def trainer_by_email(session: Session, email: str) -> Trainer | None:
    return session.exec(select(Trainer).where(Trainer.email == email.lower())).first()


def trainers(session: Session) -> list[Trainer]:
    return session.exec(select(Trainer).order_by(Trainer.full_name)).all()


def create_trainer(session: Session, trainer: Trainer) -> Trainer:
    session.add(trainer)
    session.commit()
    session.refresh(trainer)
    return trainer


def update_trainer(session: Session, trainer: Trainer) -> Trainer:
    session.add(trainer)
    session.commit()
    session.refresh(trainer)
    return trainer


def assigned_workouts(session: Session, trainer_id: int):
    statement = (
        select(WorkoutAssignment, WorkoutPlan, Member)
        .join(WorkoutPlan, WorkoutPlan.id == WorkoutAssignment.plan_id)
        .join(Member, Member.id == WorkoutAssignment.member_id)
        .where(WorkoutAssignment.trainer_id == trainer_id)
        .order_by(WorkoutAssignment.created_at.desc())
    )
    return session.exec(statement).all()


def assignment_for_trainer(
    session: Session, assignment_id: int, trainer_id: int
) -> WorkoutAssignment | None:
    return session.exec(
        select(WorkoutAssignment).where(
            WorkoutAssignment.id == assignment_id,
            WorkoutAssignment.trainer_id == trainer_id,
        )
    ).first()


def progress_for_assignment(session: Session, assignment_id: int) -> list[WorkoutProgress]:
    return session.exec(
        select(WorkoutProgress)
        .where(WorkoutProgress.assignment_id == assignment_id)
        .order_by(WorkoutProgress.progress_date.desc(), WorkoutProgress.created_at.desc())
    ).all()


def progress_for_trainer(session: Session, trainer_id: int) -> list[WorkoutProgress]:
    return session.exec(
        select(WorkoutProgress)
        .where(WorkoutProgress.trainer_id == trainer_id)
        .order_by(WorkoutProgress.progress_date.desc(), WorkoutProgress.created_at.desc())
        .limit(200)
    ).all()


def create_progress(session: Session, progress: WorkoutProgress) -> WorkoutProgress:
    session.add(progress)
    session.commit()
    session.refresh(progress)
    return progress
