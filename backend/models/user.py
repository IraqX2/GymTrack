from datetime import datetime, timezone

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
