# GymTrack deployment and account setup

## Database

The Vercel backend connects directly to the Supabase PostgreSQL database using the private connection string. The frontend does not use a Supabase client or database password.

The schema includes user accounts and sessions, member and trainer records, memberships, attendance, attendance requests, workout plans and assignments, shared groups, group permissions, shared tasks and activity logs.

## Vercel environment variables

Open Vercel → GymTrack → Settings → Environment Variables. Configure these variables for both Preview and Production:

| Name | Purpose |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL transaction-pooler URI |
| `JWT_SECRET_KEY` | Random secret used to sign access tokens |
| `PASSWORD_PEPPER` | Separate server-side value used by Argon2 password hashing |
| `BOOTSTRAP_ADMIN_EMAIL` | Email address that may receive the initial administrator role |

Keep every value private. Do not commit database credentials or put them in frontend code. Do not regenerate the password pepper after users have registered, because existing password hashes depend on it.

After changing Vercel environment variables, redeploy the project. The API health endpoint is `/api/health`; the API documentation is `/api/docs`.

## Local development

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Set local `JWT_SECRET_KEY` and `PASSWORD_PEPPER` values before testing signup/login. Local development uses SQLite by default. To test against Supabase, set `DATABASE_URL` to the private PostgreSQL connection string in the local environment.

## Initial accounts

The hosted demo database currently contains six test accounts: two administrators and four regular users. The account IDs and current roles are listed in the root README. Their credentials are stored separately from the source repository and must be provided to the instructor only through the required private submission fields/report.

Do not store test passwords in this repository or use real personal accounts as demonstration data.

## Cross-device persistence checks

1. Sign in as an administrator and create a member, membership, attendance entry, workout plan and assignment.
2. Open the deployed application on another device and sign in as the intended member.
3. Confirm that the member sees only their own membership, attendance and assigned workout records.
4. Sign in as a different member and confirm that the first member's private records are not visible.
5. Submit an attendance request as a member and review it as an administrator.
6. Add a registered user to a group and grant selected create/edit/assign permissions.
7. Confirm an action outside the member's permissions is rejected by the API.

## Database security

A Supabase inspection reported Row Level Security disabled on existing public tables. The GymTrack frontend calls FastAPI rather than the Supabase Data API, and the backend uses the private PostgreSQL connection. Still, review table grants and RLS policies before using real personal data. Enabling RLS without accounting for the backend database role can block expected backend access.
