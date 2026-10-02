from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from apps.builder.models import Form
from apps.processes.models import Process
from apps.reports.models import Visit
from apps.reports.services import record_visit


User = get_user_model()


@pytest.mark.django_db
def test_record_visit_for_form():
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="password123",
    )
    form = Form.objects.create(
        owner=user,
        title="Test Form",
        description="Test description",
        is_public=True,
    )

    request = RequestFactory().get(
        "/forms/test/",
        REMOTE_ADDR="127.0.0.1",
    )
    request.user = user

    visit = record_visit(request, form=form)

    assert visit.form == form
    assert visit.process is None
    assert visit.user == user
    assert visit.ip == "127.0.0.1"


@pytest.mark.django_db
def test_record_visit_for_process():
    user = User.objects.create_user(
        username="testuser2",
        email="test2@example.com",
        password="password123",
    )
    process = Process.objects.create(
        owner=user,
        title="Test Process",
        description="Test description",
        is_public=True,
    )

    request = RequestFactory().get(
        "/processes/test/",
        REMOTE_ADDR="127.0.0.2",
    )
    request.user = user

    visit = record_visit(request, process=process)

    assert visit.form is None
    assert visit.process == process
    assert visit.user == user
    assert visit.ip == "127.0.0.2"


@pytest.mark.django_db
def test_record_visit_for_anonymous_user():
    user = User.objects.create_user(
        username="owner",
        email="owner@example.com",
        password="password123",
    )
    form = Form.objects.create(
        owner=user,
        title="Anonymous Form",
        description="Test description",
        is_public=True,
    )

    request = RequestFactory().get(
        "/forms/test/",
        REMOTE_ADDR="127.0.0.3",
    )
    request.user = Mock()
    request.user.is_authenticated = False

    visit = record_visit(request, form=form)

    assert visit.user is None
    assert visit.ip == "127.0.0.3"


@pytest.mark.django_db
def test_record_visit_requires_exactly_one_target():
    user = User.objects.create_user(
        username="owner2",
        email="owner2@example.com",
        password="password123",
    )
    form = Form.objects.create(
        owner=user,
        title="Test Form",
        description="Test description",
        is_public=True,
    )

    request = RequestFactory().get(
        "/forms/test/",
        REMOTE_ADDR="127.0.0.4",
    )
    request.user = user

    with pytest.raises(ValidationError):
        record_visit(request)

    with pytest.raises(ValidationError):
        record_visit(request, form=form, process=Mock())