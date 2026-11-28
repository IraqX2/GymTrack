"""Workout plan and assignment business rules."""

from fastapi import HTTPException
from sqlmodel import Session

try:
    from backend.models.workout import WorkoutAssignment, WorkoutPlan
    from backend.repositories import workout_repository as repository
    from backend.schemas.resources import AssignmentBody, PlanBody
except ModuleNotFoundError:
    from models.workout import WorkoutAssignment, WorkoutPlan
    from repositories import workout_repository as repository
    from schemas.resources import AssignmentBody, PlanBody


VALID_LEVELS = {"beginner", "intermediate", "advanced"}


def list_workout_plans(session: Session, account):
    if account.role == "admin":
        return repository.list_all_plans(session)
    member = repository.member_for_account(session, account.id)
    if member is None:
        raise HTTPException(404, "No gym profile is linked to this account")
    return repository.list_plans_for_member(session, member.id)


def create_workout_plan(session: Session, payload: PlanBody, created_by: int) -> WorkoutPlan:
    if payload.level not in VALID_LEVELS:
        raise HTTPException(422, "Invalid plan level")
    plan = WorkoutPlan(**payload.model_dump(), created_by=created_by)
    return repository.save_plan(session, plan)


def update_workout_plan(session: Session, plan_id: int, payload: PlanBody) -> WorkoutPlan:
    plan = repository.get_plan(session, plan_id)
    if plan is None:
        raise HTTPException(404, "Workout plan not found")
    if payload.level not in VALID_LEVELS:
        raise HTTPException(422, "Invalid plan level")
    for key, value in payload.model_dump().items():
        setattr(plan, key, value)
    return repository.save_plan(session, plan)


def delete_workout_plan(session: Session, plan_id: int) -> None:
    plan = repository.get_plan(session, plan_id)
    if plan is None:
        raise HTTPException(404, "Workout plan not found")
    if repository.has_plan_assignments(session, plan_id):
        raise HTTPException(
            409,
            "This workout plan has member assignments. Remove those assignments first.",
        )
    repository.delete_plan(session, plan)


def list_workout_assignments(session: Session, account):
    member_id = None
    if account.role != "admin":
        member = repository.member_for_account(session, account.id)
        if member is None:
            raise HTTPException(404, "No gym profile is linked to this account")
        member_id = member.id
    return repository.list_assignments(session, member_id)


def create_workout_assignment(
    session: Session,
    payload: AssignmentBody,
    assigned_by: int,
) -> WorkoutAssignment:
    if repository.get_plan(session, payload.plan_id) is None or repository.get_member(session, payload.member_id) is None:
        raise HTTPException(404, "Plan or member not found")
    if payload.trainer_id is not None and repository.get_trainer(session, payload.trainer_id) is None:
        raise HTTPException(404, "Trainer not found")
    duplicate = repository.find_duplicate_assignment(
        session,
        payload.member_id,
        payload.plan_id,
        payload.trainer_id,
        payload.status,
    )
    if duplicate:
        raise HTTPException(409, "This workout plan is already assigned to this member and trainer.")
    assignment = WorkoutAssignment(**payload.model_dump(), assigned_by=assigned_by)
    return repository.save_assignment(session, assignment)


def delete_workout_assignment(session: Session, assignment_id: int) -> None:
    assignment = repository.get_assignment(session, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    repository.delete_assignment(session, assignment)
