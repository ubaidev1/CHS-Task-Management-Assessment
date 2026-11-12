from rest_framework import viewsets

from accounts.models import Role

from .models import Task
from .permissions import TaskPermission
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [TaskPermission]

    def get_queryset(self):
        user = self.request.user
        # select_related avoids N+1 when serializing assigned_to / created_by.
        qs = Task.objects.select_related("assigned_to", "created_by")
        if user.role in (Role.ADMIN, Role.MANAGER):
            return qs
        # Employees can only ever see tasks assigned to them. This scoping also
        # makes cross-user access by ID return 404 instead of leaking existence.
        return qs.filter(assigned_to=user)

    def perform_create(self, serializer):
        # Ownership comes from the session, never the request body.
        serializer.save(created_by=self.request.user)
