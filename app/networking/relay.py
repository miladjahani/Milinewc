import asyncio
import socket
import struct
import base64
from urllib.parse import urlparse
from typing import Tuple, Optional, Callable, List
from app.networking.dns import dns_resolver

BUFFER_SIZE = 32 * 1024

async def connect_direct(host: str, port: int, timeout: float = 10.0) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Establish direct TCP connection to target host and port."""
    resolved_host = await dns_resolver.resolve(host)
    return await asyncio.wait_for(asyncio.open_connection(resolved_host, port), timeout=timeout)

async def connect_socks5(proxy_host: str, proxy_port: int, target_host: str, target_port: int,
                         username: Optional[str] = None, password: Optional[str] = None,
                         timeout: float = 10.0) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Establish SOCKS5 tunnel connection (RFC 1928, RFC 1929)."""
    resolved_proxy = await dns_resolver.resolve(proxy_host)
    reader, writer = await asyncio.wait_for(asyncio.open_connection(resolved_proxy, proxy_port), timeout=timeout)

    # Handshake greeting
    if username and password:
        writer.write(b"\x05\x02\x00\x02")  # Methods: No Auth, Username/Password
    else:
        writer.write(b"\x05\x01\x00")  # Method: No Auth
    await writer.drain()

    resp = await reader.readexactly(2)
    if resp[0] != 5:
        writer.close()
        raise ConnectionError(f"Invalid SOCKS5 version: {resp[0]}")

    chosen_method = resp[1]
    if chosen_method == 0xFF:
        writer.close()
        raise ConnectionError("SOCKS5 server rejected all auth methods")

    if chosen_method == 0x02:  # Username / Password authentication
        u_bytes = username.encode("utf-8")
        p_bytes = password.encode("utf-8")
        req = b"\x01" + bytes([len(u_bytes)]) + u_bytes + bytes([len(p_bytes)]) + p_bytes
        writer.write(req)
        await writer.drain()
        auth_resp = await reader.readexactly(2)
        if auth_resp[1] != 0:
            writer.close()
            raise ConnectionError("SOCKS5 authentication failed")

    # Connect command (CMD 0x01: Connect)
    try:
        # Check if IPv4
        ip_bytes = socket.inet_aton(target_host)
        addr_block = b"\x01" + ip_bytes
    except Exception:
        # Domain name
        h_bytes = target_host.encode("utf-8")
        addr_block = b"\x03" + bytes([len(h_bytes)]) + h_bytes

    port_bytes = struct.pack("!H", target_port)
    cmd = b"\x05\x01\x00" + addr_block + port_bytes
    writer.write(cmd)
    await writer.drain()

    cmd_resp = await reader.readexactly(4)
    if cmd_resp[1] != 0:
        writer.close()
        raise ConnectionError(f"SOCKS5 connect error code: {cmd_resp[1]}")

    # Read bound address
    bnd_addr_type = cmd_resp[3]
    if bnd_addr_type == 1:
        await reader.readexactly(4 + 2)
    elif bnd_addr_type == 3:
        d_len = (await reader.readexactly(1))[0]
        await reader.readexactly(d_len + 2)
    elif bnd_addr_type == 4:
        await reader.readexactly(16 + 2)

    return reader, writer

async def connect_http_connect(proxy_host: str, proxy_port: int, target_host: str, target_port: int,
                               username: Optional[str] = None, password: Optional[str] = None,
                               use_tls: bool = False, timeout: float = 10.0) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Establish HTTP / HTTPS CONNECT tunnel."""
    resolved_proxy = await dns_resolver.resolve(proxy_host)
    ssl_context = True if use_tls else None
    reader, writer = await asyncio.wait_for(asyncio.open_connection(resolved_proxy, proxy_port, ssl=ssl_context), timeout=timeout)

    headers = [
        f"CONNECT {target_host}:{target_port} HTTP/1.1",
        f"Host: {target_host}:{target_port}",
        "Proxy-Connection: Keep-Alive",
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    ]
    if username and password:
        creds = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        headers.append(f"Proxy-Authorization: Basic {creds}")
    headers.append("\r\n")

    writer.write("\r\n".join(headers).encode("utf-8"))
    await writer.drain()

    # Read HTTP status line
    status_line = await reader.readline()
    if not status_line or not (b"200" in status_line):
        writer.close()
        raise ConnectionError(f"HTTP CONNECT failed: {status_line.decode('utf-8', errors='ignore').strip()}")

    # Consume response headers until empty line
    while True:
        line = await reader.readline()
        if not line or line in (b"\r\n", b"\n"):
            break

    return reader, writer

async def connect_outbound(target_host: str, target_port: int,
                           outbound_url: Optional[str] = None,
                           outbound_mode: str = "",
                           proxyip_list: Optional[List[str]] = None,
                           timeout: float = 8.0) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """
    Intelligent outbound connection router respecting cfnew `s` and `qj` conventions:
    - outbound_mode == 'only': strictly route through proxy; do not fallback to direct/ProxyIP.
    - outbound_mode == 'no': try direct first; fallback to proxy if direct fails.
    - outbound_mode == '' (default): try proxy first; fallback to direct / ProxyIP.
    """
    outbound = (outbound_url or "").strip()
    mode = outbound_mode.strip().lower()

    async def _try_proxy():
        parsed = urlparse(outbound)
        scheme = parsed.scheme.lower() if "://" in outbound else "socks5"
        host = parsed.hostname or (outbound.split("@")[-1].split(":")[0] if "@" in outbound else outbound.split(":")[0])
        port = parsed.port or (int(outbound.split(":")[-1]) if ":" in outbound else 1080)
        username = parsed.username
        password = parsed.password

        if scheme in ("http", "https"):
            return await connect_http_connect(host, port, target_host, target_port, username, password, use_tls=(scheme == "https"), timeout=timeout)
        else:
            return await connect_socks5(host, port, target_host, target_port, username, password, timeout=timeout)

    # Case 1: mode == 'only'
    if outbound and mode == "only":
        return await _try_proxy()

    # Case 2: mode == 'no' (Direct first, proxy fallback)
    if mode == "no":
        try:
            return await connect_direct(target_host, target_port, timeout=timeout)
        except Exception:
            if outbound:
                return await _try_proxy()
            raise

    # Case 3: default (Proxy first if configured, then direct/ProxyIP fallback)
    if outbound:
        try:
            return await _try_proxy()
        except Exception:
            pass

    # Try ProxyIP if specified
    if proxyip_list:
        for pip in proxyip_list:
            try:
                parts = pip.split(":")
                pip_host = parts[0]
                pip_port = int(parts[1]) if len(parts) > 1 else 443
                return await connect_direct(pip_host, pip_port, timeout=timeout)
            except Exception:
                continue

    # Fallback to direct
    return await connect_direct(target_host, target_port, timeout=timeout)

async def pipe_streams(client_reader: asyncio.StreamReader,
                       client_writer: asyncio.StreamWriter,
                       remote_reader: asyncio.StreamReader,
                       remote_writer: asyncio.StreamWriter,
                       on_traffic: Optional[Callable[[int, int], None]] = None):
    """Bidirectionally stream data between client and remote connection with traffic callbacks."""
    total_up = 0
    total_down = 0

    async def c2r():
        nonlocal total_up
        try:
            while True:
                data = await client_reader.read(BUFFER_SIZE)
                if not data:
                    break
                remote_writer.write(data)
                await remote_writer.drain()
                total_up += len(data)
                if on_traffic and total_up % 65536 < len(data):
                    on_traffic(len(data), 0)
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
                data = await remote_reader.read(BUFFER_SIZE)
                if not data:
                    break
                client_writer.write(data)
                await client_writer.drain()
                total_down += len(data)
                if on_traffic and total_down % 65536 < len(data):
                    on_traffic(0, len(data))
        except Exception:
            pass
        finally:
            try:
                client_writer.close()
            except Exception:
                pass

    await asyncio.gather(c2r(), r2c())
    if on_traffic:
        on_traffic(total_up, total_down)
