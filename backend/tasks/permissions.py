from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.roles import CAN_CREATE_TASKS, CAN_DELETE_TASKS, CAN_VIEW_ALL_TASKS


class TaskPermission(BasePermission):
    """
    Backend-enforced RBAC for tasks.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if view.action in ("create", "assign"):
            # "Create / assign tasks" -> Admin, Manager.
            return user.role in CAN_CREATE_TASKS
        if view.action == "destroy":
            return user.role in CAN_DELETE_TASKS
        # list / retrieve / update / partial_update: object-level + queryset scope.
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role in CAN_VIEW_ALL_TASKS:
            # Admin/Manager may read any task and update it; only Admin may
            # delete (gated at the view level by CAN_DELETE_TASKS).
            return True
        if request.method in SAFE_METHODS:
            return obj.assigned_to_id == user.id
        if view.action == "destroy":
            return False
        # Employee may update only a task assigned to them (field limits are
        # enforced in the serializer: status is the only writable field).
        return obj.assigned_to_id == user.id
