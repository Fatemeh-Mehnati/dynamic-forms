import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_responses_page_requires_login(client):
    response = client.get(reverse("web:responses"))

    assert response.status_code == 302
    assert "/login" in response.url or "otp" in response.url


@pytest.mark.django_db
def test_authenticated_user_can_open_responses_page(client, django_user_model):
    user = django_user_model.objects.create_user(
        username="responses_user",
        password="test-password-123",
    )
    client.force_login(user)

    response = client.get(reverse("web:responses"))

    assert response.status_code == 200
    assert "responses-page" in response.content.decode()
    assert "js/web-responses.js" in response.content.decode()
