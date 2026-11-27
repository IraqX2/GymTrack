from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class Trainer(SQLModel, table=True):
    """Gym staff profile linked to a login account."""

    __tablename__ = "trainer"

    id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(max_length=100)
    email: str = Field(unique=True, index=True, max_length=254)
    phone: str = Field(default="", max_length=30)
    specialization: str = Field(default="", max_length=100)
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
