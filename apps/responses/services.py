"""Form submission service.

This is the single place where answers are validated and stored. It is used by
the public submit API (C3) and by the process-run API (C6).

    submit_form(form, answers, user=None, process_run=None) -> Submission

`answers` is a list of dicts:
    {"question": <int>, "text": <str|None>, "number": <Decimal|None>,
     "choices": [<int>, ...]}
Only the key that matches the question type is used.

Raises rest_framework.exceptions.ValidationError with a dict
{"<question_id>": "<message>"} when anything is invalid. Nothing is written in
that case.
"""

from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.builder.models import Question

from .models import Answer, AnswerChoice, Submission


def submit_form(form, answers, *, user=None, process_run=None):
    questions = {
        q.id: q
        for q in Question.objects.filter(form=form).prefetch_related("choices")
    }

    errors = {}
    by_question = {}
    for raw in answers:
        qid = raw["question"]
        if qid not in questions:
            errors[str(qid)] = "Question does not belong to this form."
        elif qid in by_question:
            errors[str(qid)] = "Duplicate answer for this question."
        else:
            by_question[qid] = raw

    cleaned = {}
    for qid, question in questions.items():
        data, error = _clean_answer(question, by_question.get(qid, {}))
        if error:
            errors[str(qid)] = error
        elif data is not None:
            cleaned[qid] = data

    if errors:
        raise ValidationError(errors)

    with transaction.atomic():
        submission = Submission.objects.create(
            form=form, user=user, process_run=process_run
        )
        for qid, data in cleaned.items():
            answer = Answer.objects.create(
                submission=submission,
                question_id=qid,
                text_value=data.get("text_value"),
                number_value=data.get("number_value"),
            )
            choice_ids = data.get("choice_ids", [])
            if choice_ids:
                AnswerChoice.objects.bulk_create(
                    AnswerChoice(answer=answer, choice_id=cid) for cid in choice_ids
                )
    return submission


def _required_or_skip(question):
    """Empty answer: error if required, otherwise the question is skipped."""
    return (None, "This question is required.") if question.is_required else (None, None)


def _clean_answer(question, raw):
    """Return (cleaned_data, error). Both None means: nothing to store."""
    config = question.config or {}

    if question.type == Question.TYPE_TEXT:
        text = (raw.get("text") or "").strip()
        if not text:
            return _required_or_skip(question)
        if len(text) < config.get("min_length", 0):
            return None, f"Text must be at least {config['min_length']} characters."
        if "max_length" in config and len(text) > config["max_length"]:
            return None, f"Text must be at most {config['max_length']} characters."
        return {"text_value": text}, None

    if question.type == Question.TYPE_NUMBER:
        number = raw.get("number")
        if number is None:
            return _required_or_skip(question)
        if "min" in config and number < Decimal(str(config["min"])):
            return None, f"Number must be at least {config['min']}."
        if "max" in config and number > Decimal(str(config["max"])):
            return None, f"Number must be at most {config['max']}."
        return {"number_value": number}, None

    # select / checkbox
    chosen = list(raw.get("choices") or [])
    if not chosen:
        return _required_or_skip(question)
    if len(set(chosen)) != len(chosen):
        return None, "Duplicate choices."
    valid_ids = {c.id for c in question.choices.all() if c.is_active}
    if not set(chosen) <= valid_ids:
        return None, "Invalid choice."
    if question.type == Question.TYPE_SELECT and len(chosen) != 1:
        return None, "Exactly one choice is allowed."
    return {"choice_ids": chosen}, None
