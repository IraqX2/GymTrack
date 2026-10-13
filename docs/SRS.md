# Software Requirements Specification (SRS)

## GymTrack

- **Course:** CSE309
- **Version:** 1.1
- **Status:** Draft
- **Updated:** 13 October 2026

## 1. Purpose

This document lists what GymTrack should do and the basic conditions it should meet. It is meant to guide development and help check the features during testing.

## 2. Current state and scope

The current starter contains a React dashboard and a FastAPI backend with three simple endpoints. The main gym features described below are planned work. They should not be considered implemented until they are added and tested.

The frontend uses React, TypeScript, and Vite. The backend uses Python and FastAPI. The first version is intended to run locally.

## 3. User types

- **Administrator:** manages gym records.
- **Trainer:** works with assigned workout plans. Role restrictions are planned for Beta.
- **Member:** views their own membership, attendance, and workout information after login is added.

## 4. Functional requirements

### General

| ID | Requirement | Version |
|---|---|---|
| FR-01 | The app shall provide pages for the main GymTrack modules. | MVP |
| FR-02 | The frontend shall send requests to the backend through the REST API. | MVP |
| FR-03 | The backend shall check submitted data and return an error for invalid requests. | MVP |
| FR-04 | The app shall save records in a database so they remain after a restart. | MVP |
| FR-05 | The API shall provide a health endpoint. | Starter exists |

### Members and trainers

| ID | Requirement | Version |
|---|---|---|
| FR-10 | An administrator shall be able to add a member. | MVP |
| FR-11 | The app shall list and show member details. | MVP |
| FR-12 | An administrator shall be able to edit or remove a member. | MVP |
| FR-13 | An administrator shall be able to add, list, edit, and remove trainers. | MVP |

### Membership and attendance

| ID | Requirement | Version |
|---|---|---|
| FR-20 | The app shall store a member's plan and membership dates. | MVP |
| FR-21 | The app shall show the membership status. | MVP |
| FR-22 | An administrator shall be able to record a check-in for a member. | MVP |
| FR-23 | The app shall show attendance history for a selected member. | MVP |

### Workout plans

| ID | Requirement | Version |
|---|---|---|
| FR-30 | An administrator shall be able to create, view, edit, and remove workout plans. | MVP |
| FR-31 | A workout plan shall be assignable to a member and, when needed, a trainer. | MVP |
| FR-32 | The app shall keep a basic progress history. | Beta |

### Login and permissions

| ID | Requirement | Version |
|---|---|---|
| FR-40 | A registered user shall be able to sign in. | Beta |
| FR-41 | The system shall distinguish administrator, trainer, and member roles. | Beta |
| FR-42 | The backend shall check permissions for protected actions. | Beta |
| FR-43 | A member shall only be able to view their own private records. | Beta |

## 5. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | Frontend and backend code shall stay in separate folders. |
| NFR-02 | The main pages should be usable on common desktop and mobile screen sizes. |
| NFR-03 | Invalid input shall not be saved as a valid record. |
| NFR-04 | Error messages should help the user understand what went wrong without showing private system details. |
| NFR-05 | Passwords shall not be stored as plain text when login is implemented. |
| NFR-06 | Secret keys and local environment files shall not be committed to GitHub. |
| NFR-07 | The main workflows shall have repeatable test steps. |

## 6. Interfaces

- **Frontend:** browser-based React application.
- **Backend:** FastAPI REST endpoints returning JSON.
- **Local development:** Vite usually runs on port 5173; FastAPI runs on port 8000.
- **Database:** SQLite is the current proposal for the first version.

The starter endpoints are:

- `GET /api/health`
- `GET /api/hello?name=YourName`
- `GET /api/modules`

The member, trainer, membership, attendance, and workout-plan endpoints still need to be implemented.

## 7. Data to store

The planned database will include:

- **Member:** ID, name, contact details, join date, and active status.
- **Trainer:** ID, name, contact details, and specialization.
- **Membership:** ID, member ID, plan name, start date, end date, and status.
- **Attendance:** ID, member ID, and check-in time.
- **Workout plan:** ID, title, description, and assigned member/trainer.
- **Progress entry (Beta):** ID, member ID, date, and progress notes.

Records should have unique IDs. A membership or attendance record should not refer to a member who does not exist.

## 8. Acceptance checks

- **AT-01:** A member can be added and then retrieved.
- **AT-02:** Editing a member changes the stored details.
- **AT-03:** Removing a member removes it from later results.
- **AT-04:** Invalid required fields are rejected.
- **AT-05:** A membership can be linked to an existing member.
- **AT-06:** An attendance record can be saved and viewed in the member's history.
- **AT-07:** A workout plan can be created and assigned.
- **AT-08:** The frontend can reach the backend through the local Vite proxy.
- **AT-09 (Beta):** A user cannot access data or actions outside their role.

## 9. Limitations

The starter does not yet have database storage, full CRUD features, login, role permissions, or deployment. The requirements above describe the intended work for the project.
