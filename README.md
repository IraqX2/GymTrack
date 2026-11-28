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
- Member accounts created by signup; admin-controlled promotion to trainer or admin
- Server-enforced role authorization and member-owned records
- Trainer workspace for assigned members/workouts and progress history
- Admin dashboard with account search, role/status filters, pagination, account detail, bulk ban/unban, content moderation, activity/security views and filtered CSV exports
- Member and trainer records, memberships and attendance
- Attendance requests with an administrator approval/rejection workflow
- Workout plan management and member/trainer assignments
- Shared teams with owner-managed membership and separate create, edit and assign permissions

## Project structure

```text
GymTrack/
├── frontend/       React + TypeScript UI
├── backend/
│   ├── core/        Shared authentication dependencies and audit logging
│   ├── models/      SQLModel data models, including shared resources
│   ├── schemas/     Validated API request schemas
│   ├── repositories/ Database queries for members, groups and trainers
│   ├── services/   Domain/business rules for members, groups and trainers
│   ├── routers/    FastAPI controllers for members, groups and trainers
├── docs/           Requirements, design and final report
└── vercel.json
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the request flow and MVC-style domain layers. Member, group and trainer routes use dedicated routers, services and repositories. Authentication, attendance, membership, workout-plan/assignment and admin endpoints still have legacy handlers in `backend/gymtrack_api.py`; these are identified as remaining refactoring work.

## Run locally

Requirements: Python 3.10+ and Node.js 20+.

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually http://localhost:5173. The FastAPI API docs are at http://127.0.0.1:8000/docs.

Local development uses `./gymtrack.db` when `DATABASE_URL` is not configured. Set `JWT_SECRET_KEY` and `PASSWORD_PEPPER` in a local environment file before testing authentication. Do not commit that file.

## Trainer workflow

1. The person signs up through the normal signup form. The account receives the `user` role and a linked member profile.
2. An administrator opens Administration → Users and changes the account role to `trainer`.
3. The backend creates or reactivates the trainer staff profile using the account email.
4. An administrator assigns workout plans to members and selects that trainer.
5. The trainer signs in again and opens My Trainees to view assigned members/workouts and record progress.

The trainer role cannot be selected from public signup. A trainer does not receive administrator capabilities.

## Deployment

The Vercel backend requires a persistent PostgreSQL connection string. It does not use temporary SQLite storage on Vercel.

Set these server-side variables in Vercel for Preview and Production:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection string using the pooler |
| `JWT_SECRET_KEY` | JWT signing secret |
| `PASSWORD_PEPPER` | Separate password-hashing pepper |
| `BOOTSTRAP_ADMIN_EMAIL` | Account permitted to receive the initial administrator role |
| `FRONTEND_URLS` | Allowed frontend origins if using a separate frontend origin |

The connected GymTrack Supabase project already contains `public.trainer_progress` from migration `20261127071138_gymtrack_trainer_access_and_private_tables`; this branch maps to that existing schema and does not require another progress-table migration. Apply future schema changes through reviewed migrations. Never commit secrets or put them in frontend code. See [Final deployment setup](docs/FINAL_DEPLOYMENT_SETUP.md).

## Main API routes

| Area | Routes |
|---|---|
| Authentication | `/api/auth/signup`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/logout` |
| Profile and sessions | `/api/me`, `/api/auth/sessions` |
| Members | `/api/members` |
| Trainers | `/api/trainers` |
| Trainer workspace | `/api/trainer/dashboard`, `/api/trainer/assignments/{id}/progress` |
| Memberships | `/api/memberships` |
| Attendance | `/api/attendance`, `/api/attendance/requests` |
| Workout plans | `/api/workout-plans`, `/api/workout-assignments` |
| Shared teams | `/api/groups` |
| Administration | `/api/admin/stats`, `/api/admin/users`, `/api/admin/users/{id}`, `/api/admin/content`, `/api/admin/activity`, `/api/admin/security` |
| Admin exports | `/api/admin/export/users`, `/api/admin/export/members`, `/api/admin/export/trainers`, `/api/admin/export/memberships`, `/api/admin/export/attendance`, `/api/admin/export/workouts`, `/api/admin/export/assignments`, `/api/admin/export/groups`, `/api/admin/export/activity` |

The API docs page is `/api/docs` on Vercel and `/docs` locally.

## Access rules

- The frontend does not connect directly to PostgreSQL. It calls FastAPI.
- Administrator operations are checked by FastAPI, not just hidden in React.
- A member can read only their own membership, attendance and workout records.
- A trainer sees only workouts and members assigned to that trainer profile; trainer progress endpoints re-check assignment ownership.
- Only group owners can rename/delete a group or manage its membership. Group create/edit/assign permissions are checked by FastAPI.


## Demo account IDs and shared group permissions

The hosted demo database currently contains the following account IDs and roles. Passwords are deliberately excluded from this public repository; enter them only in the private final-submission form.

| User ID | Role |
|---:|---|
| 1 | Admin |
| 5 | Admin |
| 2 | User/member |
| 3 | User/member |
| 4 | User/member |
| 6 | User/member |

**Shared group: Training Operations Team (Group ID 5)**

Owner: User ID 1 (all group permissions).

| Member user ID | Create tasks | Edit tasks | Assign tasks |
|---:|---:|---:|---:|
| 2 | Yes | No | No |
| 3 | No | Yes | No |
| 4 | No | No | Yes |
| 5 | No | No | No |

The deployed demo currently has one trainer staff profile without a linked login account. For the recording, an administrator should promote User ID 6 to Trainer, assign a workout to that trainer, then sign in as User ID 6 to demonstrate the trainer dashboard. User IDs 2, 3 and 4 remain normal demo accounts.

## Known verification items

The final course rubric still requires live testing and submission artifacts. Review [docs/REQUIREMENTS_TRACEABILITY.md](docs/REQUIREMENTS_TRACEABILITY.md) and [docs/FINAL_REPORT.md](docs/FINAL_REPORT.md) for the remaining checks. Do not use real member data until Supabase grants/RLS have been reviewed.
