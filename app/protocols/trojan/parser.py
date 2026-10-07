import struct
import hashlib
from typing import Tuple, Optional, NamedTuple

class TrojanRequest(NamedTuple):
    password_hash: str
    command: int  # 1: Connect, 3: UDP Associate
    address_type: int
    target_address: str
    target_port: int
    header_length: int
    payload: bytes

def compute_trojan_hash(password: str) -> str:
    """Compute SHA224 hex digest of Trojan password."""
    return hashlib.sha224(password.encode("utf-8")).hexdigest()

def parse_trojan_header(data: bytes) -> Tuple[bool, Optional[TrojanRequest], str]:
    """
    Parse a Trojan protocol header.
    Format:
    - 56 bytes: SHA224 hash in hex
    - 2 bytes: CRLF (\r\n)
    - 1 byte: Command (0x01: Connect, 0x03: UDP)
    - 1 byte: Address type (0x01: IPv4, 0x03: Domain, 0x04: IPv6)
    - Variable: Address
    - 2 bytes: Port
    - 2 bytes: CRLF (\r\n)
    - Remainder: Payload
    """
    if len(data) < 62:
        return False, None, "Trojan packet too short (< 62 bytes)"

    try:
        password_hash = data[:56].decode("ascii")
    except Exception:
        return False, None, "Invalid hex characters in Trojan password hash"

    if data[56:58] != b"\r\n":
        return False, None, "Missing CRLF after Trojan password hash"

    command = data[58]
    if command not in (1, 3):
        return False, None, f"Unsupported Trojan command: {command}"

    addr_type = data[59]
    curr = 60

    if addr_type == 1:  # IPv4 (4 bytes)
        if len(data) < curr + 4:
            return False, None, "Truncated IPv4 in Trojan header"
        target_addr = ".".join(str(b) for b in data[curr:curr + 4])
        curr += 4
    elif addr_type == 3:  # Domain (1 byte len + domain string)
        if len(data) < curr + 1:
            return False, None, "Truncated domain length in Trojan header"
        domain_len = data[curr]
        curr += 1
        if len(data) < curr + domain_len:
            return False, None, "Truncated domain in Trojan header"
        target_addr = data[curr:curr + domain_len].decode("utf-8", errors="ignore")
        curr += domain_len
    elif addr_type == 4:  # IPv6 (16 bytes)
        if len(data) < curr + 16:
            return False, None, "Truncated IPv6 in Trojan header"
        parts = [data[curr + i * 2:curr + (i + 1) * 2].hex() for i in range(8)]
        target_addr = ":".join(parts)
        curr += 16
    else:
        return False, None, f"Unsupported Trojan address type: {addr_type}"

    if len(data) < curr + 4:
        return False, None, "Truncated port/CRLF in Trojan header"

    port = struct.unpack("!H", data[curr:curr + 2])[0]
    curr += 2

    if data[curr:curr + 2] != b"\r\n":
        return False, None, "Missing trailing CRLF in Trojan header"
    curr += 2

    payload = data[curr:]
    req = TrojanRequest(
        password_hash=password_hash,
        command=command,
        address_type=addr_type,
        target_address=target_addr,
        target_port=port,
        header_length=curr,
        payload=payload
    )
    return True, req, ""
