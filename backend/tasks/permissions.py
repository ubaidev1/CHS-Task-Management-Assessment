from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import Role


class TaskPermission(BasePermission):
    """Backend-enforced RBAC for tasks (the source of truth).

    Role matrix:
      - create / assign : Admin, Manager
      - delete          : Admin only
      - view all        : Admin, Manager
      - view / update own: everyone (Employee limited to tasks assigned to them)

    View-level checks gate the action; object-level checks gate access to a
    specific task. Employee querysets are also scoped in the view, so an
    Employee requesting another user's task by ID gets 404, not 403 (no
    existence leak) — this object check is defense in depth.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if view.action == "create":
            return user.role in (Role.ADMIN, Role.MANAGER)
        if view.action == "destroy":
            return user.role == Role.ADMIN
        # list / retrieve / update / partial_update: object-level + queryset scope.
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role in (Role.ADMIN, Role.MANAGER):
            return True
        if request.method in SAFE_METHODS:
            return obj.assigned_to_id == user.id
        if view.action == "destroy":
            return False  # only Admin may delete
        # Employee may update only a task assigned to them (field limits are
        # enforced in the serializer: status is the only writable field).
        return obj.assigned_to_id == user.id
