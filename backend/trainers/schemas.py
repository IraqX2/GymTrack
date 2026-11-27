from datetime import date
from pydantic import BaseModel, EmailStr, Field


class TrainerCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(default="", max_length=30)
    specialization: str = Field(default="", max_length=120)
    is_active: bool = True


class TrainerUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(default="", max_length=30)
    specialization: str = Field(default="", max_length=120)
    is_active: bool = True


class ProgressCreate(BaseModel):
    completion_percent: int = Field(ge=0, le=100)
    notes: str = Field(default="", max_length=1000)
    progress_date: date | None = None


class AssignmentStatusUpdate(BaseModel):
    status: str = Field(pattern="^(active|paused|completed)$")
