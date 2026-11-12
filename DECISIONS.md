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

## 3a. Seeding demo users

- **Demo users are created by a management command (`seed_users`), not a data
  migration.** A migration runs in every environment (including prod) and would
  bake known passwords into source control — both a secret-in-repo violation and
  a security hole. The command is idempotent and reads passwords from env
  (`DEMO_*`) with obvious dev-only defaults. (Role *groups* would justify a data
  migration, but we use a `role` field, so there is nothing structural to seed.)

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

## 5. RBAC, tasks & user management (Module 2)

| Decision | Choice | Why |
| --- | --- | --- |
| View style | `ModelViewSet` + router for tasks/users | Standard CRUD maps cleanly to a ViewSet and DRF's object-level permission hooks; contrast with the auth APIViews, which are actions, not resources. |
| Permission enforcement | Reusable `BasePermission` classes (`TaskPermission`, `UserManagementPermission`) | `has_permission` gates the action by role; `has_object_permission` gates the specific object — backend is the source of truth. |
| Role rules location | Named role sets in `accounts/roles.py`, referenced by permissions, querysets and the dashboard | **Permission rules are defined once as named role sets; changing who can do something means editing one constant, not hunting through the code.** Sets (not functions) were chosen because the role→action matrix is a fixed, declarative table — the whole policy reads in one screen and maps 1:1 to the brief's matrix. Runtime-editable permissions (Django Groups/Permissions) were not used because the matrix is fixed by the brief, so a static, auditable mapping is simpler and safer. Object-ownership stays a separate layer. |
| Fail-closed querysets | `get_queryset` returns `Task.objects.none()` for any role outside the known set | An unknown/unset role sees nothing, never everything. |
| Employee task visibility | Queryset scoped in `get_queryset` | Employees' queryset is `assigned_to=self`, so cross-user access by ID returns **404, not 403** (no existence leak). Object permission is defense in depth. |
| Field-level limit | Employee serializer makes every field except `status` read-only | Enforces "Employee updates only status" server-side; extra payload keys are ignored, not applied. |
| Ownership | `created_by` set in `perform_create` from `request.user`; read-only in serializer | A client cannot spoof ownership via the payload (tested). |
| Delete | Admin only (view-level + object-level) | Matches the matrix; Manager/Employee get 403. |
| User creation | `UserCreateSerializer` (password write-only, `validate_password`); Admin only | Manager can list but not create (403, tested). Role is set only on admin-driven create. |
| Self-escalation | Non-admin cannot modify users (403) | An employee cannot promote their own role (tested). |
| FK on_delete | `assigned_to` / `created_by` = `SET_NULL` | Deleting a user never cascades away task history; employee scoping still holds. |

*Assumption:* Admin/Manager may update any task (they manage all); Employee may
update only the `status` of a task assigned to them. A task may be created
unassigned and assigned later (the dedicated `/assign/` endpoint is Module 4).

*N+1 note:* task `assigned_to`/`created_by` use DRF's PK-only optimization (no
per-row query); `select_related` is added as defensive belt-and-suspenders.

*Inactive users:* DRF `SessionAuthentication` rejects users with `is_active=False`
(returns `None`), so a deactivated user's live session is denied on the next
request — fail-closed without an extra check.

## 6. Dashboard caching (Module 3)

| Decision | Choice | Why |
| --- | --- | --- |
| Cache key | `dashboard:stats:v{gen}:u{user_id}:r{role}` | User id + role in the key guarantees no cross-user/role leakage; rebuilding the key from the *current* role each request means a role change instantly produces a different key (old entry never served). |
| Invalidation | Global **generation counter** bumped on any task change | Admin/Manager stats cover all tasks, so any change affects many dashboards; bumping one counter supersedes every cached entry without enumerating users. TTL (300s) is the backstop. |
| When to invalidate | `post_save`/`post_delete` signal → `transaction.on_commit` | Invalidate only after the change commits, so a concurrent request can't cache pre-commit state under the new generation. |
| Graceful degradation | Every cache call wrapped in try/except returning a miss | A Redis outage yields a cache miss, and the view falls back to a permission-scoped DB query — correct data, never an error, never out-of-scope. Independent of `IGNORE_EXCEPTIONS` (belt-and-suspenders). |
| Compute cost | One aggregate (total + completed) + one `my_tasks` count | Two queries regardless of task count; `pending = total − completed` avoids a third. |

*Permission freshness:* authorization is re-evaluated every request (IsAuthenticated + role-in-key), so revoked access takes effect immediately; cached data for an old role is unreachable.

*Honest tradeoff:* if an invalidation is lost during a Redis outage (a brief blip where the entry survives but the generation bump fails), stale **counts** could be served until the 300s TTL expires. This never exposes *unauthorized* data (scope is in the key); it is a bounded count-staleness window, documented here.

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
