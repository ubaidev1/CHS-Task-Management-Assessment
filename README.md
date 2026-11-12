# TaskFlow — Multi-user Task Management System

A role-aware task management application demonstrating secure **session
authentication**, **role-based + object-level authorization**, **Redis-backed
dashboard caching**, **asynchronous Celery notifications**, and an **Angular**
frontend.

> **Engineering notes and every non-trivial decision/trade-off are in
> [`DECISIONS.md`](./DECISIONS.md).** This README covers setup, running, and how
> each requirement maps to the code.

---

## Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12, Django 6.1, Django REST Framework |
| Frontend | Angular 20 (standalone, signals), TypeScript |
| Database | PostgreSQL 17 |
| Cache / broker | Redis 7 |
| Async jobs | Celery 5 |
| Auth | Django session auth, CSRF, role-based access control |

---

## Architecture at a glance

```
Angular (nginx :4200) ──HTTP (cookies + X-CSRFToken)──▶ Django API (gunicorn :8000)
                                                        │
                        ┌───────────────────────────────┼───────────────┐
                        ▼                                ▼               ▼
                  PostgreSQL                       Redis (cache)   Redis (broker)
                                                                        │
                                                                   Celery worker ──▶ email (console)
```

- **Backend is the source of truth.** Angular guards only hide UI; every
  permission is enforced server-side, including object ownership.
- Role capabilities live in one place (`backend/accounts/roles.py`) and are
  referenced by permissions, querysets and the dashboard.

---

## Quick start — Docker Compose (recommended)

Requires Docker + Docker Compose.

```bash
docker compose up --build
```

This starts Postgres, Redis, the API, a Celery worker, and the Angular app. The
backend automatically runs migrations and seeds demo users on first start.

| Service | URL |
| --- | --- |
| Frontend | http://localhost:4200 |
| API | http://localhost:8000/api |
| Django admin | http://localhost:8000/admin |

Sign in with a demo account (also shown on the login screen):

| Role | Username | Password |
| --- | --- | --- |
| Admin | `sophia` | `Admin@12345` |
| Manager | `marcus` | `Manager@12345` |
| Employee | `ethan` | `Employee@12345` |

To watch asynchronous emails, view the worker logs: `docker compose logs -f worker`.

> Secrets use clearly-insecure dev defaults, overridable from the host env, e.g.
> `DJANGO_SECRET_KEY=$(openssl rand -base64 48) docker compose up`.

---

## Running natively (without Docker)

Requires Python 3.12, Node 20, a local PostgreSQL and Redis.

### 0. Start PostgreSQL and Redis

```bash
sudo service postgresql start      # or: brew services start postgresql
sudo service redis-server start    # or: redis-server  /  brew services start redis
redis-cli ping                     # expect: PONG
```

### 1. Database

```bash
sudo -u postgres psql -c "CREATE ROLE taskflow WITH LOGIN PASSWORD 'taskflow' CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE taskflow OWNER taskflow;"
```

### 2. Backend

```bash
cd backend
python3 -m venv ../.venv && source ../.venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then set DJANGO_SECRET_KEY (see the file)
python manage.py migrate
python manage.py seed_users      # creates the demo users above
python manage.py runserver       # http://localhost:8000
```

### 3. Celery worker (separate terminal)

```bash
cd backend && source ../.venv/bin/activate
celery -A taskflow worker -l info
```

### 4. Frontend (separate terminal)

```bash
cd frontend
npm install
npm start                        # http://localhost:4200
```

The dev frontend calls the API at `http://localhost:8000/api` (see
`frontend/src/environments/environment.ts`) and relies on the backend's CORS +
CSRF configuration for the cross-origin session flow.

---

## Tests

Backend tests cover authorization, sessions, CSRF, caching and background jobs.

```bash
cd backend && source ../.venv/bin/activate
python manage.py test
```

**Result:** `Ran 55 tests ... OK` (last run against PostgreSQL + Redis).

Highlights (mapping to the brief's minimum test expectations):

| Area | Tests |
| --- | --- |
| Valid/invalid login, logout, anonymous/expired rejection | `accounts/tests.py` |
| CSRF on state-changing requests (login + authenticated writes) | `accounts/tests.py` |
| Role permissions, employee-delete 403, cross-user read 404 | `tasks/tests.py` |
| Permission freshness (role change takes effect immediately) | `tasks/tests.py::test_role_change_takes_effect_immediately` |
| Cache hit, cache invalidation, Redis outage fallback | `tasks/tests.py::DashboardCacheTests` |
| Commit-ordered enqueue + retry idempotency (no duplicate email) | `tasks/tests.py::AssignmentNotificationTests` |

Frontend builds with `cd frontend && npm run build`.

---

## API reference

| Method | Endpoint | Purpose | Who |
| --- | --- | --- | --- |
| POST | `/api/auth/login/` | Establish a session (CSRF-protected) | anyone |
| POST | `/api/auth/logout/` | Invalidate the session | authenticated |
| GET | `/api/auth/me/` | Current user | authenticated |
| GET | `/api/auth/session/` | Session validity + seeds CSRF cookie | anyone |
| GET | `/api/dashboard/stats/` | Role-scoped stats (cached) | authenticated |
| GET/POST | `/api/tasks/` | List (scoped) / create | list: all · create: Admin, Manager |
| GET/PATCH/DELETE | `/api/tasks/{id}/` | Retrieve / update / delete | see matrix |
| POST | `/api/tasks/{id}/assign/` | Assign + async notify | Admin, Manager |
| GET/POST | `/api/users/` | List / create users | list: Admin, Manager · create: Admin |

### Permission matrix

| Action | Admin | Manager | Employee |
| --- | :-: | :-: | :-: |
| View all users | ✅ | ✅ | ❌ |
| Create users | ✅ | ❌ | ❌ |
| Create / assign tasks | ✅ | ✅ | ❌ |
| View all tasks | ✅ | ✅ | ❌ |
| View / update status of own tasks | ✅ | ✅ | ✅ |
| Delete tasks | ✅ | ❌ | ❌ |

---

## How the key requirements are met

### CSRF token flow
1. The browser calls `GET /api/auth/session/`, which sets a **non-HttpOnly**
   `csrftoken` cookie (so Angular can read it).
2. The Angular interceptor reads that cookie and sends it as the
   **`X-CSRFToken`** header on every unsafe (POST/PATCH/DELETE) request, with
   `withCredentials: true`.
3. Django validates the header against the cookie. The **session cookie stays
   HttpOnly**; `Secure`/`SameSite` tighten in production.

### Redis caching
`GET /api/dashboard/stats/` caches per **user + role** with a 300s TTL. Any task
change bumps a generation counter that supersedes cached entries. Because the
cache key embeds the current role, a role change takes effect immediately, and a
Redis outage falls back to a permission-scoped DB query. See
`backend/tasks/stats.py`.

### Celery idempotency
Assigning a task creates an `AssignmentEvent` row (UUID PK) in the same
transaction; only that UUID is enqueued (after commit). The worker sends the
email under a row lock and only if the event isn't already `sent`, so a retry
never duplicates, while a genuine reassignment is a new event. Assigning to the
current assignee is a no-op. See `backend/tasks/tasks.py` and `DECISIONS.md §7`.

---

## Project structure

```
backend/
  taskflow/            # project config: split settings, celery, urls
  accounts/            # custom User, roles, auth endpoints, user management
  tasks/               # Task + AssignmentEvent, permissions, caching, celery task
frontend/
  src/app/core/        # models, API services, interceptors, guards
  src/app/layout/      # app shell (sidebar + topbar)
  src/app/features/    # login, dashboard, tasks, users
docker-compose.yml
DECISIONS.md           # assumptions + engineering decisions
```

---

## Notes & trade-offs

- **Environment:** containers run Django with the `dev` settings module (console
  email, non-Secure cookies for plain HTTP). Production settings
  (`taskflow.settings.prod`) enable Secure cookies, HSTS and strict transport.
- **Admin static files** are not collected in the gunicorn image (the Django
  admin UI is not a deliverable); the JSON API and the Angular app are the
  primary surfaces.
- Full assumptions and trade-offs are documented in [`DECISIONS.md`](./DECISIONS.md).
```
