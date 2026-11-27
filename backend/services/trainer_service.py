from fastapi import HTTPException
from sqlmodel import Session, select

try:
    from backend.models.member import Member
    from backend.models.trainer import Trainer
    from backend.models.trainer_progress import WorkoutProgress
    from backend.models.workout import WorkoutAssignment
    from backend.repositories import trainer_repository as repository
    from backend.schemas.trainer import TrainerPayload, TrainerProgressCreate
except ModuleNotFoundError:
    from models.member import Member
    from models.trainer import Trainer
    from models.trainer_progress import WorkoutProgress
    from models.workout import WorkoutAssignment
    from repositories import trainer_repository as repository
    from schemas.trainer import TrainerPayload, TrainerProgressCreate


def list_trainer_records(session: Session) -> list[Trainer]:
    return repository.list_trainers(session)


def create_trainer_record(session: Session, payload: TrainerPayload) -> Trainer:
    email = str(payload.email).strip().lower()
    if repository.find_trainer_by_email(session, email):
        raise HTTPException(status_code=409, detail="A trainer with this email already exists.")

    trainer = Trainer(**payload.model_dump(exclude={"email"}), email=email)
    repository.add_trainer(session, trainer)
    session.commit()
    session.refresh(trainer)
    return trainer


def update_trainer_record(
    session: Session,
    trainer_id: int,
    payload: TrainerPayload,
) -> Trainer:
    trainer = repository.find_trainer_by_id(session, trainer_id)
    if trainer is None:
        raise HTTPException(status_code=404, detail="Trainer not found.")

    email = str(payload.email).strip().lower()
    existing = repository.find_trainer_by_email(session, email)
    if existing and existing.id != trainer_id:
        raise HTTPException(status_code=409, detail="A trainer with this email already exists.")

    changes = payload.model_dump(exclude={"email"})
    changes["email"] = email
    for key, value in changes.items():
        setattr(trainer, key, value)

    session.add(trainer)
    session.commit()
    session.refresh(trainer)
    return trainer


def delete_trainer_record(session: Session, trainer_id: int) -> None:
    trainer = repository.find_trainer_by_id(session, trainer_id)
    if trainer is None:
        raise HTTPException(status_code=404, detail="Trainer not found.")

    assigned = session.exec(
        select(WorkoutAssignment).where(WorkoutAssignment.trainer_id == trainer_id)
    ).first()
    if assigned:
        raise HTTPException(
            status_code=409,
            detail="This trainer has workout history. Deactivate the trainer instead.",
        )
    repository.delete_trainer(session, trainer)


def ensure_trainer_profile(session: Session, account) -> Trainer:
    """Link an admin-promoted login account to its trainer staff profile."""
    email = account.email.strip().lower()
    trainer = repository.find_trainer_by_user_id(session, account.id)
    if trainer is None:
        trainer = repository.find_trainer_by_email(session, email)

    member = session.exec(select(Member).where(Member.user_id == account.id)).first()

    if trainer is None:
        trainer = Trainer(
            full_name=account.full_name,
            email=email,
            phone=member.phone if member else "",
            specialization="General fitness",
            is_active=True,
            user_id=account.id,
        )
        session.add(trainer)
        session.flush()
        return trainer

    if trainer.user_id not in (None, account.id):
        raise HTTPException(
            status_code=409,
            detail="This trainer profile is already linked to another account.",
        )

    trainer.full_name = account.full_name
    trainer.email = email
    trainer.user_id = account.id
    if member and not trainer.phone:
        trainer.phone = member.phone
    trainer.is_active = True
    session.add(trainer)
    session.flush()
    return trainer


def deactivate_trainer_profile(session: Session, email: str) -> None:
    trainer = repository.find_trainer_by_email(session, email)
    if trainer is not None:
        trainer.is_active = False
        session.add(trainer)
        session.flush()


def _require_trainer_profile(session: Session, account) -> Trainer:
    if account.role != "trainer":
        raise HTTPException(status_code=403, detail="Trainer permission required.")

    trainer = repository.find_trainer_by_user_id(session, account.id)
    if trainer is None:
        trainer = repository.find_trainer_by_email(session, account.email)

    if trainer is None or not trainer.is_active:
        raise HTTPException(status_code=403, detail="Your trainer profile is inactive.")
    if trainer.user_id not in (None, account.id):
        raise HTTPException(status_code=403, detail="Your trainer profile is linked elsewhere.")

    if trainer.user_id is None:
        trainer.user_id = account.id
        session.add(trainer)
        session.flush()
    return trainer


def get_trainer_dashboard(session: Session, account) -> dict:
    trainer = _require_trainer_profile(session, account)
    records = repository.list_assignments_for_trainer(session, trainer.id)

    assignments = []
    member_ids: set[int] = set()
    for assignment, plan, member in records:
        member_ids.add(member.id)
        assignments.append({
            "assignment": assignment,
            "plan": plan,
            "member": member,
            "progress": repository.list_progress_for_assignment(session, assignment.id),
        })

    return {
        "trainer": trainer,
        "summary": {
            "assigned_workouts": len(assignments),
            "assigned_members": len(member_ids),
        },
        "assignments": assignments,
    }


def list_assignment_progress(session: Session, account, assignment_id: int):
    trainer = _require_trainer_profile(session, account)
    assignment = repository.find_assignment(session, assignment_id)
    if assignment is None or assignment.trainer_id != trainer.id:
        raise HTTPException(status_code=404, detail="Assigned workout not found.")
    return repository.list_progress_for_assignment(session, assignment_id, limit=100)


def record_assignment_progress(
    session: Session,
    account,
    assignment_id: int,
    payload: TrainerProgressCreate,
) -> WorkoutProgress:
    trainer = _require_trainer_profile(session, account)
    assignment = repository.find_assignment(session, assignment_id)
    if assignment is None or assignment.trainer_id != trainer.id:
        raise HTTPException(status_code=404, detail="Assigned workout not found.")

    progress = WorkoutProgress(
        assignment_id=assignment.id,
        member_id=assignment.member_id,
        trainer_id=trainer.id,
        completion_percent=payload.completion_percent,
        notes=payload.notes.strip(),
    )
    return repository.add_progress(session, progress)
