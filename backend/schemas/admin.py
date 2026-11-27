from typing import Literal

from pydantic import BaseModel, Field


class BulkUserAction(BaseModel):
    user_ids: list[int] = Field(min_length=1, max_length=100)
    reason: str = Field(default="", max_length=200)


class BulkContentDelete(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)
