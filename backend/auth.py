"""Short-lived, signed browser sessions for a shared judge password."""

import hashlib
import hmac
import os
import secrets
import time

from fastapi import HTTPException


COOKIE = "dyscover_session"
MAX_AGE = 24 * 60 * 60


def configured():
    return bool(os.environ.get("DYSCOVER_JUDGE_PASSWORD") and os.environ.get("DYSCOVER_SESSION_SECRET"))


def signing_key():
    if not configured():
        raise HTTPException(503, "Configure judge password and session secret")
    return (os.environ["DYSCOVER_SESSION_SECRET"] + os.environ["DYSCOVER_JUDGE_PASSWORD"]).encode()


def check_password(password):
    signing_key()
    return isinstance(password, str) and hmac.compare_digest(password, os.environ["DYSCOVER_JUDGE_PASSWORD"])


def issue():
    owner = secrets.token_hex(16)
    expiry = int(time.time()) + MAX_AGE
    payload = f"{owner}.{expiry}"
    signature = hmac.new(signing_key(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def owner(cookie):
    signing_key()
    try:
        owner_id, expiry, signature = cookie.split(".")
        payload = f"{owner_id}.{expiry}"
        expected = hmac.new(signing_key(), payload.encode(), hashlib.sha256).hexdigest()
        if (len(owner_id) == 32 and int(expiry) >= time.time()
                and hmac.compare_digest(signature, expected)):
            return owner_id
    except (AttributeError, ValueError):
        pass
    raise HTTPException(401, "Sign in to use Dyscover")
