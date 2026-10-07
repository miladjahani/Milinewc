import unittest
import time
from app.security.security import (
    hash_password, verify_password, create_access_token,
    verify_access_token, rate_limiter
)
from app.services.repository import repo
from app.database import db

class TestAuth(unittest.TestCase):
    def setUp(self):
        db.init_schema()

    def test_password_hashing_and_verification(self):
        pwd = "SecretPassword123!"
        hashed = hash_password(pwd)
        self.assertTrue(hashed.startswith("pbkdf2_sha256$"))
        self.assertTrue(verify_password(pwd, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

    def test_jwt_token_creation_and_verification(self):
        payload = {"sub": "admin_test", "role": "superadmin"}
        token = create_access_token(payload, expires_delta_seconds=60)
        decoded = verify_access_token(token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["sub"], "admin_test")
        self.assertEqual(decoded["role"], "superadmin")

    def test_jwt_token_expiration(self):
        payload = {"sub": "admin_test"}
        # Create expired token
        token = create_access_token(payload, expires_delta_seconds=-10)
        decoded = verify_access_token(token)
        self.assertIsNone(decoded)

    def test_jwt_tampered_token(self):
        payload = {"sub": "admin_test"}
        token = create_access_token(payload, expires_delta_seconds=60)
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.tampered_sig"
        self.assertIsNone(verify_access_token(tampered))

    def test_rate_limiter(self):
        key = "test_ip_127_0_0_1"
        for _ in range(5):
            self.assertTrue(rate_limiter.is_allowed(key, max_requests=5, window_seconds=10))
        # 6th request should fail
        self.assertFalse(rate_limiter.is_allowed(key, max_requests=5, window_seconds=10))

if __name__ == "__main__":
    unittest.main()
