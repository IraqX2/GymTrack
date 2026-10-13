# Product Requirements Document (PRD)

## GymTrack

- **Course:** CSE309
- **Version:** 1.1
- **Status:** Draft for the initial project
- **Updated:** 13 October 2026

## 1. Overview

GymTrack is a web app idea for managing the everyday records of a gym. It will bring member details, trainers, memberships, attendance, and workout plans into one place.

The current repository is only the starting point. It has a dashboard with sample numbers and a few test API endpoints. It does not have the actual gym-management workflows or a database yet.

## 2. Problem

A gym may keep member details in spreadsheets or paper records and track attendance separately. This can make it harder to find information and keep records up to date. GymTrack is intended to make those basic tasks easier to manage from one application.

## 3. Goals

1. Build a frontend and backend that run locally.
2. Let the gym administrator manage the main records.
3. Save records so they are still available after restarting the app.
4. Keep the first version small enough to build and demonstrate.
5. Add login and role-based access in a later version.

## 4. Users

- **Administrator:** manages member and trainer details, memberships, attendance, and workout plans.
- **Trainer:** works with assigned workout plans and member progress. These permissions are planned for the later version.
- **Member:** views their membership, attendance, and assigned workouts after login is added.
- **Instructor:** checks the project requirements, implementation, and demonstration.

## 5. Scope

### First version (MVP)

The first version should focus on these features:

- Add, view, edit, and remove member records.
- Add, view, edit, and remove trainer records.
- Create membership records and show their status.
- Record attendance and view a member's attendance history.
- Create workout plans and assign them to a member or trainer.
- Connect the React pages to the FastAPI endpoints.
- Save the records locally, with SQLite as the current proposal.

These are planned features, not features that are already complete in the starter.

### Later version (Beta)

- Login and authentication.
- Separate permissions for administrators, trainers, and members.
- Profile pages and role-specific dashboards.
- Better progress history and security checks.
- Deployment.

### Not included in the first version

Online payments, biometric entry, a mobile app, nutrition planning, messaging, and multi-branch management are outside the initial scope.

## 6. Main use cases

1. An administrator adds a member and updates their details.
2. An administrator records a membership and checks whether it is active.
3. An administrator records a member's gym visit.
4. An administrator creates a workout plan and assigns it.
5. In the later version, a trainer or member signs in and sees the information available to their role.

## 7. Requirements

| ID | Requirement | Version |
|---|---|---|
| PR-01 | Manage member records | MVP |
| PR-02 | Manage trainer records | MVP |
| PR-03 | Create and view membership records | MVP |
| PR-04 | Record attendance | MVP |
| PR-05 | Create and assign workout plans | MVP |
| PR-06 | Use the API from the frontend | MVP |
| PR-07 | Save records in a local database | MVP |
| PR-08 | Add login | Beta |
| PR-09 | Restrict actions based on user role | Beta |
| PR-10 | Deploy the app | Beta |

## 8. Constraints and assumptions

- The project uses React + TypeScript and FastAPI + Python.
- The first version should run locally.
- SQLite is proposed to keep local setup simple. This can be changed if the course instructions require something else.
- Dashboard numbers must be treated as sample data until real records are connected.

## 9. Risks

- **Too many features:** build and test one main workflow before adding optional features.
- **Frontend and backend do not connect:** test the API connection early.
- **Invalid records:** validate required fields before saving.
- **Private data is exposed:** add and test server-side permissions before using real member data.

## 10. Open decisions

The exact fields for each record and the final database setup still need to be decided during implementation. Any specific format or scope required by the instructor takes priority over this draft.
