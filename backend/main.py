import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from backend.database import create_db_and_tables
    from backend.routers.auth import router as auth_router
    from backend.routers.members import router as members_router
    from backend.routers.system import router as system_router
except ModuleNotFoundError:
    from database import create_db_and_tables
    from routers.auth import router as auth_router
    from routers.members import router as members_router
    from routers.system import router as system_router


is_vercel = os.getenv("VERCEL") == "1"

app = FastAPI(
    title="GymTrack API",
    description="REST API for GymTrack member management and account authentication.",
    version="1.1.0",
    docs_url="/api/docs" if is_vercel else "/docs",
    openapi_url="/api/openapi.json" if is_vercel else "/openapi.json",
)

# Do not use wildcard origins with credentialed requests. For the Vercel
# same-origin rewrite, the browser does not need CORS; set FRONTEND_ORIGIN
# when the frontend is hosted on a separate domain.
allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(system_router)
app.include_router(auth_router)
app.include_router(members_router)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
