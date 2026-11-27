"""Trainer use cases and business rules. No HTTP request handling belongs here."""
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session

try:
    from backend.gymtrack_api import AppUser, Trainer, WorkoutProgress
except ModuleNotFoundError:
    from gymtrack_api import AppUser, Trainer, WorkoutProgress

from . import repository
from .schemas import AssignmentStatusUpdate, ProgressCreate, TrainerCreate, TrainerUpdate


def active_trainer_for(user: AppUser, session: Session) -> Trainer:
    if user.role != "user":
        raise HTTPException(status_code=403, detail="Trainer access is only available to normal accounts.")
    trainer = repository.trainer_by_user_id(session, user.id)
    if trainer is None:
        raise HTTPException(status_code=403, detail="An active trainer profile is required.")
    return trainer


def list_trainers(session: Session):
    return repository.trainers(session)


def promote_account_to_trainer(payload: TrainerCreate, session: Session) -> Trainer:
    email = str(payload.email).lower()
    account = repository.account_by_email(session, email)
    if account is None:
        raise HTTPException(status_code=404, detail="Sign-up with this email before an administrator promotes the account.")
    if account.role != "user":
        raise HTTPException(status_code=409, detail="Only a normal user account can be promoted to trainer.")
    if account.is_banned:
        raise HTTPException(status_code=409, detail="A banned account cannot be activated as a trainer.")
    existing_trainer = repository.trainer_by_email(session, email)
    if existing_trainer is not None:
        if existing_trainer.user_id == account.id:
            raise HTTPException(status_code=409, detail="This account already has a trainer profile.")
        raise HTTPException(status_code=409, detail="A trainer profile already uses this email.")
    linked = repository.trainer_by_user_id(session, account.id)
    if linked is not None:
        raise HTTPException(status_code=409, detail="This account is already linked to a trainer profile.")

    trainer = Trainer(
        full_name=payload.full_name.strip(),
        email=email,
        phone=payload.phone.strip(),
        specialization=payload.specialization.strip(),
        is_active=payload.is_active,
        user_id=account.id,
    )
    return repository.create_trainer(session, trainer)


def update_trainer_profile(trainer_id: int, payload: TrainerUpdate, session: Session) -> Trainer:
    trainer = repository.trainer_by_id(session, trainer_id)
    if trainer is None:
        raise HTTPException(status_code=404, detail="Trainer profile not found.")
    email = str(payload.email).lower()
    owner = repository.account_by_email(session, email)
    if owner is None or owner.id != trainer.user_id:
        raise HTTPException(
            status_code=422,
            detail="Trainer email must remain the email of the linked GymTrack account.",
        )
    conflict = repository.trainer_by_email(session, email)
    if conflict is not None and conflict.id != trainer.id:
        raise HTTPException(status_code=409, detail="A trainer profile already uses this email.")

    trainer.full_name = payload.full_name.strip()
    trainer.phone = payload.phone.strip()
    trainer.specialization = payload.specialization.strip()
    trainer.is_active = payload.is_active
    return repository.update_trainer(session, trainer)


def deactivate_trainer(trainer_id: int, session: Session) -> Trainer:
    trainer = repository.trainer_by_id(session, trainer_id)
    if trainer is None:
        raise HTTPException(status_code=404, detail="Trainer profile not found.")
    trainer.is_active = False
    return repository.update_trainer(session, trainer)


def trainer_dashboard(user: AppUser, session: Session):
    trainer = active_trainer_for(user, session)
    result = []
    for assignment, plan, member in repository.assigned_workouts(session, trainer.id):
        result.append(
            {
                "assignment": assignment,
                "plan": plan,
                "member": member,
                "progress": repository.progress_for_assignment(session, assignment.id),
            }
        )
    return {"trainer": trainer, "assignments": result}


def trainer_progress(user: AppUser, session: Session):
    trainer = active_trainer_for(user, session)
    return repository.progress_for_trainer(session, trainer.id)


def add_assignment_progress(
    assignment_id: int,
    payload: ProgressCreate,
    user: AppUser,
    session: Session,
) -> WorkoutProgress:
    trainer = active_trainer_for(user, session)
    assignment = repository.assignment_for_trainer(session, assignment_id, trainer.id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assigned workout not found.")
    progress_date = payload.progress_date or date.today()
    row = WorkoutProgress(
        assignment_id=assignment.id,
        member_id=assignment.member_id,
        trainer_id=trainer.id,
        completion_percent=payload.completion_percent,
        notes=payload.notes.strip(),
        progress_date=progress_date,
    )
    return repository.create_progress(session, row)


def update_assigned_workout_status(
    assignment_id: int,
    payload: AssignmentStatusUpdate,
    user: AppUser,
    session: Session,
):
    trainer = active_trainer_for(user, session)
    assignment = repository.assignment_for_trainer(session, assignment_id, trainer.id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assigned workout not found.")
    assignment.status = payload.status
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    return assignment
