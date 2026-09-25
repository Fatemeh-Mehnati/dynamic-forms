import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

PASSWORD = "strong-pass-123"


@pytest.fixture
def user():
    return get_user_model().objects.create_user(username="tester", password=PASSWORD)


def test_health_is_public():
    response = APIClient().get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_whoami_requires_authentication():
    response = APIClient().get("/api/v1/whoami/")
    assert response.status_code == 401
    assert response.json()["error"]["status"] == 401


def test_whoami_with_jwt(user):
    client = APIClient()
    token = client.post(
        "/api/v1/auth/token/",
        {"username": "tester", "password": PASSWORD},
        format="json",
    ).json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.get("/api/v1/whoami/")
    assert response.status_code == 200
    assert response.json()["username"] == "tester"
    assert response.json()["auth_method"] == "JWTAuthentication"


def test_whoami_with_session(user):
    client = APIClient()
    client.force_login(user)

    response = client.get("/api/v1/whoami/")
    assert response.status_code == 200
    assert response.json()["auth_method"] == "SessionAuthentication"


def test_error_format_on_bad_login():
    response = APIClient().post(
        "/api/v1/auth/token/",
        {"username": "nobody", "password": "wrong"},
        format="json",
    )
    assert response.status_code == 401
    assert set(response.json()["error"].keys()) == {"status", "code", "message", "details"}