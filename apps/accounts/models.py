from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    email = models.EmailField("email address", unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Empty strings would break the unique constraint; store them as NULL.
        self.email = self.email or None
        self.phone = self.phone or None
        super().save(*args, **kwargs)


class OTPCode(models.Model):
    class Purpose(models.TextChoices):
        LOGIN = "login", "Login"
        REGISTER = "register", "Register"

    target = models.CharField(max_length=254, help_text="Phone number or email")
    purpose = models.CharField(max_length=10, choices=Purpose.choices)
    code_hash = models.CharField(max_length=128)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["target", "purpose", "-created_at"])]

    def __str__(self):
        return f"{self.target} ({self.purpose})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at