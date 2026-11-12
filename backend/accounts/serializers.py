from rest_framework import serializers

from .models import User


class LoginSerializer(serializers.Serializer):
    """Validates login input only (authentication happens in the view)."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class UserSerializer(serializers.ModelSerializer):
    """Safe public representation of a user."""

    class Meta:
        model = User
        fields = ("id", "username", "email", "role")
        read_only_fields = fields
