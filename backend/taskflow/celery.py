import os

from celery import Celery

# Use the dev settings module by default; override in the environment for prod.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "taskflow.settings.dev")

app = Celery("taskflow")

# Read CELERY_* keys from Django settings (namespace="CELERY").
app.config_from_object("django.conf:settings", namespace="CELERY")

# Discover tasks.py modules in every installed app.
app.autodiscover_tasks()
