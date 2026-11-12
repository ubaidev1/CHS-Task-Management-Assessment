"""
Single source of truth for role capabilities.

Each constant below is the set of roles allowed to perform one capability. This
mirrors the assessment's permission matrix one-to-one, so the whole policy is
readable in one place and changing *who* can do something means editing exactly
one set — not hunting through views, permissions and queries.

These constants cover CAPABILITY ("can this role do X at all"). Object-level
ownership ("is this the requester's own task") is a separate layer enforced in
the permission classes and querysets, and is intentionally not encoded here.
"""

from .models import Role

# Admin + Manager see every task; Employees only their own.
CAN_VIEW_ALL_TASKS = frozenset({Role.ADMIN, Role.MANAGER})

# Admin + Manager may create/assign tasks.
CAN_CREATE_TASKS = frozenset({Role.ADMIN, Role.MANAGER})

# Only Admin may delete tasks.
CAN_DELETE_TASKS = frozenset({Role.ADMIN})

# Admin + Manager may view the user list.
CAN_VIEW_USERS = frozenset({Role.ADMIN, Role.MANAGER})

# Only Admin may create users / perform administrative user management.
CAN_MANAGE_USERS = frozenset({Role.ADMIN})
