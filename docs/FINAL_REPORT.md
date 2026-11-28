# GymTrack Final Project Report

**Course:** CSE309 · Autumn 2026  
**Project:** GymTrack  
**Technology:** React, TypeScript, FastAPI, SQLModel, PostgreSQL/Supabase and Vercel  
**Source repository:** https://github.com/IraqX2/GymTrack

> **Before exporting this report as the submission PDF:** add the five genuine screenshots in Section 20, paste the shareable demo-video link, and confirm the demo account roles in Section 21. Keep passwords out of this public repository.

---

# Part I — Product Requirements Document (PRD)

## 1. Product overview

GymTrack is a web-based gym management application. It centralizes gym member profiles, trainer profiles, memberships, attendance, workout plans, workout assignments and shared team work.

The application has three account roles:

- **User/member:** signs up through the public signup form and accesses their own gym profile, membership, attendance and assigned workouts.
- **Trainer:** starts as a normal user. An administrator may promote the account to trainer. The trainer then receives a trainer workspace for assigned members, workout plans and progress updates.
- **Admin:** manages gym records, user accounts, roles, trainer assignments, moderation and shared teams.

The trainer role is a GymTrack extension. It does not replace the user and admin roles expected by the course brief.

## 2. Problem statement

Gym records are often split across paper forms, spreadsheets and separate attendance or workout records. This makes it difficult to keep member data consistent and coordinate trainer assignments. GymTrack provides one application with role-based access to these workflows.

## 3. Goals

1. Provide secure signup, login, profile management and session management.
2. Restrict members to their own private records.
3. Let administrators manage gym operations and application users.
4. Let administrators promote registered users to trainer accounts.
5. Give trainers access only to workouts and members assigned to them.
6. Preserve records in a hosted PostgreSQL database in production.
7. Provide an auditable administration workflow and shared teams with permission checks.

## 4. Scope

### Included

- Signup, login, JWT access tokens, refresh sessions, logout and session revocation.
- Profile update and password change.
- Member and trainer records.
- Membership records and status.
- Attendance check-in/check-out and member attendance requests.
- Workout plan creation and member/trainer assignment.
- Trainer dashboard and workout progress records.
- Admin account management, activity/security views and CSV exports.
- Shared groups with owner-managed members and create/edit/assign permissions.
- Vercel frontend/backend deployment configuration and Supabase PostgreSQL connection.

### Excluded

Online payment processing, biometric entry, nutrition plans, mobile applications, messaging and multi-branch administration are outside the current scope.

## 5. Stakeholders and users

| User | Main tasks |
|---|---|
| Member | View own membership, attendance, assigned workouts and submit attendance requests |
| Trainer | View allocated workout assignments and trainees; record progress |
| Administrator | Manage users, gym records, trainers, memberships, attendance, plans, groups and audit information |
| Course instructor | Evaluate deployed functionality, security, architecture and code defence |

---

# Part II — Software Requirements Specification (SRS)

## 6. Functional requirements

| ID | Requirement | Implementation |
|---|---|---|
| FR-01 | Register and authenticate accounts | Signup/login endpoints |
| FR-02 | Hash account passwords | Argon2 via pwdlib |
| FR-03 | Issue short-lived access tokens | JWT, configured for 15 minutes |
| FR-04 | Refresh and revoke sessions | HttpOnly refresh cookie, hashed server-side token and rotation |
| FR-05 | Manage profile/password/sessions | /api/me and /api/auth/sessions |
| FR-06 | Maintain account roles | user, trainer and admin values in the account table |
| FR-07 | Enforce admin-only operations | Shared FastAPI ADMIN dependency |
| FR-08 | Enforce member ownership | Member dashboard queries filter by signed-in account |
| FR-09 | Manage members and trainers | Admin CRUD screens and API routes |
| FR-10 | Manage memberships and attendance | Membership and attendance endpoints |
| FR-11 | Review member attendance requests | Member request and admin review workflow |
| FR-12 | Create and assign workouts | Workout plan and assignment endpoints |
| FR-13 | Promote a member account to trainer | Admin role selector; trainer profile is linked through `trainer.user_id` |
| FR-14 | View trainer assignments | Trainer-only dashboard endpoint |
| FR-15 | Record trainer progress | Assignment ownership checked before storing progress |
| FR-16 | Manage shared groups | Owner-managed group membership |
| FR-17 | Apply group permissions | Backend checks create, edit and assign permissions |
| FR-18 | Administer user accounts | Admin user listing, role changes, ban/unban and session revocation |
| FR-19 | Review audit/security events | Activity log and security endpoints |
| FR-20 | Export management data | Filter-aware CSV exports for users, members and activity, plus trainers, memberships, attendance, workouts, assignments and groups |
| FR-21 | Moderate content | Admin can search/page supported records and delete one or multiple memberships, attendance entries, plans, assignments, groups or trainer progress entries |
| FR-22 | Manage user detail and bulk actions | Admin detail view includes records, groups, sessions and recent activity; bulk ban/unban validates selected accounts |

## 7. Non-functional requirements

- Use React with TypeScript for the frontend and FastAPI for the backend.
- Use SQLModel and a relational database for persistent records.
- Do not store passwords in plain text.
- Keep secrets in server-side environment variables.
- Validate request bodies before processing them.
- Use server-side authorization; frontend visibility is not a security boundary.
- Return useful error status codes without exposing server stack traces.
- Maintain loading, empty and error states in primary screens.
- Use a hosted database for the deployed application; do not rely on temporary Vercel filesystems.

## 8. Role and access matrix

| Capability | User/member | Trainer | Admin |
|---|---:|---:|---:|
| View own member profile | Yes | Yes | Management access |
| View own membership/attendance/workouts | Yes | Yes | Management access |
| Submit own attendance request | Yes | Yes | Review requests |
| View assigned trainees/workouts | No | Yes | All management records |
| Record progress for trainer assignment | No | Own assignment only | Not trainer action |
| Manage member/trainer records | No | No | Yes |
| Create/manage workout plans and assignments | No | No | Yes |
| Promote/change account roles | No | No | Yes, except own role |
| Ban/unban accounts | No | No | Yes, cannot ban another admin |
| Administer groups | According to owner/member grant | According to owner/member grant | Create and administer |

## 9. Trainer workflow acceptance criteria

1. A visitor signs up using the normal signup form.
2. The newly created account has the user role and a member profile.
3. An administrator selects trainer for that account in Administration → Users.
4. The backend creates or reactivates a trainer staff profile using the account ID through `trainer.user_id`, with normalized email only as a compatibility fallback.
5. An administrator assigns a workout plan to a member and selects the trainer profile.
6. The trainer signs in and opens My Trainees.
7. The dashboard lists only that trainer's assigned workout/member rows.
8. The trainer can add a completion percentage from 0 to 100 with notes.
9. An attempt to read or update another trainer's assignment is rejected by the backend.

---

# Part III — Technical Design Document (TDD)

## 10. Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite |
| Backend | Python, FastAPI |
| ORM/data validation | SQLModel, Pydantic |
| Database | SQLite locally; Supabase PostgreSQL when deployed |
| Password hashing | Argon2 via pwdlib |
| Authentication | PyJWT access tokens and rotating HttpOnly refresh cookie |
| Hosting | Vercel |
| Source control | GitHub |

## 11. Architecture

GymTrack uses an MVC-style layered architecture. The general request path is:

React page/component (View) → frontend API client → FastAPI router (Controller) → shared authentication/role dependency → domain service → repository → SQLModel data model → PostgreSQL/SQLite.

All application domains use separate router/controller modules, with their business rules and database access separated into service and repository layers:

| Layer | File | Responsibility |
|---|---|---|
| Model | backend/models/member.py, trainer.py, workout.py, trainer_progress.py, resources.py | Member, trainer, workout, progress, attendance, membership and group tables |
| Schema | backend/schemas/member.py, trainer.py, admin.py, resources.py | Validated request payloads |
| Member repository | backend/repositories/member_repository.py | Member database queries and persistence |
| Member service | backend/services/member_service.py | Member CRUD, ownership and gym-history safeguards |
| Member router/controller | backend/routers/members.py | Member HTTP endpoints with role checks |
| Membership repository/service/router | backend/repositories/membership_repository.py, backend/services/membership_service.py, backend/routers/memberships.py | Subscription queries and CRUD |
| Attendance repository/service/router | backend/repositories/attendance_repository.py, backend/services/attendance_service.py, backend/routers/attendance.py | Check-in/out and correction requests |
| Workout repository/service/router | backend/repositories/workout_repository.py, backend/services/workout_service.py, backend/routers/workouts.py | Plans and assignments |
| Group repository | backend/repositories/group_repository.py | Group, membership and task queries |
| Group service | backend/services/group_service.py | Owner rules and create/edit/assign permission checks |
| Group router/controller | backend/routers/groups.py | Group, membership and task endpoints |
| Trainer repository | backend/repositories/trainer_repository.py | Trainer and assignment queries |
| Trainer service | backend/services/trainer_service.py | Profile promotion, assignment ownership and progress rules |
| Trainer router/controller | backend/routers/trainers.py | Trainer HTTP endpoints |
| Auth repository/service/router | backend/repositories/auth_repository.py, backend/services/auth_service.py, backend/routers/auth.py | Account/session data, authentication rules and endpoints |
| Admin repository/service/router | backend/repositories/admin_repository.py, backend/services/admin_service.py, backend/routers/admin.py | Admin queries, role/ban workflows, content moderation and exports |
| App entry point | backend/gymtrack_api.py | FastAPI setup, health checks and router registration |
| Shared dependencies | backend/core/dependencies.py | Signed-in user, admin and trainer authorization |
| Audit | backend/core/audit.py | Activity event recording |
| Views | frontend/src/App.tsx, frontend/src/pages/TrainerDashboard.tsx | User/admin and trainer interfaces |

The authentication and admin endpoints have been moved into dedicated routers and services. `backend/gymtrack_api.py` is now the application entry point. Admin content moderation and other admin database operations are routed through the admin service/repository layers.

## 12. Database design

Primary tables used by the application include:

- user: login account, password hash, role, ban and failed-login fields.
- authsession: hashed refresh token, expiry and revocation metadata.
- member: member profile linked to a login account where applicable.
- trainer: trainer staff profile, email, contact details and active status.
- membership: member plan, start/end dates, price and status.
- attendance: check-in/check-out records.
- attendance_request: member-submitted requests awaiting admin review.
- workout_plan: workout plan definitions.
- workout_assignment: relation from a member and plan to an optional trainer.
- trainer_progress: trainer progress entries tied to an assignment, member and trainer, with a completion percentage, notes, date and creation timestamp.
- gym_group, gym_group_member, gym_group_task: shared groups and permissions.
- activity_log: audit history.

The hosted GymTrack database already has `public.trainer_progress`, created by the existing migration `20261127071138_gymtrack_trainer_access_and_private_tables`. The application maps to that existing table; no duplicate progress table or additional production migration is required.

## 13. Authentication and authorization flow

### Login

1. The client sends email and password to /api/auth/login.
2. FastAPI looks up the account and checks the password against its Argon2 hash using the server-side pepper.
3. A short-lived signed JWT is created with account identity and role.
4. A new refresh session is stored using a hash of the refresh token.
5. The refresh token is sent in an HttpOnly cookie; the access token is returned to the client.

### Protected request

1. The frontend sends the access token in the Authorization header.
2. A shared FastAPI dependency verifies the JWT signature and expiry.
3. The account is reloaded from the database and ban status is checked.
4. The endpoint dependency checks whether the account has the required role.
5. Domain services apply ownership or assignment-specific checks before reading or writing data.

### Refresh/logout

The frontend attempts refresh after an access-token 401 on non-auth routes. Refresh rotates the stored refresh token and cookie. Logout revokes the associated refresh session and clears the cookie. Users may list and revoke their sessions; administrators may revoke all sessions belonging to a user.

## 14. Trainer role design

The public signup endpoint always creates a user, never a trainer. An administrator performs a role change through the admin user endpoint. When the target role becomes trainer, the service creates or reactivates the linked trainer profile. Demoting the account deactivates its trainer profile.

The trainer service resolves the trainer profile and filters workout assignments by its trainer ID. The progress write operation checks the same relationship before creating a progress row. The client does not decide which assignments are accessible.

## 15. API endpoint summary

| Area | Endpoint examples |
|---|---|
| Auth | /api/auth/signup, /api/auth/login, /api/auth/refresh, /api/auth/logout |
| Profile | /api/me, /api/me/password |
| Sessions | /api/auth/sessions, /api/auth/sessions/{session_id} |
| Members | /api/members and /api/members/{member_id} |
| Trainers | /api/trainers and /api/trainers/{trainer_id} |
| Trainer dashboard | /api/trainer/dashboard |
| Trainer progress | /api/trainer/assignments/{assignment_id}/progress |
| Memberships | /api/memberships |
| Attendance | /api/attendance, /api/attendance/requests |
| Workouts | /api/workout-plans, /api/workout-assignments |
| Groups | /api/groups and nested membership/work endpoints |
| Admin | /api/admin/stats, /api/admin/users, /api/admin/activity, /api/admin/security |
| Health/docs | /api/health, /api/docs on Vercel |

## 16. Validation and error handling

The trainer schemas restrict role values to user, trainer or admin, limit text sizes and validate progress completion percentage to the 0–100 range. The service layer rejects missing or unrelated assignment IDs with 404. Non-trainer accounts are rejected by the trainer dependency with 403.

## 17. Deployment configuration

The Vercel backend requires server-side environment variables:

- DATABASE_URL: Supabase PostgreSQL connection string.
- JWT_SECRET_KEY: JWT signing secret.
- PASSWORD_PEPPER: password-hashing pepper.
- BOOTSTRAP_ADMIN_EMAIL: account permitted to receive initial admin status.
- FRONTEND_URLS: allowed origins when frontend and API origins differ.

The hosted Supabase project already contains the `trainer_progress` table from migration `20261127071138_gymtrack_trainer_access_and_private_tables`; no additional progress-table migration is required. A read-only schema inspection on 27 November 2026 confirmed the table columns and that its RLS flag is enabled. The inspected trainer, progress, workout-assignment and group-membership tables had no table-specific policies; the browser does not connect directly to the database, and FastAPI performs the authorization checks. Review the server database role and policies before using real member data. Production credentials must never be committed to Git.

---

# Part IV — Verification and submission status

## 18. Required verification matrix

The following tests must be run against the actual preview/production deployment. A source-code review or successful build alone is not sufficient.

| Test | Expected result | Status |
|---|---|---|
| Normal signup | Account is created with user role | To verify live |
| Admin promotes user to trainer | Trainer profile is linked by email | To verify live |
| Trainer opens My Trainees | Only the trainer's assignments appear | To verify live |
| Trainer requests another trainer's assignment | API returns 404 | To verify live |
| Trainer records own progress | Progress row is saved and shown in history | To verify live |
| Normal user requests trainer dashboard | API returns 403 | To verify live |
| Member requests another member's private record | API returns 403/404 | To verify live |
| Expired/tampered JWT | API rejects or refreshes session as designed | To verify live |
| Logout/revoked refresh token | Refresh is rejected | To verify live |
| Group permission denial | API rejects ungranted action | To verify live |
| Hosted data persistence | Data remains after redeploy/restart and across devices | To verify live |
| CSV exports | Downloaded file respects selected scope | To verify live |

## 19. Remaining rubric verification and technical debt

The source now contains admin role/status filters and paginated user results, account detail, bulk ban/unban, a content-moderation tab with single/bulk deletion for supported record categories, filter-aware CSV exports, and failed-login summaries grouped by IP and account. Automated tests are configured in GitHub Actions; the current suite covers authorization dependency behavior, assignment ownership, token rejection, app route registration and password hashing.

The remaining work is verification rather than another large code refactor: test the deployed login/refresh/logout flow, confirm member ownership and group permissions, exercise trainer assignment/progress ownership, and verify admin moderation and CSV exports using the hosted demo records. Review Supabase grants and Row Level Security before using real member data. The content-moderation page supports memberships, attendance, workout plans, assignments, groups and trainer progress; it is not a generic delete tool for every table.

The automated build and test checks validate the source and production bundle. Complete the live workflow checks separately and record any results in the final submission. See REQUIREMENTS_TRACEABILITY.md.

## 20. Report screenshots and video

Add these five screenshots from the deployed application. Replace each bracketed line with the actual screenshot:

1. **Member dashboard:** [Add screenshot of the normal member dashboard and personal records.]
2. **Admin dashboard:** [Add screenshot of the admin overview and account management.]
3. **RBAC denial:** [Add screenshot showing a normal user request denied by the admin-only API, including the endpoint and HTTP 403 status.]
4. **Token refresh:** [Add screenshot of an expired access-token request followed by the refresh request and the renewed request.]
5. **Activity log:** [Add screenshot of the admin activity log with demo events.]

**Demo video:** [Paste the shareable Google Drive link to the 5–8 minute voice recording.]

The recording should show login, member access, a denied admin-only action, group permissions, token expiry/refresh, trainer progress and the admin dashboard including ban/unban, activity and CSV export.

Do not include real user passwords, JWT values, refresh cookies, database connection strings or other secrets in screenshots or recordings.

## 21. Demo accounts

The hosted demo database currently contains two admin accounts and four normal user accounts. Use the following IDs in the recording and private submission details:

| User ID | Current role | Demo use |
|---:|---|---|
| 1 | Admin | Main administrator and group owner |
| 5 | Admin | Second administrator account |
| 2 | User/member | Normal member and group Create permission |
| 3 | User/member | Normal member and group Edit permission |
| 4 | User/member | Normal member and group Assign permission |
| 6 | User/member | Promote to Trainer before the trainer demonstration |

After promoting User ID 6, sign in again with that account to demonstrate the trainer workspace. Keep demo passwords out of Git and the public README; enter them only in the private submission fields.
