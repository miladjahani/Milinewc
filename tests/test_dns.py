import unittest
import asyncio
from app.networking.dns import DNSResolver

class TestDNS(unittest.TestCase):
    def test_ipv4_bypass(self):
        resolver = DNSResolver()
        ip = "1.2.3.4"
        res = asyncio.run(resolver.resolve(ip))
        self.assertEqual(res, ip)

    def test_system_resolution(self):
        resolver = DNSResolver()
        # localhost should always resolve
        res = asyncio.run(resolver.resolve("localhost"))
        self.assertIn(res, ("127.0.0.1", "::1", "localhost"))

    def test_cache_mechanism(self):
        resolver = DNSResolver()
        resolver._cache["custom-domain.local"] = "192.168.1.100"
        res = asyncio.run(resolver.resolve("custom-domain.local"))
        self.assertEqual(res, "192.168.1.100")

if __name__ == "__main__":
    unittest.main()
