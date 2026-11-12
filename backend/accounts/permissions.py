from rest_framework.permissions import BasePermission

from .roles import CAN_MANAGE_USERS, CAN_VIEW_USERS


class UserManagementPermission(BasePermission):
    """Admin and Manager may view users; only Admin may create/modify them."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if view.action in ("list", "retrieve"):
            return user.role in CAN_VIEW_USERS
        # create / update / partial_update / destroy -> Admin only.
        return user.role in CAN_MANAGE_USERS
