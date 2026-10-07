import os
import time
import json
import base64
import hmac
import hashlib
import secrets
from typing import Optional, Dict, Any, Tuple
from app.config import settings

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with a cryptographically secure random salt."""
    salt = secrets.token_bytes(16)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${base64.b64encode(salt).decode('utf-8')}${base64.b64encode(derived).decode('utf-8')}"

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored PBKDF2 hash with constant-time comparison."""
    try:
        parts = hashed.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = base64.b64decode(parts[2].encode("utf-8"))
        expected_derived = base64.b64decode(parts[3].encode("utf-8"))
        actual_derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual_derived, expected_derived)
    except Exception:
        return False

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _b64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)

def create_access_token(data: Dict[str, Any], expires_delta_seconds: int = 86400) -> str:
    """Generate a standard RFC 7519 HS256 JSON Web Token."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_delta_seconds
    payload["iat"] = int(time.time())

    h_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    p_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    unsigned = f"{_b64url_encode(h_bytes)}.{_b64url_encode(p_bytes)}"
    sig = hmac.new(settings.JWT_SECRET.encode("utf-8"), unsigned.encode("utf-8"), hashlib.sha256).digest()
    return f"{unsigned}.{_b64url_encode(sig)}"

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode HS256 JWT, checking signature and expiration."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        unsigned = f"{parts[0]}.{parts[1]}"
        expected_sig = hmac.new(settings.JWT_SECRET.encode("utf-8"), unsigned.encode("utf-8"), hashlib.sha256).digest()
        actual_sig = _b64url_decode(parts[2])
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_bytes = _b64url_decode(parts[1])
        payload = json.loads(payload_bytes.decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

class RateLimiter:
    """In-memory sliding window rate limiter for security endpoints."""
    def __init__(self):
        self.records: Dict[str, list] = {}

    def is_allowed(self, key: str, max_requests: int = 5, window_seconds: int = 60) -> bool:
        now = time.time()
        timestamps = self.records.get(key, [])
        timestamps = [t for t in timestamps if now - t < window_seconds]
        if len(timestamps) >= max_requests:
            self.records[key] = timestamps
            return False
        timestamps.append(now)
        self.records[key] = timestamps
        return True

rate_limiter = RateLimiter()
