# Engineering Decisions & Assumptions

Key decisions, the reasoning behind them, and the assumptions made where the
brief is silent.

## Ground rules

- **Backend is the source of truth.** Frontend guards are usability only; every
  permission is enforced server-side, including object ownership.
- **Fail closed.** Private by default (`IsAuthenticated`); endpoints opt out of
  auth explicitly, never the reverse.
- **No secrets in source control.** Config comes from the environment;
  `.env.example` holds names + safe sample values only.

## Assumptions (brief is silent)

- **Status values:** `pending / in_progress / completed`, used everywhere.
  `pending_tasks = total_tasks − completed_tasks` (both `pending` and
  `in_progress` count as pending).
- **Roles as a field:** `User.role` is a `CharField` with choices — the brief's
  allowed "well-documented alternative" to Groups. Simpler, and a role check is a
  plain attribute compare (no extra query). One role per user.
- **Employee may change only `status`** on tasks assigned to them.
- **Email** is unique and lowercased on save, so `A@x.com` and `a@x.com` can't
  become two identities.
- **Assigning to the current assignee is a no-op** (no event, no email).
- **Creating a task with an assignee notifies that person** (extension of the
  brief — see Celery below).

## Authentication (Module 1)

- DRF `SessionAuthentication` only (no token/JWT); it also enforces CSRF on
  authenticated writes.
- Session cookie is **HttpOnly**; CSRF cookie is **not** HttpOnly so Angular can
  read it and echo it as `X-CSRFToken`. Secure + SameSite tighten in prod.
- Login is additionally wrapped in `csrf_protect` (DRF skips CSRF for anonymous
  requests, which would otherwise leave login unprotected).
- **Unauthenticated → 401, forbidden → 403** (custom `SessionAuthentication401`),
  so the frontend can tell "log in again" apart from "not allowed".
- **CSRF flow:** `GET /auth/session/` sets the `csrftoken` cookie → Angular sends
  it as `X-CSRFToken` on unsafe requests → Django validates header vs cookie.

## RBAC & object-level authorization (Module 2)

- `ModelViewSet` + reusable DRF permission classes (`TaskPermission`,
  `UserManagementPermission`): `has_permission` gates the action, 
  `has_object_permission` gates the specific object.
- **Role capabilities live in one place** (`accounts/roles.py`) as named role
  sets, referenced by permissions, querysets and the dashboard — changing who can
  do something is a one-line edit, and the policy reads 1:1 against the matrix.
- **Employee querysets are scoped** to their own tasks, so cross-user access by
  ID returns **404, not 403** (no existence leak). Fail-closed: an unknown role
  gets `none()`.
- `created_by` and `role` are server-set / read-only, so a client can't escalate
  via the payload. Delete is Admin-only.

## Redis caching (Module 3)

- Cache key is `dashboard:stats:v{generation}:u{user}:r{role}` with a **300s
  TTL**. User + role in the key prevents cross-user/role leakage, and rebuilding
  it from the *current* role means a **role change takes effect immediately**.
- **Invalidation:** any task change bumps a global generation counter (on
  `transaction.on_commit`), superseding every cached entry at once.
- **Graceful degradation:** every cache call is wrapped, so a Redis outage is a
  cache miss and the view falls back to a permission-scoped DB query.
- *Trade-off:* if an invalidation is lost during a Redis blip, stale **counts**
  (never unauthorized data — scope is in the key) could show until the TTL
  expires. Bounded and acceptable.

## Celery notifications (Module 4)

- **Idempotency key = a persisted `AssignmentEvent` UUID**, created in the same
  transaction as the assignment. Only the UUID is sent to Celery; the worker
  sends under a row lock **iff `status != SENT`**, then marks it SENT. A retry /
  re-delivery reuses the UUID and skips → no duplicate; a reassignment is a new
  row → a new email.
- Enqueued **after commit** (`transaction.on_commit`), so the API returns
  immediately and the worker never sees an uncommitted event. Retries 3×; console
  email backend.
- The create path and the `/assign/` endpoint share one helper
  (`queue_assignment_notification`), so both notify through the same idempotent
  path. The `/assign/` endpoint stays the canonical trigger the brief's tests hit.
- *Limitation:* a crash in the tiny window after send but before the row commits
  could resend on retry. Negligible with the console backend; not worth an
  outbox pattern here.

## Frontend (Module 5)

- Angular 20 standalone components, signals, lazy-loaded routes, reusable
  services.
- Two functional interceptors: one adds `withCredentials` + `X-CSRFToken`, one
  routes to login on 401 (cross-origin needs the CSRF header set manually, since
  Angular's built-in XSRF is same-origin only).
- `provideAppInitializer` resolves the session before the first route so guards
  are correct on refresh. Guards are usability only.
- Custom design system (no component library); every page has loading, empty and
  error states.

## Delivery (Module 6)

- Docker Compose runs db, redis, backend (gunicorn), worker (celery) and frontend
  (nginx); the backend migrates + seeds on start. Containers use the `dev`
  settings (cookies work over plain HTTP); `prod` settings add Secure cookies and
  HSTS.
- Secrets use clearly-insecure dev defaults overridable from the host env — none
  are committed.
- *Caveat:* Docker is not installed on the dev machine, so Compose was authored
  and validated but not booted here. The native run path (local Postgres + Redis)
  is fully exercised, and the cross-origin CORS/CSRF/session flow was verified
  end-to-end.
