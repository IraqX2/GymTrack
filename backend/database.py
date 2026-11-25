import os
from collections.abc import Generator

from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine


configured_database_url = os.getenv("DATABASE_URL")

# A Vercel Function can be restarted or run in another instance at any time.
# Its local filesystem (including /tmp) is not a shared, durable database.
# Fail fast instead of silently losing member records when production is misconfigured.
if not configured_database_url and os.getenv("VERCEL") == "1":
    raise RuntimeError(
        "DATABASE_URL is required on Vercel. Configure a persistent PostgreSQL "
        "database (for example, Supabase) in the project's Environment Variables."
    )

# Local development uses SQLite. Production must provide a hosted database URL.
raw_database_url = configured_database_url or "sqlite:///./gymtrack.db"

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
