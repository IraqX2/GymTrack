# Product Requirements Document (PRD)
## GymTrack

| Document field | Value |
|---|---|
| Version | 1.0 |
| Status | Initial project baseline |
| Course | CSE309 |
| Product | GymTrack |
| Last updated | 13 October 2026 |

## 1. Product overview
GymTrack is a web-based gym management system intended to help a gym organize member records, trainers, memberships, attendance, and workout plans in one place. The project begins as a small local application with a React + TypeScript frontend and a FastAPI + Python REST backend.

The dashboard currently in the repository is a starter interface. Its displayed counts are placeholders, not live database records. Functional CRUD features and persistent storage are planned for the MVP implementation.

## 2. Problem statement
Gym information can become fragmented across paper registers, spreadsheets, and separate messages. This makes it harder to find member details, check membership status, record attendance consistently, and follow workout progress. GymTrack aims to provide a single, structured workspace for these routine tasks.

## 3. Goals and success criteria
- **G-01:** Provide a single interface for the core gym-management modules.
- **G-02:** Deliver a working local MVP using the required React + TypeScript and FastAPI + Python stack.
- **G-03:** Provide REST APIs for creating, viewing, updating, and deleting core records.
- **G-04:** Make requirements and release scope clear enough to guide implementation and demonstrations.
- **G-05:** Add authentication, role-based permissions, and deployment in the Beta release.

MVP success means a demonstrator can run the application locally, use core CRUD workflows, and verify API responses. Beta success additionally requires authenticated access, role-restricted actions, a profile dashboard, and a deployed version.

## 4. Users and stakeholders
- **Gym administrator:** Maintains member and trainer records, membership plans, attendance records, and workout-plan assignments.
- **Trainer:** Creates or updates workout plans and reviews assigned members' progress. Full role permissions are planned for Beta.
- **Member:** Views membership information, attendance history, assigned workouts, and progress. Authenticated self-service is planned for Beta.
- **Course instructor/evaluator:** Reviews project scope, documents, API behavior, GitHub workflow, and demonstrated features.
- **Development team:** Builds, tests, documents, and maintains the system.

## 5. Product scope by release

### MVP — Midterm demonstration
The MVP should run locally and prioritize a small, complete core:
1. Member CRUD: create, list, view, update, and delete member records.
2. Trainer CRUD: maintain trainer records.
3. Membership records: assign a plan, record start/end dates, and show membership status.
4. Attendance: record a member check-in and view attendance history.
5. Workout plans: create a plan and assign it to a member or trainer.
6. REST APIs with validation and useful error responses.
7. A frontend that consumes the backend APIs.
8. Basic local persistence, proposed as SQLite for the MVP.

### Beta — Final demonstration
- User registration/sign-in and secure authentication.
- Role-based access control for administrators, trainers, and members.
- User profile and role-appropriate dashboard.
- Permission checks on protected API operations.
- Security hardening, validation, and error handling.
- Deployment and configuration for the deployed environment.
- More complete progress history and usability refinements.

### Out of scope for the initial MVP
Payment-gateway integration, biometric access control, mobile applications, nutrition planning, messaging, advanced analytics, and multi-branch franchise management. These features would increase risk without being needed to demonstrate the core project.

## 6. High-level user journeys
**Administrator (MVP):** Opens the dashboard, creates a member and trainer, assigns a membership, records a check-in, and creates a workout plan.

**Trainer (Beta):** Signs in, views assigned members, updates their workout plans, and reviews recorded progress.

**Member (Beta):** Signs in, views membership status and attendance, opens assigned workout plans, and reviews progress.

## 7. Product requirements and priorities

| ID | Requirement | Release | Priority |
|---|---|---|---|
| PR-01 | Maintain member records through CRUD operations | MVP | Must |
| PR-02 | Maintain trainer records through CRUD operations | MVP | Must |
| PR-03 | Create and view membership records/status | MVP | Must |
| PR-04 | Record attendance and view attendance history | MVP | Must |
| PR-05 | Create and assign workout plans | MVP | Must |
| PR-06 | Connect frontend views to REST endpoints | MVP | Must |
| PR-07 | Persist core records in a local database | MVP | Must |
| PR-08 | Authenticate users securely | Beta | Must |
| PR-09 | Enforce permissions by user role | Beta | Must |
| PR-10 | Provide profile and role-appropriate dashboard | Beta | Should |
| PR-11 | Deploy the application | Beta | Must |
| PR-12 | Show member workout progress history | Beta | Should |

## 8. Constraints and assumptions
- The required stack is React + TypeScript for the frontend and FastAPI + Python for the backend.
- The midterm MVP is expected to run locally and use REST APIs.
- The initial interface may show placeholder metrics while the CRUD modules are developed; placeholders must be labelled and must not be represented as live data.
- SQLite is proposed for the local MVP to limit setup complexity. The database choice may be reviewed before implementation if the course requires another option.
- Authentication and RBAC are reserved for Beta unless the instructor specifies otherwise.

## 9. Risks and mitigations
- **Scope growth:** Keep the first release focused on the five core modules.
- **Late integration:** Test frontend-to-backend requests early using the health endpoint.
- **Data integrity issues:** Validate input and enforce required fields before saving records.
- **Security gaps:** Do not expose protected member information without authentication and authorization in Beta.
- **Schedule pressure:** Complete one end-to-end workflow before building optional features.

## 10. Dependencies and open decisions
The project depends on Python, Node.js/npm, and the course-required tools being available in the development environment. The final data fields for member, trainer, membership, and workout records should be reviewed during implementation. Any additional format or documentation rubric requirements from the instructor take precedence over this baseline.
