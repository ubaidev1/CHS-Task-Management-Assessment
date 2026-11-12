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
