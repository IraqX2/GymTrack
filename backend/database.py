import os
from collections.abc import Generator

from sqlalchemy.pool import NullPool
from sqlmodel import Session, create_engine

# Local development defaults to SQLite. A Vercel function must never silently
# write to /tmp: that filesystem is temporary and is not shared across instances.
configured_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
if not configured_url and os.getenv("VERCEL") == "1":
    raise RuntimeError(
        "DATABASE_URL is required on Vercel. Configure the GymTrack Supabase "
        "PostgreSQL connection string in Project Settings > Environment Variables."
    )

raw_url = configured_url or "sqlite:///./gymtrack.db"
if raw_url.startswith(("postgres://", "postgresql://")):
    raw_url = "postgresql+psycopg://" + raw_url.split("://", 1)[1]

# Remove Supabase/Vercel helper query flags without parsing the authority/host.
# urllib.parse.urlsplit can reject a transaction-pooler URI before SQLAlchemy
# gets a chance to handle it. Connection options needed by psycopg are passed
# through connect_args below.
if raw_url.startswith("postgresql+psycopg://"):
    base_url, separator, query_string = raw_url.partition("?")
    if separator:
        supported = [
            item for item in query_string.split("&")
            if item and item.split("=", 1)[0].lower() not in {"supa", "pgbouncer"}
        ]
        raw_url = base_url + (("?" + "&".join(supported)) if supported else "")

DATABASE_URL = raw_url
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        connect_args={"prepare_threshold": None, "sslmode": "require"},
    )


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
