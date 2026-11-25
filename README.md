# GymTrack

GymTrack is a gym-management application for members, trainers, memberships, attendance, workout plans and staff collaboration. This is the CSE309 final-project codebase.

## Technology

- Frontend: React 19, TypeScript and Vite
- Backend: Python, FastAPI and SQLModel
- Database: SQLite for local development; PostgreSQL (Supabase) for Vercel
- Authentication: Argon2 password hashing, JWT access tokens and rotating HttpOnly refresh sessions
- Hosting: Vercel

## Current features

- Account signup and login
- Personal profile and password change
- JWT access authentication, refresh and logout
- Short-lived access tokens and HttpOnly refresh cookies
- User and administrator roles, server-side checks and private member-profile ownership
- Admin dashboard statistics, account role changes, ban/unban, session revocation, activity and security views, CSV exports
- Member records (create, list, view, update, delete)
- Trainer records
- Membership records and status
- Attendance check-in/check-out
- Workout plan CRUD and member/trainer assignment
- Groups with owner/member roles, create/edit/assign grants and shared group work
- Activity records with timestamps, IP address and browser details

## Project structure

```text
GymTrack/
├── frontend/       React + TypeScript UI
├── backend/        FastAPI application and SQLModel database access
├── docs/           Project requirements and deployment instructions
└── vercel.json     Vercel frontend/API routing
```

## Run locally

Requirements: Python 3.10+ and Node.js 20+.

Backend, from the repository root:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
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

Without environment variables, local development uses `./gymtrack.db` (SQLite). For local testing, set `JWT_SECRET_KEY` and `PASSWORD_PEPPER` to separate random values. To test with Supabase locally, set `DATABASE_URL` to the private PostgreSQL connection string.

## Deploy to Vercel

The backend **requires** a persistent database URL in Vercel. It intentionally does not fall back to `/tmp` SQLite, because a serverless filesystem is not durable or shared between function instances.

Set these variables for Preview and Production:

- `DATABASE_URL`: Supabase PostgreSQL connection string
- `JWT_SECRET_KEY`: random JWT signing secret
- `PASSWORD_PEPPER`: a separate random server-side pepper
- `BOOTSTRAP_ADMIN_EMAIL`: email address that may receive the first admin role during signup

See [Final deployment setup](docs/FINAL_DEPLOYMENT_SETUP.md) for setup, initial accounts, database and smoke-test instructions.

## Current API groups

| Area | Main routes |
|---|---|
| Authentication | `/api/auth/signup`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout` |
| Profile & sessions | `/api/me`, `/api/auth/sessions` |
| Members | `/api/members` |
| Trainers | `/api/trainers` |
| Memberships | `/api/memberships` |
| Attendance | `/api/attendance` |
| Workout plans | `/api/workout-plans`, `/api/workout-assignments` |
| Groups | `/api/groups` |
| Admin | `/api/admin/stats`, `/api/admin/users`, `/api/admin/activity`, `/api/admin/security` |

API documentation is available at `/api/docs` when running on Vercel.

## Important security notes

- Never place the database password, JWT secret, password pepper or Supabase service-role key in frontend code or Git.
- The first admin account must be explicitly designated; other signups receive the regular `user` role.
- Personal member records are linked to the account that owns them. Regular users only see their own profile and related records.
- The current Supabase project inspection reported RLS disabled on public tables. Review the Supabase RLS warning and configure defense-in-depth before using real personal data.
- The project should only be treated as ready for real records after the preview and production smoke tests pass.

## Project status

This repository has a preview implementation of the final-project features. A successful Vercel build is not the same as a working API: the deployed backend needs `DATABASE_URL` configured before login, records and sessions can operate. Automated tests, all final acceptance checks and the submission report/evidence still need completion.
