import unittest
import struct
from app.protocols.trojan.parser import parse_trojan_header, compute_trojan_hash

class TestTrojan(unittest.TestCase):
    def test_trojan_hash_computation(self):
        pwd = "test_password_123"
        h = compute_trojan_hash(pwd)
        self.assertEqual(len(h), 56)  # SHA224 hex string length

    def test_parse_trojan_ipv4(self):
        pwd = "my_trojan_pass"
        h = compute_trojan_hash(pwd)
        data = (
            h.encode("ascii") +
            b"\r\n" +
            b"\x01" +  # Command: Connect
            b"\x01" +  # Address type: IPv4
            bytes([8, 8, 8, 8]) +
            struct.pack("!H", 853) +
            b"\r\n" +
            b"Initial TLS Payload"
        )
        ok, req, err = parse_trojan_header(data)
        self.assertTrue(ok, err)
        self.assertEqual(req.password_hash.lower(), h.lower())
        self.assertEqual(req.command, 1)
        self.assertEqual(req.address_type, 1)
        self.assertEqual(req.target_address, "8.8.8.8")
        self.assertEqual(req.target_port, 853)
        self.assertEqual(req.payload, b"Initial TLS Payload")

    def test_parse_trojan_domain(self):
        pwd = "domain_trojan_pass"
        h = compute_trojan_hash(pwd)
        domain = b"example.com"
        data = (
            h.encode("ascii") +
            b"\r\n" +
            b"\x01" +
            b"\x03" +  # Address type: Domain
            bytes([len(domain)]) +
            domain +
            struct.pack("!H", 443) +
            b"\r\n" +
            b"GET / HTTP/1.1\r\n\r\n"
        )
        ok, req, err = parse_trojan_header(data)
        self.assertTrue(ok, err)
        self.assertEqual(req.target_address, "example.com")
        self.assertEqual(req.target_port, 443)
        self.assertEqual(req.payload, b"GET / HTTP/1.1\r\n\r\n")

    def test_parse_trojan_invalid_crlf(self):
        pwd = "bad_pass"
        h = compute_trojan_hash(pwd)
        data = h.encode("ascii") + b"XX" + b"\x01\x01\x08\x08\x08\x08\x01\xbb\r\n"
        ok, req, err = parse_trojan_header(data)
        self.assertFalse(ok)
        self.assertIn("CRLF", err)

if __name__ == "__main__":
    unittest.main()
