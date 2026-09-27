import uuid

from django.db import models
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Category(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_category_owner_name"
            ),
        ]
    def __str__(self):
        return self.name

class Form(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="forms",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="forms",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    slug = models.SlugField(max_length=32, unique=True, editable=False,)
    is_public = models.BooleanField(default=False)
    password_hash = models.CharField(
        max_length=128,
        null=True,
        blank=True,
    )
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


class Question(models.Model)
    TYPE_TEXT = "text"
    TYPE_SELECT = "select"
    TYPE_CHECKBOX = "checkbox"
    TYPE_NUMBER = "number"

    TYPE_CHOICES = [
        (TYPE_TEXT, "Text"),
        (TYPE_SELECT, "Select"),
        (TYPE_CHECKBOX, "Checkbox"),
        (TYPE_NUMBER, "Number"),
    ]

    form = models.ForeignKey(
        Form,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
    )
    text = models.CharField(max_length=255)
    is_required = models.BooleanField(default=False)
    order = models.IntegerField()
    config = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    def __str__(self):
        return self.text

    
