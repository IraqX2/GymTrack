from fastapi import APIRouter, Request, Response

try:
    from backend.core.audit import audit
    from backend.core.dependencies import ADMIN, CURRENT, DB
    from backend.schemas.resources import AssignmentBody, PlanBody
    from backend.services import workout_service
except ModuleNotFoundError:
    from core.audit import audit
    from core.dependencies import ADMIN, CURRENT, DB
    from schemas.resources import AssignmentBody, PlanBody
    from services import workout_service


router = APIRouter(tags=["workouts"])


@router.get("/api/workout-plans")
def list_workout_plans(user: CURRENT, db: DB):
    return workout_service.list_workout_plans(db, user)


@router.post("/api/workout-plans", status_code=201)
def create_workout_plan(payload: PlanBody, user: ADMIN, db: DB, request: Request):
    plan = workout_service.create_workout_plan(db, payload, user.id)
    audit(db, request, "workout_plan_created", user, "workout_plan", plan.id)
    return plan


@router.put("/api/workout-plans/{plan_id}")
def update_workout_plan(
    plan_id: int,
    payload: PlanBody,
    user: ADMIN,
    db: DB,
    request: Request,
):
    plan = workout_service.update_workout_plan(db, plan_id, payload)
    audit(db, request, "workout_plan_updated", user, "workout_plan", plan.id)
    return plan


@router.delete("/api/workout-plans/{plan_id}", status_code=204)
def delete_workout_plan(plan_id: int, user: ADMIN, db: DB, request: Request):
    workout_service.delete_workout_plan(db, plan_id)
    audit(db, request, "workout_plan_deleted", user, "workout_plan", plan_id)
    return Response(status_code=204)


@router.get("/api/workout-assignments")
def list_workout_assignments(user: CURRENT, db: DB):
    return workout_service.list_workout_assignments(db, user)


@router.post("/api/workout-assignments", status_code=201)
def create_workout_assignment(
    payload: AssignmentBody,
    user: ADMIN,
    db: DB,
    request: Request,
):
    assignment = workout_service.create_workout_assignment(db, payload, user.id)
    audit(db, request, "workout_assigned", user, "workout_assignment", assignment.id)
    return assignment


@router.delete("/api/workout-assignments/{assignment_id}", status_code=204)
def delete_workout_assignment(
    assignment_id: int,
    user: ADMIN,
    db: DB,
    request: Request,
):
    workout_service.delete_workout_assignment(db, assignment_id)
    audit(db, request, "workout_assignment_deleted", user, "workout_assignment", assignment_id)
    return Response(status_code=204)
