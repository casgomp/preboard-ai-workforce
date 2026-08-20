"""Per-offer auth (NOTES.md invariant §1.5): stateless signed magic-link tokens.

No internal directory identity exists pre-day-1, so there's no user store to check a
token against — the token IS the credential. Verifying it needs only the shared secret,
which matches "no internal identity" directly instead of building a login system that
implies one.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
import time

_DEV_SECRET = b"preboard-dev-secret-do-not-use-in-prod"

DEFAULT_TTL_SECONDS = 60 * 60 * 24 * 90


class InvalidToken(Exception):
    """Token is malformed, tampered with, or expired."""


def _secret() -> bytes:
    env = os.environ.get("PREBOARD_AUTH_SECRET")
    return env.encode("utf-8") if env else _DEV_SECRET


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(s: str) -> bytes:
    if not s:
        raise binascii.Error("empty base64")

    allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    if any(char not in allowed for char in s):
        raise binascii.Error("invalid base64")

    if len(s) % 4 == 1:
        raise binascii.Error("invalid base64 length")

    padded = s + "=" * (-len(s) % 4)
    decoded = base64.urlsafe_b64decode(padded)

    # Reject non-canonical Base64 representations.
    if _b64(decoded) != s:
        raise binascii.Error("non-canonical base64")

    return decoded


def issue_token(offer_id: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Mint a magic-link token scoped to one offer."""
    expiry = int(time.time()) + ttl_seconds
    payload = f"{offer_id}:{expiry}".encode("utf-8")
    sig = hmac.new(_secret(), payload, hashlib.sha256).digest()
    return f"{_b64(payload)}.{_b64(sig)}"


def verify_token(token: str) -> str:
    """Return the offer_id a token is scoped to, or raise InvalidToken."""
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        payload = _unb64(payload_b64)
        sig = _unb64(sig_b64)
    except (ValueError, binascii.Error) as exc:
        raise InvalidToken("malformed token") from exc

    expected_sig = hmac.new(_secret(), payload, hashlib.sha256).digest()

    if not hmac.compare_digest(sig, expected_sig):
        raise InvalidToken("bad signature")

    try:
        offer_id, expiry_str = payload.decode("utf-8").rsplit(":", 1)
        expiry = int(expiry_str)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidToken("malformed payload") from exc

    if time.time() > expiry:
        raise InvalidToken("expired")

    return offer_id
