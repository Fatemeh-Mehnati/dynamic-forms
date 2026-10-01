from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from apps.builder.models import Choice, Form, Question
from apps.responses.models import Answer, AnswerChoice, Submission

User = get_user_model()




@pytest.fixture
def owner():
    return User.objects.create_user(username="owner", password="pass-12345")


@pytest.fixture
def form(owner):
    return Form.objects.create(owner=owner, title="Survey", description="", is_public=True)


def make_question(form, type, order, text="Q", required=False, config=None):
    return Question.objects.create(
        form=form, type=type, text=text, order=order,
        is_required=required, config=config or {},
    )


def make_choice(question, order, label="c"):
    return Choice.objects.create(question=question, label=label, order=order)


@pytest.fixture
def text_q(form):
    return make_question(form, Question.TYPE_TEXT, 1, "Name", config={"max_length": 5})


@pytest.fixture
def number_q(form):
    return make_question(form, Question.TYPE_NUMBER, 2, "Age", config={"min": 1, "max": 10})


@pytest.fixture
def select_q(form):
    q = make_question(form, Question.TYPE_SELECT, 3, "Color")
    make_choice(q, 1, "red")
    make_choice(q, 2, "blue")
    return q


@pytest.fixture
def checkbox_q(form):
    q = make_question(form, Question.TYPE_CHECKBOX, 4, "Hobbies")
    make_choice(q, 1, "a")
    make_choice(q, 2, "b")
    return q


def url(form):
    return f"/api/v1/public/forms/{form.slug}/submissions/"


def post(form, answers, client=None):
    client = client or APIClient()
    return client.post(url(form), {"answers": answers}, format="json")


def details(response):
    return response.json()["error"]["details"]


# ------------------------------------------------------------ model tests --


@pytest.mark.django_db
def test_answer_unique_per_submission_and_question(form, text_q):
    sub = Submission.objects.create(form=form)
    Answer.objects.create(submission=sub, question=text_q, text_value="a")
    with pytest.raises(IntegrityError), transaction.atomic():
        Answer.objects.create(submission=sub, question=text_q, text_value="b")


@pytest.mark.django_db
def test_answer_choice_unique_per_answer(form, select_q):
    sub = Submission.objects.create(form=form)
    answer = Answer.objects.create(submission=sub, question=select_q)
    choice = select_q.choices.first()
    AnswerChoice.objects.create(answer=answer, choice=choice)
    with pytest.raises(IntegrityError), transaction.atomic():
        AnswerChoice.objects.create(answer=answer, choice=choice)


@pytest.mark.django_db
def test_submission_defaults_to_anonymous(form):
    sub = Submission.objects.create(form=form)
    assert sub.user is None
    assert sub.process_run is None


# -------------------------------------------------------------- happy path --


@pytest.mark.django_db
def test_submit_all_question_types(form, text_q, number_q, select_q, checkbox_q):
    red = select_q.choices.get(label="red")
    a, b = checkbox_q.choices.all()
    response = post(form, [
        {"question": text_q.id, "text": "Ali"},
        {"question": number_q.id, "number": "7"},
        {"question": select_q.id, "choices": [red.id]},
        {"question": checkbox_q.id, "choices": [a.id, b.id]},
    ])
    assert response.status_code == 201
    body = response.json()
    assert body["form"] == form.slug

    sub = Submission.objects.get(id=body["id"])
    assert sub.user is None
    assert sub.answers.count() == 4
    assert sub.answers.get(question=text_q).text_value == "Ali"
    assert sub.answers.get(question=number_q).number_value == 7
    assert AnswerChoice.objects.filter(answer__submission=sub).count() == 3


@pytest.mark.django_db
def test_submit_as_authenticated_user_sets_user(form, text_q, owner):
    client = APIClient()
    client.force_login(owner)
    response = post(form, [{"question": text_q.id, "text": "Ali"}], client=client)
    assert response.status_code == 201
    assert Submission.objects.get(id=response.json()["id"]).user == owner


@pytest.mark.django_db
def test_optional_questions_can_be_skipped(form, text_q, number_q):
    response = post(form, [])
    assert response.status_code == 201
    assert Submission.objects.get(id=response.json()["id"]).answers.count() == 0


# ------------------------------------------------------------- validation --


@pytest.mark.django_db
def test_required_question_missing(form):
    q = make_question(form, Question.TYPE_TEXT, 1, required=True)
    response = post(form, [])
    assert response.status_code == 400
    assert str(q.id) in details(response)
    assert Submission.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("value", ["", "   ", None])
def test_required_text_blank_is_rejected(form, value):
    q = make_question(form, Question.TYPE_TEXT, 1, required=True)
    response = post(form, [{"question": q.id, "text": value}])
    assert response.status_code == 400


@pytest.mark.django_db
def test_required_checkbox_needs_at_least_one_choice(form):
    q = make_question(form, Question.TYPE_CHECKBOX, 1, required=True)
    make_choice(q, 1)
    response = post(form, [{"question": q.id, "choices": []}])
    assert response.status_code == 400


@pytest.mark.django_db
def test_text_too_long(form, text_q):
    response = post(form, [{"question": text_q.id, "text": "toolong"}])
    assert response.status_code == 400
    assert str(text_q.id) in details(response)


@pytest.mark.django_db
def test_text_too_short(form):
    q = make_question(form, Question.TYPE_TEXT, 1, config={"min_length": 3})
    assert post(form, [{"question": q.id, "text": "ab"}]).status_code == 400
    assert post(form, [{"question": q.id, "text": "abc"}]).status_code == 201


@pytest.mark.django_db
@pytest.mark.parametrize("value, expected", [(0, 400), (11, 400), (1, 201), (10, 201)])
def test_number_range(form, number_q, value, expected):
    response = post(form, [{"question": number_q.id, "number": value}])
    assert response.status_code == expected


@pytest.mark.django_db
def test_number_must_be_numeric(form, number_q):
    response = post(form, [{"question": number_q.id, "number": "abc"}])
    assert response.status_code == 400


@pytest.mark.django_db
def test_select_rejects_two_choices(form, select_q):
    ids = [c.id for c in select_q.choices.all()]
    response = post(form, [{"question": select_q.id, "choices": ids}])
    assert response.status_code == 400
    assert str(select_q.id) in details(response)


@pytest.mark.django_db
def test_choice_of_another_question_is_rejected(form, select_q, checkbox_q):
    foreign = checkbox_q.choices.first()
    response = post(form, [{"question": select_q.id, "choices": [foreign.id]}])
    assert response.status_code == 400


@pytest.mark.django_db
def test_inactive_choice_is_rejected(form, select_q):
    choice = select_q.choices.first()
    choice.is_active = False
    choice.save()
    response = post(form, [{"question": select_q.id, "choices": [choice.id]}])
    assert response.status_code == 400


@pytest.mark.django_db
def test_duplicate_choices_are_rejected(form, checkbox_q):
    c = checkbox_q.choices.first()
    response = post(form, [{"question": checkbox_q.id, "choices": [c.id, c.id]}])
    assert response.status_code == 400


@pytest.mark.django_db
def test_inactive_question_is_rejected(form, text_q):
    text_q.is_active = False
    text_q.save()
    response = post(form, [{"question": text_q.id, "text": "Ali"}])
    assert response.status_code == 400
    assert str(text_q.id) in details(response)


@pytest.mark.django_db
def test_question_from_another_form_is_rejected(form, owner):
    other = Form.objects.create(owner=owner, title="Other", description="", is_public=True)
    foreign_q = make_question(other, Question.TYPE_TEXT, 1)
    response = post(form, [{"question": foreign_q.id, "text": "x"}])
    assert response.status_code == 400


@pytest.mark.django_db
def test_duplicate_answer_for_same_question(form, text_q):
    response = post(form, [
        {"question": text_q.id, "text": "a"},
        {"question": text_q.id, "text": "b"},
    ])
    assert response.status_code == 400


@pytest.mark.django_db
def test_all_errors_are_reported_together(form, text_q, number_q):
    response = post(form, [
        {"question": text_q.id, "text": "toolong"},
        {"question": number_q.id, "number": 99},
    ])
    assert response.status_code == 400
    assert {str(text_q.id), str(number_q.id)} <= set(details(response))


@pytest.mark.django_db
def test_malformed_body(form):
    response = APIClient().post(url(form), {"answers": "nope"}, format="json")
    assert response.status_code == 400
    response = APIClient().post(url(form), {}, format="json")
    assert response.status_code == 400


# ----------------------------------------------------------- access rules --


@pytest.mark.django_db
def test_unknown_slug_is_404():
    response = APIClient().post(
        "/api/v1/public/forms/doesnotexist/submissions/", {"answers": []}, format="json"
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_private_form_without_token_is_forbidden(form, text_q):
    form.is_public = False
    form.save()
    response = post(form, [{"question": text_q.id, "text": "Ali"}])
    assert response.status_code == 403
    assert Submission.objects.count() == 0


# ------------------------------------------------------------- atomicity --


@pytest.mark.django_db
def test_failure_in_the_middle_leaves_nothing_behind(form, text_q, select_q):
    red = select_q.choices.get(label="red")
    with mock.patch("apps.responses.services.AnswerChoice") as fake:
        fake.objects.bulk_create.side_effect = RuntimeError("boom")
        client = APIClient(raise_request_exception=True)
        with pytest.raises(RuntimeError):
            post(form, [
                {"question": text_q.id, "text": "Ali"},
                {"question": select_q.id, "choices": [red.id]},
            ], client=client)
    assert Submission.objects.count() == 0
    assert Answer.objects.count() == 0


# -------------------------------------------------------------------- C4 --


def owner_client(owner):
    client = APIClient()
    client.force_login(owner)
    return client


@pytest.fixture
def other_user():
    return User.objects.create_user(username="other", password="pass-12345")


@pytest.mark.django_db
def test_owner_can_list_submissions(form, owner, text_q):
    post(form, [{"question": text_q.id, "text": "Ali"}])
    post(form, [{"question": text_q.id, "text": "Sara"}])
    response = owner_client(owner).get(f"/api/v1/forms/{form.id}/submissions/")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert {item["id"] for item in body["results"]} == set(
        Submission.objects.values_list("id", flat=True)
    )


@pytest.mark.django_db
def test_list_is_paginated(form, owner, text_q):
    for _ in range(3):
        post(form, [{"question": text_q.id, "text": "x"}])
    response = owner_client(owner).get(f"/api/v1/forms/{form.id}/submissions/")
    body = response.json()
    assert "next" in body and "previous" in body


@pytest.mark.django_db
def test_other_user_cannot_list_submissions(form, text_q, other_user):
    post(form, [{"question": text_q.id, "text": "Ali"}])
    response = owner_client(other_user).get(f"/api/v1/forms/{form.id}/submissions/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_anonymous_cannot_list_submissions(form):
    response = APIClient().get(f"/api/v1/forms/{form.id}/submissions/")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_owner_can_see_submission_detail_with_answers(
    form, owner, text_q, select_q
):
    red = select_q.choices.get(label="red")
    create_response = post(form, [
        {"question": text_q.id, "text": "Ali"},
        {"question": select_q.id, "choices": [red.id]},
    ])
    sub_id = create_response.json()["id"]

    response = owner_client(owner).get(
        f"/api/v1/forms/{form.id}/submissions/{sub_id}/"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == sub_id
    assert len(body["answers"]) == 2
    text_answer = next(a for a in body["answers"] if a["question"] == text_q.id)
    assert text_answer["text_value"] == "Ali"
    assert text_answer["type"] == "text"
    select_answer = next(a for a in body["answers"] if a["question"] == select_q.id)
    assert select_answer["choices"] == [{"id": red.id, "label": "red"}]


@pytest.mark.django_db
def test_other_user_cannot_see_submission_detail(form, text_q, other_user):
    create_response = post(form, [{"question": text_q.id, "text": "Ali"}])
    sub_id = create_response.json()["id"]
    response = owner_client(other_user).get(
        f"/api/v1/forms/{form.id}/submissions/{sub_id}/"
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_submission_detail_404_for_unknown_id(form, owner):
    response = owner_client(owner).get(f"/api/v1/forms/{form.id}/submissions/9999/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_submission_from_another_form_is_not_visible(form, owner, text_q):
    other_form = Form.objects.create(
        owner=owner, title="Other", description="", is_public=True
    )
    create_response = post(form, [{"question": text_q.id, "text": "Ali"}])
    sub_id = create_response.json()["id"]
    response = owner_client(owner).get(
        f"/api/v1/forms/{other_form.id}/submissions/{sub_id}/"
    )
    assert response.status_code == 404
