# Software Requirements Specification (SRS)
## GymTrack

| Document field | Value |
|---|---|
| Version | 1.0 |
| Status | Initial project baseline |
| Course | CSE309 |
| Last updated | 13 October 2026 |

## 1. Purpose
This document defines the functional and non-functional requirements for GymTrack. The requirements are written to guide implementation and testing. Release labels distinguish the locally running MVP from the Beta planned for the final demonstration.

## 2. Product scope
GymTrack is a web application with a React + TypeScript frontend and a FastAPI + Python backend exposed through REST endpoints. The repository currently includes a starter dashboard and demo API endpoints. The CRUD requirements below describe planned implementation work and are not claims that all features are already complete.

## 3. User classes
- **Administrator:** manages gym operations and core records.
- **Trainer:** manages assigned workout plans and reviews progress; role-based access is planned for Beta.
- **Member:** views personal membership, attendance, and workout information; authenticated self-service is planned for Beta.
- **Visitor/unauthenticated user:** can access only non-sensitive public or sign-in surfaces once authentication is implemented.

## 4. Operating environment
- Modern desktop or mobile web browser.
- Frontend development server: Vite, normally at `http://localhost:5173`.
- Backend development server: Uvicorn/FastAPI, normally at `http://127.0.0.1:8000`.
- MVP persistence target: SQLite local database.
- The exact deployment environment will be selected during Beta planning.

## 5. Functional requirements

### 5.1 Shared application requirements
| ID | Requirement | Release |
|---|---|---|
| FR-01 | The system shall provide a frontend interface for the GymTrack core modules. | MVP |
| FR-02 | The frontend shall communicate with the backend through HTTP REST endpoints. | MVP |
| FR-03 | The backend shall validate request data and return meaningful HTTP status codes for success and failure. | MVP |
| FR-04 | The system shall persist core records so data remains available after a local application restart. | MVP |
| FR-05 | The system shall provide a health endpoint for checking API availability. | MVP (starter present) |

### 5.2 Member management
| ID | Requirement | Release |
|---|---|---|
| FR-10 | The system shall create a member record with a unique identifier and required profile fields. | MVP |
| FR-11 | The system shall list and retrieve member records. | MVP |
| FR-12 | The system shall update and delete a member record. | MVP |
| FR-13 | The system shall validate required fields and reject invalid data. | MVP |

### 5.3 Trainer management
| ID | Requirement | Release |
|---|---|---|
| FR-20 | The system shall create a trainer record with a unique identifier and required profile fields. | MVP |
| FR-21 | The system shall list, retrieve, update, and delete trainer records. | MVP |
| FR-22 | The system shall allow workout plans to be associated with a trainer. | MVP |

### 5.4 Membership and attendance
| ID | Requirement | Release |
|---|---|---|
| FR-30 | The system shall record a member's membership plan and start/end dates. | MVP |
| FR-31 | The system shall derive or display membership status from the stored dates and status fields. | MVP |
| FR-32 | The system shall record a dated attendance check-in for a member. | MVP |
| FR-33 | The system shall retrieve attendance history for a selected member. | MVP |

### 5.5 Workout plans and progress
| ID | Requirement | Release |
|---|---|---|
| FR-40 | The system shall create, retrieve, update, and delete workout plans. | MVP |
| FR-41 | The system shall associate a workout plan with a member and optionally a trainer. | MVP |
| FR-42 | The system shall support recording or reviewing basic progress history. | Beta |
| FR-43 | A member shall be able to view their assigned workout plans after signing in. | Beta |

### 5.6 Authentication, roles, and profiles
| ID | Requirement | Release |
|---|---|---|
| FR-50 | The system shall authenticate registered users before granting access to protected views. | Beta |
| FR-51 | The system shall distinguish administrator, trainer, and member roles. | Beta |
| FR-52 | The backend shall enforce role permissions for protected operations. | Beta |
| FR-53 | Users shall be able to view and update permitted profile fields. | Beta |
| FR-54 | Members shall only be able to view their own private membership, attendance, and workout data. | Beta |

## 6. External interface requirements
- **User interface:** Responsive browser-based pages with clear module navigation, forms, loading states, success messages, and validation errors.
- **Software interface:** React calls FastAPI REST endpoints using JSON for request and response bodies where applicable.
- **API baseline:** The starter currently provides `GET /api/health`, `GET /api/hello`, and `GET /api/modules`. Future CRUD endpoints should use resource-oriented paths (for example, `/api/members`) and standard HTTP methods.
- **Error interface:** Invalid input should return a 4xx response; unexpected server failures should not reveal secrets or stack traces to end users.

## 7. Non-functional requirements
| ID | Requirement | Target/Release |
|---|---|---|
| NFR-01 | The frontend and backend shall be maintainable in separate folders with clear responsibilities. | MVP |
| NFR-02 | Core pages should remain usable on common desktop and mobile viewport sizes. | MVP |
| NFR-03 | API input shall be validated before changing stored records. | MVP |
| NFR-04 | During normal local demonstration, common CRUD requests should return promptly under a small test dataset. | MVP |
| NFR-05 | Protected data shall require authentication and server-side authorization. | Beta |
| NFR-06 | Passwords, when authentication is implemented, shall never be stored in plain text. | Beta |
| NFR-07 | Secrets and environment-specific settings shall be kept out of source control. | Beta |
| NFR-08 | Important workflows shall have repeatable manual or automated test steps. | MVP |
| NFR-09 | The application shall provide useful error messages without exposing sensitive implementation details. | MVP/Beta |

## 8. Data requirements (MVP target)
The proposed SQLite schema will include:
- **Member:** member ID, name, contact details, join date, and active status.
- **Trainer:** trainer ID, name, contact details, specialization, and active status.
- **Membership:** membership ID, member ID, plan name, start date, end date, and status.
- **Attendance:** attendance ID, member ID, check-in timestamp.
- **WorkoutPlan:** plan ID, title, description, trainer ID (optional), member ID (optional), and created/updated timestamps.
- **ProgressEntry (Beta):** entry ID, member ID, plan ID, date, notes, and progress measurements as agreed by the team.

Each record shall have a stable identifier. Related records shall use valid references. Final fields and validation rules should be confirmed before database migrations are written.

## 9. Acceptance and verification
- **AT-01:** A valid member can be created and then retrieved by the API.
- **AT-02:** Updating a record changes the returned data; deleting it removes it from subsequent retrieval.
- **AT-03:** Invalid required fields are rejected with a 4xx response.
- **AT-04:** A membership can be associated with an existing member and its status can be displayed.
- **AT-05:** An attendance check-in can be saved and appears in that member's history.
- **AT-06:** A workout plan can be created and assigned.
- **AT-07:** The frontend can call the backend through the configured development proxy.
- **AT-08 (Beta):** Users cannot access functions or personal data beyond their assigned permissions.

## 10. Assumptions and limitations
SQLite is a proposed local MVP database and may be adjusted if the course rubric specifies another technology. The starter currently has no persistent database, real authentication, complete CRUD modules, or production deployment. These are planned features, not implemented functionality.
