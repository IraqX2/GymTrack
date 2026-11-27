from fastapi import APIRouter, Request, Response

from backend.gymtrack_api import ADMIN, DB, TRAINER, audit
from backend.schemas.trainer import TrainerPayload, TrainerProgressCreate
from backend.services import trainer_service

router = APIRouter(tags=["trainers"])


@router.get("/api/trainers")
def list_trainers(user: ADMIN, db: DB):
    return trainer_service.list_trainer_records(db)


@router.post("/api/trainers", status_code=201)
def create_trainer(payload: TrainerPayload, user: ADMIN, db: DB, request: Request):
    trainer = trainer_service.create_trainer_record(db, payload)
    audit(db, request, "trainer_created", user, "trainer", trainer.id)
    return trainer


@router.put("/api/trainers/{trainer_id}")
def update_trainer(
    trainer_id: int,
    payload: TrainerPayload,
    user: ADMIN,
    db: DB,
    request: Request,
):
    trainer = trainer_service.update_trainer_record(db, trainer_id, payload)
    audit(db, request, "trainer_updated", user, "trainer", trainer.id)
    return trainer


@router.delete("/api/trainers/{trainer_id}", status_code=204)
def delete_trainer(trainer_id: int, user: ADMIN, db: DB, request: Request):
    trainer_service.delete_trainer_record(db, trainer_id)
    audit(db, request, "trainer_deleted", user, "trainer", trainer_id)
    return Response(status_code=204)


@router.get("/api/trainer/dashboard")
def trainer_dashboard(user: TRAINER, db: DB):
    return trainer_service.get_trainer_dashboard(db, user)


@router.get("/api/trainer/assignments/{assignment_id}/progress")
def assignment_progress(assignment_id: int, user: TRAINER, db: DB):
    return trainer_service.list_assignment_progress(db, user, assignment_id)


@router.post("/api/trainer/assignments/{assignment_id}/progress", status_code=201)
def add_assignment_progress(
    assignment_id: int,
    payload: TrainerProgressCreate,
    user: TRAINER,
    db: DB,
    request: Request,
):
    progress = trainer_service.record_assignment_progress(db, user, assignment_id, payload)
    audit(
        db,
        request,
        "trainer_progress_recorded",
        user,
        "workout_assignment",
        assignment_id,
        f"status={progress.status}",
    )
    return progress
