# API contract: responses and processes (C)

Base URL: `/api/v1/`. Errors always use the common shape:
`{"error": {"status": 400, "code": "...", "message": "...", "details": {...}}}`.
Numbers of type `decimal` are returned as strings (for example `"7.000000"`).

## 1. Submit answers to a form (C3)

`POST /api/v1/public/forms/{slug}/submissions/`

- Auth: none required. If the user is logged in (session or JWT) the submission is linked to them, otherwise it is anonymous.
- Public form: works directly.
- Private form: needs the short-lived access token from B6 in the header `X-Form-Access-Token` (final name to be confirmed with B). Without it: `403`.

Request:

```json
{
  "answers": [
    {"question": 12, "text": "Ali"},
    {"question": 13, "number": 7},
    {"question": 14, "choices": [31]},
    {"question": 15, "choices": [40, 41]}
  ]
}
```

- `text` for `text` questions, `number` for `number` questions, `choices` (list of choice ids) for `select` (exactly one) and `checkbox`.
- Optional questions can be omitted.

Responses:

- `201`: `{"id": 5, "form": "<slug>", "submitted_at": "2026-09-30T10:00:00+03:30"}`
- `400`: `details` maps question id to a message, all errors together:

```json
{"error": {"status": 400, "code": "invalid", "message": "Invalid input.",
           "details": {"12": "Text must be at most 5 characters.", "13": "This question is required."}}}
```

- `403` private form without a valid token, `404` unknown slug.

Validation rules: required questions, number range (`config.min` / `config.max`), text length (`config.min_length` / `config.max_length`), `select` exactly one active choice, `checkbox` only active choices without duplicates, question and choices must belong to this form.

## 2. Submissions for the form owner (C4)

- `GET /api/v1/forms/{form_id}/submissions/` : paginated list (`count`, `next`, `previous`, `results`), owner only.
- `GET /api/v1/forms/{form_id}/submissions/{id}/` : one submission with its answers.

Answer item shape:

```json
{"question": 12, "question_text": "Name", "type": "text",
 "text_value": "Ali", "number_value": null, "choices": []}
```

## 3. Processes (C5), owner only

- `GET /api/v1/processes/` (filters: `category`, `search`) and `POST /api/v1/processes/`
- `GET|PATCH|DELETE /api/v1/processes/{id}/`

Process shape:

```json
{"id": 1, "title": "Onboarding", "description": "", "slug": "<slug>",
 "mode": "linear", "is_public": false, "category": null,
 "password": "write-only, optional", "steps": [{"id": 3, "form": 7, "order": 1}]}
```

Steps:

- `POST /api/v1/processes/{id}/steps/` body `{"form": 7}` (appended at the end; the form must belong to the same user)
- `DELETE /api/v1/processes/{id}/steps/{step_id}/`
- `POST /api/v1/processes/{id}/steps/reorder/` body `{"order": [step_id, step_id, ...]}`

## 4. Running a process (C6)

- `POST /api/v1/public/processes/{slug}/runs/` : starts a run. Private process needs a password token (same mechanism as forms). Response `201`:
  `{"id": 9, "respondent_token": "<string>", "status": [...]}`
- `GET /api/v1/public/processes/{slug}/runs/{respondent_token}/` : run status:

```json
{"id": 9, "completed_at": null,
 "steps": [{"id": 3, "form": 7, "order": 1, "state": "done"},
           {"id": 4, "form": 8, "order": 2, "state": "available"},
           {"id": 5, "form": 9, "order": 3, "state": "locked"}]}
```

`state` is one of `done`, `available`, `locked`. In `free` mode no step is locked.

- `POST /api/v1/public/processes/{slug}/runs/{respondent_token}/steps/{step_id}/submit/` : same body as section 1. Errors: `400` validation, `403` step is locked (linear mode), `409` step already submitted. When the last step is done the run gets `completed_at`.

## Shared function signatures (stable)

```python
# apps/responses/services.py
submit_form(form, answers, *, user=None, process_run=None) -> Submission
```
