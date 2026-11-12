"""Tests for the custom User model and the authentication endpoints."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

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


class AuthEndpointTests(APITestCase):
    def setUp(self):
        self.password = "pw-123456!"
        self.user = User.objects.create_user(
            username="alice", email="alice@example.com", password=self.password
        )
        self.login_url = reverse("login")
        self.logout_url = reverse("logout")
        self.me_url = reverse("me")
        self.session_url = reverse("session")

    # --- login / logout / me --------------------------------------------
    def test_valid_login_establishes_session(self):
        resp = self.client.post(
            self.login_url, {"username": "alice", "password": self.password}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["username"], "alice")
        # Session is usable: a protected endpoint now succeeds.
        self.assertEqual(self.client.get(self.me_url).status_code, 200)

    def test_invalid_login_is_rejected(self):
        resp = self.client.post(
            self.login_url, {"username": "alice", "password": "wrong"}
        )
        self.assertEqual(resp.status_code, 401)

    def test_me_requires_authentication(self):
        self.assertEqual(self.client.get(self.me_url).status_code, 403)

    def test_expired_session_is_rejected(self):
        self.client.login(username="alice", password=self.password)
        # Force the session to be already expired, then confirm access is denied.
        session = self.client.session
        session.set_expiry(-1)
        session.save()
        self.assertEqual(self.client.get(self.me_url).status_code, 403)

    def test_logout_invalidates_session(self):
        self.client.login(username="alice", password=self.password)
        self.assertEqual(self.client.post(self.logout_url).status_code, 204)
        # After logout the session no longer grants access.
        self.assertEqual(self.client.get(self.me_url).status_code, 403)

    # --- session / CSRF --------------------------------------------------
    def test_session_endpoint_reports_state_and_sets_csrf_cookie(self):
        resp = self.client.get(self.session_url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["authenticated"])
        self.assertIn("csrftoken", resp.cookies)

    def test_login_without_csrf_token_is_rejected(self):
        csrf_client = APIClient(enforce_csrf_checks=True)
        resp = csrf_client.post(
            self.login_url, {"username": "alice", "password": self.password}
        )
        self.assertEqual(resp.status_code, 403)

    def test_login_with_csrf_token_succeeds(self):
        csrf_client = APIClient(enforce_csrf_checks=True)
        token = csrf_client.get(self.session_url).cookies["csrftoken"].value
        resp = csrf_client.post(
            self.login_url,
            {"username": "alice", "password": self.password},
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(resp.status_code, 200)

    def test_authenticated_write_without_csrf_is_rejected(self):
        """DRF SessionAuthentication enforces CSRF on authenticated writes (logout)."""
        csrf_client = APIClient(enforce_csrf_checks=True)
        token = csrf_client.get(self.session_url).cookies["csrftoken"].value
        csrf_client.post(
            self.login_url,
            {"username": "alice", "password": self.password},
            HTTP_X_CSRFTOKEN=token,
        )
        # Now logout WITHOUT a CSRF token must be rejected.
        self.assertEqual(csrf_client.post(self.logout_url).status_code, 403)
