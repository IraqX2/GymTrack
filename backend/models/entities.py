"""SQLModel entities for GymTrack.

Member remains in member.py; these records reference it through database foreign keys.
"""
from datetime import date, datetime, timezone

from sqlmodel import Field, SQLModel


class AppUser(SQLModel, table=True):
    __tablename__ = "user"
    id: int | None = Field(default=None, primary_key=True)
    full_name: str
    email: str = Field(index=True)
    password_hash: str
    role: str = "user"
    is_banned: bool = False
    failed_login_count: int = 0
    locked_until: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuthSession(SQLModel, table=True):
    __tablename__ = "authsession"
    id: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    refresh_token_hash: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    revoked_at: datetime | None = None
    ip_address: str | None = None
    user_agent: str | None = None


class Trainer(SQLModel, table=True):
    __tablename__ = "trainer"
    id: int | None = Field(default=None, primary_key=True)
    full_name: str
    email: str = Field(unique=True, index=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    phone: str = ""
    specialization: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Membership(SQLModel, table=True):
    __tablename__ = "membership"
    id: int | None = Field(default=None, primary_key=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    plan_name: str
    start_date: date = Field(default_factory=date.today)
    end_date: date
    price: float = 0
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Attendance(SQLModel, table=True):
    __tablename__ = "attendance"
    id: int | None = Field(default=None, primary_key=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    check_in: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    check_out: datetime | None = None
    notes: str = ""
    recorded_by: int | None = Field(default=None, foreign_key="user.id")


class AttendanceRequest(SQLModel, table=True):
    __tablename__ = "attendance_request"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    requested_check_in: datetime
    requested_check_out: datetime | None = None
    notes: str = ""
    status: str = "pending"
    reviewed_by: int | None = Field(default=None, foreign_key="user.id")
    reviewed_at: datetime | None = None
    review_note: str = ""
    attendance_id: int | None = Field(default=None, foreign_key="attendance.id", unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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


class WorkoutProgress(SQLModel, table=True):
    __tablename__ = "trainer_progress"
    id: int | None = Field(default=None, primary_key=True)
    assignment_id: int = Field(foreign_key="workout_assignment.id", index=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    trainer_id: int = Field(foreign_key="trainer.id", index=True)
    completion_percent: int = Field(ge=0, le=100)
    notes: str = Field(default="", max_length=1000)
    progress_date: date = Field(default_factory=date.today)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GymGroup(SQLModel, table=True):
    __tablename__ = "gym_group"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    created_by: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GymGroupMember(SQLModel, table=True):
    __tablename__ = "gym_group_member"
    group_id: int = Field(foreign_key="gym_group.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    role: str = "member"
    can_create: bool = False
    can_edit: bool = False
    can_assign: bool = False
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GymGroupTask(SQLModel, table=True):
    __tablename__ = "gym_group_task"
    id: int | None = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="gym_group.id", index=True)
    title: str
    description: str = ""
    due_date: date | None = None
    assigned_to: int | None = Field(default=None, foreign_key="user.id")
    created_by: int = Field(foreign_key="user.id")
    is_completed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActivityLog(SQLModel, table=True):
    __tablename__ = "activity_log"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    email: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    details: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
