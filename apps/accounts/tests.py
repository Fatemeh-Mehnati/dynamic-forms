from django.test import TestCase

# Create your tests here.
from datetime import timedelta

import pytest
from django.utils import timezone

from .models import OTPCode, User

pytestmark = pytest.mark.django_db


def test_users_without_email_or_phone_do_not_collide():
    User.objects.create_user(username="a")
    User.objects.create_user(username="b")
    assert User.objects.filter(email__isnull=True, phone__isnull=True).count() == 2


def test_email_must_be_unique():
    from django.db import IntegrityError

    User.objects.create_user(username="a", email="x@example.com")
    with pytest.raises(IntegrityError):
        User.objects.create_user(username="b", email="x@example.com")


def test_otp_expiry():
    otp = OTPCode.objects.create(
        target="09120000000",
        purpose=OTPCode.Purpose.LOGIN,
        code_hash="x",
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    assert otp.is_expired