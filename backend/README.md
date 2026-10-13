# GymTrack Backend

FastAPI REST API starter for GymTrack.

## Run locally

From the repository root:

```bash
python -m venv .venv
```

Activate it in Windows PowerShell with `.venv\Scripts\Activate.ps1`, or on macOS/Linux with `source .venv/bin/activate`.

Install and run:

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

API documentation: http://127.0.0.1:8000/docs

## Starter endpoints

- `GET /api/health`
- `GET /api/hello?name=YourName`
- `GET /api/modules`

These are foundation/demo endpoints. Database persistence, authentication, and full CRUD will be developed in later project tasks.
