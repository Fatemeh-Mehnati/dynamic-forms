from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory

from apps.builder.models import Form, Question
from apps.processes.models import Process , ProcessRun , ProcessStep
from apps.reports.models import Visit
from apps.reports.services import record_visit
from apps.reports.views import FormReportView, ProcessReportView
from apps.responses.models import Answer, Submission

from django.utils import timezone

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
def test_process_report_owner():
    user = User.objects.create_user(
        username="processowner",
        email="processowner@example.com",
        password="password123",
    )

    process = Process.objects.create(
        owner=user,
        title="Onboarding",
        description="Test process",
        is_public=True,
    )

    request = RequestFactory().get(
        f"/api/v1/processes/{process.id}/report/",
    )
    request.user = user

    response = ProcessReportView.as_view()(
        request,
        process_id=process.id,
    )

    assert response.status_code == 200
    assert response.data["process"]["id"] == process.id
    assert response.data["process"]["title"] == "Onboarding"
    assert response.data["summary"]["visits"] == 0
    assert response.data["summary"]["runs_started"] == 0
    assert response.data["summary"]["runs_completed"] == 0
    assert response.data["steps"] == []


@pytest.mark.django_db
def test_process_report_runs_and_visits():
    user = User.objects.create_user(
        username="runowner",
        email="runowner@example.com",
        password="password123",
    )

    process = Process.objects.create(
        owner=user,
        title="Process Report",
        is_public=True,
    )

    form = Form.objects.create(
        owner=user,
        title="Step Form",
        description="Test form",
        is_public=True,
    )

    ProcessStep.objects.create(
        process=process,
        form=form,
        order=1,
    )

    Visit.objects.create(
        process=process,
        ip="127.0.0.1",
    )

    Visit.objects.create(
        process=process,
        ip="127.0.0.2",
    )

    ProcessRun.objects.create(process=process)
    ProcessRun.objects.create(process=process)

    completed_run = ProcessRun.objects.create(process=process)
    completed_run.completed_at = timezone.now()
    completed_run.save(update_fields=["completed_at"])

    request = RequestFactory().get(
        f"/api/v1/processes/{process.id}/report/",
    )
    request.user = user

    response = ProcessReportView.as_view()(
        request,
        process_id=process.id,
    )

    assert response.status_code == 200
    assert response.data["summary"]["visits"] == 2
    assert response.data["summary"]["runs_started"] == 3
    assert response.data["summary"]["runs_completed"] == 1


@pytest.mark.django_db
def test_process_report_step_completion():
    user = User.objects.create_user(
        username="stepowner",
        email="stepowner@example.com",
        password="password123",
    )

    process = Process.objects.create(
        owner=user,
        title="Step Report",
        is_public=True,
    )

    form = Form.objects.create(
        owner=user,
        title="Step Form",
        description="Test form",
        is_public=True,
    )

    step = ProcessStep.objects.create(
        process=process,
        form=form,
        order=1,
    )

    run1 = ProcessRun.objects.create(process=process)
    run2 = ProcessRun.objects.create(process=process)
    ProcessRun.objects.create(process=process)
    ProcessRun.objects.create(process=process)

    Submission.objects.create(
        form=form,
        user=user,
        process_run=run1,
    )

    Submission.objects.create(
        form=form,
        user=user,
        process_run=run2,
    )

    request = RequestFactory().get(
        f"/api/v1/processes/{process.id}/report/",
    )
    request.user = user

    response = ProcessReportView.as_view()(
        request,
        process_id=process.id,
    )

    assert response.status_code == 200

    step_report = response.data["steps"][0]

    assert step_report["step_id"] == step.id
    assert step_report["form_id"] == form.id
    assert step_report["order"] == 1
    assert step_report["submissions"] == 2
    assert step_report["completion_percentage"] == 50.0


@pytest.mark.django_db
def test_process_report_non_owner_forbidden():
    owner = User.objects.create_user(
        username="processrealowner",
        email="processrealowner@example.com",
        password="password123",
    )

    other_user = User.objects.create_user(
        username="processotheruser",
        email="processotheruser@example.com",
        password="password123",
    )

    process = Process.objects.create(
        owner=owner,
        title="Private Process Report",
        is_public=True,
    )

    request = RequestFactory().get(
        f"/api/v1/processes/{process.id}/report/",
    )
    request.user = other_user

    response = ProcessReportView.as_view()(
        request,
        process_id=process.id,
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_process_report_zero_runs_has_zero_completion():
    user = User.objects.create_user(
        username="zeroruns",
        email="zeroruns@example.com",
        password="password123",
    )

    process = Process.objects.create(
        owner=user,
        title="Zero Runs",
        is_public=True,
    )

    form = Form.objects.create(
        owner=user,
        title="Empty Step",
        description="Test form",
        is_public=True,
    )

    step = ProcessStep.objects.create(
        process=process,
        form=form,
        order=1,
    )

    request = RequestFactory().get(
        f"/api/v1/processes/{process.id}/report/",
    )
    request.user = user

    response = ProcessReportView.as_view()(
        request,
        process_id=process.id,
    )

    assert response.status_code == 200

    step_report = response.data["steps"][0]

    assert step_report["step_id"] == step.id
    assert step_report["submissions"] == 0
    assert step_report["completion_percentage"] == 0