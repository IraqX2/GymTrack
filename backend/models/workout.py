from datetime import date, datetime, timezone

from sqlmodel import Field, SQLModel


class WorkoutPlan(SQLModel, table=True):
    __tablename__ = "workout_plan"

    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str = ""
    level: str = "beginner"
    duration_weeks: int = 4
    created_by: int | None = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkoutAssignment(SQLModel, table=True):
    __tablename__ = "workout_assignment"

    id: int | None = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="workout_plan.id")
    member_id: int = Field(foreign_key="member.id", index=True)
    trainer_id: int | None = Field(default=None, foreign_key="trainer.id")
    start_date: date = Field(default_factory=date.today)
    end_date: date | None = None
    status: str = "active"
    assigned_by: int | None = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
