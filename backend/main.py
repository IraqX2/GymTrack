from fastapi import FastAPI

app = FastAPI(
    title="GymTrack API",
    description="Starter REST API for the GymTrack gym management system.",
    version="0.1.0",
)

@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "GymTrack API"}

@app.get("/api/hello", tags=["demo"])
def hello(name: str = "World") -> dict[str, str]:
    return {"message": f"Hello, {name}! GymTrack API is working."}

@app.get("/api/modules", tags=["project"])
def modules() -> dict:
    return {
        "mvp_modules": [
            "Members", "Trainers", "Memberships",
            "Attendance", "Workout plans"
        ],
        "release": "MVP",
    }
