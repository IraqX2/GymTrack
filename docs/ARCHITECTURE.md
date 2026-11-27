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

## Trainer feature structure

| Layer | File | Responsibility |
|---|---|---|
| Model | `backend/models/trainer.py` | Gym trainer profile |
| Model | `backend/models/workout.py` | Workout plans and assignments |
| Model | `backend/models/trainer_progress.py` maps the existing `public.trainer_progress` table. | Trainer progress records |
| Schema | `backend/schemas/trainer.py` | Validated request bodies and role values |
| Repository | `backend/repositories/trainer_repository.py` | Database reads and writes |
| Service | `backend/services/trainer_service.py` | Promotion, assignment ownership, progress business rules |
| Router | `backend/routers/trainers.py` | HTTP endpoints and response codes |
| Shared dependency | `backend/core/dependencies.py` | Current-user, admin and trainer authorization |
| Shared audit | `backend/core/audit.py` | Audit events with request metadata |
| View | `frontend/src/pages/TrainerDashboard.tsx` | Assigned members/workouts and progress form |
| API client | `frontend/src/services/gymtrack.ts` | Authenticated API calls and refresh behavior |

## Role model

- `user`: normal account created by signup. It has member self-service access.
- `trainer`: an administrator-promoted account. It retains its linked member profile and gains access to a trainer workspace.
- `admin`: manages gym operations and user roles.

The trainer record is a gym staff profile. The login account role is stored in the `user` table. The service links them through the existing `trainer.user_id` foreign key, using `trainer.user_id`, with normalized email only as a compatibility fallback. New signups cannot choose their own role.

## Trainer authorization

The API resolves the signed-in account from the access token and reloads the account from the database. The trainer dependency rejects accounts without the trainer role. The service then finds the active trainer profile and filters assignments by its trainer ID. Progress queries and writes also verify that the requested assignment belongs to that trainer. The frontend navigation is a convenience only; the backend checks are the security boundary.

## Scope of the refactor

The new trainer feature is separated into router, service, repository, schema and model layers. Shared authentication and audit code have also been extracted from the original API module into `backend/core`.

Some pre-existing member, attendance, membership, workout and group endpoints remain in `backend/gymtrack_api.py`. They were retained during this feature change to avoid a broad rewrite of working workflows immediately before the submission deadline. The next maintainability step is to migrate each existing domain into the same router/service/repository structure. The frontend's original app shell also still hosts several older page components; the trainer dashboard is a dedicated page module.
