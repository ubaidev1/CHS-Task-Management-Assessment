"""
Production settings.

Assumes HTTPS termination in front of the app. Cookies are Secure, DEBUG is
off, and security headers are tightened. Every secret and origin comes from the
environment with no insecure fallback.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Must be provided explicitly in production; no permissive default.
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# --- Secure cookies over HTTPS ---------------------------------------------
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# SameSite policy:
# - Same-site deployment (API and app on the same site): Lax is ideal.
# - Cross-site (different sites): the deployment must set SAMESITE=None, and
#   because the cookies are already Secure above, the None+Secure pairing the
#   brief requires is satisfied.
SESSION_COOKIE_SAMESITE = env("COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = env("COOKIE_SAMESITE", default="Lax")

# --- Transport security -----------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# --- Email ------------------------------------------------------------------
# Default to console so the project runs end-to-end without SMTP credentials;
# a real deployment overrides EMAIL_BACKEND/host via environment variables.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
