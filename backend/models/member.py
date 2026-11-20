from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class Member(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str = Field(index=True, max_length=100)
    email: str = Field(index=True, max_length=254)
    phone: str = Field(default="", max_length=30)
    join_date: date = Field(default_factory=date.today)
    is_active: bool = Field(default=True)
