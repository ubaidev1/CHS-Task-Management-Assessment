"""
Seed one demo user per role for local development and demos.

Idempotent: safe to run repeatedly. Passwords come from the environment so no
credentials are hardcoded in the repo; the defaults below are obvious
development-only values and must be overridden in any real deployment.

Usage:
    python manage.py seed_users
"""

import os

from django.core.management.base import BaseCommand

from accounts.models import Role, User

# (username, email, role, env var for the password, dev-only default password)
SEED = [
    ("sophia", "sophia@example.com", Role.ADMIN, "DEMO_ADMIN_PASSWORD", "Admin@12345"),
    ("marcus", "marcus@example.com", Role.MANAGER, "DEMO_MANAGER_PASSWORD", "Manager@12345"),
    ("ethan", "ethan@example.com", Role.EMPLOYEE, "DEMO_EMPLOYEE_PASSWORD", "Employee@12345"),
]

# Earlier demo accounts whose usernames matched the role name; remove them so the
# user list isn't cluttered with role-named duplicates.
LEGACY_USERNAMES = ["admin", "manager", "employee"]


class Command(BaseCommand):
    help = "Create (or update) one demo user per role."

    def handle(self, *args, **options):
        removed = User.objects.filter(username__in=LEGACY_USERNAMES).delete()[0]
        if removed:
            self.stdout.write(self.style.WARNING(f"Removed {removed} legacy demo user(s)."))

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
