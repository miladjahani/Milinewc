import os
import struct
import hashlib
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305, AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

CIPHER_CONFIGS = {
    "chacha20-ietf-poly1305": {"key_size": 32, "salt_size": 32, "tag_size": 16, "nonce_size": 12, "type": "chacha20"},
    "aes-256-gcm": {"key_size": 32, "salt_size": 32, "tag_size": 16, "nonce_size": 12, "type": "aes-gcm"},
    "aes-128-gcm": {"key_size": 16, "salt_size": 16, "tag_size": 16, "nonce_size": 12, "type": "aes-gcm"},
}

def evp_bytes_to_key(password: str, key_size: int) -> bytes:
    """Standard OpenSSL / ShadowSocks EVP_BytesToKey using MD5."""
    pw_bytes = password.encode("utf-8")
    m = []
    d = b""
    while len(b"".join(m)) < key_size:
        h = hashlib.md5()
        if d:
            h.update(d)
        h.update(pw_bytes)
        d = h.digest()
        m.append(d)
    return b"".join(m)[:key_size]

def derive_subkey(master_key: bytes, salt: bytes, subkey_len: int) -> bytes:
    """Derive session subkey from master key and salt using HKDF-SHA1 (SIP004)."""
    hkdf = HKDF(
        algorithm=hashes.SHA1(),
        length=subkey_len,
        salt=salt,
        info=b"ss-subkey"
    )
    return hkdf.derive(master_key)

class AEADCipherState:
    def __init__(self, method: str, subkey: bytes):
        self.method = method
        self.config = CIPHER_CONFIGS.get(method, CIPHER_CONFIGS["chacha20-ietf-poly1305"])
        self.subkey = subkey
        self.nonce_int = 0
        
        if self.config["type"] == "chacha20":
            self.aead = ChaCha20Poly1305(subkey)
        elif self.config["type"] == "aes-gcm":
            self.aead = AESGCM(subkey)
        else:
            raise ValueError(f"Unsupported cipher type: {self.config['type']}")

    def get_nonce(self) -> bytes:
        # 12-byte little endian nonce
        n = struct.pack("<Q", self.nonce_int) + b"\x00\x00\x00\x00"
        self.nonce_int += 1
        return n

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = self.get_nonce()
        return self.aead.encrypt(nonce, plaintext, None)

    def decrypt(self, ciphertext: bytes) -> bytes:
        nonce = self.get_nonce()
        return self.aead.decrypt(nonce, ciphertext, None)

def parse_ss_target_address(data: bytes) -> Tuple[bool, str, int, bytes, str]:
    """
    Parse SOCKS5/ShadowSocks target address from decrypted payload.
    Format:
    - 1 byte: addr_type (1: IPv4, 3: Domain, 4: IPv6)
    - Address
    - 2 bytes: Port
    - Remainder: initial data
    """
    if len(data) < 7:
        return False, "", 0, b"", "Address payload too short"

    addr_type = data[0]
    curr = 1

    if addr_type == 1:  # IPv4
        if len(data) < curr + 6:
            return False, "", 0, b"", "Truncated IPv4"
        addr = ".".join(str(b) for b in data[curr:curr + 4])
        curr += 4
    elif addr_type == 3:  # Domain
        domain_len = data[curr]
        curr += 1
        if len(data) < curr + domain_len + 2:
            return False, "", 0, b"", "Truncated domain"
        addr = data[curr:curr + domain_len].decode("utf-8", errors="ignore")
        curr += domain_len
    elif addr_type == 4:  # IPv6
        if len(data) < curr + 18:
            return False, "", 0, b"", "Truncated IPv6"
        parts = [data[curr + i * 2:curr + (i + 1) * 2].hex() for i in range(8)]
        addr = ":".join(parts)
        curr += 16
    else:
        return False, "", 0, b"", f"Invalid SS address type: {addr_type}"

    port = struct.unpack("!H", data[curr:curr + 2])[0]
    curr += 2
    payload = data[curr:]
    return True, addr, port, payload, ""
