"""
Dashboard statistics with permission-scoped Redis caching.

Design
------
Cache key embeds the user id AND the current role AND a global generation
counter:  ``dashboard:stats:v{gen}:u{user_id}:r{role}``

- **Per-user / per-role scope:** the key includes user id and role, so cached
  data can never be served across users or roles.
- **Permission freshness:** because the key is rebuilt from the user's *current*
  role on every request, a role change produces a different key — the old
  role's cached entry is never served. Revoked access takes effect immediately.
- **Invalidation:** any task create/update/assign/delete bumps the global
  generation (via a post-commit signal). Every cached key then references a
  stale generation and is effectively invalidated at once, without having to
  enumerate every affected user.
- **Graceful degradation:** all cache access is wrapped so a Redis outage
  returns a cache miss (never an error), and the view falls back to a
  permission-scoped database query. We never serve data outside the requester's
  current scope.
"""

import logging

from django.core.cache import cache
from django.db.models import Count, Q

from accounts.roles import CAN_VIEW_ALL_TASKS

from .models import Task, TaskStatus

logger = logging.getLogger(__name__)

STATS_TTL = 300  # five minutes, per the brief
_GEN_KEY = "dashboard:stats:generation"


# --- safe cache access (never raises to the caller) ------------------------
def _safe_cache_get(key):
    try:
        return cache.get(key)
    except Exception:
        logger.warning("Cache read failed for %s; falling back to DB.", key, exc_info=True)
        return None


def _safe_cache_set(key, value, timeout):
    try:
        cache.set(key, value, timeout)
    except Exception:
        logger.warning("Cache write failed for %s; continuing without cache.", key, exc_info=True)


def _generation():
    """Current generation; initialised to 1 if absent (or on a Redis outage)."""
    gen = _safe_cache_get(_GEN_KEY)
    if gen is None:
        _safe_cache_set(_GEN_KEY, 1, None)  # None timeout = persist
        return 1
    return gen


def invalidate_stats():
    """Bump the generation so every cached dashboard entry is superseded."""
    try:
        cache.incr(_GEN_KEY)
    except ValueError:
        # Key absent: nothing cached under a prior generation to invalidate.
        _safe_cache_set(_GEN_KEY, 1, None)
    except Exception:
        logger.warning("Failed to invalidate dashboard stats generation.", exc_info=True)


# --- stats computation (the source of truth) -------------------------------
def _compute_stats(user):
    """Permission-scoped counts, computed from the database."""
    if user.role in CAN_VIEW_ALL_TASKS:
        base = Task.objects.all()
    else:
        base = Task.objects.filter(assigned_to=user)

    # One aggregate query for total + completed on the scoped set.
    agg = base.aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=TaskStatus.COMPLETED)),
    )
    total = agg["total"]
    completed = agg["completed"]
    my_tasks = Task.objects.filter(assigned_to=user).count()

    return {
        "total_tasks": total,
        "completed_tasks": completed,
        # pending = total - completed: both `pending` and `in_progress` count
        # as pending (documented in DECISIONS.md).
        "pending_tasks": total - completed,
        "my_tasks": my_tasks,
    }


def _stats_key(user, gen):
    return f"dashboard:stats:v{gen}:u{user.id}:r{user.role}"


def get_dashboard_stats(user):
    """Return cached stats for the user, computing + caching on a miss."""
    key = _stats_key(user, _generation())
    cached = _safe_cache_get(key)
    if cached is not None:
        return cached
    data = _compute_stats(user)
    _safe_cache_set(key, data, STATS_TTL)
    return data
