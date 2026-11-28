# GymTrack Technical Design Document (TDD)

**Course:** CSE309 · Autumn 2026  
**Version:** 2.0 · **Status:** Final implementation scope  
**Detailed report:** [FINAL_REPORT.md](FINAL_REPORT.md) · [Architecture notes](ARCHITECTURE.md)

## 1. Overview

GymTrack is a React/TypeScript frontend with a FastAPI backend and SQLModel persistence. In production the backend connects to Supabase PostgreSQL and the app is deployed on Vercel.

## 2. Layered request design

The member, group and trainer domains follow an MVC-style layered architecture:

1. React page displays the data and gathers user input.
2. The shared frontend API client sends an authenticated HTTP request.
3. A FastAPI router handles the endpoint.
4. Shared auth dependencies validate identity and role.
5. The domain service enforces business rules.
6. A repository performs SQLModel queries and persistence.
7. SQLModel maps data to relational tables.

## 3. Implemented domain modules

| Domain/layer | File | Responsibility |
|---|---|---|
| Models | `backend/models/resources.py` | Auth sessions, memberships, attendance and groups |
| Schemas | `backend/schemas/resources.py` | Shared resource request validation |
| Member repository/service/router | `backend/repositories/member_repository.py`, `backend/services/member_service.py`, `backend/routers/members.py` | Member queries, ownership and CRUD endpoints |
| Membership repository/service/router | `backend/repositories/membership_repository.py`, `backend/services/membership_service.py`, `backend/routers/memberships.py` | Subscription data, validation and CRUD endpoints |
| Attendance repository/service/router | `backend/repositories/attendance_repository.py`, `backend/services/attendance_service.py`, `backend/routers/attendance.py` | Check-in/out and attendance correction requests |
| Workout repository/service/router | `backend/repositories/workout_repository.py`, `backend/services/workout_service.py`, `backend/routers/workouts.py` | Workout plans and member/trainer assignments |
| Group repository/service/router | `backend/repositories/group_repository.py`, `backend/services/group_service.py`, `backend/routers/groups.py` | Group data access and permission-enforced endpoints |
| Trainer repository/service/router | `backend/repositories/trainer_repository.py`, `backend/services/trainer_service.py`, `backend/routers/trainers.py` | Trainer profiles, assignment ownership and progress |
| Shared security | `backend/core/dependencies.py`, `backend/core/audit.py` | Authentication, role dependencies and audit logging |
| Trainer view | `frontend/src/pages/TrainerDashboard.tsx` | Trainer view and progress form |
| API client | `frontend/src/services/gymtrack.ts` | Authenticated API calls and refresh behavior |

Authentication/profile/session and admin endpoint handlers remain in `backend/gymtrack_api.py` and need domain-by-domain extraction.

## 4. Trainer role flow

- Signup always creates a user account and links a member profile.
- An admin changes the account role to trainer.
- The trainer service links the trainer profile using `trainer.user_id`, falling back to normalized email for an older profile without an account link.
- The admin assigns a workout plan and selects the trainer.
- The trainer dashboard queries assignments by the signed-in trainer ID.
- Progress reads and writes verify assignment ownership.

## 5. Authentication and security

- Argon2 password hashing uses a server-side pepper.
- Access JWT is configured for a 15-minute lifetime.
- Protected requests verify JWT signature and expiry, then reload the account to check role and ban status.
- Refresh uses an HttpOnly cookie and server-side hashed refresh token with rotation.
- Logout/session revocation invalidates refresh sessions.
- Admin/trainer and ownership checks are enforced by the backend.

## 6. Database and migration

Local development defaults to SQLite. Vercel requires DATABASE_URL and must use hosted PostgreSQL. The production GymTrack Supabase project already contains `public.trainer_progress` from migration `20261127071138_gymtrack_trainer_access_and_private_tables`; the application maps to that table, so no duplicate table migration is needed. Hosted schema must not be assumed to update from SQLModel create_all at server startup.

## 7. Deployment

Configure DATABASE_URL, JWT_SECRET_KEY, PASSWORD_PEPPER and BOOTSTRAP_ADMIN_EMAIL as Vercel server-side environment variables. Configure FRONTEND_URLS if the frontend/API use different origins. Never commit secret values.

## 8. Testing and limitations

Run the trainer promotion, assignment filtering, cross-trainer denial, member ownership, JWT expiry/refresh, logout/revocation, group permission and hosted persistence checks on the deployed URL. The current source still needs broader automated pytest coverage and further modularization of earlier resource endpoints. See docs/REQUIREMENTS_TRACEABILITY.md for remaining rubric items.
