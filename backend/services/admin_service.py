"""Shared admin data operations and export helpers."""

import csv
import io
from datetime import datetime, timezone

from fastapi import HTTPException, Response
from sqlmodel import Session, select

try:
    from backend.models.member import Member
    from backend.models.trainer_progress import WorkoutProgress
    from backend.models.workout import WorkoutAssignment, WorkoutPlan
    from backend.models.resources import (
        Membership, Attendance, GymGroup, GymGroupMember, GymGroupTask,
    )
except ModuleNotFoundError:
    from models.member import Member
    from models.trainer_progress import WorkoutProgress
    from models.workout import WorkoutAssignment, WorkoutPlan
    from models.resources import (
        Membership, Attendance, GymGroup, GymGroupMember, GymGroupTask,
    )


def now():
    return datetime.now(timezone.utc)


def csv_response(filename: str, headers: list[str], rows: list[list]):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([
            "'" + str(value)
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@"))
            else value
            for value in row
        ])
    return Response(
        output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


def _admin_content_query(db: Session, content_type: str, q: str):
    from sqlalchemy import func

    if content_type == "memberships":
        statement = select(Membership)
        if q:
            statement = statement.where(Membership.plan_name.ilike(f"%{q}%"))
        total = db.exec(select(func.count()).select_from(statement.subquery())).one()
        rows = db.exec(statement.order_by(Membership.created_at.desc()).limit(10000)).all()
        items = [
            {"id": row.id, "label": row.plan_name, "details": f"Member #{row.member_id} · {row.status}",
             "created_at": row.created_at}
            for row in rows
        ]
    elif content_type == "attendance":
        statement = select(Attendance)
        if q and q.isdigit():
            statement = statement.where(
                (Attendance.member_id == int(q)) | (Attendance.id == int(q))
            )
        total = db.exec(select(func.count()).select_from(statement.subquery())).one()
        rows = db.exec(statement.order_by(Attendance.check_in.desc()).limit(10000)).all()
        items = [
            {"id": row.id, "label": f"Attendance #{row.id}",
             "details": f"Member #{row.member_id} · {row.check_in} · "
                        f"{'Checked out' if row.check_out else 'Currently checked in'}",
             "created_at": row.check_in}
            for row in rows
        ]
    elif content_type == "workout_plans":
        statement = select(WorkoutPlan)
        if q:
            statement = statement.where(
                WorkoutPlan.title.ilike(f"%{q}%") | WorkoutPlan.description.ilike(f"%{q}%")
            )
        total = db.exec(select(func.count()).select_from(statement.subquery())).one()
        rows = db.exec(statement.order_by(WorkoutPlan.created_at.desc()).limit(10000)).all()
        items = [
            {"id": row.id, "label": row.title,
             "details": f"{row.level} · {row.duration_weeks} weeks", "created_at": row.created_at}
            for row in rows
        ]
    elif content_type == "assignments":
        statement = (
            select(WorkoutAssignment, WorkoutPlan, Member)
            .join(WorkoutPlan, WorkoutPlan.id == WorkoutAssignment.plan_id)
            .join(Member, Member.id == WorkoutAssignment.member_id)
        )
        if q:
            statement = statement.where(
                WorkoutPlan.title.ilike(f"%{q}%")
                | Member.full_name.ilike(f"%{q}%")
                | Member.email.ilike(f"%{q}%")
            )
        total = db.exec(select(func.count()).select_from(statement.subquery())).one()
        rows = db.exec(
            statement.order_by(WorkoutAssignment.created_at.desc()).limit(10000)
        ).all()
        items = [
            {"id": assignment.id, "label": f"{plan.title} → {member.full_name}",
             "details": f"{assignment.status} · Trainer #{assignment.trainer_id or 'unassigned'}",
             "created_at": assignment.created_at}
            for assignment, plan, member in rows
        ]
    elif content_type == "groups":
        statement = select(GymGroup)
        if q:
            statement = statement.where(GymGroup.name.ilike(f"%{q}%"))
        total = db.exec(select(func.count()).select_from(statement.subquery())).one()
        rows = db.exec(statement.order_by(GymGroup.created_at.desc()).limit(10000)).all()
        items = [
            {"id": row.id, "label": row.name,
             "details": f"Owner account #{row.created_by}", "created_at": row.created_at}
            for row in rows
        ]
    elif content_type == "trainer_progress":
        statement = select(WorkoutProgress)
        if q:
            statement = statement.where(WorkoutProgress.notes.ilike(f"%{q}%"))
        total = db.exec(select(func.count()).select_from(statement.subquery())).one()
        rows = db.exec(
            statement.order_by(WorkoutProgress.created_at.desc()).limit(10000)
        ).all()
        items = [
            {"id": row.id, "label": f"Progress #{row.id}",
             "details": f"Assignment #{row.assignment_id} · Member #{row.member_id} · Trainer #{row.trainer_id} · {row.completion_percent}% complete",
             "created_at": row.created_at}
            for row in rows
        ]
    else:
        raise HTTPException(422, "Unsupported content type")
    return items, total


def _delete_admin_content_record(db: Session, content_type: str, record_id: int) -> None:
    if content_type == "memberships":
        row = db.get(Membership, record_id)
        if row is None:
            raise HTTPException(404, "Membership record not found")
        db.delete(row)
    elif content_type == "attendance":
        row = db.get(Attendance, record_id)
        if row is None:
            raise HTTPException(404, "Attendance record not found")
        db.delete(row)
    elif content_type == "trainer_progress":
        row = db.get(WorkoutProgress, record_id)
        if row is None:
            raise HTTPException(404, "Progress record not found")
        db.delete(row)
    elif content_type == "assignments":
        row = db.get(WorkoutAssignment, record_id)
        if row is None:
            raise HTTPException(404, "Workout assignment not found")
        for progress in db.exec(
            select(WorkoutProgress).where(WorkoutProgress.assignment_id == record_id)
        ).all():
            db.delete(progress)
        db.delete(row)
    elif content_type == "workout_plans":
        row = db.get(WorkoutPlan, record_id)
        if row is None:
            raise HTTPException(404, "Workout plan not found")
        assignments = db.exec(
            select(WorkoutAssignment).where(WorkoutAssignment.plan_id == record_id)
        ).all()
        for assignment in assignments:
            for progress in db.exec(
                select(WorkoutProgress).where(WorkoutProgress.assignment_id == assignment.id)
            ).all():
                db.delete(progress)
            db.delete(assignment)
        db.delete(row)
    elif content_type == "groups":
        row = db.get(GymGroup, record_id)
        if row is None:
            raise HTTPException(404, "Group not found")
        for task in db.exec(
            select(GymGroupTask).where(GymGroupTask.group_id == record_id)
        ).all():
            db.delete(task)
        for membership in db.exec(
            select(GymGroupMember).where(GymGroupMember.group_id == record_id)
        ).all():
            db.delete(membership)
        db.delete(row)
    else:
        raise HTTPException(422, "Unsupported content type")



