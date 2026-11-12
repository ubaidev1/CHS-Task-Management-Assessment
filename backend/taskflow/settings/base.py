"""
Base settings shared by every environment.

Environment-specific files (dev.py, prod.py) import everything from here with
``from .base import *`` and then override only what differs. All secrets and
deployment-specific values are read from the environment (via django-environ),
so this file never contains credentials and is safe to commit.
"""

from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# settings/base.py -> settings/ -> taskflow/ -> backend/  == BASE_DIR
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Environment loading
# ---------------------------------------------------------------------------
# django-environ maps a .env file (and real environment variables) onto typed
# settings. Real process environment variables always win over the .env file,
# which is what we want in Docker/CI where config is injected as env vars.
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
)

# Load backend/.env if present. In containers we usually pass env vars directly,
# so a missing .env is not an error.
environ.Env.read_env(BASE_DIR / ".env")

# SECURITY: no default — a missing SECRET_KEY must fail loudly, never fall back
# to a predictable value.
SECRET_KEY = env("DJANGO_SECRET_KEY")

DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
]

LOCAL_APPS = [
    "accounts",
    "tasks",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
# CorsMiddleware must sit as early as possible and, per django-cors-headers
# docs, before CommonMiddleware so CORS headers are attached even on responses
# produced by other middleware.
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "taskflow.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "taskflow.wsgi.application"
ASGI_APPLICATION = "taskflow.asgi.application"

# ---------------------------------------------------------------------------
# Database (PostgreSQL via DATABASE_URL)
# ---------------------------------------------------------------------------
# A single DATABASE_URL keeps connection config in one env var and works
# identically in Docker Compose, CI and locally.
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

# ---------------------------------------------------------------------------
# Custom user model
# ---------------------------------------------------------------------------
# Set BEFORE the first migration. Swapping the user model later is a painful,
# migration-breaking change, so we commit to a custom model from day one even
# though roles themselves are modelled with Django Groups.
AUTH_USER_MODEL = "accounts.User"

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
# - SessionAuthentication only: the brief mandates session-based auth, so we do
#   NOT enable TokenAuthentication. SessionAuthentication also enforces CSRF on
#   unsafe methods, which is exactly the protection we want.
# - IsAuthenticated by default: every endpoint is private unless it explicitly
#   opts out (fail-closed). Login is the one documented exception.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Custom: returns 401 for unauthenticated (vs DRF's default 403), so the
        # frontend can distinguish "not logged in" from "forbidden".
        "accounts.authentication.SessionAuthentication401",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# ---------------------------------------------------------------------------
# Cache (Redis via django-redis)
# ---------------------------------------------------------------------------
# django-redis gives us Django's cache API over Redis. IGNORE_EXCEPTIONS makes
# a Redis outage degrade gracefully (cache calls return None/miss instead of
# raising) so the dashboard can fall back to a permission-scoped DB query
# rather than 500. This directly supports the "Redis unavailable" requirement.
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_CACHE_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "taskflow",
    }
}
DJANGO_REDIS_IGNORE_EXCEPTIONS = True

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
# Redis is the broker (and result backend). task_always_eager stays False here;
# tests flip it on so the full produce->consume path runs inline.
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://127.0.0.1:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# ---------------------------------------------------------------------------
# Sessions & CSRF (security-sensitive; environments tighten these further)
# ---------------------------------------------------------------------------
# Session cookie is HttpOnly so JavaScript can never read it (mitigates XSS
# session theft). The CSRF cookie is deliberately NOT HttpOnly because Angular
# must read it to echo it back in the X-CSRFToken header (Django's double-submit
# CSRF flow). SameSite/Secure are set per-environment.
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"  # Django's expected X-CSRFToken header

# Sessions expire after inactivity and when the browser closes, so an abandoned
# browser does not keep a usable session indefinitely.
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=60 * 60 * 8)  # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True  # sliding expiry: activity refreshes the window

# ---------------------------------------------------------------------------
# CORS (explicit origins only; never wildcard with credentials)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True  # cookies must cross origins for session auth
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

# ---------------------------------------------------------------------------
# Email (overridden per environment; console backend in dev)
# ---------------------------------------------------------------------------
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@taskflow.local")

# ---------------------------------------------------------------------------
# Logging (useful, structured-enough logging to stdout)
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "apps": {  # our application logs
            "handlers": ["console"],
            "level": env("APP_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
}
