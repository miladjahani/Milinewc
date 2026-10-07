import unittest
from app.database import db
from app.services.repository import repo

class TestProxyIP(unittest.TestCase):
    def setUp(self):
        db.init_schema()

    def test_proxyip_lifecycle(self):
        pip = repo.add_proxy_ip("198.51.100.1", port=443, region="SG")
        self.assertIsNotNone(pip.id)
        self.assertEqual(pip.address, "198.51.100.1")
        self.assertEqual(pip.region, "SG")

        pips = repo.list_proxy_ips()
        self.assertTrue(any(p.id == pip.id for p in pips))

        # Update latency
        repo.update_proxy_ip_latency(pip.id, latency_ms=45.2, is_active=True)
        updated = [p for p in repo.list_proxy_ips() if p.id == pip.id][0]
        self.assertEqual(updated.latency_ms, 45.2)

        # Delete
        repo.delete_proxy_ip(pip.id)
        remaining = [p for p in repo.list_proxy_ips() if p.id == pip.id]
        self.assertEqual(len(remaining), 0)

if __name__ == "__main__":
    unittest.main()
