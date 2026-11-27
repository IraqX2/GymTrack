# GymTrack Technical Design Document (TDD)

**Course:** CSE309 · Autumn 2026  
**Version:** 2.0 · **Status:** Final implementation scope  
**Detailed report:** [FINAL_REPORT.md](FINAL_REPORT.md) · [Architecture notes](ARCHITECTURE.md)

## 1. Overview

GymTrack is a React/TypeScript frontend with a FastAPI backend and SQLModel persistence. In production the backend connects to Supabase PostgreSQL and the app is deployed on Vercel.

## 2. Layered request design

The trainer feature follows an MVC-style layered architecture:

1. React page displays the data and gathers user input.
2. The shared frontend API client sends an authenticated HTTP request.
3. A FastAPI router handles the endpoint.
4. Shared auth dependencies validate identity and role.
5. The domain service enforces business rules.
6. A repository performs SQLModel queries and persistence.
7. SQLModel maps data to relational tables.

## 3. Trainer implementation files

| File | Responsibility |
|---|---|
| backend/models/trainer.py | Trainer staff model |
| backend/models/workout.py | Workout plan and assignment models |
| backend/models/trainer_progress.py | Progress history model |
| backend/schemas/trainer.py | Role and progress request validation |
| backend/repositories/trainer_repository.py | Trainer and assignment queries |
| backend/services/trainer_service.py | Promotion, assignment ownership and progress rules |
| backend/routers/trainers.py | Admin and trainer API routes |
| backend/core/dependencies.py | Shared authenticated-user/admin/trainer dependencies |
| backend/core/audit.py | Reusable audit logging |
| frontend/src/pages/TrainerDashboard.tsx | Trainer view and progress form |
| frontend/src/services/gymtrack.ts | Authenticated API client |

Older resource endpoints remain in backend/gymtrack_api.py and are documented as pending domain-by-domain refactoring.

## 4. Trainer role flow

- Signup always creates a user account and links a member profile.
- An admin changes the account role to trainer.
- The trainer service finds or creates the trainer profile using normalized email.
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

Local development defaults to SQLite. Vercel requires DATABASE_URL and must use hosted PostgreSQL. The trainer progress table is created by applying backend/migrations/2026_11_27_trainer_progress.sql to Supabase. Hosted schema must not be assumed to update from SQLModel create_all at server startup.

## 7. Deployment

Configure DATABASE_URL, JWT_SECRET_KEY, PASSWORD_PEPPER and BOOTSTRAP_ADMIN_EMAIL as Vercel server-side environment variables. Configure FRONTEND_URLS if the frontend/API use different origins. Never commit secret values.

## 8. Testing and limitations

Run the trainer promotion, assignment filtering, cross-trainer denial, member ownership, JWT expiry/refresh, logout/revocation, group permission and hosted persistence checks on the deployed URL. The current source still needs broader automated pytest coverage and further modularization of earlier resource endpoints. See docs/REQUIREMENTS_TRACEABILITY.md for remaining rubric items.
