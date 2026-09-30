import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User

pytestmark = pytest.mark.django_db

ME_URL = "/api/v1/auth/me/"
LOGOUT_URL = "/api/v1/auth/logout/"


@pytest.fixture
def user():
    return User.objects.create_user(username="kimi", email="kimi@example.com")


def _jwt_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client, str(refresh)


def test_me_requires_authentication():
    assert APIClient().get(ME_URL).status_code == 401


def test_me_returns_current_user(user):
    client, _ = _jwt_client(user)
    response = client.get(ME_URL)
    assert response.status_code == 200
    assert response.json()["username"] == "kimi"


def test_patch_me_updates_name(user):
    client, _ = _jwt_client(user)
    response = client.patch(ME_URL, {"first_name": "Kimia"}, format="json")
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == "Kimia"


def test_patch_me_cannot_change_email(user):
    client, _ = _jwt_client(user)
    client.patch(ME_URL, {"email": "hacker@example.com"}, format="json")
    user.refresh_from_db()
    assert user.email == "kimi@example.com"


def test_patch_me_rejects_taken_username(user):
    User.objects.create_user(username="taken")
    client, _ = _jwt_client(user)
    response = client.patch(ME_URL, {"username": "taken"}, format="json")
    assert response.status_code == 400


def test_logout_blacklists_refresh_token(user):
    client, refresh = _jwt_client(user)
    assert client.post(LOGOUT_URL, {"refresh": refresh}, format="json").status_code == 204

    response = APIClient().post(
        "/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json"
    )
    assert response.status_code == 401


def test_logout_ends_session(user):
    client = APIClient()
    client.force_login(user)
    assert client.post(LOGOUT_URL).status_code == 204
    assert client.get(ME_URL).status_code == 401