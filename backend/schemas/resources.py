"""Pydantic request schemas for GymTrack API resources."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field as PField


class Signup(BaseModel):
    full_name: str = PField(min_length=2, max_length=100)
    email: EmailStr
    password: str = PField(min_length=8, max_length=128)

class Login(BaseModel):
    email: EmailStr
    password: str = PField(min_length=1, max_length=128)

class ProfilePatch(BaseModel):
    full_name: str = PField(min_length=2, max_length=100)

class PasswordPatch(BaseModel):
    current_password: str
    new_password: str = PField(min_length=8, max_length=128)

class MemberBody(BaseModel):
    full_name: str = PField(min_length=2, max_length=100)
    email: EmailStr
    phone: str = PField(default="", max_length=30)
    join_date: date = PField(default_factory=date.today)
    is_active: bool = True



class MembershipBody(BaseModel):
    member_id: int
    plan_name: str = PField(min_length=2, max_length=100)
    start_date: date = PField(default_factory=date.today)
    end_date: date
    price: float = PField(default=0, ge=0)
    status: str = "active"

class AttendanceBody(BaseModel):
    member_id: int
    check_in: datetime | None = None
    check_out: datetime | None = None
    notes: str = PField(default="", max_length=500)

class AttendanceRequestBody(BaseModel):
    requested_check_in: datetime
    requested_check_out: datetime | None = None
    notes: str = PField(default="", max_length=500)

class AttendanceRequestReview(BaseModel):
    status: Literal["approved", "rejected"]
    review_note: str = PField(default="", max_length=500)

class PlanBody(BaseModel):
    title: str = PField(min_length=2, max_length=120)
    description: str = ""
    level: str = "beginner"
    duration_weeks: int = PField(default=4, ge=1, le=52)

class AssignmentBody(BaseModel):
    plan_id: int
    member_id: int
    trainer_id: int | None = None
    start_date: date = PField(default_factory=date.today)
    end_date: date | None = None
    status: str = "active"

class GroupBody(BaseModel):
    name: str = PField(min_length=2, max_length=100)

class GroupMemberBody(BaseModel):
    email: EmailStr
    can_create: bool = False
    can_edit: bool = False
    can_assign: bool = False

class GroupPermissions(BaseModel):
    can_create: bool = False
    can_edit: bool = False
    can_assign: bool = False

class GroupWorkBody(BaseModel):
    title: str = PField(min_length=2, max_length=140)
    description: str = ""
    due_date: date | None = None
    assigned_to: int | None = None

class GroupWorkPatch(BaseModel):
    title: str | None = PField(default=None, min_length=2, max_length=140)
    description: str | None = None
    due_date: date | None = None
    assigned_to: int | None = None
    is_completed: bool | None = None
