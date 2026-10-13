# GymTrack

GymTrack is a gym management web app for keeping track of members, trainers, memberships, attendance, and workout plans. This is a CSE309 project.

## Tech stack

- Frontend: React, TypeScript, and Vite
- Backend: Python and FastAPI
- Frontend/backend communication: REST API

## Current status

The repository has the initial dashboard and a few API endpoints to check that the frontend can reach the backend. The numbers on the dashboard are sample values. They are not coming from a database.

The main gym features are still to be built. The planned first version is meant to run locally and cover basic member and trainer records, memberships, attendance, and workout plans. Database storage is also part of that work. Login, role-based permissions, profiles, and deployment are planned for the later version.

## Project structure

```text
GymTrack/
├── frontend/  # React app
├── backend/   # FastAPI app
└── docs/      # PRD, SRS, and TDD
```

## Run locally

You need Python and Node.js/npm installed. Start the backend and frontend in separate terminals.

**1. Backend**  
Run these commands from the repository root:

```bash
python -m venv .venv
```

Activate the environment:

- Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

Then install the packages and start FastAPI:

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

**2. Frontend**  
Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, usually http://localhost:5173. FastAPI's interactive API page is at http://127.0.0.1:8000/docs.

## Starter endpoints

- `GET /api/health`: check whether the API is running
- `GET /api/hello?name=YourName`: test a simple request and response
- `GET /api/modules`: return the planned modules

These endpoints are only for the starter stage. Full CRUD, database storage, and authentication are not implemented yet.

See [docs/PRD.md](docs/PRD.md), [docs/SRS.md](docs/SRS.md), and [docs/TDD.md](docs/TDD.md) for the planned scope and design.
