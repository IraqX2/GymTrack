# Vercel FastAPI entry point. Keep a top-level `app` binding for the framework adapter.
try:
    from backend.gymtrack_api import app as gymtrack_app
except ModuleNotFoundError:
    from gymtrack_api import app as gymtrack_app

app = gymtrack_app
