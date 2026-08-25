from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

import jwt

from app.core.config import Settings


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"pbkdf2_sha256$120000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(username: str, settings: Settings, *, activity_id: str | None = None) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, object] = {"sub": username, "exp": expires}
    if activity_id:
        payload["activity_id"] = activity_id
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token_payload(token: str, settings: Settings) -> dict[str, object]:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    username = payload.get("sub")
    if not isinstance(username, str) or not username:
        raise jwt.InvalidTokenError("missing subject")
    return payload


def decode_access_token(token: str, settings: Settings) -> str:
    return str(decode_access_token_payload(token, settings)["sub"])
