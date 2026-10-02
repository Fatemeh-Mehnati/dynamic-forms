# Builder API Contract

Base URL: `/api/v1/`

This document defines the API contract for the dynamic form builder.

## 1. Authentication and Permissions

* Category and form management endpoints require authentication.
* Users can manage only their own categories and forms.
* Public form retrieval does not require authentication.
* Private form access requires a short-lived access token.

## 2. Categories API

### Endpoints

All category management endpoints require authentication.

Users can access and manage only their own categories.

### 2.1 List Categories

**Endpoint**

`GET /api/v1/categories/`

**Response: 200 OK**

```json
[
  {
    "id": 1,
    "name": "Customer Feedback",
    "created_at": "2026-10-02T10:00:00Z",
    "updated_at": "2026-10-02T10:00:00Z"
  },
  {
    "id": 2,
    "name": "Internal Forms",
    "created_at": "2026-10-02T11:00:00Z",
    "updated_at": "2026-10-02T11:00:00Z"
  }
]
```

### 2.2 Create Category

**Endpoint**

`POST /api/v1/categories/`

**Request**

```json
{
  "name": "Customer Feedback"
}
```

**Response: 201 Created**

```json
{
  "id": 1,
  "name": "Customer Feedback",
  "created_at": "2026-10-02T10:00:00Z",
  "updated_at": "2026-10-02T10:00:00Z"
}
```

**Validation**

* `name` is required.
* Category names must be unique for the same owner.

### 2.3 Retrieve Category

**Endpoint**

`GET /api/v1/categories/{id}/`

**Response: 200 OK**

```json
{
  "id": 1,
  "name": "Customer Feedback",
  "created_at": "2026-10-02T10:00:00Z",
  "updated_at": "2026-10-02T10:00:00Z"
}
```

### 2.4 Update Category

**Endpoint**

`PATCH /api/v1/categories/{id}/`

**Request**

```json
{
  "name": "Customer Surveys"
}
```

**Response: 200 OK**

```json
{
  "id": 1,
  "name": "Customer Surveys",
  "created_at": "2026-10-02T10:00:00Z",
  "updated_at": "2026-10-02T12:00:00Z"
}
```

### 2.5 Delete Category

**Endpoint**

`DELETE /api/v1/categories/{id}/`

**Response: 204 No Content**

Deleting a category sets the category reference of related forms to `null`. It does not delete those forms.

### Errors

* `400 Bad Request`: Invalid input or duplicate category name.
* `401 Unauthorized`: Authentication is required.
* `404 Not Found`: Category does not exist or does not belong to the authenticated user.

## 3. Forms API

### Endpoints

All form management endpoints require authentication.

Users can manage only their own forms.

### 3.1 List Forms

**Endpoint**

`GET /api/v1/forms/`

**Query Parameters**

| Parameter  | Type    | Description                    |
| ---------- | ------- | ------------------------------ |
| `search`   | string  | Search by title or description |
| `category` | integer | Filter by category ID          |

**Response: 200 OK**

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Customer Survey",
      "description": "Customer feedback form",
      "category": 2,
      "slug": "a1b2c3d4e5f6",
      "is_public": true,
      "created_at": "2026-10-02T10:00:00Z",
      "updated_at": "2026-10-02T10:00:00Z"
    }
  ]
}
```

### 3.2 Create Form

**Endpoint**

`POST /api/v1/forms/`

**Request**

```json
{
  "title": "Customer Survey",
  "description": "Customer feedback form",
  "category": 2,
  "is_public": true
}
```

**Response: 201 Created**

```json
{
  "id": 1,
  "title": "Customer Survey",
  "description": "Customer feedback form",
  "category": 2,
  "slug": "a1b2c3d4e5f6",
  "is_public": true,
  "created_at": "2026-10-02T10:00:00Z",
  "updated_at": "2026-10-02T10:00:00Z"
}
```

### 3.3 Retrieve Form

**Endpoint**

`GET /api/v1/forms/{id}/`

**Response: 200 OK**

```json
{
  "id": 1,
  "title": "Customer Survey",
  "description": "Customer feedback form",
  "category": 2,
  "slug": "a1b2c3d4e5f6",
  "is_public": true,
  "created_at": "2026-10-02T10:00:00Z",
  "updated_at": "2026-10-02T10:00:00Z"
}
```

### 3.4 Update Form

**Endpoint**

`PATCH /api/v1/forms/{id}/`

**Request**

```json
{
  "title": "Updated Customer Survey",
  "description": "Updated description",
  "category": 3,
  "is_public": false,
  "password": "new-secret"
}
```

**Response: 200 OK**

```json
{
  "id": 1,
  "title": "Updated Customer Survey",
  "description": "Updated description",
  "category": 3,
  "slug": "a1b2c3d4e5f6",
  "is_public": false,
  "created_at": "2026-10-02T10:00:00Z",
  "updated_at": "2026-10-02T12:00:00Z"
}
```

### 3.5 Delete Form

**Endpoint**

`DELETE /api/v1/forms/{id}/`

**Response: 204 No Content**

Deleting a form also deletes its related questions and choices according to the model relationships.

### Validation and Behavior

* `title` is required when creating a form.
* `description` may be empty if allowed by the implementation.
* `category` must refer to a category owned by the authenticated user.
* `slug` is generated automatically and is read-only.
* `password` is write-only and must never be returned in API responses.
* `password_hash` is never exposed.
* A private form may require a password to be accessed through the public form endpoint.
* The exact behavior for removing an existing password or switching a form to public must be confirmed during implementation.

### Errors

* `400 Bad Request`: Invalid input.
* `401 Unauthorized`: Authentication is required.
* `403 Forbidden`: The user does not have access to the requested resource.
* `404 Not Found`: The form does not exist or does not belong to the authenticated user.

## 4. Questions and Choices API

Questions belong to a form. Choices belong to a question.

All question and choice management operations require authentication. Users can manage questions and choices only within their own forms.

The following endpoint structure is a proposed contract and must be confirmed before implementation.

### 4.1 Create Questions with a Form

**Endpoint**

`POST /api/v1/forms/`

Questions and their choices may be included when creating a form.

**Request**

```json
{
  "title": "Customer Survey",
  "description": "Customer feedback",
  "category": 1,
  "is_public": true,
  "questions": [
    {
      "type": "text",
      "text": "What is your name?",
      "is_required": true,
      "order": 1,
      "config": {
        "min_length": 2,
        "max_length": 100
      },
      "choices": []
    },
    {
      "type": "select",
      "text": "How did you hear about us?",
      "is_required": true,
      "order": 2,
      "config": {},
      "choices": [
        {
          "label": "Instagram",
          "order": 1
        },
        {
          "label": "Google",
          "order": 2
        }
      ]
    }
  ]
}
```

**Response: 201 Created**

```json
{
  "id": 1,
  "title": "Customer Survey",
  "description": "Customer feedback",
  "category": 1,
  "slug": "a1b2c3d4",
  "is_public": true,
  "questions": [
    {
      "id": 10,
      "type": "text",
      "text": "What is your name?",
      "is_required": true,
      "order": 1,
      "config": {
        "min_length": 2,
        "max_length": 100
      },
      "choices": []
    },
    {
      "id": 11,
      "type": "select",
      "text": "How did you hear about us?",
      "is_required": true,
      "order": 2,
      "config": {},
      "choices": [
        {
          "id": 21,
          "label": "Instagram",
          "order": 1
        },
        {
          "id": 22,
          "label": "Google",
          "order": 2
        }
      ]
    }
  ]
}
```

### 4.2 Retrieve Form Questions

**Endpoint**

`GET /api/v1/forms/{id}/`

The response includes the form's questions and their choices, subject to the agreed response structure.

### 4.3 Update Questions and Choices

**Endpoint**

`PATCH /api/v1/forms/{id}/`

**Request**

```json
{
  "questions": [
    {
      "id": 10,
      "type": "text",
      "text": "What is your full name?",
      "is_required": true,
      "order": 1,
      "config": {
        "min_length": 2,
        "max_length": 150
      },
      "choices": []
    },
    {
      "type": "checkbox",
      "text": "Which services do you use?",
      "is_required": false,
      "order": 2,
      "config": {},
      "choices": [
        {
          "label": "Support",
          "order": 1
        },
        {
          "label": "Consulting",
          "order": 2
        }
      ]
    }
  ]
}
```

The exact semantics for adding, updating, omitting, and deleting nested questions and choices must be confirmed before implementation.

### 4.4 Supported Question Types

| Type       | Description               | Example config                         |
| ---------- | ------------------------- | -------------------------------------- |
| `text`     | Text input                | `{"min_length": 2, "max_length": 100}` |
| `select`   | Single-choice selection   | `{}`                                   |
| `checkbox` | Multiple-choice selection | `{}`                                   |
| `number`   | Numeric input             | `{"min": 0, "max": 100}`               |

### 4.5 Validation Rules

* `type` must be one of `text`, `select`, `checkbox`, or `number`.
* `text` is the question label.
* `is_required` indicates whether an answer is mandatory.
* `order` determines the question's position.
* `config` must be valid for the question type.
* `select` and `checkbox` questions require at least two choices, according to the task specification.
* `text` questions may define `min_length` and `max_length`.
* `number` questions may define `min` and `max`.
* Choices must belong to their question.
* Users cannot manage questions or choices belonging to another user's form.

### 4.6 Reordering Questions

The API must support changing question order.

The exact endpoint and request format are to be agreed upon with the frontend developer.

### Errors

* `400 Bad Request`: Invalid question type, config, or choice data.
* `401 Unauthorized`: Authentication is required.
* `403 Forbidden`: The user does not own the form.
* `404 Not Found`: The requested form or question does not exist.

## 5. Public Form API

### 5.1 Retrieve a Public Form

`GET /api/v1/public/forms/{slug}/`

Retrieve a form by its slug.

**Access:**

* Public forms: accessible without authentication.
* Private forms: require a valid access token.

**Path parameters:**

| Parameter | Type   | Description      |
| --------- | ------ | ---------------- |
| slug      | string | Unique form slug |

**Successful response — `200 OK`:**

```json
{
  "id": 1,
  "title": "Customer Feedback",
  "description": "Share your feedback",
  "slug": "customer-feedback",
  "questions": [
    {
      "id": 10,
      "type": "text",
      "text": "What did you think?",
      "is_required": true,
      "order": 1,
      "config": {},
      "choices": []
    }
  ]
}
```

**Errors:**

* `403 Forbidden`: A valid access token is required for a private form.
* `404 Not Found`: The form does not exist or is unavailable.

### 5.2 Private Form Access

Private forms require password verification before retrieval.

The API must provide an endpoint that:

* Accepts the form password.
* Verifies the password against the stored password hash.
* Issues a short-lived access token when the password is correct.

The exact endpoint, request/response schema, token format, and expiration policy must be confirmed with the team before implementation.

**Proposed token header:**

`X-Form-Access-Token: <token>`

This header is tentative and must be coordinated with the response API contract.

**Errors:**

* `400 Bad Request`: Invalid request data.
* `403 Forbidden`: Incorrect password or invalid access token.
* `404 Not Found`: The form does not exist or is unavailable.
* `429 Too Many Requests`: Too many password attempts, if rate limiting is implemented.

## 6. Common Errors

Errors use the project's common response format:

```json
{
  "error": {
    "status": 400,
    "code": "invalid",
    "message": "Invalid input.",
    "details": {}
  }
}
```
