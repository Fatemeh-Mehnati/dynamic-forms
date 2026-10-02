from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.responses.models import Submission

from .cache import invalidate_process_report, invalidate_form_report


@receiver(post_save, sender=Submission)
def invalidate_report_cache(sender, instance, **kwargs):
    """Invalidate report caches when a new submission is created."""
    if not kwargs.get("created"):
        return

    invalidate_form_report(instance.form_id)

    if instance.process_run_id:
        process_id = instance.process_run.process_id
        invalidate_process_report(process_id)
