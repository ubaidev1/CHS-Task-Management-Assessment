# Engineering Decisions & Assumptions

This document records every non-trivial decision, the reasoning behind it, and
the assumptions made where the brief is silent. It is updated as the project
progresses, module by module.

> Status key: ✅ decided & implemented · 🔜 planned · 💭 open question

---

## 0. Ground rules

- **Backend is the source of truth.** Frontend guards are usability only; every
  permission is enforced server-side, including object ownership.
- **Fail closed.** Private by default (DRF `IsAuthenticated` default permission);
  endpoints opt *out* of auth explicitly, never the reverse.
- **No secrets in source control.** All secrets come from the environment; the
  committed `.env.example` holds variable names and safe sample values only.

---

## 1. Project structure & tooling

| Decision | Choice | Why |
| --- | --- | --- |
| Backend folder vs project name | Folder `backend/`, Django project package `taskflow` | Decoupling the settings import path (`taskflow.settings`) from the directory name is clearer and portable; a project literally named `backend` inside `backend/` is confusing. |
| Settings layout | Split package `taskflow/settings/{base,dev,prod}.py` | The brief requires environment-based configuration. A split expresses "same code, different environment" without scattered `if DEBUG` branches. Selected via `DJANGO_SETTINGS_MODULE` (defaults to `dev` in `manage.py`). |
| App layout | Flat apps at `backend/` root (`accounts`, `tasks`) | With only two apps an `apps/` container adds nesting for no benefit; flat is simpler. (Would reconsider a package if the app count grew.) |
| Dependency versions | Latest stable as of 2026-11 (Django 6.1.3, DRF 3.18.3, django-redis 7.0.0, celery 5.7.0, redis 8.1.0, psycopg 3.3.9) | Build on current, supported releases rather than trailing versions. |
| Config library | `django-environ` | Maps a `.env` file + real env vars onto typed settings; real env vars win (correct for Docker/CI). |
| DB driver | `psycopg[binary]` (psycopg 3) | Current, actively-developed adapter; psycopg2 is maintenance-only. |
| Cache backend | `django-redis` | Gives Django's cache API over Redis plus atomic ops and `IGNORE_EXCEPTIONS` graceful degradation (needed for the "Redis unavailable" requirement). |
| Redis DB split | broker/results on DB `0`, cache on DB `1` | Keeps queue data and cache data isolated in one Redis instance. |

## 2. Authentication & security posture

| Decision | Choice | Why |
| --- | --- | --- |
| Auth mechanism | DRF `SessionAuthentication` only (no Token/JWT) | The brief mandates session-based auth; SessionAuthentication also enforces CSRF on unsafe methods. |
| Session cookie | `HttpOnly=True` | JS can never read the session id (mitigates XSS session theft). |
| CSRF cookie | `HttpOnly=False` | Angular must read the CSRF cookie to echo it in the `X-CSRFToken` header (Django's double-submit flow). |
| Cookie Secure/SameSite | `Secure=False`,`SameSite=Lax` in dev; `Secure=True` in prod, `SameSite` env-driven (`None` only when cross-site, always paired with Secure) | Matches the brief's cookie guidance for same-site vs cross-site topologies. |
| CORS | Explicit origins + `CORS_ALLOW_CREDENTIALS=True`; never wildcard | Brief forbids wildcard origin with credentialed requests. |
| Session expiry | 8h age, sliding (`SESSION_SAVE_EVERY_REQUEST`), expire at browser close | Abandoned sessions do not stay usable indefinitely. |

## 3. Custom user model

- ✅ **Custom `accounts.User` (extends `AbstractUser`) created before the first
  migration.** Swapping the user model later is a breaking, migration-heavy
  change, so we commit on day one.
- **Role stored as a `role` CharField** with `choices` (`admin`/`manager`/
  `employee`, default `employee`). The brief allows "Django Groups/Permissions
  **or a well-documented alternative**"; a single role field is that
  alternative — simpler to read and reason about, and a role check is a plain
  attribute compare (no extra query, no N+1). Permissions are enforced by custom
  DRF permission classes that read `user.role` (RBAC phase).
  *Assumption:* one role per user.
- **Privilege-escalation guard (serializer-level, RBAC phase):** `role` is
  settable only by Admin on user creation and is read-only to a user editing
  themselves — a client cannot escalate by sending `role` in a payload.
- Email is `unique=True` and lowercased on save, so `A@x.com` and `a@x.com`
  cannot become two separate users. *Assumption:* email is lowercased wholesale
  as the canonical identity.

## 4. Authentication endpoints (Module 1)

| Decision | Choice | Why |
| --- | --- | --- |
| View style | Plain `APIView` for login/logout/me/session | These are actions, not CRUD over a resource; a ViewSet/router adds indirection for no gain. (ViewSets come later for tasks/users.) |
| CSRF on login | `csrf_protect` added explicitly to `LoginView` | DRF `SessionAuthentication` only enforces CSRF once a session user exists, so the anonymous login POST is otherwise unprotected. This closes login-CSRF. |
| CSRF cookie seeding | `GET /session/` uses `ensure_csrf_cookie` | The frontend calls it first to obtain the (non-HttpOnly) `csrftoken` cookie, then echoes it in `X-CSRFToken` on writes. |
| Rejection status | Anonymous/expired → **403** (DRF default with SessionAuthentication) | DRF returns 403 (not 401) when there is no auth challenge scheme. It is still a hard rejection; noted in case 401 is preferred. |
| Inactive users | Handled by `authenticate()` returning `None` → 401 | `ModelBackend` rejects inactive users, so no separate check is needed (fail-closed). |

**CSRF flow (documented):** `GET /api/auth/session/` → browser stores `csrftoken`
cookie (readable by Angular) → Angular sends it as `X-CSRFToken` on every unsafe
request → Django validates header against cookie. Session cookie stays HttpOnly.

---

## Assumptions (brief is silent)

1. **Task fields** (planned): `title, description, status, assigned_to,
   created_by, created_at, updated_at`.
2. **Status values** 🔜: `pending / in_progress / completed`. Used consistently
   across model, serializers, tests and Angular. **`pending_tasks =
   total_tasks − completed_tasks`**, i.e. both `pending` and `in_progress`
   count as pending.
3. **Employee may change only `status`** on tasks assigned to them — enforced in
   the serializer, not just the UI.
4. **Idempotency** 🔜: a persisted `AssignmentEvent` row with a UUID PK, created
   in the same transaction as the assignment; only the UUID is passed to Celery;
   the worker sends under a row lock iff not already sent. Retry reuses the UUID
   (no duplicate); a genuine reassignment creates a new row (new email).
   Assigning a task to the user who already holds it is a **no-op** (no event).
5. **User management**: Admin and Manager can view users; only Admin can create
   users / perform administrative actions (Manager receives 403 on create).
6. **One role group per user** in normal operation.

---

## Known constraints in this environment

- Docker is not installed on the development machine, so Compose files are
  authored and reviewed but the stack is run natively (local Postgres 18 +
  Redis 7) during development. Both run paths are documented in the README.
