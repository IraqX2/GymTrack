# GymTrack requirements traceability

This file maps the original course project documents to the current implementation. The source requirements remain in [PRD.md](PRD.md), [SRS.md](SRS.md), and [TDD.md](TDD.md). This status document does not replace or rewrite those requirements.

## What the project documents require

The PRD v1.1 (13 October 2026) lists four user types:

- **Administrator:** manage member and trainer details, memberships, attendance, and workout plans.
- **Trainer:** work with assigned workout plans and member progress. The PRD labels the corresponding permissions as later-version work.
- **Member:** view their own membership, attendance, and assigned workouts after login is added.
- **Instructor:** check the project requirements and implementation.

The SRS is more explicit:

- FR-10 to FR-13: administrator member and trainer management.
- FR-20 to FR-21: membership plan, dates, and status.
- FR-22 to FR-23: administrator records check-ins; the app shows a selected member's attendance history.
- FR-30 to FR-31: create and assign workout plans.
- FR-32: basic progress history (Beta).
- FR-40 to FR-43: login, administrator/trainer/member roles, server-side permissions, and member ownership.

The documented Member use case is primarily **read-only self-service**. The PRD does not require members to create memberships, edit other people, or record attendance themselves. Attendance is recorded by the administrator and shown to the member as history.

## Current implementation status on this branch

| Requirement | Implementation | Status |
|---|---|---|
| PR-01 / FR-10 to FR-12: member CRUD | Admin member module and protected API | Implemented; needs full CRUD regression test |
| PR-02 / FR-13: trainer CRUD | Admin trainer module and protected API | Implemented; needs full CRUD regression test |
| PR-03 / FR-20 to FR-21: memberships | Admin management and member-owned read API | Implemented; database currently has no membership rows |
| PR-04 / FR-22 to FR-23: attendance | Admin check-in/check-out; member-owned history | Implemented; database currently has no attendance rows |
| PR-05 / FR-30 to FR-31: workout plans | Admin plan CRUD and assignments | Implemented; duplicate-assignment guard added |
| FR-32: progress history | No dedicated progress-entry workflow yet | Not implemented |
| PR-06 / FR-02: frontend-to-API | React calls FastAPI JSON endpoints | Implemented; needs end-to-end test |
| PR-07 / FR-04: persistent records | Supabase PostgreSQL connected through the Vercel backend | Connected; persistence verified for account creation |
| PR-08 / FR-40: login | Signup, login, refresh, logout, Argon2 password hashing | Implemented; tested for initial Admin account |
| PR-09 / FR-41 to FR-43: role permissions | Admin and Member role checks, member-owned data queries | Admin/Member implemented; separate Trainer account role not implemented yet |
| PR-10: deployment | Vercel preview and Supabase PostgreSQL | Preview works; production release still separate |

## User and navigation scope

The current navigation is deliberately limited to the documented gym workflows:

- **Administrator:** Overview, People (Members + Trainers), Operations (Memberships + Attendance), Workouts, Administration.
- **Member:** Overview, My Membership, My Attendance, My Workouts, Profile.

Groups and shared group tasks are not part of the original GymTrack PRD/SRS. Their navigation entry is hidden to keep the project within its stated scope. The existing group tables and rows are retained; they are not deleted.

## Current demo database facts

The inspected Supabase database contains five login accounts: two administrators and three regular Member accounts. All five have linked member profiles.

At the time of inspection:

- 1 workout plan exists.
- 5 workout assignments exist, but all five point to the same Member and same plan; these are repeated assignments rather than five different members' plans.
- 0 membership records exist.
- 0 attendance records exist.
- 1 trainer record exists.

This explains why the Member screens looked empty. The member-facing views were limited, and the database did not contain membership or attendance records to display. Do not present empty records as a frontend failure.

## Performance changes

- Vercel Functions are configured for Mumbai (bom1) to be near the Supabase project in ap-south-1.
- The database uses Supabase's transaction-mode pooler with SQLAlchemy NullPool, which is the recommended pattern for serverless deployments.
- Database connection attempts now have a five-second connection timeout instead of waiting for the driver's longer default.
- Session restoration uses the user profile already returned by the refresh endpoint, avoiding an immediate second profile query.
- Workout assignment submission disables the form while saving and the API rejects duplicate active assignments.

The Vercel region change needs to be confirmed in the new deployment. Actual user-perceived load time should be measured after that deployment; no unsupported claim of a fixed 30–40 second improvement is made.

## Test checklist before calling the project complete

1. Admin creates a member, trainer, membership, attendance visit, workout plan, and assignment.
2. Member signs in and sees only their own membership, attendance history, and assigned workout.
3. A second Member cannot retrieve the first Member's private records.
4. Repeated assignment of the same active plan to the same member/trainer is rejected with HTTP 409.
5. Refreshing the page and opening the site on another computer returns the same database records.
6. Measure the first login and subsequent navigation after deploying in bom1.
7. Verify every admin add/edit/delete path and capture a successful response.
8. Keep the separate Trainer role and progress-history feature listed as remaining Beta work until they are implemented and tested.
