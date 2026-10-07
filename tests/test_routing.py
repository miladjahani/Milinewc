import unittest
from app.database import db
from app.services.repository import repo
from app.routing.engine import routing_engine

class TestRouting(unittest.TestCase):
    def setUp(self):
        db.init_schema()
        # Add test routing rules
        repo.create_routing_rule("Domestic Direct", domain_pattern="*.ir", outbound="direct")
        repo.create_routing_rule("Apple Direct", domain_pattern="*.apple.com", outbound="direct")
        repo.create_routing_rule("Private Subnet", ip_cidr="10.0.0.0/8", outbound="direct")
        repo.create_routing_rule("Telegram Proxy", domain_pattern="*.telegram.org", outbound="proxy")

    def test_domain_matching(self):
        res1 = routing_engine.match_rule("varzesh3.ir", 443)
        self.assertEqual(res1, "direct")

        res2 = routing_engine.match_rule("api.telegram.org", 443)
        self.assertEqual(res2, "proxy")

        res3 = routing_engine.match_rule("unmatched-site.com", 443)
        self.assertEqual(res3, "direct")  # default

    def test_cidr_matching(self):
        res = routing_engine.match_rule("10.1.2.3", 80)
        self.assertEqual(res, "direct")

if __name__ == "__main__":
    unittest.main()
