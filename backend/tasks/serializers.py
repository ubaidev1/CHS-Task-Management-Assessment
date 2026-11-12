from rest_framework import serializers

from accounts.models import Role, User

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    # Read-only display names (no extra query: the view select_related()s these).
    assigned_to_username = serializers.CharField(
        source="assigned_to.username", read_only=True, allow_null=True
    )
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, allow_null=True
    )

    class Meta:
        model = Task
        fields = (
            "id", "title", "description", "status",
            "assigned_to", "assigned_to_username",
            "created_by", "created_by_username",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "created_by", "created_by_username",
            "assigned_to_username", "created_at", "updated_at",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        # Employees may change ONLY the status of a task assigned to them.
        # Make every other field read-only so extra payload keys are ignored
        if user and user.is_authenticated and user.role == Role.EMPLOYEE:
            for name, field in self.fields.items():
                if name != "status":
                    field.read_only = True


class AssignSerializer(serializers.Serializer):
    """Validates the assignment payload: {"assigned_to": <user id>}."""

    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
