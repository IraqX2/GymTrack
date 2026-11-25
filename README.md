# GymTrack

GymTrack is a gym-management application for members, trainers, memberships, attendance, workout plans and staff collaboration.

## Technology

- Frontend: React, TypeScript and Vite
- Backend: Python, FastAPI and SQLModel
- Database: SQLite for local development; PostgreSQL on Supabase for deployment
- Authentication: Argon2 password hashing, signed JWT access tokens and rotating HttpOnly refresh sessions
- Hosting: Vercel

## Features

- Account signup, login, profile updates, password changes and session management
- Admin and member roles with backend authorization and member-owned records
- Admin dashboard with account management, activity/security views and CSV exports
- Member and trainer records
- Membership plans with dates, price and status
- Attendance check-in/check-out and member attendance history
- Member attendance requests with an administrator approval/rejection workflow
- Workout plan management and member/trainer assignments
- Shared teams with owner-managed membership and separate create, edit and assign permissions

## Project structure

```text
GymTrack/
├── frontend/       React + TypeScript UI
├── backend/        FastAPI application and SQLModel database access
├── docs/           Requirements and deployment documentation
└── vercel.json     Vercel frontend/API routing
```

## Run locally

Requirements: Python 3.10+ and Node.js 20+.

From the repository root, create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually http://localhost:5173. The FastAPI API docs are at http://127.0.0.1:8000/docs.

Local development uses `./gymtrack.db` when `DATABASE_URL` is not configured. Set separate `JWT_SECRET_KEY` and `PASSWORD_PEPPER` values for local authentication. To use the hosted database locally, set `DATABASE_URL` to the private PostgreSQL connection string.

## Deployment

The Vercel backend requires a persistent PostgreSQL connection string. It does not use temporary SQLite storage on Vercel.

Set the following server-side environment variables for Preview and Production:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection string using the pooler |
| `JWT_SECRET_KEY` | JWT signing secret |
| `PASSWORD_PEPPER` | Separate password-hashing pepper |
| `BOOTSTRAP_ADMIN_EMAIL` | Account permitted to receive the initial administrator role |

Never commit these values or put them in frontend code. See [Final deployment setup](docs/FINAL_DEPLOYMENT_SETUP.md).

## Main API routes

| Area | Routes |
|---|---|
| Authentication | `/api/auth/signup`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout` |
| Profile and sessions | `/api/me`, `/api/auth/sessions` |
| Members | `/api/members` |
| Trainers | `/api/trainers` |
| Memberships | `/api/memberships` |
| Attendance | `/api/attendance` |
| Attendance requests | `/api/attendance/requests` |
| Workout plans | `/api/workout-plans`, `/api/workout-assignments` |
| Shared teams | `/api/groups` |
| Administration | `/api/admin/stats`, `/api/admin/users`, `/api/admin/activity`, `/api/admin/security` |

The deployed API documentation is available at `/api/docs`.

## Access rules

- The frontend does not connect directly to PostgreSQL. It calls the FastAPI backend.
- Administrator-only operations are checked by FastAPI, not just hidden in React.
- A member can read only their own member, membership, attendance and workout records.
- Only an administrator can create a team. Its owner controls membership and grants.
- Team members can create, edit or assign shared tasks only when the corresponding permission is granted. These permissions are checked by the backend.
- Member attendance requests stay pending until an administrator approves or rejects them.

## Deployment and security notes

The application uses the private PostgreSQL connection from the backend. The Supabase project inspection also identified disabled Row Level Security on existing public tables. The frontend does not use the Supabase Data API, but the RLS and grants configuration still needs a deliberate security review before storing real member information. Do not enable RLS without considering the backend database role and required access.

A successful build confirms that the source compiles. It does not replace testing authentication, record operations, ownership restrictions, team permissions and data persistence on the deployed URL.
