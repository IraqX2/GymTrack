import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# The Vercel service runs with backend/ as its root, while local development
# imports this file as backend.main. Support both import contexts.
try:
    from backend.database import create_db_and_tables
    from backend.routers.members import router as members_router
    from backend.routers.system import router as system_router
except ModuleNotFoundError:
    from database import create_db_and_tables
    from routers.members import router as members_router
    from routers.system import router as system_router


# Vercel's /api/* rewrite preserves the original URL path, so expose
# Swagger under /api/docs there. Keep the standard /docs path locally.
is_vercel = os.getenv("VERCEL") == "1"

app = FastAPI(
    title="GymTrack API",
    description="REST API for GymTrack member management.",
    version="1.0.0",
    docs_url="/api/docs" if is_vercel else "/docs",
    openapi_url="/api/openapi.json" if is_vercel else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(members_router)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
