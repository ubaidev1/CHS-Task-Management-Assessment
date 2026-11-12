from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Role
from accounts.roles import CAN_VIEW_ALL_TASKS

from .models import Task
from .notifications import queue_assignment_notification
from .permissions import TaskPermission
from .serializers import AssignSerializer, TaskSerializer
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
        # Ownership comes from the session, never the request body. If the task
        # is created already assigned to someone, that is an assignment too, so
        # it notifies via the same idempotent path as the /assign/ endpoint.
        with transaction.atomic():
            task = serializer.save(created_by=self.request.user)
            if task.assigned_to_id:
                queue_assignment_notification(task, task.assigned_to, self.request.user)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """Assign a task and queue an async notification (Admin/Manager only).

        The assignment and its AssignmentEvent are saved in one transaction; the
        Celery job is enqueued only on commit, so the API returns immediately and
        the worker never sees an uncommitted event.
        """
        task = self.get_object()
        serializer = AssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_assignee = serializer.validated_data["assigned_to"]

        # Documented no-op: assigning to the user who already holds the task is
        # not a new assignment event, so no duplicate notification.
        if task.assigned_to_id == new_assignee.id:
            return Response(
                {"detail": "Task is already assigned to this user.", "queued": False}
            )

        with transaction.atomic():
            task.assigned_to = new_assignee
            task.save()
            event = queue_assignment_notification(task, new_assignee, request.user)

        return Response(
            {
                "detail": "Assignment saved; notification queued.",
                "event_id": str(event.id),
                "queued": True,
            },
            status=status.HTTP_200_OK,
        )


class DashboardStatsView(APIView):
    """Role-scoped dashboard statistics, cached in Redis (see tasks/stats.py)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_dashboard_stats(request.user))
