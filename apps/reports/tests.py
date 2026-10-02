from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from apps.builder.models import Form, Question
from apps.processes.models import Process
from apps.reports.services import record_visit
from apps.reports.views import FormReportView
from apps.responses.models import Answer, Submission

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


@pytest.mark.django_db
def test_form_report_owner():
    user = User.objects.create_user(
        username="reportowner",
        email="reportowner@example.com",
        password="password123",
    )

    form = Form.objects.create(
        owner=user,
        title="Customer Survey",
        description="Test survey",
        is_public=True,
    )

    request = RequestFactory().get(
        f"/api/v1/forms/{form.id}/report/",
    )
    request.user = user

    response = FormReportView.as_view()(
        request,
        form_id=form.id,
    )

    assert response.status_code == 200
    assert response.data["form"]["id"] == form.id
    assert response.data["form"]["title"] == "Customer Survey"
    assert response.data["summary"]["visits"] == 0
    assert response.data["summary"]["submissions"] == 0


@pytest.mark.django_db
def test_form_report_number_question():
    user = User.objects.create_user(
        username="numberowner",
        email="numberowner@example.com",
        password="password123",
    )

    form = Form.objects.create(
        owner=user,
        title="Number Survey",
        description="Test survey",
        is_public=True,
    )

    question = Question.objects.create(
        form=form,
        type="number",
        text="Age",
        is_required=True,
        order=1,
    )

    submission1 = Submission.objects.create(form=form, user=user)
    submission2 = Submission.objects.create(form=form, user=user)

    Answer.objects.create(
        submission=submission1,
        question=question,
        number_value=20,
    )

    Answer.objects.create(
        submission=submission2,
        question=question,
        number_value=30,
    )

    request = RequestFactory().get(
        f"/api/v1/forms/{form.id}/report/",
    )
    request.user = user

    response = FormReportView.as_view()(
        request,
        form_id=form.id,
    )

    assert response.status_code == 200

    question_report = response.data["questions"][0]

    assert question_report["question_id"] == question.id
    assert question_report["type"] == "number"
    assert question_report["responses"] == 2

    assert float(question_report["statistics"]["average"]) == 25
    assert float(question_report["statistics"]["min"]) == 20
    assert float(question_report["statistics"]["max"]) == 30


@pytest.mark.django_db
def test_form_report_non_owner_forbidden():
    owner = User.objects.create_user(
        username="realowner",
        email="realowner@example.com",
        password="password123",
    )

    other_user = User.objects.create_user(
        username="otheruser",
        email="otheruser@example.com",
        password="password123",
    )

    form = Form.objects.create(
        owner=owner,
        title="Private Report",
        description="Test survey",
        is_public=True,
    )

    request = RequestFactory().get(
        f"/api/v1/forms/{form.id}/report/",
    )
    request.user = other_user

    response = FormReportView.as_view()(
        request,
        form_id=form.id,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_form_report_cache_is_invalidated_on_submission():
    user = User.objects.create_user(
        username="cacheowner",
        email="cacheowner@example.com",
        password="password123",
    )

    form = Form.objects.create(
        owner=user,
        title="Cached Report",
        description="Cache test",
        is_public=True,
    )

    cache_key = f"report:form:{form.id}"

    cached_data = {
        "form": {
            "id": form.id,
            "title": form.title,
        },
        "summary": {
            "visits": 0,
            "submissions": 0,
        },
        "questions": [],
    }

    cache.set(cache_key, cached_data, 300)

    assert cache.get(cache_key) == cached_data

    Submission.objects.create(
        form=form,
        user=user,
    )

    assert cache.get(cache_key) is None


@pytest.mark.django_db
def test_form_report_uses_cache():
    user = User.objects.create_user(
        username="cacheviewowner",
        email="cacheviewowner@example.com",
        password="password123",
    )

    form = Form.objects.create(
        owner=user,
        title="Original Title",
        description="Cache view test",
        is_public=True,
    )

    cached_report = {
        "form": {
            "id": form.id,
            "title": "Cached Title",
        },
        "summary": {
            "visits": 99,
            "submissions": 88,
        },
        "questions": [],
    }

    cache.set(
        f"report:form:{form.id}",
        cached_report,
        300,
    )

    request = RequestFactory().get(
        f"/api/v1/forms/{form.id}/report/",
    )
    request.user = user

    response = FormReportView.as_view()(
        request,
        form_id=form.id,
    )

    assert response.status_code == 200
    assert response.data == cached_report