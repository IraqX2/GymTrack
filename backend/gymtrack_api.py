import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

try:
    from backend.database import engine
    from backend.services.auth_service import hash_password, check_password
except ModuleNotFoundError:
    from database import engine
    from services.auth_service import hash_password, check_password


# App setup. In production the frontend and API share one Vercel origin.
app = FastAPI(
    title="GymTrack API",
    description="Gym membership, attendance and workout management.",
    version="2.0.0",
    docs_url="/api/docs" if os.getenv("VERCEL") == "1" else "/docs",
    openapi_url="/api/openapi.json" if os.getenv("VERCEL") == "1" else "/openapi.json",
)
origins = [value.strip() for value in os.getenv("FRONTEND_URLS", "").split(",") if value.strip()]
if not os.getenv("VERCEL"):
    origins += ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(origins)),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

JWT_SECRET = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET")
PEPPER = os.getenv("PASSWORD_PEPPER")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "GymTrack API", "version": "2.0.0"}


@app.on_event("startup")
def startup():
    if os.getenv("VERCEL") == "1" and (not JWT_SECRET or not PEPPER):
        raise RuntimeError("JWT_SECRET_KEY and PASSWORD_PEPPER must be set in Vercel.")
    # In local SQLite only, create tables for models. Supabase uses explicit migrations.
    if os.getenv("VERCEL") != "1":
        SQLModel.metadata.create_all(engine)


try:
    from backend.routers.trainers import router as trainers_router
    from backend.routers.members import router as members_router
    from backend.routers.groups import router as groups_router
    from backend.routers.memberships import router as memberships_router
    from backend.routers.workouts import router as workouts_router
    from backend.routers.attendance import router as attendance_router
    from backend.routers.auth import router as auth_router
    from backend.routers.admin import router as admin_router
except ModuleNotFoundError:
    from routers.trainers import router as trainers_router
    from routers.members import router as members_router
    from routers.groups import router as groups_router
    from routers.memberships import router as memberships_router
    from routers.workouts import router as workouts_router
    from routers.attendance import router as attendance_router
    from routers.auth import router as auth_router
    from routers.admin import router as admin_router

app.include_router(trainers_router)
app.include_router(members_router)
app.include_router(groups_router)
app.include_router(memberships_router)
app.include_router(workouts_router)
app.include_router(attendance_router)
app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return {"message": "GymTrack API is running", "docs": "/api/docs"}
