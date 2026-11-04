from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlmodel import Field as SQLField, Session, SQLModel, create_engine, select

import os

from sqlalchemy.pool import NullPool

raw_database_url = os.getenv("DATABASE_URL", "sqlite:///./gymtrack.db")

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

class Member(SQLModel, table=True):
    id: Optional[int] = SQLField(default=None, primary_key=True)
    full_name: str = SQLField(index=True, max_length=100)
    email: str = SQLField(index=True, max_length=254)
    phone: str = SQLField(default="", max_length=30)
    join_date: date = SQLField(default_factory=date.today)
    is_active: bool = SQLField(default=True)

class MemberCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(default="", max_length=30)
    join_date: date = Field(default_factory=date.today)
    is_active: bool = True

class MemberUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    join_date: Optional[date] = None
    is_active: Optional[bool] = None

class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: str
    phone: str
    join_date: date
    is_active: bool

def get_session():
    with Session(engine) as session:
        yield session

app = FastAPI(
    title="GymTrack API",
    description="REST API for GymTrack member management.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "service": "GymTrack API"}

@app.post("/api/members", response_model=MemberRead, status_code=201, tags=["members"])
def create_member(payload: MemberCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(Member).where(Member.email == str(payload.email))).first()
    if existing:
        raise HTTPException(status_code=409, detail="A member with this email already exists.")
    member = Member(**payload.model_dump())
    session.add(member)
    session.commit()
    session.refresh(member)
    return member

@app.get("/api/members", response_model=list[MemberRead], tags=["members"])
def list_members(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    session: Session = Depends(get_session),
):
    statement = select(Member).order_by(Member.id.desc()).offset(offset).limit(limit)
    return session.exec(statement).all()

@app.get("/api/members/{member_id}", response_model=MemberRead, tags=["members"])
def get_member(member_id: int, session: Session = Depends(get_session)):
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    return member

@app.put("/api/members/{member_id}", response_model=MemberRead, tags=["members"])
def update_member(
    member_id: int,
    payload: MemberUpdate,
    session: Session = Depends(get_session),
):
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")

    changes = payload.model_dump(exclude_unset=True)
    if "email" in changes:
        changes["email"] = str(changes["email"])
        duplicate = session.exec(
            select(Member).where(Member.email == changes["email"], Member.id != member_id)
        ).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="A member with this email already exists.")

    for key, value in changes.items():
        setattr(member, key, value)

    session.add(member)
    session.commit()
    session.refresh(member)
    return member

@app.delete("/api/members/{member_id}", status_code=204, tags=["members"])
def delete_member(member_id: int, session: Session = Depends(get_session)):
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")
    session.delete(member)
    session.commit()
    return Response(status_code=204)
