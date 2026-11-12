# Engineering Decisions & Assumptions

Only the choices I made where the brief was silent or offered options.
Prescribed requirements are covered in the README and code.

## Business rules I assumed

- **Status values:** `pending / in_progress / completed`. The brief names
  `pending_tasks` but not the statuses, so `pending_tasks = total_tasks −
  completed_tasks` (both `pending` and `in_progress` count as pending).
- **Re-assigning to the current assignee is a no-op:** no new event, no email.
  This avoids spurious notifications.
- **Creating a task already assigned to someone notifies that person.** Assigning
  during creation is still assigning, so it uses the same idempotent path.
  Creating an unassigned task sends nothing.
- **Emails are stored lowercase** so login lookup is case-insensitive.

## Design choices

- **Role as a `CharField`, not Django Groups.** The brief allows a
  "well-documented alternative". A single field is simpler, a role check is a
  plain attribute compare (no join, no N+1), and one role per user is guaranteed
  by the schema. *Cost:* no runtime-editable permissions, which this fixed matrix
  doesn't need.
- **Role capabilities centralized in `accounts/roles.py`** as named sets, used by
  permissions, querysets and the dashboard. Changing who can do something is a
  one-line edit.
- **Cross-user access returns 404, not 403**, so the API doesn't confirm that
  another user's task exists.
- **Unauthenticated returns 401, forbidden returns 403**, so the frontend can
  tell "session expired" from "not allowed".
- **Login is wrapped in `csrf_protect`:** DRF only enforces CSRF once a session
  exists, so the anonymous login POST would otherwise be unprotected.
- **Dashboard cache invalidation via a global generation counter**, with the
  user's current role in the key. One task change affects many dashboards;
  bumping one counter supersedes every entry without enumerating users, and
  role-in-key makes a role change effective on the next request.
  *Trade-off:* if a counter bump is lost during a Redis blip, stale **counts**
  (never unauthorized data, since scope is in the key) can show until the TTL
  expires.
- **Idempotency keyed on a persisted `AssignmentEvent` UUID**, created with the
  assignment and the only value passed to Celery. Chosen over a task-generated
  timestamp (differs on retry, causing duplicates) and over a `(task, user)`
  composite key (would wrongly block A→B→A reassignment).
  *Trade-off:* a crash after sending but before the row commits could resend on
  retry; accepted for this scope.
- **The frontend sets the CSRF header manually in an interceptor** because
  Angular's built-in XSRF support is same-origin only and the API is on a
  different origin (`:8000`). I kept the real cross-origin flow instead of hiding
  it behind a dev proxy.