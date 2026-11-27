# Trainer account workflow

GymTrack keeps the two account roles required by the CSE309 brief: `admin` and `user`.
A trainer is an administrator-granted capability attached to a normal user account, not a
third global account role. This keeps course RBAC role checks consistent while allowing
trainers to have their own workspace.

## Promote an existing account

1. The future trainer signs up through the ordinary GymTrack signup form.
2. An administrator opens **People → Trainers**.
3. The administrator adds the trainer using the exact email address used at signup.
4. The API verifies that the account exists, is a normal non-banned user, and is not already
   linked to another trainer profile.
5. The trainer signs out and signs back in (or refreshes the session) to receive
   `is_trainer` and `trainer_id` in the account payload.

A trainer cannot self-promote. Creating or changing a trainer profile is administrator-only.

## Trainer facilities

The Trainer Portal shows only workout assignments linked to the signed-in trainer's
trainer profile. Trainers can update the status of those assignments and record progress
with a completion percentage, date and note. Every trainer operation checks the trainer
profile and assignment ownership on the server. Hiding a menu item in React is not an
authorization check.

Members see progress associated with their own assignments. Trainers cannot query another
trainer's assignments by changing an ID in the URL.

## Database migration

Before deploying this branch, apply
`backend/migrations/20261127_trainer_access.sql` to the Supabase PostgreSQL database.
This adds the nullable trainer-account link, its unique index, and the trainer progress
table. The API cannot create or alter production tables automatically.

Existing trainer rows are intentionally left unlinked. Once the migration is applied,
an administrator can create a linked trainer profile using the account's registered email.
Do not manually change account roles to a new `trainer` value.

## Architecture

The trainer feature is implemented as a feature module:

- `router.py`: HTTP request/response handling
- `schemas.py`: request validation
- `service.py`: authorization and business rules
- `repository.py`: database queries and persistence

This is a Router–Service–Repository layered pattern (an MVC-style separation of concerns).
The instructor's smarter-todo project was reviewed only as an architectural reference;
GymTrack uses its own gym-specific domain model, endpoint design and implementation.
