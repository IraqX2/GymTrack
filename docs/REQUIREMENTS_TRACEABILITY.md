# GymTrack requirements traceability

This document maps the GymTrack implementation to the original project documents and the CSE309 final-project expectations.

## Roles and product scope

The original GymTrack PRD describes:

- **Administrator:** manages member and trainer records, memberships, attendance and workout plans.
- **Trainer:** works with assigned workout plans and member progress. Separate trainer permissions are listed as later-version work in the original PRD/SRS.
- **Member:** views their own membership, attendance history and assigned workouts.

The final CSE309 project brief adds mandatory account security, role-based access control, admin management, persistent deployment and shared groups/teams with mixed member permissions. Those final course requirements take precedence where the initial GymTrack draft has narrower scope.

The deployed application currently uses two account roles: `admin` and `user`. A trainer is a gym staff record, not a separate login role.

## Implemented workflows

| Requirement | Implementation |
|---|---|
| Member records | Admin creates, views, updates and removes member records |
| Trainer records | Admin manages trainer records |
| Memberships | Admin selects a member, chooses a plan duration, records dates, price and status; members see only their own records |
| Attendance | Admin selects a member and records visit date, check-in and optional check-out time; open visits can be checked out later |
| Member attendance access | Members see their own visit history |
| Attendance requests | Members can submit a dated check-in request; admins approve it into the official attendance log or reject/remove it |
| Workout plans | Admin manages plans and assigns them to members and trainers |
| Member dashboard | Members see their own membership, attendance and assigned workouts |
| Authentication | Signup/login, Argon2 password hashing, signed short-lived JWT access tokens, rotating HttpOnly refresh sessions, logout and session revocation |
| Authorization | FastAPI dependencies check account role and ownership for protected routes |
| Administration | Account search, role changes, ban/unban, session revocation, activity/security views and CSV exports |
| Shared groups | Admin creates a team and adds registered users with independent create, edit and assign permissions; the owner alone can rename/delete the team and manage membership |
| Persistent deployment | React frontend and FastAPI backend are deployed through Vercel and use Supabase PostgreSQL |

## Group permission model

Groups are shared workspaces required by the final CSE309 project brief. They are not gym memberships or class schedules.

An administrator creates the group and is its owner. The owner can add registered accounts, grant or revoke three permissions, rename the group and delete it.

A normal member cannot create or administer groups. They can view a group they belong to and use only the permissions granted to them:

- **Create:** add a shared task.
- **Edit:** update shared tasks they did not create.
- **Assign:** assign a task to another member of the same group.

FastAPI checks each permission. Hiding a control in the frontend is not treated as an authorization boundary.

## Database sample data

The inspected hosted database contains five login accounts: two administrators and three regular users. Each account is linked to a member profile. It also contains one trainer, membership records, attendance records, workout plans and assignments, shared groups and group members, plus a shared task.

These records are sample data for checking the workflows. Use test accounts only; do not enter real gym members' personal information.

## Remaining scope and limitations

- The separate Trainer login role and dedicated progress-history workflow remain outside the current implementation.
- The final report PDF with required screenshots and the screen-recorded submission video must still be prepared.
- The Supabase RLS finding requires a deliberate security configuration review before real personal data is used.
- Build success alone does not prove that every workflow or permission rule works on the deployed URL. Each main role and denied-access case should be tested there.

## Source documents

- [Product Requirements Document](PRD.md)
- [Software Requirements Specification](SRS.md)
- [Technical Design Document](TDD.md)
- CSE309 final project submission expectations supplied for the Autumn 2026 course
