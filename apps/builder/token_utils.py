from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

TOKEN_SALT = "private-form-access"


def create_form_access_token(form):
    signer = TimestampSigner(salt=TOKEN_SALT)
    return signer.sign(form.slug)


def verify_form_access_token(form, token):
    if not token:
        return False

    signer = TimestampSigner(salt=TOKEN_SALT)

    try:
        slug = signer.unsign(
            token,
            max_age=getattr(settings, "FORM_ACCESS_TOKEN_TTL", 300),
        )
    except (BadSignature, SignatureExpired):
        return False

    return slug == form.slug