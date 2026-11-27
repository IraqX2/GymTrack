# GymTrack Product Requirements Document (PRD)

**Course:** CSE309 · Autumn 2026  
**Version:** 2.0 · **Status:** Final implementation scope  
**Detailed report:** [FINAL_REPORT.md](FINAL_REPORT.md)

## 1. Product overview

GymTrack is a web application for managing gym members, trainers, memberships, attendance, workout plans, workout assignments and shared team work. It uses role-based access to separate member, trainer and administrator capabilities.

## 2. Problem

Gym records stored in separate spreadsheets and paper files are difficult to maintain consistently. GymTrack centralizes the core records and gives members and trainers scoped access to their own gym workflows.

## 3. Goals

1. Secure user signup, login, refresh, logout and session control.
2. Give members access only to their own membership, attendance and workouts.
3. Let admins manage accounts and the gym's operational records.
4. Let admins promote a normal account to trainer.
5. Let trainers see only assigned trainees/workouts and write progress updates.
6. Keep deployed records in hosted PostgreSQL.
7. Provide groups with server-enforced member permissions.

## 4. User types

- **User/member:** created by public signup; sees their own member portal and may use group permissions granted to them.
- **Trainer:** a user account promoted by an administrator; keeps its member profile and receives access to assigned training work.
- **Admin:** manages accounts, gym records, trainers, plans, attendance, groups and activity records.
- **Instructor:** evaluates live deployment, security, code architecture and demonstration.

## 5. Scope

### Included

Authentication, role-based access control, member/trainer CRUD, memberships, attendance, attendance requests, workout plans and assignments, trainer progress, admin controls, audit/security views, CSV exports and shared groups.

### Excluded

Online payments, biometric access, nutrition planning, mobile apps, messaging and multi-branch operations.

## 6. Success criteria

- Users cannot access another member's private records.
- Signup cannot assign privileged roles.
- Only an admin can promote an account to trainer.
- Trainers can only view and update their own workout assignments.
- Admin-only endpoints reject non-admin accounts.
- Shared group permissions are checked on the backend.
- Production data persists in the hosted database.

## 7. Risks and constraints

- Trainer profile links use normalized account email; email changes require careful synchronization.
- Hosted schema changes must be applied as SQL migrations.
- Build success alone does not prove that all authorization rules work on the deployed site.
- Supabase table grants/RLS must be reviewed before any real member data is stored.
- Current legacy domains are still being moved toward the layered architecture documented in [ARCHITECTURE.md](ARCHITECTURE.md).
