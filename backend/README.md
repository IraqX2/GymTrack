# GymTrack Backend

FastAPI backend for GymTrack.

## Local setup

From the repository root, configure `.env` using the root `.env.example`, then run:

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

API documentation: http://127.0.0.1:8000/docs

## Main routes

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `GET` and `PATCH /api/auth/me`
- `POST /api/auth/change-password`
- `GET /api/auth/sessions`
- `DELETE /api/auth/sessions/{id}`
- `/api/members/*` (administrator role required)

Public registration creates only normal user accounts. Create the first administrator with `python -m backend.create_admin` after configuring the database and secrets.

Use a hosted PostgreSQL database for Vercel. The temporary `/tmp` SQLite fallback is not persistent and must not be used for the final assessed deployment.
