"""Shared assignment-notification helper used by both task creation and the
explicit assign endpoint, so the notification path (event + idempotent Celery
job, enqueued only after commit) lives in exactly one place."""

from django.db import transaction

from .models import AssignmentEvent
from .tasks import send_assignment_notification


def queue_assignment_notification(task, assigned_to, assigned_by):
    """Record an assignment event and enqueue its notification after commit.

    Must be called inside a transaction (the caller's atomic block), so the
    event and the task change commit together and the Celery job is published
    only once the row is durable.
    """
    event = AssignmentEvent.objects.create(
        task=task, assigned_to=assigned_to, assigned_by=assigned_by
    )
    transaction.on_commit(lambda: send_assignment_notification.delay(str(event.id)))
    return event
