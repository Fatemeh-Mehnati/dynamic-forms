import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.builder.models import Choice, Form, Question
from apps.responses.models import Answer, AnswerChoice, Submission

User = get_user_model()


@pytest.fixture
def form():
    owner = User.objects.create_user(username="owner", password="pass-12345")
    return Form.objects.create(owner=owner, title="Survey", description="", is_public=True)


@pytest.fixture
def text_q(form):
    return Question.objects.create(
        form=form, type=Question.TYPE_TEXT, text="Name", order=1, config={}
    )


@pytest.fixture
def select_q(form):
    q = Question.objects.create(
        form=form, type=Question.TYPE_SELECT, text="Color", order=2, config={}
    )
    Choice.objects.create(question=q, label="red", order=1)
    return q


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