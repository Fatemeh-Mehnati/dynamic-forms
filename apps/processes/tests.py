import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.builder.models import Form
from apps.processes.models import Process, ProcessRun, ProcessStep

User = get_user_model()


@pytest.fixture
def owner():
    return User.objects.create_user(username="owner", password="pass-12345")


@pytest.fixture
def process(owner):
    return Process.objects.create(owner=owner, title="P")


@pytest.fixture
def forms(owner):
    return [Form.objects.create(owner=owner, title=f"F{i}", description="") for i in range(2)]


@pytest.mark.django_db
def test_process_slug_is_generated_and_unique(owner):
    p1 = Process.objects.create(owner=owner, title="A")
    p2 = Process.objects.create(owner=owner, title="B")
    assert p1.slug and p2.slug and p1.slug != p2.slug
    assert p1.mode == Process.MODE_LINEAR


@pytest.mark.django_db
def test_process_password(process):
    assert process.check_password("x") is False  # no password set
    process.set_password("secret")
    process.save()
    assert process.password_hash != "secret"
    assert process.check_password("secret") is True
    assert process.check_password("wrong") is False


@pytest.mark.django_db(transaction=True)
def test_step_order_is_unique_per_process(process, forms):
    with pytest.raises(IntegrityError), transaction.atomic():
        ProcessStep.objects.create(process=process, form=forms[0], order=1)
        ProcessStep.objects.create(process=process, form=forms[1], order=1)


@pytest.mark.django_db
def test_step_order_can_repeat_across_processes(owner, process, forms):
    other = Process.objects.create(owner=owner, title="Other")
    ProcessStep.objects.create(process=process, form=forms[0], order=1)
    ProcessStep.objects.create(process=other, form=forms[0], order=1)
    assert ProcessStep.objects.count() == 2


@pytest.mark.django_db
def test_run_token_is_generated_and_unique(process):
    r1 = ProcessRun.objects.create(process=process)
    r2 = ProcessRun.objects.create(process=process)
    assert r1.respondent_token and r1.respondent_token != r2.respondent_token
    assert r1.user is None
    assert r1.completed_at is None
