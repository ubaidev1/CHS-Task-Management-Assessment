from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Task
from .stats import invalidate_stats


@receiver(post_save, sender=Task)
@receiver(post_delete, sender=Task)
def invalidate_dashboard_stats(sender, **kwargs):
    # Invalidate only AFTER the change is committed and visible, so a concurrent
    # dashboard request can never cache pre-commit state under the new generation.
    transaction.on_commit(invalidate_stats)
