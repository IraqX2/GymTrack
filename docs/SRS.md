# GymTrack Software Requirements Specification (SRS)

**Course:** CSE309 · Autumn 2026  
**Version:** 2.0 · **Status:** Final implementation scope  
**Detailed report:** [FINAL_REPORT.md](FINAL_REPORT.md)

## 1. Purpose

This document defines GymTrack's current functional and non-functional requirements. The consolidated project report contains the full role matrix, design and verification checklist.

## 2. Technology

- Frontend: React, TypeScript and Vite.
- Backend: Python and FastAPI.
- Persistence: SQLModel; SQLite locally and Supabase PostgreSQL in deployment.
- Authentication: Argon2 password hashes, signed JWT access token and rotating HttpOnly refresh session.
- Hosting: Vercel.

## 3. Account types

- User/member: normal public signup, personal gym portal.
- Trainer: admin-promoted user with access to assignments linked to their trainer profile.
- Admin: account and gym management.

## 4. Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | A visitor can sign up and log in. |
| FR-02 | Passwords are hashed using Argon2 with a server-side pepper. |
| FR-03 | The API signs and verifies short-lived JWT access tokens. |
| FR-04 | Refresh tokens are HttpOnly, rotated and revocable. |
| FR-05 | Users can update their profile, change password and list/revoke sessions. |
| FR-06 | The backend enforces role and account-ban checks on protected requests. |
| FR-07 | A member can access only their own membership, attendance, requests and workouts. |
| FR-08 | Admins can manage members, trainers, memberships, attendance, plans and assignments. |
| FR-09 | Admins can change account roles, ban/unban users and revoke sessions. |
| FR-10 | Admins can promote a normal user account to trainer. |
| FR-11 | Trainers can list only their own allocated members and workout assignments. |
| FR-12 | Trainers can record a completion percentage and notes only against assignments linked to their trainer ID. |
| FR-13 | Members can submit attendance requests for admin review. |
| FR-14 | Groups support create/edit/assign permissions checked by the backend. |
| FR-15 | Admins can review activity/security information and export supported CSV reports. |
| FR-16 | Production records are stored in hosted PostgreSQL. |

## 5. Non-functional requirements

- Keep secrets out of frontend source control and public README.
- Validate request data and provide consistent HTTP errors.
- Never rely on hidden buttons as the only security check.
- Do not persist production data on temporary Vercel filesystem storage.
- Provide loading, empty and error states on primary screens.
- Test role denial, ownership, refresh/revocation and persistence on the live deployment.

## 6. Acceptance tests

- Signup always creates a normal user and member profile.
- Admin promotion links or creates the trainer profile.
- A trainer sees only assignments associated with their trainer profile.
- A trainer cannot read or write another trainer's assignment.
- A normal user cannot call trainer-only or admin-only endpoints.
- A user cannot read another member's private records.
- Group permission checks reject ungranted operations.
- Logout/revocation prevents refresh-token reuse.
- Hosted records remain after redeployment/restart.

## 7. Verification still required before submission

The implementation includes admin role/status filters, pagination, user details, bulk ban/unban, supported content moderation and CSV exports. Before submission, complete the remaining verification work:

- Confirm the live Vercel site is accessible to the instructor and connects to Supabase.
- Demonstrate the member, trainer and admin workflows using the demo accounts.
- Review Supabase database grants and Row Level Security before using real member data.
- Add broader automated tests for login failures, refresh rotation, logout/revocation and full admin workflows.
- Capture the required report screenshots and record the 5–8 minute voice demo.

See [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md).
