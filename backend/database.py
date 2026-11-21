import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine

# Load local .env values when running outside Vercel. Platform environment
# variables continue to take precedence over values in this file.
load_dotenv()

configured_database_url = os.getenv("DATABASE_URL")

# Vercel Functions have a read-only deployment filesystem. Without a hosted
# DATABASE_URL the temporary SQLite fallback is for local/demo testing only.
if configured_database_url:
    raw_database_url = configured_database_url
elif os.getenv("VERCEL") == "1":
    raw_database_url = "sqlite:////tmp/gymtrack.db"
    print("DATABASE_URL is not set; using ephemeral /tmp SQLite on Vercel.")
else:
    raw_database_url = "sqlite:///./gymtrack.db"

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
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        connect_args={"prepare_threshold": None, "sslmode": "require"},
    )


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    # Import every model so SQLModel registers all tables before create_all().
    try:
        from backend.models.member import Member  # noqa: F401
        from backend.models.user import User  # noqa: F401
        from backend.models.auth_session import AuthSession  # noqa: F401
    except ModuleNotFoundError:
        from models.member import Member  # noqa: F401
        from models.user import User  # noqa: F401
        from models.auth_session import AuthSession  # noqa: F401

    SQLModel.metadata.create_all(engine)
