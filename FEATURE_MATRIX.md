# MILICONFIG: Feature Matrix & Capability Parity

This matrix outlines every feature present in the original `byjoey/cfnew` codebase alongside newly added enterprise features in **MILICONFIG**, detailing their implementation status and test verification.

| Feature | Original (`cfnew`) | Ported (`MILICONFIG`) | Tested | Notes / Implementation Strategy |
| :--- | :---: | :---: | :---: | :--- |
| **VLESS** | ✓ | ✓ | ✓ | Python binary packet parser & serializer, UUID auth, TCP/UDP command handling |
| **Trojan** | ✓ | ✓ | ✓ | SHA224 password hashing, CRLF frame parsing, TCP/UDP stream relay |
| **WebSocket** | ✓ | ✓ | ✓ | ASGI WebSocket transport with binary frame pipelining & backpressure |
| **xHTTP** | ✓ | ✓ | ✓ | HTTP POST pseudo-streaming with chunked transfer and randomized anti-DPI padding |
| **ProxyIP** | ✓ | ✓ | ✓ | Upstream fallback pools, CF Anycast IPs, custom ProxyIP mapping & health verification |
| **DNS** | ✓ | ✓ | ✓ | Asynchronous UDP/TCP DNS proxy, port 53 routing, DoH (DNS-over-HTTPS via httpx) |
| **ECH** | ✓ | ✓ | ✓ | Encrypted Client Hello configuration discovery and client config generator |
| **ALPN** | ✓ | ✓ | ✓ | Configurable ALPN negotiation parameter generator (`h3`, `h2`, `http/1.1`) |
| **Preferred IP** | ✓ | ✓ | ✓ | Dynamic preferred IP/domain lists, API management, and latency filtering |
| **Custom Path** | ✓ | ✓ | ✓ | Configurable URL prefix routing (`d` variable, `/custom-path`) |
| **UUID Path** | ✓ | ✓ | ✓ | Direct UUID endpoint path routing (`/{uuid}`) with format verification |
| **User-Agent detection** | ✓ | ✓ | ✓ | Automatic client UA parsing (Clash, Sing-box, V2Ray, Shadowrocket, Surge, etc.) |
| **Subscription** | ✓ | ✓ | ✓ | Multi-format subscription generator (Base64, Clash/Mihomo, Sing-box, V2Ray) |
| **ShadowSocks** | **NEW** | ✓ | ✓ | Native Python asyncio AEAD ShadowSocks server (chacha20-poly1305, aes-256-gcm) |
| **Multi User** | **NEW** | ✓ | ✓ | Relational User model with UUID, token, traffic quota, expiry, and device tracking |
| **Admin Panel** | **NEW** | ✓ | ✓ | Dark Glassmorphic Neon dashboard with management tabs and zero fake metrics |

---

## Detailed Feature Specifications

### 1. Protocol Core & Transports
- **VLESS Protocol**:
  - Implements VLESS v0 binary specification.
  - Multi-user authentication: incoming client UUIDs are validated against the database in real-time.
  - Commands supported: `0x01` (TCP stream outbound) and `0x02` (UDP / DNS port 53 relay).
  - Outbound connection is established to target destination with response header `[0x00, 0x00]` written back before transparent streaming.
- **Trojan Protocol**:
  - Validates client 56-character SHA224 password hash against user credentials.
  - Supports WebSocket transport and native TCP stream.
- **xHTTP Transport**:
  - Implements the HTTP POST streaming transport used in cfnew.
  - Generates and verifies anti-censorship padding query parameters and headers (`X-Padding`).
- **ShadowSocks Engine (NEW)**:
  - Complete Python asyncio TCP & UDP implementation.
  - Supported modern AEAD ciphers: `chacha20-ietf-poly1305`, `aes-256-gcm`, `aes-128-gcm`.
  - Individual per-user credentials and port configuration.
  - Emits real `ss://` subscription links compatible with all standard clients.

### 2. Networking & Outbound Relay
- **SOCKS5 Outbound**:
  - Full RFC 1928 / RFC 1929 client implementation in Python.
  - Supports no-auth and username/password authentication (`user:pass@host:port`).
- **HTTP / HTTPS CONNECT Outbound**:
  - Establishes HTTP CONNECT tunnels to upstream HTTP/HTTPS proxies.
- **ProxyIP System**:
  - Integrated Anycast pool with failover mechanics.
  - Respects `qj` routing modes:
    - Default: Proxy first, fallback to direct.
    - `no`: Direct first, fallback to proxy.
    - `only`: Proxy only (prevents IP leakage).

### 3. Subscription & Client Management
- **Naming Rule**:
  - **ALL** client-facing node names strictly start with `miliconfig` (e.g. `miliconfig-01`, `miliconfig-US`, `miliconfig • VLESS`, `miliconfig • Trojan`, `miliconfig • ShadowSocks`).
- **Client Auto-Detection**:
  - Detects incoming `User-Agent`:
    - `clash`, `meta`, `mihomo`, `stash`, `flclash` -> Clash Meta / Mihomo YAML
    - `sing-box`, `singbox` -> Sing-box JSON (v1.12+)
    - `v2ray`, `v2rayng`, `neko`, `shadowrocket` -> Base64 URI list
    - `surge`, `loon`, `quanx` -> Targeted client configurations
  - Explicit parameter override via `?target=clash`, `?target=singbox`, `?target=v2ray`, `?target=ss`.
- **Unique Per-User Subscriptions**:
  - Endpoint: `/sub/{subscription_token}` or `/api/sub/{subscription_token}`.
  - Generates configurations filtered by user permissions, active status, and non-expired quota.

### 4. Admin Panel & Multi-User Governance
- Responsive SaaS dashboard built with Tailwind CSS / CSS variables in Dark Glassmorphism and Neon Green palette.
- Management modules for Users, Nodes, Subscriptions, ShadowSocks, ProxyIPs, DNS Profiles, Routing Rules, and Audit Logs.
- Real-time telemetry: active user count, healthy node count, bandwidth usage (upload/download), active sessions. Zero simulated or fabricated metrics.
