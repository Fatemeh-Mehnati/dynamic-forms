import re
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from .models import OTPCode, User

pytestmark = pytest.mark.django_db

REQUEST_URL = "/api/v1/auth/otp/request/"
VERIFY_URL = "/api/v1/auth/otp/verify/"


def _code_from(mailoutbox):
    return re.search(r"\b(\d{6})\b", mailoutbox[-1].body).group(1)


def _request(client, target, purpose):
    return client.post(REQUEST_URL, {"target": target, "purpose": purpose}, format="json")


def _verify(client, target, purpose, code, **extra):
    data = {"target": target, "purpose": purpose, "code": code, **extra}
    return client.post(VERIFY_URL, data, format="json")


def test_register_flow(mailoutbox):
    client = APIClient()
    assert _request(client, "new@example.com", "register").status_code == 200

    response = _verify(
        client, "new@example.com", "register", _code_from(mailoutbox), username="newbie"
    )
    assert response.status_code == 200
    assert "access" in response.json()
    assert response.json()["user"]["email"] == "new@example.com"
    assert User.objects.filter(username="newbie").exists()


def test_login_flow_for_existing_user(mailoutbox):
    User.objects.create_user(username="old", email="old@example.com")
    client = APIClient()
    _request(client, "old@example.com", "login")

    response = _verify(client, "old@example.com", "login", _code_from(mailoutbox))
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "old"


def test_login_with_unknown_target_is_rejected():
    response = _request(APIClient(), "ghost@example.com", "login")
    assert response.status_code == 400


def test_register_requires_username(mailoutbox):
    client = APIClient()
    _request(client, "new@example.com", "register")
    response = _verify(client, "new@example.com", "register", _code_from(mailoutbox))
    assert response.status_code == 400


def test_wrong_code_increments_attempts(mailoutbox):
    User.objects.create_user(username="u", email="u@example.com")
    client = APIClient()
    _request(client, "u@example.com", "login")
    real = _code_from(mailoutbox)
    wrong = "000000" if real != "000000" else "111111"

    assert _verify(client, "u@example.com", "login", wrong).status_code == 400
    assert OTPCode.objects.get(target="u@example.com").attempts == 1


def test_expired_code_is_rejected(mailoutbox):
    User.objects.create_user(username="u", email="u@example.com")
    client = APIClient()
    _request(client, "u@example.com", "login")
    OTPCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

    assert _verify(client, "u@example.com", "login", _code_from(mailoutbox)).status_code == 400


def test_code_cannot_be_reused(mailoutbox):
    User.objects.create_user(username="u", email="u@example.com")
    client = APIClient()
    _request(client, "u@example.com", "login")
    code = _code_from(mailoutbox)

    assert _verify(client, "u@example.com", "login", code).status_code == 200
    assert _verify(client, "u@example.com", "login", code).status_code == 400


def test_resend_cooldown():
    User.objects.create_user(username="u", email="u@example.com")
    client = APIClient()
    assert _request(client, "u@example.com", "login").status_code == 200
    assert _request(client, "u@example.com", "login").status_code == 429