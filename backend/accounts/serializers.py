from django.contrib.auth.password_validation import validate_password
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


class UserCreateSerializer(serializers.ModelSerializer):
    """Admin-only user creation. Password is validated and never returned."""

    password = serializers.CharField(
        write_only=True, validators=[validate_password], style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "role", "password")

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
