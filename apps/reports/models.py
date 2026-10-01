from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Visit(models.Model):
    form = models.ForeignKey(
        "builder.Form",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="visits",
    )
    process = models.ForeignKey(
        "processes.Process",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="visits",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visits",
    )
    ip = models.GenericIPAddressField()
    visited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(form__isnull=False, process__isnull=True)
                    | Q(form__isnull=True, process__isnull=False)
                ),
                name="visit_exactly_one_target",
            ),
        ]
        ordering = ["-visited_at"]

    def clean(self):
        if (self.form_id is None) == (self.process_id is None):
            raise ValidationError(
                "A visit must be related to exactly one form or process."
            )

    def __str__(self):
        if self.form_id:
            return f"Visit for form {self.form_id}"
        return f"Visit for process {self.process_id}"


class ReportSchedule(models.Model):
    FREQUENCY_WEEKLY = "weekly"
    FREQUENCY_MONTHLY = "monthly"

    FREQUENCY_CHOICES = [
        (FREQUENCY_WEEKLY, "Weekly"),
        (FREQUENCY_MONTHLY, "Monthly"),
    ]

    CHANNEL_EMAIL = "email"
    CHANNEL_API = "api"

    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, "Email"),
        (CHANNEL_API, "API"),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="report_schedules",
    )
    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
    )
    channel = models.CharField(
        max_length=5,
        choices=CHANNEL_CHOICES,
    )
    target = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.created_by_id and not self.created_by.is_staff:
            raise ValidationError(
                "Only staff users can create report schedules."
            )

    def __str__(self):
        return f"{self.frequency} report via {self.channel}"