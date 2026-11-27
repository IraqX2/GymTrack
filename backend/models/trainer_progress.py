from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class WorkoutProgress(SQLModel, table=True):
    """A trainer-authored progress entry for a workout assignment."""

    __tablename__ = "workout_progress"

    id: int | None = Field(default=None, primary_key=True)
    assignment_id: int = Field(foreign_key="workout_assignment.id", index=True)
    trainer_id: int = Field(foreign_key="trainer.id", index=True)
    status: str = Field(default="in_progress", max_length=20)
    notes: str = Field(default="", max_length=600)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
