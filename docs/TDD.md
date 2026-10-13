# Technical Design Document (TDD)

## GymTrack

- **Course:** CSE309
- **Version:** 1.1
- **Status:** Draft
- **Updated:** 13 October 2026

## 1. Overview

This document explains how GymTrack is arranged now and how the main features are expected to be added. The current code is a starter, so the proposed database and gym-management endpoints below are not implemented yet.

## 2. Technology

- React, TypeScript, and Vite for the frontend.
- Python and FastAPI for the backend.
- REST endpoints with JSON for communication.
- SQLite is proposed for local data storage in the first version.
- GitHub Issues, feature branches, and pull requests for tracking changes.

## 3. Application structure

The browser loads the React app. The frontend sends HTTP requests to FastAPI. When database storage is added, the backend will validate the request and read or write records in SQLite.

```text
Browser
  |
  v
React + TypeScript (Vite)
  |
  | HTTP / JSON
  v
FastAPI backend
  |
  v
SQLite database (planned)
```

The frontend should not connect directly to the database. Validation and data rules belong in the backend.

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
└── README.md
```

## 5. Backend

### Endpoints already in the starter

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Check whether the API is running |
| GET | `/api/hello?name=...` | Test a simple request and response |
| GET | `/api/modules` | Return the list of planned modules |

FastAPI also provides an interactive page at `/docs` when the backend is running.

### Endpoints planned for the first version

| Resource | Planned operations |
|---|---|
| Members | Create, list, view, edit, and delete |
| Trainers | Create, list, view, edit, and delete |
| Memberships | Create, list, view, edit, and delete |
| Attendance | Record a check-in and view history |
| Workout plans | Create, list, view, edit, and delete |

The exact paths and request fields should be settled when each feature is implemented. The backend should validate the submitted data and return useful status codes. For example, a missing record should return 404 and invalid input should return a 4xx response.

## 6. Database plan

SQLite is proposed because the first version needs to run locally without a separate database server. The initial tables are expected to be:

- **Member:** member details and active status.
- **Trainer:** trainer details and specialization.
- **Membership:** member reference, plan, dates, and status.
- **Attendance:** member reference and check-in time.
- **WorkoutPlan:** title, description, and assigned member/trainer.
- **ProgressEntry (later version):** member reference, date, and progress notes.

Each table should have a unique ID. Related records should use valid references. The final fields and database library still need to be confirmed during implementation.

## 7. Frontend plan

The current dashboard is in `frontend/src/App.tsx`. It displays sample counts and planned modules, and includes a small form to test the API connection. The numbers are not real gym data.

As the project grows, the planned pages are:

- Members
- Trainers
- Memberships
- Attendance
- Workout plans

Each page should call the backend rather than keep its own separate copy of the data. Forms should show validation errors and a useful message when a request fails.

## 8. Login and permissions

Login is planned for the later version. When it is added, the backend must check the user's role on protected requests. Hiding a button in React is not enough to protect data. Passwords should be hashed using an established library, and secret keys should be kept out of the repository.

## 9. Local setup

Install Python and Node.js/npm first. Run the backend and frontend in separate terminals.

**Backend, from the repository root:**

```bash
python -m venv .venv
```

Activate the environment:

- Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

Then run:

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

**Frontend, in another terminal:**

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite, usually `http://localhost:5173`. To check the backend, open `http://127.0.0.1:8000/api/health` or `http://127.0.0.1:8000/docs`.

## 10. Testing plan

For the starter, check that the health endpoint works and that the frontend can send a request to the backend.

When the main features are added, test that:
- records can be created, viewed, edited, and deleted;
- invalid input is rejected;
- memberships and attendance refer to existing members;
- workout plans can be assigned correctly;
- the frontend shows an error if the API is unavailable.

After login is added, test that each role can only access the actions and records it is allowed to use.

## 11. Known gaps

The repository currently has no database, full CRUD endpoints, login, role permissions, or deployment setup. SQLite is a proposal, not a completed implementation. These items should be added in small steps and reflected in the documentation as they are completed.
