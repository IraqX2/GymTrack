# GymTrack

GymTrack is a web-based gym management system for organizing members, trainers, memberships, attendance, and workout plans.

## Technology stack
- **Frontend:** React + TypeScript + Vite
- **Backend:** FastAPI + Python
- **API style:** REST

## Planned releases

### MVP — Midterm demo
- React + TypeScript starter dashboard
- FastAPI service and REST endpoints
- Core CRUD workflows for members, trainers, memberships, attendance, and workout plans
- Run locally

### Beta — Final demo
- Authentication and role-based access control (RBAC)
- User profile dashboard
- Permission/security scopes
- Deployment

> The dashboard statistics and module cards currently contain demo/placeholder data. Database persistence and full CRUD are not implemented yet.

## Repository structure
```text
GymTrack/
├── frontend/  # React + TypeScript + Vite
├── backend/   # FastAPI + Python
└── docs/      # PRD, SRS, and TDD
```

## Run locally

Use two terminals from the repository root.

**Terminal 1 — Backend**

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

**Terminal 2 — Frontend**

```bash
cd frontend
npm install
npm run dev
```

Open the local URL shown by Vite, usually http://localhost:5173. The FastAPI interactive docs are at http://127.0.0.1:8000/docs.

## Current status

This repository contains the initial frontend and backend foundation. Core business workflows, database persistence, authentication, and deployment remain future work.
