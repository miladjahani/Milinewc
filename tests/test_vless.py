import unittest
import struct
import uuid
from app.protocols.vless.parser import parse_vless_header, build_vless_response_header

class TestVless(unittest.TestCase):
    def test_parse_vless_ipv4_tcp(self):
        user_uuid = uuid.uuid4()
        # Header format:
        # version (1B) + UUID (16B) + addon_len (1B = 0) + cmd (1B = 1 TCP) + port (2B = 443) + addr_type (1B = 1 IPv4) + IP (4B: 1.1.1.1) + payload
        data = (
            b"\x00" +
            user_uuid.bytes +
            b"\x00" +
            b"\x01" +
            struct.pack("!H", 443) +
            b"\x01" +
            bytes([1, 1, 1, 1]) +
            b"GET / HTTP/1.1\r\n\r\n"
        )
        ok, req, err = parse_vless_header(data)
        self.assertTrue(ok, err)
        self.assertEqual(req.version, 0)
        self.assertEqual(req.user_uuid, str(user_uuid))
        self.assertEqual(req.command, 1)
        self.assertEqual(req.target_port, 443)
        self.assertEqual(req.address_type, 1)
        self.assertEqual(req.target_address, "1.1.1.1")
        self.assertEqual(req.payload, b"GET / HTTP/1.1\r\n\r\n")

    def test_parse_vless_domain_udp(self):
        user_uuid = uuid.uuid4()
        domain = b"dns.google"
        data = (
            b"\x00" +
            user_uuid.bytes +
            b"\x00" +
            b"\x02" +  # UDP
            struct.pack("!H", 53) +
            b"\x02" +  # Domain
            bytes([len(domain)]) +
            domain +
            b"\x12\x34\x01\x00"
        )
        ok, req, err = parse_vless_header(data)
        self.assertTrue(ok, err)
        self.assertEqual(req.command, 2)
        self.assertEqual(req.target_port, 53)
        self.assertEqual(req.target_address, "dns.google")
        self.assertEqual(req.payload, b"\x12\x34\x01\x00")

    def test_parse_vless_too_short(self):
        ok, req, err = parse_vless_header(b"\x00\x01\x02")
        self.assertFalse(ok)
        self.assertIn("too short", err)

    def test_build_response_header(self):
        resp = build_vless_response_header(0)
        self.assertEqual(resp, b"\x00\x00")

if __name__ == "__main__":
    unittest.main()
