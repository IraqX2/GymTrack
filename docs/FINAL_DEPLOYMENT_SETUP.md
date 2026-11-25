# GymTrack final deployment and account setup

This document applies to the **GymTrack** project, not the instructor's Smarter Todo demo.

## What has been added to the GymTrack database

The migration is additive. It retains the existing `member`, `user` and `authsession` tables and their rows, and adds:

- trainers
- memberships
- attendance
- workout plans and assignments
- groups, group members and delegated permissions
- shared group work
- activity log and failed-login data
- a link between each registered user and their own member profile

The migrations currently present in Supabase are `gymtrack_initial_schema`, `gymtrack_final_domain_and_auth`, and `gymtrack_user_member_and_group_work`.

## Required Vercel environment variables

Open Vercel → GymTrack → Settings → Environment Variables. Set the following for **Preview** and **Production**:

| Name | Purpose |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `JWT_SECRET_KEY` | Random secret used to sign access tokens |
| `PASSWORD_PEPPER` | Separate random secret mixed into passwords before Argon2 hashing |
| `BOOTSTRAP_ADMIN_EMAIL` | Email address that is allowed to receive the first admin role at signup |

The current project already has `JWT_SECRET_KEY` and `PASSWORD_PEPPER`. The database connection variable is the missing deployment dependency.

Use the Supabase Dashboard → Project Settings → Database → Connection string. Prefer the Supavisor transaction pooler URL, using the PostgreSQL URI format, for Vercel serverless functions. Keep the database password private. Do not commit it, paste it into GitHub, or put it in frontend code.

Generate two separate random secrets, for example from a terminal:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Run the command twice, once for `JWT_SECRET_KEY` and once for `PASSWORD_PEPPER`. Do not regenerate the pepper after users have passwords, because existing hashes depend on it.

After changing environment variables, redeploy the preview branch. The API should return `200` from `/api/health` and the documentation page should load at `/api/docs`.

## First admin and demo accounts

1. Add your chosen first-admin email to `BOOTSTRAP_ADMIN_EMAIL` in Vercel.
2. Redeploy the preview branch.
3. Sign up using that email. It will receive the `admin` role.
4. Sign up at least one further admin and three regular user accounts.
5. The second admin can be promoted by the first admin from Administration → Users.

Alternatively, after the first account has signed up, the initial admin can be promoted once from the Supabase SQL editor:

```sql
UPDATE public."user"
SET role = 'admin', updated_at = now()
WHERE email = 'your-admin-email@example.com';
```

Replace the example email with the account you created. Never put demo passwords in this repository. Put them only in the private PDF appendix required by the instructor.

## Cross-device persistence smoke test

After the API has a working database connection:

1. Sign in as an administrator on Computer A.
2. Create a test member and a trainer.
3. Create a membership, attendance record, workout plan and assignment.
4. Open the same Vercel URL on Computer B and sign in as an authorised user.
5. Confirm that the permitted records appear after refresh.
6. Sign in as a different regular user and verify the first user's private member profile and assigned records are not visible.
7. Add a registered user to a group, change their create/edit/assign grants, and test that an ungranted action receives HTTP 403.

Do not use real gym members' personal information until access control and deployment tests pass.

## Supabase Row Level Security warning

The current Supabase project inspection reported Row Level Security disabled on the public tables. This is a critical warning because Supabase's publishable/anon API roles can access exposed public tables when grants permit it.

The GymTrack frontend talks to FastAPI, not directly to Supabase, and the backend should use the private PostgreSQL connection string. Still, enable RLS and verify grants/policies for every public table before treating the database as production-safe. Do not merely enable RLS without understanding the policies: that can block API access for roles that do not bypass RLS. Keep any service-role key and database password on the server only.

## Current implementation boundaries

The frontend contains login/signup, profile/session screens, role-based navigation, gym record modules, groups and admin screens. The backend has matching API routes and database models. This is not a claim that every instructor acceptance criterion has passed: runtime testing depends on the Vercel `DATABASE_URL`, and automated tests and final evidence screenshots still need to be completed.
