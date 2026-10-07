import unittest
from app.database import db
from app.services.repository import repo
from app.migrate_cfnew import parse_cfnew_kv

class TestMigration(unittest.TestCase):
    def setUp(self):
        db.init_schema()

    def test_migrate_sample_cfnew_kv(self):
        sample = {
            "u": "7b134d1f-827b-472d-9443-4dc975b9f7a1",
            "p": "104.16.12.34:443",
            "s": "socks5://user:pass@127.0.0.1:1080",
            "wk": "SG",
            "ev": "yes",
            "et": "yes",
            "yx": "1.1.1.1:443#Singapore Premium,1.0.0.1:443#Singapore Backup"
        }
        parse_cfnew_kv(sample)

        # Verify user created
        user = repo.get_user_by_uuid("7b134d1f-827b-472d-9443-4dc975b9f7a1")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "cfnew_migrated_user")

        # Verify settings migrated
        outbound = repo.get_setting("outbound_proxy")
        self.assertEqual(outbound, "socks5://user:pass@127.0.0.1:1080")

        # Verify nodes created with miliconfig prefix
        nodes = repo.list_nodes()
        migrated_nodes = [n for n in nodes if "Singapore" in n.name]
        self.assertGreaterEqual(len(migrated_nodes), 2)
        for n in migrated_nodes:
            self.assertTrue(n.name.startswith("miliconfig • "))

        # Verify ProxyIP imported
        pips = repo.list_proxy_ips()
        imported_pip = [p for p in pips if p.address == "104.16.12.34"]
        self.assertTrue(len(imported_pip) > 0)

if __name__ == "__main__":
    unittest.main()
