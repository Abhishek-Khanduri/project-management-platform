# Project Management Platform

A lightweight Jira/Trello-style app. Users create projects, invite members and manage tasks.
Access is controlled by a central **Policy-Based Access Control (PBAC)** layer.

**Stack:** Django REST Framework, PostgreSQL, React (Vite), JWT authentication, Docker Compose.

## Contents

- [Quick start](#quick-start)
- [Features](#features)
- [Architecture](#architecture)
- [Technology choices](#technology-choices)
- [Authorization (PBAC)](#authorization-pbac)
- [Database design](#database-design)
- [API documentation](#api-documentation)
- [Environment variables](#environment-variables)
- [Local development without Docker](#local-development-without-docker)
- [Testing](#testing)
- [Assumptions](#assumptions)
- [Trade-offs and possible next steps](#trade-offs-and-possible-next-steps)

## Quick start

Requirements: Docker with Docker Compose.

```bash
docker compose up --build
```

| What | URL |
|---|---|
| Web app | http://localhost:3000 |
| API (Swagger UI) | http://localhost:8000/api/docs/ |
| OpenAPI schema | http://localhost:8000/api/schema/ |

Database migrations run automatically when the backend starts. Open the web app and register an account to begin.
To try the access rules, register a second user and add them to a project by email.

A `.env` file is optional: every variable has a development default. To customise, run `cp .env.example .env`.

> Ports 3000 and 8000 must be free. Postgres is not published to the host.

## Features

- **Authentication:**
  - Register, login, logout, refresh and verify, using JWT access and refresh tokens.
  - Passwords are hashed.
  - Refresh tokens are rotated and blacklisted on logout.
- **Projects:**
  - Create, view, update and delete.
  - Status can be active or archived.
  - Members are added by email and can be removed.
  - The project list supports search, a status filter and pagination.
- **Tasks:**
  - Create, view, update and delete.
  - Fields: status, priority, assignee, due date and timestamps.
  - Search on title and description, filters for status, priority and assignee, and pagination.
- **Dashboard:** total and active projects; total, completed and pending tasks.
- **PBAC:** every rule lives in one place (`backend/authz/`). Views never contain permission checks.
- **Consistent API:**
  - Proper status codes (200/201/204/400/401/403/404/409).
  - One error format, input validation and paginated lists.
  - Swagger/OpenAPI docs.
- **UI:**
  - Responsive layout.
  - Form validation, with server errors shown next to the fields.
  - Loading, empty and error states, and toast messages.
  - Status changes through a dropdown.

## Architecture

```
Browser ──> nginx (frontend container :3000)
              ├── /        → React single-page app (static files)
              └── /api/*   → Django + DRF via gunicorn (backend container :8000)
                                   │
                                   └──> PostgreSQL (db container)
```

Inside the backend, a request flows through these layers:

```
URL → View (HTTP only) → PolicyPermission → authz.authorize() → policies.py
                      → Serializer (input validation)
                      → Service (business logic, transactions) → Models / DB
Errors from any layer → core.exceptions.api_exception_handler → {"error": {...}}
```

```
backend/
  config/      settings (all from environment variables), root URLs, WSGI
  core/        shared helpers: error handler, pagination, health check
  accounts/    User model (email login) and auth endpoints
  authz/       PBAC: policies.py (rules), engine.py (authorize/can/scope), permissions.py (DRF bridge)
  projects/    Project + ProjectMembership models, services, API, dashboard
  tasks/       Task model, services, API
frontend/
  src/api/client.js     axios instance, token refresh, error helpers
  src/auth/             AuthContext (current user, login/logout)
  src/hooks.js          useApi (loading/error/data), useDebounce
  src/components/       Layout, TaskForm, TaskList, MembersPanel, Toast, small UI pieces
  src/pages/            Login, Register, Dashboard, Projects, ProjectDetail, TaskDetail
docs/openapi.yaml       exported API specification (importable into Postman)
```

## Technology choices

| Choice | Why |
|---|---|
| **Django + DRF** | Mature, batteries included (database layer, migrations, validation, auth). DRF gives serializers, viewsets, pagination and a pluggable exception handler. |
| **PostgreSQL** | Production-grade. Enforces the unique and check constraints used here. Tests also run on SQLite for speed. |
| **simplejwt** | Standard JWT implementation for DRF, with rotation and a built-in blacklist for logout. |
| **drf-spectacular** | Generates OpenAPI 3 and Swagger UI from the code, so the docs can't drift from it. |
| **React + Vite (plain JavaScript)** | A fast, minimal single-page app. Only four runtime libraries (react, react-dom, react-router-dom, axios). Server state is handled by a small `useApi` hook. |
| **nginx** | Serves the built frontend and proxies `/api`, so the browser sees one origin and no CORS setup is needed. |
| **gunicorn** | A production WSGI server (not Django's development server). |

## Authorization (PBAC)

RBAC is **not** used. There are no roles and no role column. Every decision is computed from
**attributes of the user, the resource and their relationship** at request time.

```python
# backend/authz/policies.py: one small function per rule
def can_delete_task(user, task):
    return task.status == "todo" and is_project_owner(user, task.project)

POLICIES = {
    "task.delete": (can_delete_task, "Only the project owner can delete a task, and only while it is in Todo."),
    ...
}

# backend/authz/engine.py: the single entry point
authorize(user, "task.delete", task)   # raises 403 with the policy's message if denied
can(user, "task.delete", task)         # True / False (used to tell the UI what is allowed)
scope(user, "project.view", queryset)  # applies a rule to a list as a DB filter
```

Views only **declare** which policy protects each action. The `PolicyPermission` class runs it automatically
when the object is loaded:

```python
policy_actions = {"retrieve": "task.view", "partial_update": "task.update", "destroy": "task.delete"}
```

| Action | Rule |
|---|---|
| `project.view` | The user is a member of the project. Lists are filtered with `scope()`. |
| `project.update` | The user is the project owner. |
| `project.delete` | The user is the project owner. |
| `project.manage_members` | The user is the project owner. |
| `task.create` | The user is a project member. |
| `task.view` | The user is a member of the task's project. |
| `task.update` | The user created the task **or** is its assignee, and is still a project member. |
| `task.delete` | The task status is **Todo** **and** the user is the project owner. |
| `task.complete` | The task has an assignee, a description and a due date. It's checked on the task *with the requested changes applied*. |

Behaviour worth noting:

- **Deny by default.** An unknown action name raises an error instead of allowing access.
- **Non-members get 404, not 403.** Lists and detail views are scoped, so a project's existence is never revealed.
  Members who are allowed to see a resource but not change it get **403**, with the policy's message.
- **The UI doesn't duplicate rules.** Projects and tasks include a `permissions` object (for example `can_delete`),
  computed by the same policies. The frontend only shows or hides buttons; the backend always enforces.

## Database design

```
User 1───* ProjectMembership *───1 Project
  │                                 │ owner_id → User
  │                                 1
  │                                 *
  └── assignee_id / created_by_id ─ Task
```

| Table | Key columns | Constraints and indexes |
|---|---|---|
| `accounts_user` | email (login), password (hashed), names | email unique |
| `projects_project` | name, description, status, owner_id, timestamps | CHECK status in (active, archived) |
| `projects_projectmembership` | project_id, user_id, joined_at | UNIQUE (project_id, user_id) |
| `tasks_task` | project_id, title, description, status, priority, assignee_id, created_by_id, due_date, completed_at, timestamps | CHECK status, CHECK priority, INDEX (project_id, status), INDEX (project_id, priority) |

- **Normalised:** membership is its own table (many-to-many). Users are referenced by foreign key and never copied.
- **On delete:**
  - Deleting a project removes its tasks and memberships (`CASCADE`).
  - Deleting a user clears them from tasks (`SET_NULL`), so task history survives.
- **Scalability:**
  - Indexes match the main query pattern (tasks of one project, filtered by status or priority).
  - Lists are paginated.
  - Counts use one `annotate`/`aggregate` query instead of one query per row.
- **Migrations:** `backend/*/migrations/`.

## API documentation

- **Swagger UI:** http://localhost:8000/api/docs/. Click *Authorize* and paste an access token from `/api/auth/login/`.
- **OpenAPI file:** [`docs/openapi.yaml`](docs/openapi.yaml). In Postman, use *Import* and select this file to get a ready collection.
- Every endpoint except register, login, refresh and verify needs `Authorization: Bearer <access token>`.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Create an account: `{email, password, first_name, last_name}` |
| POST | `/api/auth/login/` | `{email, password}` returns `{access, refresh}` |
| POST | `/api/auth/refresh/` | `{refresh}` returns a new `{access, refresh}` |
| POST | `/api/auth/verify/` | `{token}` returns 200 if valid |
| POST | `/api/auth/logout/` | `{refresh}` blacklists the refresh token (204) |
| GET | `/api/auth/me/` | The current user |
| GET | `/api/dashboard/` | `{total_projects, active_projects, total_tasks, completed_tasks, pending_tasks}` |
| GET | `/api/projects/?search=&status=&page=&page_size=` | Your projects (paginated) |
| POST | `/api/projects/` | Create a project (you become its owner and first member) |
| GET / PATCH / PUT / DELETE | `/api/projects/{id}/` | View, update or delete a project |
| GET | `/api/projects/{id}/members/` | List members |
| POST | `/api/projects/{id}/members/` | Add a member: `{email}` |
| DELETE | `/api/projects/{id}/members/{user_id}/` | Remove a member |
| GET | `/api/projects/{id}/tasks/?search=&status=&priority=&assignee=&page=&page_size=` | The project's tasks (paginated) |
| POST | `/api/projects/{id}/tasks/` | Create a task: `{title, description, status, priority, assignee_id, due_date}` |
| GET / PATCH / PUT / DELETE | `/api/tasks/{id}/` | View, update or delete a task |

**Response formats**

```jsonc
// Paginated list
{ "count": 23, "next": "http://.../?page=2", "previous": null, "results": [ ... ] }

// Every error (400, 401, 403, 404, 409, 500)
{ "error": { "code": "permission_denied", "message": "Only the project owner can delete this project.", "details": {} } }

// Validation error (400): field messages in "details"
{ "error": { "code": "validation_error", "message": "Invalid input.", "details": { "title": ["This field is required."] } } }
```

## Environment variables

See [`.env.example`](.env.example). All variables are optional in development.

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | development-only value | Signs the JWTs. **Must be changed in production.** |
| `DJANGO_DEBUG` | `False` | Django debug mode |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,backend` | Host names the backend accepts |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `pm` / `pm` / `pm` | Database credentials, used by both db and backend |
| `POSTGRES_HOST` | set to `db` by Compose | If unset, the backend uses SQLite (local development and tests) |
| `JWT_ACCESS_MINUTES` | `30` | Access token lifetime |
| `JWT_REFRESH_DAYS` | `7` | Refresh token lifetime |
| `LOG_LEVEL` | `INFO` | Log level (logs go to the console) |

## Local development without Docker

```bash
# Backend (uses SQLite when POSTGRES_HOST is not set)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver          # http://localhost:8000

# Frontend (in another terminal; /api is proxied to localhost:8000)
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

## Testing

There are 69 backend tests (pytest + pytest-django):

| File | What it covers |
|---|---|
| `authz/tests/test_policies.py` | Unit tests for every policy (allowed and denied cases), list scoping and engine behaviour |
| `accounts/tests/test_auth_api.py` | Register, login, invalid and missing tokens, refresh, logout (blacklist) |
| `projects/tests/test_project_api.py` | Project create/list/update/delete, search/filter, 404 vs 403, permissions, members |
| `tasks/tests/test_task_api.py` | Task create/list/update/delete, search/filter/pagination, completion rule, dashboard |
| `core/tests/test_core.py` | Health check and error format |

```bash
docker compose run --rm backend pytest           # against PostgreSQL
cd backend && pytest                             # locally, against SQLite
```

## Assumptions

- Any logged-in user can create a project. The creator becomes its owner and first member.
- Only the owner can add or remove members (the assignment doesn't specify). Members are added by email, which must belong to a registered user.
- The owner can't be removed from their own project.
- A member removed from a project is unassigned from that project's tasks.
- Updating a task requires being its creator or assignee **and** still a project member.
- "All required information" for completion means title, description, due date and assignee.
- Moving a task out of Completed clears `completed_at`.
- An assignee must be a member of the task's project (400 if not).
- "Pending tasks" on the dashboard means every task not Completed (Todo + In Progress).
- "Active projects" means projects with status `active`. Owners can archive a project.

## Trade-offs and possible next steps

| Decision | Trade-off | Next step |
|---|---|---|
| Policies as Python functions | Easy to read, test and debug, but changing a rule needs a deploy | Load rule combinations from YAML/JSON (a configurable PBAC engine) |
| Tokens in `localStorage` | Simple, but readable by JavaScript if an XSS bug ever existed | Refresh token in an httpOnly, SameSite cookie |
| Dropdown for status changes | Simple and accessible | Drag-and-drop Kanban board |
| Plain `icontains` search | No extra infrastructure; fine at this scale | PostgreSQL full-text search with a GIN index |
| `useApi` hook instead of a data library | Fewer dependencies | TanStack Query for caching and background refresh |
| Backend tests only | The UI was verified manually | Vitest + React Testing Library, plus Playwright end-to-end tests |

Bonus features deliberately left out to keep the scope focused: activity timeline / audit log, WebSockets, Redis caching,
background jobs, email notifications, file attachments, CI pipeline.
