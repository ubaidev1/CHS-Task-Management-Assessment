"""Tests for the custom User model."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import Role

User = get_user_model()


class UserModelTests(TestCase):
    def test_default_role_is_employee(self):
        user = User.objects.create_user(username="u", email="u@example.com", password="pw-123456!")
        self.assertEqual(user.role, Role.EMPLOYEE)

    def test_role_can_be_set(self):
        user = User.objects.create_user(
            username="a", email="a@example.com", password="pw-123456!", role=Role.ADMIN
        )
        self.assertEqual(user.role, Role.ADMIN)

    def test_email_is_lowercased_on_save(self):
        user = User.objects.create_user(
            username="mixed", email="  MixedCase@Example.COM ", password="pw-123456!"
        )
        self.assertEqual(user.email, "mixedcase@example.com")

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(username="first", email="dup@example.com", password="pw-123456!")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username="second", email="DUP@EXAMPLE.COM", password="pw-123456!"
                )
