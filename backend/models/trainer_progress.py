from datetime import date, datetime, timezone

from sqlmodel import Field, SQLModel


class WorkoutProgress(SQLModel, table=True):
    """Trainer progress entry for a member's assigned workout."""

    __tablename__ = "trainer_progress"

    id: int | None = Field(default=None, primary_key=True)
    assignment_id: int = Field(foreign_key="workout_assignment.id", index=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    trainer_id: int = Field(foreign_key="trainer.id", index=True)
    completion_percent: int = Field(default=0, ge=0, le=100)
    notes: str = Field(default="", max_length=600)
    progress_date: date = Field(default_factory=date.today, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
