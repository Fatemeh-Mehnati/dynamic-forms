import secrets
import uuid

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models


def generate_respondent_token():
    """Unguessable token that identifies an anonymous respondent of a run."""
    return secrets.token_urlsafe(32)


class Process(models.Model):
    MODE_LINEAR = "linear"
    MODE_FREE = "free"
    MODE_CHOICES = [
        (MODE_LINEAR, "Linear"),
        (MODE_FREE, "Free"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="processes",
    )
    category = models.ForeignKey(
        "builder.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processes",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=32, unique=True, editable=False)
    mode = models.CharField(
        max_length=10,
        choices=MODE_CHOICES,
        default=MODE_LINEAR,
    )
    is_public = models.BooleanField(default=False)
    password_hash = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuid.uuid4().hex[:32]
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        if not self.password_hash:
            return False
        return check_password(raw_password, self.password_hash)

    def __str__(self):
        return self.title


class ProcessStep(models.Model):
    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    form = models.ForeignKey(
        "builder.Form",
        on_delete=models.CASCADE,
        related_name="process_steps",
    )
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]
        constraints = [
            # Deferrable: reordering steps inside one transaction must be
            # possible (two steps may briefly share the same order).
            models.UniqueConstraint(
                fields=["process", "order"],
                name="unique_step_process_order",
                deferrable=models.Deferrable.DEFERRED,
            ),
        ]

    def __str__(self):
        return f"{self.process_id}:{self.order}"


class ProcessRun(models.Model):
    process = models.ForeignKey(
        Process,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="process_runs",
    )
    respondent_token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_respondent_token,
        editable=False,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Run {self.pk} of process {self.process_id}"
