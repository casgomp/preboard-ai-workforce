import time

import pytest

from preboard.auth import InvalidToken, issue_token, verify_token


def test_roundtrip():
    token = issue_token("jordan-rivera")
    assert verify_token(token) == "jordan-rivera"


def test_tampered_signature_rejected():
    # A flip of the last base64url character only perturbs 2 significant bits
    # of the underlying byte, so ~6% of flips decode to the same signature —
    # not a tamper. Flip a middle character instead, where a full 6-bit swap
    # changes the decoded byte(s) every time.
    token = issue_token("jordan-rivera")
    payload_b64, sig_b64 = token.split(".", 1)
    mid = len(sig_b64) // 2
    tampered_char = "A" if sig_b64[mid] != "A" else "B"
    tampered = f"{payload_b64}.{sig_b64[:mid]}{tampered_char}{sig_b64[mid + 1:]}"

    with pytest.raises(InvalidToken):
        verify_token(tampered)


def test_offer_id_cannot_be_forged_by_editing_payload():
    token = issue_token("jordan-rivera")
    payload_b64, sig_b64 = token.split(".", 1)
    forged = f"{issue_token('alex-chen').split('.', 1)[0]}.{sig_b64}"

    with pytest.raises(InvalidToken):
        verify_token(forged)


def test_expired_token_rejected():
    token = issue_token("jordan-rivera", ttl_seconds=-1)

    with pytest.raises(InvalidToken):
        verify_token(token)


def test_malformed_token_rejected():
    with pytest.raises(InvalidToken):
        verify_token("not-a-real-token")


def test_different_offers_get_different_tokens():
    assert issue_token("jordan-rivera") != issue_token("alex-chen")
