from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class TrainerPayload(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(default="", max_length=30)
    specialization: str = Field(default="", max_length=100)
    is_active: bool = True


class RoleChangeBody(BaseModel):
    role: Literal["user", "trainer", "admin"]


class TrainerProgressCreate(BaseModel):
    status: Literal["in_progress", "completed"] = "in_progress"
    notes: str = Field(default="", max_length=600)
