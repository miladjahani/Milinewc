import unittest
import uuid
from app.database import db
from app.services.repository import repo

class TestUsers(unittest.TestCase):
    def setUp(self):
        db.init_schema()

    def test_create_and_fetch_user(self):
        username = f"user_{uuid.uuid4().hex[:8]}"
        user = repo.create_user(
            username=username,
            display_name="Test User",
            traffic_limit=1000000
        )
        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, username)
        self.assertTrue(len(user.uuid) == 36)
        self.assertTrue(len(user.subscription_token) > 0)
        self.assertEqual(user.status, "active")

        # Fetch by UUID
        fetched = repo.get_user_by_uuid(user.uuid)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, user.id)

        # Fetch by subscription token
        fetched_sub = repo.get_user_by_sub_token(user.subscription_token)
        self.assertIsNotNone(fetched_sub)
        self.assertEqual(fetched_sub.id, user.id)

    def test_user_traffic_recording(self):
        username = f"traffic_user_{uuid.uuid4().hex[:8]}"
        user = repo.create_user(username=username, display_name="Traffic Tester")
        repo.record_user_traffic(user.id, upload_bytes=1024, download_bytes=2048)
        
        updated = repo.get_user_by_id(user.id)
        self.assertEqual(updated.upload, 1024)
        self.assertEqual(updated.download, 2048)
        self.assertIsNotNone(updated.last_seen_at)

    def test_reset_uuid_and_token(self):
        username = f"reset_user_{uuid.uuid4().hex[:8]}"
        user = repo.create_user(username=username, display_name="Reset Tester")
        old_uuid = user.uuid
        old_token = user.subscription_token

        new_uuid = repo.reset_user_uuid(user.id)
        new_token = repo.reset_user_sub_token(user.id)

        self.assertNotEqual(old_uuid, new_uuid)
        self.assertNotEqual(old_token, new_token)
        
        updated = repo.get_user_by_id(user.id)
        self.assertEqual(updated.uuid, new_uuid)
        self.assertEqual(updated.subscription_token, new_token)

if __name__ == "__main__":
    unittest.main()
