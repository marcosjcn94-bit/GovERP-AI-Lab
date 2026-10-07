from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionClaims:
    user_id: str
    municipality_id: str
    expires_at: int
    nonce: str


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    if not value or any(
        c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in value
    ):
        raise ValueError("Invalid session token")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_session_token(
    user_id: str, municipality_id: str, secret: str, *, now: int | None = None, lifetime: int = 3600
) -> str:
    if len(secret.encode("utf-8")) < 32:
        raise ValueError("Session secret must contain at least 32 bytes")
    if not user_id or not municipality_id or lifetime < 1 or lifetime > 43200:
        raise ValueError("Invalid session context")
    issued = int(time.time()) if now is None else now
    payload = json.dumps(
        {
            "u": user_id,
            "m": municipality_id,
            "e": issued + lifetime,
            "n": secrets.token_urlsafe(12),
        },
        separators=(",", ":"),
    ).encode("utf-8")
    body = _encode(payload)
    signature = _encode(
        hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    )
    return f"{body}.{signature}"


def verify_session_token(token: str, secret: str, *, now: int | None = None) -> SessionClaims:
    try:
        body, signature = token.split(".", maxsplit=1)
        expected = _encode(
            hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        )
        if len(secret.encode("utf-8")) < 32 or not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid session token")
        payload = json.loads(_decode(body))
        claims = SessionClaims(
            str(payload["u"]), str(payload["m"]), int(payload["e"]), str(payload["n"])
        )
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid session token") from exc
    current = int(time.time()) if now is None else now
    if not claims.user_id or not claims.municipality_id or claims.expires_at <= current:
        raise ValueError("Expired or invalid session token")
    return claims


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    actual_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), actual_salt, 310_000)
    return f"pbkdf2_sha256$310000${_encode(actual_salt)}${_encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", maxsplit=3)
        if algorithm != "pbkdf2_sha256" or int(iterations) != 310_000:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _decode(salt), int(iterations)
        )
        return hmac.compare_digest(actual, _decode(expected))
    except (ValueError, TypeError):
        return False
