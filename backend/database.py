import os
from collections.abc import Generator

from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine


configured_database_url = os.getenv("DATABASE_URL")

# Vercel Functions have a read-only deployment filesystem. When no hosted
# DATABASE_URL is configured, use /tmp only as a temporary demo fallback.
# Local development continues to use the persistent project SQLite file.
if configured_database_url:
    raw_database_url = configured_database_url
elif os.getenv("VERCEL") == "1":
    raw_database_url = "sqlite:////tmp/gymtrack.db"
    print("DATABASE_URL is not set; using ephemeral /tmp SQLite on Vercel.")
else:
    raw_database_url = "sqlite:///./gymtrack.db"

# Supabase provides PostgreSQL URLs. Use psycopg 3 explicitly so the same
# SQLModel code works locally with SQLite and in Vercel with PostgreSQL.
if raw_database_url.startswith("postgres://"):
    DATABASE_URL = raw_database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif raw_database_url.startswith("postgresql://"):
    DATABASE_URL = raw_database_url.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    DATABASE_URL = raw_database_url

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # Vercel functions use short-lived invocations. NullPool avoids retaining
    # connections between invocations; prepare_threshold=None is compatible
    # with Supabase's transaction-mode pooler.
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        connect_args={"prepare_threshold": None, "sslmode": "require"},
    )


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    # Importing the model registers its table in SQLModel.metadata.
    try:
        from backend.models.member import Member  # noqa: F401
    except ModuleNotFoundError:
        from models.member import Member  # noqa: F401

    SQLModel.metadata.create_all(engine)
