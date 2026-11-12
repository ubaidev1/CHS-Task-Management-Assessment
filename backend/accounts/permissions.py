from rest_framework.permissions import BasePermission

from .models import Role


class UserManagementPermission(BasePermission):
    """Admin and Manager may view users; only Admin may create/modify them."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if view.action in ("list", "retrieve"):
            return user.role in (Role.ADMIN, Role.MANAGER)
        # create / update / partial_update / destroy -> Admin only.
        return user.role == Role.ADMIN
