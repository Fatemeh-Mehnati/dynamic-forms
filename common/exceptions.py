from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Wrap every DRF error in one consistent shape:

    {"error": {"status": 400, "code": "invalid", "message": "...", "details": {...}}}
    """
    response = exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    if isinstance(data, dict) and set(data.keys()) == {"detail"}:
        message = str(data["detail"])
        details = None
    else:
        message = "Invalid input." if response.status_code == 400 else "Request failed."
        details = data

    response.data = {
        "error": {
            "status": response.status_code,
            "code": getattr(exc, "default_code", "error"),
            "message": message,
            "details": details,
        }
    }
    return response