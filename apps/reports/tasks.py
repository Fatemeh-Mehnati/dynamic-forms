from datetime import timedelta

import requests
from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone

from apps.builder.models import Form
from apps.processes.models import Process

from .models import ReportSchedule


@shared_task
def send_periodic_reports():
    now = timezone.now()

    schedules = ReportSchedule.objects.filter(is_active=True)

    for schedule in schedules:
        if not _is_due(schedule, now):
            continue

        report = _build_report()

        if schedule.channel == ReportSchedule.CHANNEL_EMAIL:
            _send_email(schedule, report)
        elif schedule.channel == ReportSchedule.CHANNEL_API:
            _send_api(schedule, report)

        schedule.last_sent_at = now
        schedule.save(update_fields=["last_sent_at"])


def _is_due(schedule, now):
    if schedule.last_sent_at is None:
        return True

    if schedule.frequency == ReportSchedule.FREQUENCY_WEEKLY:
        return now - schedule.last_sent_at >= timedelta(days=7)

    if schedule.frequency == ReportSchedule.FREQUENCY_MONTHLY:
        return now - schedule.last_sent_at >= timedelta(days=30)

    return False


def _build_report():
    return {
        "forms": Form.objects.count(),
        "processes": Process.objects.count(),
    }


def _send_email(schedule, report):
    send_mail(
        subject="Dynamic Forms Periodic Report",
        message=(
            f"Forms: {report['forms']}\n"
            f"Processes: {report['processes']}"
        ),
        from_email=None,
        recipient_list=[schedule.target],
    )


def _send_api(schedule, report):
    response = requests.post(
        schedule.target,
        json=report,
        timeout=10,
    )
    response.raise_for_status()