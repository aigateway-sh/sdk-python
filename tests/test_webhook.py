"""Unit tests for webhook signature verification."""

import hashlib
import hmac
import time

import pytest

from aigateway import verify_webhook


def sign(secret: str, body: str, t: int) -> str:
    h = hmac.new(secret.encode(), f"{t}.{body}".encode(), hashlib.sha256).hexdigest()
    return f"t={t},v1={h}"


def test_accepts_valid_signature():
    secret = "whsec_test"
    body = '{"id":"job_1","status":"completed"}'
    t = int(time.time())
    assert verify_webhook(secret, body, sign(secret, body, t)) is True


def test_rejects_tampered_body():
    secret = "whsec_test"
    t = int(time.time())
    sig = sign(secret, "hello", t)
    assert verify_webhook(secret, "hello-tampered", sig) is False


def test_rejects_wrong_secret():
    t = int(time.time())
    sig = sign("whsec_a", "body", t)
    assert verify_webhook("whsec_b", "body", sig) is False


def test_rejects_stale_timestamp():
    secret = "whsec_test"
    old = int(time.time()) - 3600
    sig = sign(secret, "body", old)
    assert verify_webhook(secret, "body", sig, tolerance_seconds=60) is False


def test_rejects_malformed_header():
    assert verify_webhook("s", "body", "garbage") is False
    assert verify_webhook("s", "body", "t=nope,v1=abc") is False
    assert verify_webhook("s", "body", "") is False


def test_accepts_bytes_body():
    secret = "whsec_test"
    body = '{"id":"j"}'
    t = int(time.time())
    assert verify_webhook(secret, body.encode(), sign(secret, body, t)) is True
