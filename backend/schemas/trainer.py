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
    completion_percent: int = Field(default=0, ge=0, le=100)
    notes: str = Field(default="", max_length=600)
