"""Celery tasks for asynchronous assignment notifications."""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import AssignmentEvent

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_assignment_notification(self, event_id):
    """Email the assignee for one AssignmentEvent, exactly once.

    Idempotency: the row is locked (`select_for_update`) and skipped if already
    marked SENT, so a Celery re-delivery or manual retry of the same event never
    sends a duplicate. Transient failures (e.g. the email backend) are retried.
    """
    try:
        with transaction.atomic():
            event = (
                AssignmentEvent.objects.select_for_update()
                .select_related("task", "assigned_to")
                .get(id=event_id)
            )

            if event.status == AssignmentEvent.Status.SENT:
                logger.info("Assignment event %s already sent; skipping.", event_id)
                return

            assignee = event.assigned_to
            send_mail(
                subject=f"New task assigned: {event.task.title}",
                message=(
                    f"Hi {assignee.username},\n\n"
                    f"The task \"{event.task.title}\" has been assigned to you."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[assignee.email],
                fail_silently=False,
            )

            event.status = AssignmentEvent.Status.SENT
            event.sent_at = timezone.now()
            event.save(update_fields=["status", "sent_at"])
            logger.info(
                "Sent assignment notification for event %s to %s", event_id, assignee.email
            )
    except AssignmentEvent.DoesNotExist:
        # The event was deleted before processing; nothing to do. Not retryable.
        logger.warning("Assignment event %s not found; skipping.", event_id)
        return
    except Exception as exc:
        logger.error("Error sending assignment notification %s: %s", event_id, exc)
        raise self.retry(exc=exc)
