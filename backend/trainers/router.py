"""HTTP routes for the trainer workspace."""
from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import Session

try:
    from backend.gymtrack_api import ADMIN, CURRENT, DB, audit
except ModuleNotFoundError:
    from gymtrack_api import ADMIN, CURRENT, DB, audit

from . import service
from .schemas import AssignmentStatusUpdate, ProgressCreate, TrainerCreate, TrainerUpdate

router = APIRouter(tags=["trainers"])


@router.get("/api/trainers")
def get_trainers(user: CURRENT, db: DB):
    return service.list_trainers(db)


@router.post("/api/trainers", status_code=201)
def create_trainer(
    data: TrainerCreate,
    user: ADMIN,
    db: DB,
    request: Request,
):
    trainer = service.promote_account_to_trainer(data, db)
    audit(db, request, "trainer_promoted", user, "trainer", trainer.id, trainer.email)
    return trainer


@router.put("/api/trainers/{trainer_id}")
def update_trainer(
    trainer_id: int,
    data: TrainerUpdate,
    user: ADMIN,
    db: DB,
    request: Request,
):
    trainer = service.update_trainer_profile(trainer_id, data, db)
    audit(db, request, "trainer_updated", user, "trainer", trainer.id)
    return trainer


@router.delete("/api/trainers/{trainer_id}", status_code=204)
def delete_trainer(
    trainer_id: int,
    user: ADMIN,
    db: DB,
    request: Request,
):
    trainer = service.deactivate_trainer(trainer_id, db)
    audit(db, request, "trainer_deactivated", user, "trainer", trainer.id)
    return Response(status_code=204)


@router.get("/api/trainer/dashboard")
def get_trainer_dashboard(user: CURRENT, db: DB):
    return service.trainer_dashboard(user, db)


@router.get("/api/trainer/progress")
def get_trainer_progress(user: CURRENT, db: DB):
    return service.trainer_progress(user, db)


@router.post("/api/trainer/assignments/{assignment_id}/progress", status_code=201)
def create_assignment_progress(
    assignment_id: int,
    data: ProgressCreate,
    user: CURRENT,
    db: DB,
    request: Request,
):
    row = service.add_assignment_progress(assignment_id, data, user, db)
    audit(db, request, "trainer_progress_recorded", user, "workout_progress", row.id)
    return row


@router.patch("/api/trainer/assignments/{assignment_id}/status")
def change_assignment_status(
    assignment_id: int,
    data: AssignmentStatusUpdate,
    user: CURRENT,
    db: DB,
    request: Request,
):
    row = service.update_assigned_workout_status(assignment_id, data, user, db)
    audit(db, request, "trainer_assignment_status_changed", user, "workout_assignment", row.id, row.status)
    return row
