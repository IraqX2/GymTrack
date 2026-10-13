# Technical Design Document (TDD)
## GymTrack

| Document field | Value |
|---|---|
| Version | 1.0 |
| Status | Initial technical baseline |
| Course | CSE309 |
| Last updated | 13 October 2026 |

## 1. Purpose
This document describes the proposed technical architecture, module boundaries, API conventions, data design, security approach, and verification plan for GymTrack. It separates what exists in the starter repository from design decisions that remain to be implemented.

## 2. Technology stack
- **Frontend:** React + TypeScript, built and served during development with Vite.
- **Backend:** FastAPI + Python, served locally with Uvicorn.
- **Communication:** HTTP REST API using JSON.
- **MVP persistence proposal:** SQLite, accessed through a Python ORM (SQLModel or SQLAlchemy, subject to implementation choice).
- **Version control:** Git and GitHub, using Issues, feature branches, commits, and Pull Requests.

The required frontend/backend stack is fixed by the course. The specific ORM and final deployment target remain implementation decisions.

## 3. High-level architecture
```text
Browser
  |
  v
React + TypeScript (Vite frontend)
  |  HTTP / JSON requests under /api
  v
FastAPI REST backend
  |  validation and business rules
  v
Persistence layer (planned for MVP)
  |
  v
SQLite database (proposed for local MVP)
```

The frontend is responsible for presentation, form state, and displaying responses. The backend is responsible for request validation, business rules, permission checks when added, and data persistence. The frontend must not connect directly to the database.

## 4. Repository layout
```text
GymTrack/
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── main.tsx
│       └── index.css
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── README.md
├── docs/
│   ├── PRD.md
│   ├── SRS.md
│   └── TDD.md
├── .gitignore
└── README.md
```

As the MVP grows, backend modules may be split into routers, schemas, services, and database models. Avoid adding abstractions before the core workflows require them.

## 5. Backend design

### 5.1 Current starter endpoints
| Method | Path | Purpose | Status |
|---|---|---|---|
| GET | `/api/health` | Return API health status | Implemented |
| GET | `/api/hello?name=...` | Demo request/response | Implemented |
| GET | `/api/modules` | List the planned core modules | Implemented |

FastAPI also provides interactive API documentation locally at `/docs`.

### 5.2 Planned MVP resource endpoints
| Resource | Proposed endpoints |
|---|---|
| Members | `GET /api/members`, `POST /api/members`, `GET /api/members/{id}`, `PUT /api/members/{id}`, `DELETE /api/members/{id}` |
| Trainers | Same CRUD pattern under `/api/trainers` |
| Memberships | CRUD under `/api/memberships` |
| Attendance | `POST /api/attendance`, `GET /api/attendance?member_id={id}` |
| Workout plans | CRUD under `/api/workout-plans` |

These routes are proposed and are not present in the starter yet. Endpoint schemas should use typed Pydantic request/response models. Use suitable status codes such as 200/201 for success, 204 where no response body is needed, 404 for missing records, and 422 for invalid request data.

## 6. Data model design
The initial relational model is:
- **Member** has many Membership records, Attendance records, and assigned WorkoutPlans.
- **Trainer** may be associated with multiple WorkoutPlans.
- **WorkoutPlan** may reference a member, a trainer, or both depending on the assignment workflow.
- **ProgressEntry** (Beta) references a member and optionally a workout plan.

Every entity should use a stable primary key. Foreign keys should protect relationships and required fields should be validated at the API boundary. Membership status can be stored explicitly or derived from start/end dates; choose one consistent approach during implementation. Database migrations or a documented schema-creation step should be used when persistence is added.

## 7. Frontend design
The React app currently uses a small dashboard component and a Vite proxy so local requests to `/api` are forwarded to the FastAPI server on port 8000. The displayed counts and module rows are placeholder content.

Planned frontend components:
- **Dashboard:** entry point and summary of core modules.
- **Members:** member list and create/edit form.
- **Trainers:** trainer list and create/edit form.
- **Memberships:** plan and status views.
- **Attendance:** check-in and history.
- **Workout plans:** plan creation, assignment, and details.
- **Profile and access-aware navigation (Beta):** show information and actions appropriate to the signed-in role.

Keep API calls separate from display-only concerns as the app expands, and show loading, empty, success, and error states for data operations.

## 8. Authentication and authorization (Beta)
Use established password hashing and a well-reviewed authentication approach rather than custom cryptography. The backend must verify role permissions on each protected endpoint; hiding a button in the frontend is not an authorization control. Enforce member-level data isolation so members can only access their own private records. Keep secret keys in environment variables and do not commit local `.env` files. Production deployment should use HTTPS.

## 9. Error handling and validation
- Validate incoming fields using typed request schemas.
- Return consistent JSON error responses.
- Use 404 for missing resources and 422 for invalid payloads.
- Prevent invalid relationships, such as an attendance record for a nonexistent member.
- Avoid leaking tracebacks, credentials, or private information in user-visible messages.

## 10. Local development setup
Prerequisites: Python 3.10+ and a current Node.js/npm installation.

**Backend terminal, from the repository root:**
```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

**Frontend terminal, from the repository root:**
```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite, typically `http://localhost:5173`. Check the API at `http://127.0.0.1:8000/api/health` and the interactive docs at `http://127.0.0.1:8000/docs`.

## 11. Testing strategy
- **API smoke tests:** confirm the health endpoint responds and the demo endpoints return the expected JSON.
- **CRUD tests (MVP):** test success paths, missing IDs, invalid values, and relationship constraints for each resource.
- **Frontend integration:** confirm frontend requests reach the backend through the Vite proxy and failures are displayed clearly.
- **Role/security tests (Beta):** test unauthenticated access, role restrictions, and member data isolation.
- **Regression checks:** run tests after each feature branch is merged and document any known limitations.

## 12. Release and deployment strategy
- **MVP:** local development, REST endpoints, basic CRUD, and local persistence; no public deployment required.
- **Beta:** add authentication, RBAC, profile dashboard, scoped permissions, security hardening, and deployment-specific environment configuration.

## 13. Known limitations and pending decisions
The current repository contains a starter dashboard and demo FastAPI endpoints only. It does not yet contain database persistence, core CRUD endpoints, authentication, role permissions, or production deployment. SQLite and an ORM are proposed for the MVP, but the implementation choice should be confirmed with the course requirements before being treated as final.
