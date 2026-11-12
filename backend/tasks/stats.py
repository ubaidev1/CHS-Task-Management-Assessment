import logging

from django.core.cache import cache
from django.db.models import Count, Q

from accounts.roles import CAN_VIEW_ALL_TASKS

from .models import Task, TaskStatus

logger = logging.getLogger(__name__)

STATS_TTL = 300  # five minutes
_GEN_KEY = "dashboard:stats:generation"


# safe cache access
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


# --- stats computation ---
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
