from django.core.exceptions import ValidationError

from .models import Visit


def get_client_ip(request):
    """Return the client's IP address from the request."""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


def record_visit(request, form=None, process=None):
    """
    Record a visit for exactly one form or process.

    The visitor can be authenticated or anonymous.
    """
    if (form is None) == (process is None):
        raise ValidationError(
            "A visit must be related to exactly one form or process."
        )

    user = request.user if request.user.is_authenticated else None

    return Visit.objects.create(
        form=form,
        process=process,
        user=user,
        ip=get_client_ip(request),
    )