import hashlib
import hmac
import logging
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError

from .models import OTPCode, User

logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r"^09\d{9}$")


def normalize_target(target: str) -> tuple[str, str]:
    """Return (normalized_target, kind) where kind is "email" or "phone"."""
    target = target.strip().lower()
    if "@" in target:
        return target, "email"
    if PHONE_RE.match(target):
        return target, "phone"
    raise ValidationError(
        {"target": "Enter a valid email or an Iranian mobile number (09xxxxxxxxx)."}
    )


def _hash_code(target: str, code: str) -> str:
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, f"{target}:{code}".encode(), hashlib.sha256).hexdigest()


def _find_user(target: str, kind: str):
    return User.objects.filter(**{kind: target}).first()


def _send_code(target: str, kind: str, code: str) -> None:
    minutes = settings.OTP_TTL_SECONDS // 60
    message = f"Your verification code is {code}. It expires in {minutes} minutes."
    if kind == "email":
        send_mail("Your verification code", message, settings.DEFAULT_FROM_EMAIL, [target])
    else:
        # No real SMS provider: the message is only logged.
        logger.info("SMS to %s: %s", target, message)


def request_otp(target: str, purpose: str) -> None:
    target, kind = normalize_target(target)
    user = _find_user(target, kind)

    if purpose == OTPCode.Purpose.LOGIN and user is None:
        raise ValidationError({"target": "No account found for this email or phone."})
    if purpose == OTPCode.Purpose.REGISTER and user is not None:
        raise ValidationError({"target": "An account with this email or phone already exists."})

    last = OTPCode.objects.filter(target=target, purpose=purpose).first()
    if last:
        elapsed = (timezone.now() - last.created_at).total_seconds()
        cooldown = settings.OTP_RESEND_COOLDOWN_SECONDS
        if elapsed < cooldown:
            raise Throttled(
                wait=int(cooldown - elapsed),
                detail="Please wait before requesting a new code.",
            )

    code = f"{secrets.randbelow(10**settings.OTP_LENGTH):0{settings.OTP_LENGTH}d}"
    with transaction.atomic():
        # Any older unused code for this target becomes invalid.
        OTPCode.objects.filter(target=target, purpose=purpose, is_used=False).update(is_used=True)
        OTPCode.objects.create(
            target=target,
            purpose=purpose,
            code_hash=_hash_code(target, code),
            expires_at=timezone.now() + timedelta(seconds=settings.OTP_TTL_SECONDS),
        )
    _send_code(target, kind, code)


def verify_otp(target: str, purpose: str, code: str, username: str | None = None) -> User:
    target, kind = normalize_target(target)
    error = None

    with transaction.atomic():
        otp = (
            OTPCode.objects.select_for_update()
            .filter(target=target, purpose=purpose, is_used=False)
            .first()
        )
        if otp is None or otp.is_expired:
            error = "Code is expired or was not requested."
        elif otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            error = "Too many wrong attempts. Request a new code."
        elif not hmac.compare_digest(otp.code_hash, _hash_code(target, code)):
            otp.attempts = F("attempts") + 1
            otp.save(update_fields=["attempts"])
            error = "Invalid code."
        else:
            otp.is_used = True
            otp.save(update_fields=["is_used"])
            if purpose == OTPCode.Purpose.REGISTER:
                user = User(username=username, **{kind: target})
                user.set_unusable_password()
                user.save()
            else:
                user = _find_user(target, kind)

    # Raised outside the transaction so the attempts counter is kept.
    if error:
        raise ValidationError({"code": error})
    return user