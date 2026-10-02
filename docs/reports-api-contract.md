# API contract: reporting (D2)

Base URL: `/api/v1/`.

Errors always use the common shape:

`{"error": {"status": 400, "code": "...", "message": "...", "details": {...}}}`.

Numbers of type `decimal` are returned as strings.

Reporting endpoints are owner-only. A user can access a report only if they own the related form or process.

---

## 1. Form report

### Endpoint

`GET /api/v1/forms/{form_id}/report/`

### Auth

* Authentication is required.
* The authenticated user must be the owner of the form.
* Non-owners receive `403`.
* Unknown form id returns `404`.

### Response `200`

```json
{
  "form": {
    "id": 1,
    "title": "Customer Survey"
  },
  "summary": {
    "visits": 120,
    "submissions": 45
  },
  "questions": [
    {
      "question_id": 1,
      "text": "Age",
      "type": "number",
      "responses": 40,
      "statistics": {
        "average": "24.500000",
        "min": "18.000000",
        "max": "41.000000"
      }
    },
    {
      "question_id": 2,
      "text": "How did you find us?",
      "type": "select",
      "responses": 42,
      "options": [
        {
          "choice_id": 1,
          "label": "Instagram",
          "count": 20,
          "percentage": 47.62
        },
        {
          "choice_id": 2,
          "label": "Google",
          "count": 15,
          "percentage": 35.71
        }
      ]
    },
    {
      "question_id": 3,
      "text": "Which features do you use?",
      "type": "checkbox",
      "responses": 30,
      "options": [
        {
          "choice_id": 5,
          "label": "Reports",
          "count": 18,
          "percentage": 60.0
        }
      ]
    },
    {
      "question_id": 4,
      "text": "Additional comments",
      "type": "text",
      "responses": 25
    }
  ]
}
```

### Summary fields

| Field                 | Description                           |
| --------------------- | ------------------------------------- |
| `form.id`             | Form id                               |
| `form.title`          | Form title                            |
| `summary.visits`      | Number of recorded visits to the form |
| `summary.submissions` | Number of submissions for the form    |
| `questions`           | Report data for active questions      |

### Question fields

Each active question appears once in the `questions` list.

Common fields:

* `question_id`: question id.
* `text`: question text.
* `type`: one of `text`, `select`, `checkbox`, `number`.
* `responses`: number of submissions containing an answer for this question.

### Text questions

For `type = "text"`:

```json
{
  "question_id": 4,
  "text": "Additional comments",
  "type": "text",
  "responses": 25
}
```

The report does not return the actual text answers. It only returns the number of responses.

### Number questions

For `type = "number"`:

```json
{
  "question_id": 1,
  "text": "Age",
  "type": "number",
  "responses": 40,
  "statistics": {
    "average": "24.500000",
    "min": "18.000000",
    "max": "41.000000"
  }
}
```

`average`, `min`, and `max` are returned as strings because they are decimal values.

If the question has no numeric responses, `statistics` contains null values:

```json
{
  "average": null,
  "min": null,
  "max": null
}
```

### Select and checkbox questions

For `type = "select"` or `type = "checkbox"`:

```json
{
  "question_id": 2,
  "text": "How did you find us?",
  "type": "select",
  "responses": 42,
  "options": [
    {
      "choice_id": 1,
      "label": "Instagram",
      "count": 20,
      "percentage": 47.62
    }
  ]
}
```

Each active choice appears in `options`.

* `choice_id`: choice id.
* `label`: choice label.
* `count`: number of answers selecting this choice.
* `percentage`: percentage of question responses that selected this choice.

Percentage is calculated as:

`count / responses * 100`

For checkbox questions, one respondent may select multiple choices, therefore the sum of option percentages can be greater than 100%.

---

## 2. Process report

### Endpoint

`GET /api/v1/processes/{process_id}/report/`

### Auth

* Authentication is required.
* The authenticated user must be the owner of the process.
* Non-owners receive `403`.
* Unknown process id returns `404`.

### Response `200`

```json
{
  "process": {
    "id": 1,
    "title": "Employee Onboarding",
    "mode": "linear"
  },
  "summary": {
    "visits": 200,
    "runs_started": 80,
    "runs_completed": 55
  },
  "steps": [
    {
      "step_id": 1,
      "form_id": 10,
      "order": 1,
      "form_title": "Personal Information",
      "submissions": 70,
      "completion_percentage": 87.5
    },
    {
      "step_id": 2,
      "form_id": 11,
      "order": 2,
      "form_title": "Employment Information",
      "submissions": 60,
      "completion_percentage": 75.0
    }
  ]
}
```

### Process fields

| Field                    | Description                              |
| ------------------------ | ---------------------------------------- |
| `process.id`             | Process id                               |
| `process.title`          | Process title                            |
| `process.mode`           | `linear` or `free`                       |
| `summary.visits`         | Number of recorded visits to the process |
| `summary.runs_started`   | Number of process runs                   |
| `summary.runs_completed` | Number of completed process runs         |
| `steps`                  | Report data for process steps            |

### Step fields

Each process step appears once in the `steps` list.

* `step_id`: ProcessStep id.
* `form_id`: Form used by this process step.
* `order`: Step order.
* `form_title`: Title of the form.
* `submissions`: Number of submissions associated with this form as part of this process.
* `completion_percentage`: Percentage of started process runs that completed this step.

Completion percentage is calculated as:

`submissions / runs_started * 100`

If `runs_started` is zero, `completion_percentage` is `0`.

Steps are returned ordered by `order` ascending.

---

## 3. Error responses

### Unauthorized

`401` when authentication is required but the user is not authenticated.

```json
{
  "error": {
    "status": 401,
    "code": "authentication_required",
    "message": "Authentication credentials were not provided.",
    "details": {}
  }
}
```

### Forbidden

`403` when the authenticated user does not own the requested form or process.

```json
{
  "error": {
    "status": 403,
    "code": "forbidden",
    "message": "You do not have permission to access this report.",
    "details": {}
  }
}
```

### Not found

`404` when the requested form or process does not exist.

```json
{
  "error": {
    "status": 404,
    "code": "not_found",
    "message": "The requested resource was not found.",
    "details": {}
  }
}
```

---

## 4. Report data rules

* Only active questions are included in form reports.
* Only active choices are included in `options`.
* Text answers are not exposed in reports.
* Number statistics are calculated from non-null numeric answers.
* Select and checkbox statistics are calculated from selected choices.
* Visits are counted from the `Visit` model.
* Form submissions are counted from the `Submission` model.
* Process runs are counted from the `ProcessRun` model.
* Process step submissions are determined from submissions associated with the corresponding process run and form.
* Report data is aggregated on the server using ORM queries.
* Report endpoints return aggregated data suitable for charts and dashboards.
* Report endpoints do not expose individual respondent information.

---

## 5. Stable endpoint summary

| Method | Endpoint                                 | Access        |
| ------ | ---------------------------------------- | ------------- |
| `GET`  | `/api/v1/forms/{form_id}/report/`        | Form owner    |
| `GET`  | `/api/v1/processes/{process_id}/report/` | Process owner |
