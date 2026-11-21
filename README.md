# GymTrack

GymTrack is a gym management web app for keeping track of members, trainers, memberships, attendance, and workout plans. This is a CSE309 project.

## Tech stack

- Frontend: React, TypeScript, and Vite
- Backend: Python and FastAPI
- Database: SQLModel with SQLite locally or hosted PostgreSQL through \`DATABASE_URL\`
- Authentication: Argon2id password hashes, short-lived JWT access tokens, and rotating HTTP-only refresh sessions

## Implemented features

### Member management

- Create, list, read, update, and delete member records
- Validate required fields and email addresses
- Prevent duplicate member email addresses
- Persist member records through SQLModel

### Authentication and access control

- Sign up and log in with an email and password
- Passwords are peppered using a server-side environment variable and hashed with Argon2id
- JWT access tokens expire after 15 minutes and contain the user ID, role, and session ID
- Refresh tokens are stored only as hashes, rotated on refresh, and sent in an HTTP-only cookie
- Logout revokes the refresh session
- Users can list and revoke their own sessions
- Users can update their profile and change their password
- Changing a password revokes existing sessions and issues a new session for the current browser
- Public signup always creates the normal \`user\` role
- Member-management endpoints require the \`admin\` role on the server

## Project structure

\`\`\`text
GymTrack/
├── frontend/       # React + TypeScript app
├── backend/        # FastAPI app, models, services, and routes
├── docs/           # PRD, SRS, TDD, and implementation progress
└── .env.example    # Required environment variable names
\`\`\`

## Local setup

You need Python 3.10+ and Node.js/npm. Run the backend and frontend in separate terminals.

### 1. Configure the backend

Copy \`.env.example\` to \`.env\`. Replace both example secret values with different random values of at least 32 characters. Do not commit \`.env\`.

Install dependencies and start FastAPI:

\`\`\`bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
\`\`\`

The API documentation is available at http://127.0.0.1:8000/docs.

Local development uses \`gymtrack.db\` by default. For a persistent deployment, configure \`DATABASE_URL\` with a hosted PostgreSQL connection string. Vercel's \`/tmp\` SQLite fallback is temporary and is not suitable for assessed production data.

### 2. Create the first administrator

Public signup cannot create an administrator. After configuring the same database URL and secrets that the app will use, run:

\`\`\`bash
python -m backend.create_admin
\`\`\`

The command prompts for the administrator name, email, and password. Use a demo account for the instructor, not a personal password.

### 3. Start the frontend

In another terminal:

\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

Open the Vite URL, usually http://localhost:5173. Vite proxies \`/api\` requests to FastAPI on port 8000.

## Authentication API

| Method | Endpoint | Description |
|---|---|---|
| POST | \`/api/auth/register\` | Create a normal user account |
| POST | \`/api/auth/login\` | Log in and issue tokens |
| POST | \`/api/auth/refresh\` | Rotate the HTTP-only refresh cookie |
| POST | \`/api/auth/logout\` | Revoke the current refresh session |
| GET | \`/api/auth/me\` | Read the authenticated user's profile |
| PATCH | \`/api/auth/me\` | Update the authenticated user's name |
| POST | \`/api/auth/change-password\` | Change password after checking the current password |
| GET | \`/api/auth/sessions\` | List the authenticated user's sessions |
| DELETE | \`/api/auth/sessions/{id}\` | Revoke one of the user's sessions |

The frontend keeps the short-lived access token in memory and sends it as a Bearer token. The refresh token is never exposed to JavaScript.

## Member API

All member endpoints require an authenticated administrator:

| Method | Endpoint | Description |
|---|---|---|
| POST | \`/api/members\` | Create a member |
| GET | \`/api/members\` | List members |
| GET | \`/api/members/{id}\` | Read one member |
| PUT | \`/api/members/{id}\` | Update a member |
| DELETE | \`/api/members/{id}\` | Delete a member |

## Tests

Run backend unit tests from the repository root:

\`\`\`bash
python -m pytest backend/tests
\`\`\`

## Remaining assessment work

This is an implementation increment, not the completed final-project specification. Admin user management, ban/unban controls, detailed audit logging, group/team membership permissions, CSV exports, brute-force protection, broader RBAC tests, and verified production deployment still need to be completed.
