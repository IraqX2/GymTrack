# Implementation Progress

**Project:** GymTrack  
**Course:** CSE309, Autumn 2026  
**Progress snapshot:** 21 November 2026

This file records the implementation that is present in the repository. It does not claim that unfinished requirements are complete.

## Implemented in this increment

- React login and signup forms connected to the FastAPI backend.
- User records with a database-stored `user` or `admin` role.
- Public signup creates only the normal `user` role.
- Argon2id password hashing with a server-side pepper from `PASSWORD_PEPPER`.
- JWT access tokens signed with `JWT_SECRET_KEY`, with a 15-minute lifetime and user ID, role, and session ID claims.
- HTTP-only refresh cookies, hashed refresh-token storage, token rotation, logout revocation, and refresh-session expiry.
- Authenticated profile read/update, password change, and per-user session list/revocation endpoints.
- A reusable server-side role dependency. All existing member CRUD endpoints require the administrator role.
- A command-line utility to provision the first administrator without exposing an admin signup option.
- Unit tests for password hashing, token claims, and tampered-token rejection.

## Not complete yet

- Admin dashboard, user search/filter/pagination, user detail and management actions.
- Ban/unban, bulk actions, role management, and corresponding safety rules.
- Audit log and security view.
- Group/team resources and fine-grained membership permissions.
- CSV exports and content moderation tools.
- Brute-force protection and comprehensive route/RBAC integration tests.
- Persistent hosted PostgreSQL configuration, Vercel environment variables, and live deployment verification.
- Required instructor demo accounts, screenshots, report PDF, and recorded walkthrough.

## Deployment warning

A hosted PostgreSQL database must be configured with `DATABASE_URL`. The Vercel `/tmp` SQLite fallback is temporary and data may disappear between function instances or restarts. Authentication also requires two separate secrets of at least 32 characters: `JWT_SECRET_KEY` and `PASSWORD_PEPPER`.

## Code defence preparation

Be prepared to explain why passwords are peppered and Argon2-hashed, what claims are placed in an access token, how the backend validates token signature/expiry/session state, why refresh tokens are stored as hashes, how rotation and logout work, and why the member router checks the admin role on the server.
