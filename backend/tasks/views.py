from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role
from accounts.roles import CAN_VIEW_ALL_TASKS

from .models import Task
from .permissions import TaskPermission
from .serializers import TaskSerializer
from .stats import get_dashboard_stats


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [TaskPermission]

    def get_queryset(self):
        user = self.request.user
        qs = Task.objects.select_related("assigned_to", "created_by")
        if user.role in CAN_VIEW_ALL_TASKS:
            return qs
        if user.role == Role.EMPLOYEE:
            # Employees only ever see tasks assigned to them. This scoping also
            # makes cross-user access by ID return 404 (no existence leak).
            return qs.filter(assigned_to=user)
        # Fail closed: an unknown/unset role sees nothing.
        return qs.none()

    def perform_create(self, serializer):
        # Ownership comes from the session, never the request body.
        serializer.save(created_by=self.request.user)


class DashboardStatsView(APIView):
    """Role-scoped dashboard statistics, cached in Redis (see tasks/stats.py)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_dashboard_stats(request.user))
