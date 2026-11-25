# GymTrack

GymTrack is a CSE309 gym-management project. The current implementation is an **MVP for member records**, not yet the complete secure multi-user final project.

## Current implementation

- React, TypeScript and Vite frontend
- FastAPI REST backend
- SQLModel database model for members
- Member create, list, view, update and delete endpoints
- Request validation (including email validation), duplicate-email checks and pagination
- Local development database: SQLite

The Trainers, Memberships, Attendance and Workout Plans navigation items are placeholders. Their CRUD workflows are not implemented yet.

## Architecture

```text
Browser (React + TypeScript)
        |
        | HTTP JSON requests (/api/...)
        v
FastAPI backend
        |
        | SQLModel Session
        v
SQLite (local) / PostgreSQL (hosted)
```

The frontend calls the backend through `frontend/src/services/api.ts`. The backend routes are in `backend/routers`, validation schemas are in `backend/schemas`, SQLModel tables are in `backend/models`, and database operations are in `backend/services`.

## Run locally

Requirements: Python 3.10+ and Node.js/npm.

Backend, from the repository root:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

Frontend, in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL (usually http://localhost:5173).

The local SQLite file is `gymtrack.db` in the working directory. It is excluded from Git.

## Production database requirement

**Do not use SQLite on Vercel.** Serverless instances may restart or run on different machines, so a local SQLite file (including `/tmp`) is not durable shared storage.

Configure `DATABASE_URL` in Vercel Project Settings → Environment Variables to a hosted PostgreSQL connection string (for example, the Supabase PostgreSQL connection string). Never commit the connection string or share its password publicly.

The backend now intentionally fails at startup on Vercel if `DATABASE_URL` is missing. This is safer than silently accepting writes to temporary storage that may disappear.

For PostgreSQL, the backend uses the `psycopg` driver. Local development still defaults to SQLite.

## Current API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Backend health check |
| POST | `/api/members` | Create member |
| GET | `/api/members` | List members |
| GET | `/api/members/{id}` | Read one member |
| PUT | `/api/members/{id}` | Update member |
| DELETE | `/api/members/{id}` | Delete member |

The list endpoint accepts `offset` and `limit`.

## Important limitations before final submission

The current code does **not** yet implement signup/login, JWT refresh/logout, user roles, server-side RBAC, private per-user records, group/team permissions, admin management, audit/security logs, or automated tests. Do not present these as completed until implemented and tested.

Member endpoints currently have no authentication or authorization. Use demo data only; do not store real gym-member personal information in this version.

## Deployment checklist

- [ ] Set `DATABASE_URL` to hosted PostgreSQL in Vercel (Production and Preview as appropriate).
- [ ] Confirm the Vercel project uses this repository and the correct root configuration.
- [ ] Check `/api/health` and `/api/docs` on the deployed URL.
- [ ] Create a test member, refresh the page and verify the record remains.
- [ ] Open the same deployed URL from a second browser/device and verify the same member appears.
- [ ] Do not deploy real personal records while endpoints remain public.
