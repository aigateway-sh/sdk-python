"""HMAC-SHA256 webhook signature verification for AIgateway callbacks."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Union


def verify_webhook(
    secret: str,
    body: Union[str, bytes],
    header: str,
    tolerance_seconds: int = 5 * 60,
) -> bool:
    """Verify an AIgateway ``X-Gateway-Signature`` header.

    The signed payload is ``f"{t}.{raw_body}"`` (UTF-8).
    """
    if isinstance(body, bytes):
        body = body.decode("utf-8")

    parts = {}
    for kv in header.split(","):
        idx = kv.find("=")
        if idx > 0:
            parts[kv[:idx].strip()] = kv[idx + 1 :].strip()

    t_raw = parts.get("t")
    v1 = parts.get("v1")
    if not t_raw or not v1:
        return False
    try:
        t = int(t_raw)
    except ValueError:
        return False

    now = int(time.time())
    if abs(now - t) > tolerance_seconds:
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        f"{t}.{body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, v1)
