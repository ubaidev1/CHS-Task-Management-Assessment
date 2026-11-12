"""
Seed one user per role for local development and demos.

Idempotent: safe to run repeatedly. Passwords come from the environment so no
credentials are hardcoded in the repo; the defaults below are obvious
development-only values and must be overridden in any real deployment.

Usage:
    python manage.py seed_users
"""

import os

from django.core.management.base import BaseCommand

from accounts.models import Role, User

SEED = [
    ("admin", "admin@example.com", Role.ADMIN, "DEMO_ADMIN_PASSWORD", "Admin@12345"),
    ("manager", "manager@example.com", Role.MANAGER, "DEMO_MANAGER_PASSWORD", "Manager@12345"),
    ("employee", "employee@example.com", Role.EMPLOYEE, "DEMO_EMPLOYEE_PASSWORD", "Employee@12345"),
]


class Command(BaseCommand):
    help = "Create (or update) one demo user per role."

    def handle(self, *args, **options):
        for username, email, role, env_key, default_pw in SEED:
            password = os.environ.get(env_key, default_pw)
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": email, "role": role}
            )
            user.email = email
            user.role = role
            user.is_staff = role == Role.ADMIN  # admin can reach Django admin
            user.set_password(password)
            user.save()
            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{verb} {username} (role={role})"))
