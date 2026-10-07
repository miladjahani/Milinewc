import unittest
import asyncio
import os
import struct
import uuid
from app.protocols.shadowsocks.crypto import (
    CIPHER_CONFIGS, evp_bytes_to_key, derive_subkey,
    AEADCipherState, parse_ss_target_address
)
from app.protocols.shadowsocks.server import ShadowSocksServer
from app.services.repository import repo
from app.database import db

class TestShadowSocks(unittest.TestCase):
    def setUp(self):
        db.init_schema()

    def test_evp_and_hkdf_derivation(self):
        password = "test_password_2026"
        master_key = evp_bytes_to_key(password, 32)
        self.assertEqual(len(master_key), 32)

        salt = os.urandom(32)
        subkey = derive_subkey(master_key, salt, 32)
        self.assertEqual(len(subkey), 32)

    def test_aead_cipher_chacha20(self):
        password = "chacha_secret_test"
        salt = os.urandom(32)
        master_key = evp_bytes_to_key(password, 32)
        subkey = derive_subkey(master_key, salt, 32)

        enc = AEADCipherState("chacha20-ietf-poly1305", subkey)
        dec = AEADCipherState("chacha20-ietf-poly1305", subkey)

        plaintext = b"MILICONFIG ShadowSocks AEAD Real Payload Verification"
        ciphertext = enc.encrypt(plaintext)
        self.assertNotEqual(ciphertext, plaintext)

        decrypted = dec.decrypt(ciphertext)
        self.assertEqual(decrypted, plaintext)

    def test_aead_cipher_aes256gcm(self):
        password = "aes_secret_test"
        salt = os.urandom(32)
        master_key = evp_bytes_to_key(password, 32)
        subkey = derive_subkey(master_key, salt, 32)

        enc = AEADCipherState("aes-256-gcm", subkey)
        dec = AEADCipherState("aes-256-gcm", subkey)

        plaintext = b"Test AES-256-GCM encryption chunk"
        ciphertext = enc.encrypt(plaintext)
        decrypted = dec.decrypt(ciphertext)
        self.assertEqual(decrypted, plaintext)

    def test_parse_target_address(self):
        data = b"\x01\x7f\x00\x00\x01" + struct.pack("!H", 8080) + b"HELLO SERVER"
        ok, host, port, payload, err = parse_ss_target_address(data)
        self.assertTrue(ok, err)
        self.assertEqual(host, "127.0.0.1")
        self.assertEqual(port, 8080)
        self.assertEqual(payload, b"HELLO SERVER")

    def test_shadowsocks_server_integration(self):
        """Integration test: start server, connect real client, send AEAD encrypted payload."""
        async def _run_integration():
            unique_uname = f"ss_user_{uuid.uuid4().hex[:8]}"
            user = repo.create_user(unique_uname, "SS Tester")
            ss_pwd = "ss_integration_pwd_2026"
            test_port = 18388
            repo.create_or_update_ss(user.id, password=ss_pwd, port=test_port)

            server = ShadowSocksServer(host="127.0.0.1", port=test_port)
            await server.start()
            self.assertTrue(server.is_running)

            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", test_port)
                
                cfg = CIPHER_CONFIGS["chacha20-ietf-poly1305"]
                client_salt = os.urandom(cfg["salt_size"])
                client_master_key = evp_bytes_to_key(ss_pwd, cfg["key_size"])
                client_subkey = derive_subkey(client_master_key, client_salt, cfg["key_size"])
                client_cipher = AEADCipherState("chacha20-ietf-poly1305", client_subkey)

                writer.write(client_salt)
                await writer.drain()

                # Encrypt payload
                target_payload = b"\x01\x7f\x00\x00\x01\x00\x09PING"
                len_hdr = struct.pack("!H", len(target_payload))
                writer.write(client_cipher.encrypt(len_hdr))
                writer.write(client_cipher.encrypt(target_payload))
                await writer.drain()

                await asyncio.sleep(0.05)
                writer.close()
                await writer.wait_closed()
            finally:
                await server.stop()

        asyncio.run(_run_integration())

if __name__ == "__main__":
    unittest.main()
