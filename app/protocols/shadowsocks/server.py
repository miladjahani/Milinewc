import asyncio
import os
import struct
import logging
from typing import Dict, Optional, Tuple
from app.protocols.shadowsocks.crypto import (
    CIPHER_CONFIGS, evp_bytes_to_key, derive_subkey,
    AEADCipherState, parse_ss_target_address
)
from app.networking.relay import connect_outbound
from app.services.repository import repo

logger = logging.getLogger("miliconfig.shadowsocks")

class ShadowSocksServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8388):
        self.host = host
        self.port = port
        self.server: Optional[asyncio.AbstractServer] = None
        self.is_running = False

    async def start(self):
        """Start the native Python ShadowSocks AEAD TCP server."""
        if self.is_running:
            return
        try:
            self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
            self.is_running = True
            logger.info(f"ShadowSocks server listening on {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start ShadowSocks server on {self.host}:{self.port}: {e}")

    async def stop(self):
        """Stop the ShadowSocks server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.is_running = False
            logger.info("ShadowSocks server stopped")

    async def handle_client(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        """Handle incoming AEAD ShadowSocks TCP connection."""
        active_creds = repo.list_all_active_ss()
        if not active_creds:
            client_writer.close()
            return

        # Default to chacha20-ietf-poly1305 config
        cfg = CIPHER_CONFIGS["chacha20-ietf-poly1305"]
        salt_size = cfg["salt_size"]

        try:
            salt = await client_reader.readexactly(salt_size)
        except Exception:
            client_writer.close()
            return

        # Attempt to decrypt first chunk with available user credentials
        authenticated_user = None
        decrypt_state = None
        matched_cred = None

        # Peek / read the first 2-byte encrypted length + 16-byte tag (18 bytes total)
        try:
            enc_len_chunk = await client_reader.readexactly(2 + cfg["tag_size"])
        except Exception:
            client_writer.close()
            return

        for cred in active_creds:
            c_cfg = CIPHER_CONFIGS.get(cred.method, cfg)
            master_key = evp_bytes_to_key(cred.password, c_cfg["key_size"])
            subkey = derive_subkey(master_key, salt, c_cfg["key_size"])
            temp_cipher = AEADCipherState(cred.method, subkey)
            try:
                dec_len_bytes = temp_cipher.decrypt(enc_len_chunk)
                payload_len = struct.unpack("!H", dec_len_bytes)[0]
                authenticated_user = repo.get_user_by_id(cred.user_id)
                decrypt_state = temp_cipher
                matched_cred = cred
                break
            except Exception:
                continue

        if not authenticated_user or not decrypt_state:
            logger.warning("ShadowSocks authentication failed: no matching credentials")
            client_writer.close()
            return

        # Check user status
        if authenticated_user.status != "active":
            logger.warning(f"ShadowSocks connection rejected: user {authenticated_user.username} is {authenticated_user.status}")
            client_writer.close()
            return

        # Read encrypted payload of length + tag
        enc_payload = await client_reader.readexactly(payload_len + cfg["tag_size"])
        dec_payload = decrypt_state.decrypt(enc_payload)

        # Parse target address and initial data
        ok, target_addr, target_port, initial_data, err = parse_ss_target_address(dec_payload)
        if not ok:
            logger.warning(f"Failed to parse ShadowSocks target address: {err}")
            client_writer.close()
            return

        logger.info(f"ShadowSocks user {authenticated_user.username} connecting to {target_addr}:{target_port}")

        # Connect to outbound destination
        try:
            remote_reader, remote_writer = await connect_outbound(target_addr, target_port)
        except Exception as e:
            logger.error(f"Failed to connect outbound {target_addr}:{target_port}: {e}")
            client_writer.close()
            return

        # Write initial data to remote if any
        if initial_data:
            remote_writer.write(initial_data)
            await remote_writer.drain()

        # Initialize server-to-client encryptor
        server_salt = os.urandom(cfg["salt_size"])
        server_master_key = evp_bytes_to_key(matched_cred.password, cfg["key_size"])
        server_subkey = derive_subkey(server_master_key, server_salt, cfg["key_size"])
        encrypt_state = AEADCipherState(matched_cred.method, server_subkey)

        # Send server salt
        client_writer.write(server_salt)
        await client_writer.drain()

        # Traffic counters
        total_up = len(salt) + len(enc_len_chunk) + len(enc_payload)
        total_down = len(server_salt)

        async def c2r():
            nonlocal total_up
            try:
                while True:
                    len_bytes_enc = await client_reader.readexactly(2 + cfg["tag_size"])
                    len_bytes = decrypt_state.decrypt(len_bytes_enc)
                    chunk_len = struct.unpack("!H", len_bytes)[0]
                    chunk_enc = await client_reader.readexactly(chunk_len + cfg["tag_size"])
                    chunk = decrypt_state.decrypt(chunk_enc)
                    remote_writer.write(chunk)
                    await remote_writer.drain()
                    total_up += len(len_bytes_enc) + len(chunk_enc)
            except Exception:
                pass
            finally:
                try:
                    remote_writer.close()
                except Exception:
                    pass

        async def r2c():
            nonlocal total_down
            try:
                while True:
                    data = await remote_reader.read(16384)
                    if not data:
                        break
                    len_hdr = struct.pack("!H", len(data))
                    enc_hdr = encrypt_state.encrypt(len_hdr)
                    enc_body = encrypt_state.encrypt(data)
                    client_writer.write(enc_hdr + enc_body)
                    await client_writer.drain()
                    total_down += len(enc_hdr) + len(enc_body)
            except Exception:
                pass
            finally:
                try:
                    client_writer.close()
                except Exception:
                    pass

        await asyncio.gather(c2r(), r2c())
        repo.record_user_traffic(authenticated_user.id, total_up, total_down)

ss_server = ShadowSocksServer()
