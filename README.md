# GymTrack

GymTrack is a gym management web app for keeping track of members, trainers, memberships, attendance, and workout plans. This is a CSE309 project.

## Tech stack

- Frontend: React, TypeScript, and Vite
- Backend: Python and FastAPI
- Database: SQLite with SQLModel
- Frontend/backend communication: REST API

## Member Management MVP

The current MVP implements member record management:

- Create a member
- List members
- Read one member by ID
- Update member details
- Delete a member
- Validate required fields and email addresses
- Prevent duplicate email addresses
- Store member records in SQLite

Other GymTrack modules are planned for later development.

## Project structure

```text
GymTrack/
├── frontend/  # React + TypeScript app
├── backend/   # FastAPI app and SQLite model
└── docs/      # PRD, SRS, and TDD
```

## Run locally

You need Python 3.10+ and Node.js/npm installed. Start the backend and frontend in separate terminals.

### 1. Backend

From the repository root:

```bash
python -m venv .venv
```

Activate the environment:

- Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

Install dependencies and start FastAPI:

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

The API documentation is available at http://127.0.0.1:8000/docs.

The local database file `gymtrack.db` is created automatically when the backend starts. It is excluded from Git.

### 2. Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, usually http://localhost:5173. Vite proxies `/api` requests to the local FastAPI server on port 8000.

## Member API

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/members` | Create a member |
| GET | `/api/members` | List members |
| GET | `/api/members/{id}` | Read one member |
| PUT | `/api/members/{id}` | Update a member |
| DELETE | `/api/members/{id}` | Delete a member |

The list endpoint supports `offset` and `limit` query parameters.

## Notes

- Member data is stored by the FastAPI backend, not in browser local storage.
- SQLite is suitable for local demonstration. A persistent hosted database is required for production deployment.
- Authentication and role-based permissions are outside this MVP.
