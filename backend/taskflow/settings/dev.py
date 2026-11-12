"""
Development settings.

Optimised for local work over plain HTTP: cookies are not marked Secure (so
they work without TLS), email is printed to the console, and CORS/CSRF default
to the local Angular dev server. Never use this module in production.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True

ALLOWED_HOSTS = env(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "0.0.0.0"],
)

# --- Cookies over HTTP -----------------------------------------------------
# Secure=False so cookies are sent over http://localhost during development.
# SameSite=Lax is correct for a same-site dev setup and still mitigates CSRF.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# --- CORS / CSRF for the Angular dev server --------------------------------
CORS_ALLOWED_ORIGINS = env(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:4200", "http://127.0.0.1:4200"],
)
CSRF_TRUSTED_ORIGINS = env(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:4200", "http://127.0.0.1:4200"],
)

# --- Email -----------------------------------------------------------------
# Console backend: the brief explicitly accepts this to demonstrate that the
# Celery task actually runs and "sends" the notification.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Browsable API is handy during development only.
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
