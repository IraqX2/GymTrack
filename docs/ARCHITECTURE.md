# GymTrack architecture

## Architecture decision

GymTrack uses a layered, MVC-style architecture. The course reference calls this style MVC; the sample repository also separates routers/controllers, services, repositories, models, schemas and shared dependencies. The implementation in GymTrack is independently written and uses the same general separation-of-concerns principles rather than reproducing the sample source.

## Request flow

```text
React page / component (View)
        |
        v
frontend/src/services/gymtrack.ts (HTTP client)
        |
        | JSON + bearer access token + refresh cookie
        v
FastAPI router (Controller)
        |
        v
Shared authentication / role dependency
        |
        v
Domain service (business rules)
        |
        v
Repository (database queries)
        |
        v
SQLModel (Model) -> PostgreSQL / SQLite
```

## Domain layer structure

| Domain/layer | File | Responsibility |
|---|---|---|
| Models | `backend/models/member.py`, `backend/models/trainer.py`, `backend/models/workout.py`, `backend/models/trainer_progress.py` | Member, trainer, workout and progress data |
| Shared models | `backend/models/resources.py` | Auth sessions, memberships, attendance and groups |
| Shared schemas | `backend/schemas/resources.py` | Authentication, membership, attendance, workout and group request validation |
| Member repository | `backend/repositories/member_repository.py` | Member queries and persistence |
| Member service | `backend/services/member_service.py` | Member CRUD, ownership checks and history safeguards |
| Member router | `backend/routers/members.py` | Member HTTP endpoints and role dependencies |
| Membership repository/service/router | `backend/repositories/membership_repository.py`, `backend/services/membership_service.py`, `backend/routers/memberships.py` | Subscription queries, validation and role-protected CRUD |
| Attendance repository/service/router | `backend/repositories/attendance_repository.py`, `backend/services/attendance_service.py`, `backend/routers/attendance.py` | Check-in/out and member correction requests |
| Workout repository/service/router | `backend/repositories/workout_repository.py`, `backend/services/workout_service.py`, `backend/routers/workouts.py` | Plans, assignment validation and member filtering |
| Group repository | `backend/repositories/group_repository.py` | Group, membership and task queries |
| Group service | `backend/services/group_service.py` | Ownership and create/edit/assign permission rules |
| Group router | `backend/routers/groups.py` | Group, membership and group-work endpoints |
| Trainer repository | `backend/repositories/trainer_repository.py` | Trainer and assignment queries |
| Trainer service | `backend/services/trainer_service.py` | Promotion, assignment ownership and progress rules |
| Trainer router | `backend/routers/trainers.py` | Trainer management and workspace endpoints |
| Shared dependencies | `backend/core/dependencies.py` | Current-user, admin and trainer authorization |
| Shared audit | `backend/core/audit.py` | Audit events with request metadata |
| Views | `frontend/src/pages/TrainerDashboard.tsx`, `frontend/src/App.tsx` | Trainer and member/admin interfaces |
| API client | `frontend/src/services/gymtrack.ts` | Authenticated API calls and refresh behavior |

## Role model

- `user`: normal account created by signup. It has member self-service access.
- `trainer`: an administrator-promoted account. It retains its linked member profile and gains access to a trainer workspace.
- `admin`: manages gym operations and user roles.

The trainer record is a gym staff profile. The login account role is stored in the `user` table. The service links them through the existing `trainer.user_id` foreign key, with normalized email used only as a compatibility fallback. New signups cannot choose their own role.

## Trainer authorization

The API resolves the signed-in account from the access token and reloads the account from the database. The trainer dependency rejects accounts without the trainer role. The service then finds the active trainer profile and filters assignments by its trainer ID. Progress queries and writes also verify that the requested assignment belongs to that trainer. The frontend navigation is a convenience only; the backend checks are the security boundary.

## Scope of the refactor

Member, group, trainer, membership, attendance and workout-plan/assignment domains now have dedicated router/controller, service, repository, schema and model layers. Shared resource table models and request schemas have also been moved out of the monolithic API module. The remaining authentication/profile/session and admin management/export handlers still live in `backend/gymtrack_api.py`; they are the next domain-by-domain refactoring work. This is a partial migration of the legacy API, not a claim that every endpoint is already modular.
