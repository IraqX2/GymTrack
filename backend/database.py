import os
from collections.abc import Generator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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

# Supabase/Vercel may add query flags that libpq does not recognize.
if raw_url.startswith("postgresql+psycopg://"):
    parts = urlsplit(raw_url)
    query = [(key, value) for key, value in parse_qsl(parts.query)
             if key not in {"supa", "pgbouncer"}]
    raw_url = urlunsplit(parts._replace(query=urlencode(query)))

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
