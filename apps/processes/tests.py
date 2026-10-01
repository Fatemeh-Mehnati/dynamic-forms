import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from apps.builder.models import Form
from apps.processes.models import Process, ProcessRun, ProcessStep

User = get_user_model()


@pytest.fixture
def owner():
    return User.objects.create_user(username="owner", password="pass-12345")


@pytest.fixture
def other_user():
    return User.objects.create_user(username="other", password="pass-12345")


@pytest.fixture
def process(owner):
    return Process.objects.create(owner=owner, title="P", is_public=True)


@pytest.fixture
def forms(owner):
    return [Form.objects.create(owner=owner, title=f"F{i}", description="") for i in range(3)]


def owner_client(user):
    client = APIClient()
    client.force_login(user)
    return client


# -- model tests --


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


# ---- CRUD ----


@pytest.mark.django_db
def test_create_public_process(owner):
    response = owner_client(owner).post(
        "/api/v1/processes/", {"title": "Onboarding", "is_public": True}, format="json"
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Onboarding"
    assert body["mode"] == "linear"
    assert "password" not in body
    assert Process.objects.get(id=body["id"]).owner == owner


@pytest.mark.django_db
def test_create_private_process_requires_password(owner):
    response = owner_client(owner).post(
        "/api/v1/processes/", {"title": "Secret", "is_public": False}, format="json"
    )
    assert response.status_code == 400
    assert "password" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_create_private_process_with_password(owner):
    response = owner_client(owner).post(
        "/api/v1/processes/",
        {"title": "Secret", "is_public": False, "password": "abc123"},
        format="json",
    )
    assert response.status_code == 201
    process = Process.objects.get(id=response.json()["id"])
    assert process.check_password("abc123")


@pytest.mark.django_db
def test_list_only_shows_own_processes(owner, other_user):
    Process.objects.create(owner=owner, title="Mine", is_public=True)
    Process.objects.create(owner=other_user, title="Theirs", is_public=True)
    response = owner_client(owner).get("/api/v1/processes/")
    titles = [p["title"] for p in response.json()["results"]]
    assert titles == ["Mine"]


@pytest.mark.django_db
def test_list_filter_by_search(owner):
    Process.objects.create(owner=owner, title="Survey A", is_public=True)
    Process.objects.create(owner=owner, title="Other", is_public=True)
    response = owner_client(owner).get("/api/v1/processes/?search=survey")
    titles = [p["title"] for p in response.json()["results"]]
    assert titles == ["Survey A"]


@pytest.mark.django_db
def test_retrieve_process_includes_steps(owner, process, forms):
    ProcessStep.objects.create(process=process, form=forms[0], order=1)
    response = owner_client(owner).get(f"/api/v1/processes/{process.id}/")
    assert response.status_code == 200
    assert len(response.json()["steps"]) == 1


@pytest.mark.django_db
def test_other_user_cannot_see_process(process, other_user):
    response = owner_client(other_user).get(f"/api/v1/processes/{process.id}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_patch_process_title(owner, process):
    response = owner_client(owner).patch(
        f"/api/v1/processes/{process.id}/", {"title": "New title"}, format="json"
    )
    assert response.status_code == 200
    process.refresh_from_db()
    assert process.title == "New title"


@pytest.mark.django_db
def test_patch_cannot_set_category_of_another_user(owner, other_user, process):
    from apps.builder.models import Category

    foreign_category = Category.objects.create(owner=other_user, name="Theirs")
    response = owner_client(owner).patch(
        f"/api/v1/processes/{process.id}/",
        {"category": foreign_category.id},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_delete_process(owner, process):
    response = owner_client(owner).delete(f"/api/v1/processes/{process.id}/")
    assert response.status_code == 204
    assert not Process.objects.filter(id=process.id).exists()


@pytest.mark.django_db
def test_other_user_cannot_delete_process(process, other_user):
    response = owner_client(other_user).delete(f"/api/v1/processes/{process.id}/")
    assert response.status_code == 404
    assert Process.objects.filter(id=process.id).exists()


@pytest.mark.django_db
def test_anonymous_cannot_access_processes(process):
    assert APIClient().get("/api/v1/processes/").status_code in (401, 403)
    assert APIClient().get(f"/api/v1/processes/{process.id}/").status_code in (401, 403)


# -------- C5: steps ---------


@pytest.mark.django_db
def test_add_step(owner, process, forms):
    response = owner_client(owner).post(
        f"/api/v1/processes/{process.id}/steps/", {"form": forms[0].id}, format="json"
    )
    assert response.status_code == 201
    assert response.json()["order"] == 1
    response = owner_client(owner).post(
        f"/api/v1/processes/{process.id}/steps/", {"form": forms[1].id}, format="json"
    )
    assert response.json()["order"] == 2


@pytest.mark.django_db
def test_cannot_add_step_with_foreign_form(owner, process, other_user):
    foreign_form = Form.objects.create(owner=other_user, title="X", description="")
    response = owner_client(owner).post(
        f"/api/v1/processes/{process.id}/steps/", {"form": foreign_form.id}, format="json"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_cannot_add_step_to_foreign_process(process, other_user, forms):
    response = owner_client(other_user).post(
        f"/api/v1/processes/{process.id}/steps/", {"form": forms[0].id}, format="json"
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_step(owner, process, forms):
    step = ProcessStep.objects.create(process=process, form=forms[0], order=1)
    response = owner_client(owner).delete(
        f"/api/v1/processes/{process.id}/steps/{step.id}/"
    )
    assert response.status_code == 204
    assert not ProcessStep.objects.filter(id=step.id).exists()


@pytest.mark.django_db
def test_other_user_cannot_delete_step(process, other_user, forms):
    step = ProcessStep.objects.create(process=process, form=forms[0], order=1)
    response = owner_client(other_user).delete(
        f"/api/v1/processes/{process.id}/steps/{step.id}/"
    )
    assert response.status_code == 404
    assert ProcessStep.objects.filter(id=step.id).exists()


@pytest.mark.django_db
def test_reorder_steps(owner, process, forms):
    s1 = ProcessStep.objects.create(process=process, form=forms[0], order=1)
    s2 = ProcessStep.objects.create(process=process, form=forms[1], order=2)
    s3 = ProcessStep.objects.create(process=process, form=forms[2], order=3)

    response = owner_client(owner).post(
        f"/api/v1/processes/{process.id}/steps/reorder/",
        {"order": [s3.id, s1.id, s2.id]},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [s3.id, s1.id, s2.id]
    assert [item["order"] for item in body] == [1, 2, 3]

    s1.refresh_from_db()
    s2.refresh_from_db()
    s3.refresh_from_db()
    assert (s3.order, s1.order, s2.order) == (1, 2, 3)


@pytest.mark.django_db
def test_reorder_rejects_wrong_step_set(owner, process, forms):
    s1 = ProcessStep.objects.create(process=process, form=forms[0], order=1)
    response = owner_client(owner).post(
        f"/api/v1/processes/{process.id}/steps/reorder/",
        {"order": [s1.id, 9999]},
        format="json",
    )
    assert response.status_code == 400
