# GymTrack requirements traceability

This document maps GymTrack to the CSE309 Autumn 2026 final-project expectations and records the extra trainer workflow.

## Roles

- **Admin:** manages gym records, accounts, roles and shared groups.
- **User/member:** created by public signup; views their own membership, attendance and assigned workouts.
- **Trainer:** a normal registered account that an administrator promotes. It keeps its member profile and receives a trainer workspace for assigned trainees and workouts.

The course brief requires normal user and admin roles. GymTrack adds trainer as a third application role without allowing public signup to choose privileged access.

## Implemented workflows in source

| Requirement | Implementation |
|---|---|
| Signup/login | FastAPI authentication routes with Argon2 password hashing |
| Access token | Signed JWT, 15-minute lifetime, identity and role claims, account reload on protected requests |
| Refresh/logout | HttpOnly refresh cookie, stored token hash, token rotation and revocation |
| Sessions | List/revoke own sessions; admin can revoke all sessions for an account |
| Profile/password | Profile update and password change with current password verification |
| Member ownership | Member dashboard, memberships, attendance, requests and workouts filtered to signed-in member |
| Admin authorization | Shared FastAPI admin dependency |
| Trainer promotion | Admin role selector; public signup always creates normal user |
| Trainer profile | Promotion creates/reactivates a trainer record linked by normalized email |
| Trainer dashboard | Shows only assignments linked to signed-in trainer's profile |
| Trainer progress | Trainer can view and write progress only for their own assignments |
| Gym records | Admin screens for member/trainer CRUD, memberships, attendance, workout plans and assignments |
| Attendance requests | Member submits; admin approves/rejects |
| Administration | Account search, role/status filters, paginated results, account detail, role changes, ban/unban, bulk ban/unban, session revocation, activity/security views and CSV exports |
| Shared groups | Owner-managed membership and server-enforced create/edit/assign permissions |
| Content moderation | Search and paginate supported record types; delete one/many memberships, attendance entries, workout plans, assignments, groups and trainer progress |
| CSV exports | Filter-aware user/member/activity exports plus trainer, membership, attendance, plan, assignment and group exports; export events are audited |
| Security summaries | Failed-login events summarized by IP address and account |
| Database | Supabase PostgreSQL for deployment; local SQLite only for local development |
| Frontend/backend separation | React calls FastAPI through the shared frontend API service |

## Trainer permissions

A trainer is not an administrator. A trainer cannot manage accounts, membership plans, global workout plans or gym staff. They see only member details included in assignments allocated to their trainer profile. The backend checks assignment ownership again before returning or saving progress.

The trainer profile is linked to an account by normalized email. When an administrator demotes a trainer, the profile is marked inactive and the account returns to the user role. Historical assignments are preserved.

## Architecture

The new trainer workflow uses router, service, repository, schema, model and shared auth/audit layers. See [ARCHITECTURE.md](ARCHITECTURE.md). This is an independently implemented MVC-style/layered architecture, not copied source code from the instructor's reference.

Some older resource endpoints remain in `backend/gymtrack_api.py`; the remaining domain-by-domain refactor is documented as technical debt.

## Important outstanding checks against the course brief

The source now implements the main admin controls that were missing in the first review: account search/filter/pagination, account detail, bulk ban/unban, supported content moderation and broader CSV exports. GitHub Actions currently runs backend authorization/security smoke tests and a frontend TypeScript/Vite production build.

The remaining work is primarily verification and broader quality coverage:

- Run end-to-end tests against Vercel + Supabase for normal member, trainer and admin accounts.
- Verify the migration on the actual hosted database and review database grants/RLS.
- Expand pytest coverage to login failures, refresh rotation, logout/revocation, member ownership and group create/edit/assign denial.
- Check moderation/export flows using representative hosted records and confirm exported data respects the active filter choices.
- Continue migrating older endpoint domains out of `backend/gymtrack_api.py` into separate routers, services and repositories.
- Record the required screenshots and voice demo from the deployed application.

The content-moderation page intentionally supports memberships, attendance, workout plans, assignments, groups and trainer progress. It is not a generic delete operation for every database table. Do not claim live behavior without completing the deployed checks.

## Deployment and student submission items

Apply `backend/migrations/2026_11_27_trainer_progress.sql` in Supabase before using trainer progress. Configure Vercel environment variables separately; keep secrets private.

A report PDF with real screenshots and a 5–8 minute voice demo must be prepared from the deployed app. Required screenshots: member view, admin dashboard, RBAC denial, expired-token handling and activity log. Do not present build success as proof of live workflow tests.

The instructor requires at least two admin and three normal demo accounts, demo passwords only in private submission fields/report (never README/Git), GitHub/Vercel/API/docs URLs and final report files.
