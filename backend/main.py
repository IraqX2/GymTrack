# FastAPI entry point used by Vercel (entrypoint: main:app) and local uvicorn.
try:
    from backend.gymtrack_api import app
except ModuleNotFoundError:
    from gymtrack_api import app

