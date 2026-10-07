import struct
import uuid
from typing import Tuple, Optional, NamedTuple

class VlessRequest(NamedTuple):
    version: int
    user_uuid: str
    command: int  # 1: TCP, 2: UDP, 3: MUX
    target_port: int
    address_type: int  # 1: IPv4, 2: Domain, 3: IPv6
    target_address: str
    header_length: int
    payload: bytes

def parse_vless_header(data: bytes) -> Tuple[bool, Optional[VlessRequest], str]:
    """
    Parse a VLESS binary protocol header.
    Format:
    - 1 byte: version (0)
    - 16 bytes: UUID
    - 1 byte: addon length (M)
    - M bytes: addon bytes
    - 1 byte: command (1: TCP, 2: UDP, 3: MUX)
    - 2 bytes: port (big-endian)
    - 1 byte: address type (1: IPv4, 2: Domain, 3: IPv6)
    - Variable: address bytes
    - Remainder: initial client payload
    """
    if len(data) < 24:
        return False, None, "VLESS packet too short (< 24 bytes)"

    version = data[0]
    uuid_bytes = data[1:17]
    try:
        user_uuid = str(uuid.UUID(bytes=uuid_bytes))
    except Exception as e:
        return False, None, f"Invalid UUID in VLESS header: {e}"

    addon_len = data[17]
    cmd_offset = 18 + addon_len
    if len(data) <= cmd_offset + 3:
        return False, None, "Truncated VLESS header after addons"

    command = data[cmd_offset]
    if command not in (1, 2, 3):
        return False, None, f"Unsupported VLESS command: {command}"

    port = struct.unpack("!H", data[cmd_offset + 1:cmd_offset + 3])[0]
    addr_type_offset = cmd_offset + 3
    addr_type = data[addr_type_offset]

    curr = addr_type_offset + 1
    if addr_type == 1:  # IPv4 (4 bytes)
        if len(data) < curr + 4:
            return False, None, "Truncated IPv4 address in VLESS header"
        target_addr = ".".join(str(b) for b in data[curr:curr + 4])
        curr += 4
    elif addr_type == 2:  # Domain (1 byte length + ASCII string)
        if len(data) < curr + 1:
            return False, None, "Truncated domain length in VLESS header"
        domain_len = data[curr]
        curr += 1
        if len(data) < curr + domain_len:
            return False, None, "Truncated domain name in VLESS header"
        target_addr = data[curr:curr + domain_len].decode("utf-8", errors="ignore")
        curr += domain_len
    elif addr_type == 3:  # IPv6 (16 bytes)
        if len(data) < curr + 16:
            return False, None, "Truncated IPv6 address in VLESS header"
        parts = [data[curr + i * 2:curr + (i + 1) * 2].hex() for i in range(8)]
        target_addr = ":".join(parts)
        curr += 16
    else:
        return False, None, f"Invalid address type in VLESS header: {addr_type}"

    payload = data[curr:]
    req = VlessRequest(
        version=version,
        user_uuid=user_uuid,
        command=command,
        target_port=port,
        address_type=addr_type,
        target_address=target_addr,
        header_length=curr,
        payload=payload
    )
    return True, req, ""

def build_vless_response_header(version: int = 0) -> bytes:
    """Build VLESS response header: 1 byte version + 1 byte addon length (0)."""
    return bytes([version, 0])
