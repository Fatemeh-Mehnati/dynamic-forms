"""Process-run service (C6).

Everything about *state* of a run lives here so the views stay thin:

    get_run_steps(run)  -> [(ProcessStep, state), ...]   state: done | available | locked
    submit_step(run, step_id, answers, user=None) -> (Submission, run)

Answer validation and storage are NOT reimplemented: they are delegated to
apps.responses.services.submit_form (C3).
"""

from collections import Counter

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, PermissionDenied

from apps.responses.services import submit_form

from .models import Process, ProcessRun

STATE_DONE = "done"
STATE_AVAILABLE = "available"
STATE_LOCKED = "locked"


class StepAlreadySubmitted(APIException):
    status_code = 409
    default_detail = "This step has already been submitted."
    default_code = "conflict"


def track_visit(request, process):
    """Call D3's record_visit(request, process=...).

    TODO(D3): once D3 is merged, replace this helper with a plain import
    `from apps.reports.services import record_visit` (fix the module path to
    wherever D3 put it) and call record_visit(request, process=process).
    """
    try:
        from apps.reports.services import record_visit
    except ImportError:
        return
    record_visit(request, process=process)


def start_run(process, user=None):
    return ProcessRun.objects.create(process=process, user=user)


def get_run_steps(run):
    """Return [(step, state)] in step order.

    done      a submission of this step's form exists in this run
    available the respondent may fill it now
    locked    (linear mode only) an earlier step is not done yet

    A form may appear twice in one process; the k-th occurrence counts as done
    when the run has at least k submissions of that form.
    """
    steps = list(run.process.steps.all())  # Meta.ordering = ["order"]
    submitted = Counter(run.submissions.values_list("form_id", flat=True))
    seen = Counter()
    linear = run.process.mode == Process.MODE_LINEAR

    previous_done = True
    result = []
    for step in steps:
        seen[step.form_id] += 1
        if submitted[step.form_id] >= seen[step.form_id]:
            state = STATE_DONE
        elif linear and not previous_done:
            state = STATE_LOCKED
        else:
            state = STATE_AVAILABLE
        previous_done = previous_done and state == STATE_DONE
        result.append((step, state))
    return result


def serialize_steps(pairs):
    return [
        {"id": step.id, "form": step.form_id, "order": step.order, "state": state}
        for step, state in pairs
    ]


def submit_step(run, step_id, answers, *, user=None):
    """Validate and store the answers of one step of a run.

    Raises: NotFound (step not in this process), StepAlreadySubmitted (409),
    PermissionDenied (403, locked step in linear mode), ValidationError (400).
    """
    with transaction.atomic():
        # Lock the run row so two parallel requests cannot both pass the
        # "already submitted" check.
        run = (
            ProcessRun.objects.select_for_update(of=("self",))
            .select_related("process")
            .get(pk=run.pk)
        )
        pairs = get_run_steps(run)
        match = next(((s, st) for s, st in pairs if s.id == step_id), None)
        if match is None:
            raise NotFound("Step not found in this process.")
        step, state = match
        if state == STATE_DONE:
            raise StepAlreadySubmitted()
        if state == STATE_LOCKED:
            raise PermissionDenied("This step is locked. Finish the previous steps first.")

        submission = submit_form(step.form, answers, user=user, process_run=run)

        if run.completed_at is None and all(
            st == STATE_DONE for _, st in get_run_steps(run)
        ):
            run.completed_at = timezone.now()
            run.save(update_fields=["completed_at"])
    return submission, run