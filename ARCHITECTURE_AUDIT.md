# MILICONFIG: Architecture Audit & CFNEW Source Analysis

## 1. Executive Summary

This document provides a comprehensive audit of the upstream repository [`byjoey/cfnew`](https://github.com/byjoey/cfnew) (v3.1) and outlines the architectural blueprint for its complete Python + Docker + Railway production rewrite under the product name **MILICONFIG**.

The primary objective is to liberate the core proxy, tunneling, subscription generation, and management capabilities from Cloudflare Workers/Pages constraints (`cloudflare:sockets`, `WebSocketPair`, Workers KV) and re-engineer them into a sovereign, high-performance, asynchronous Python platform that runs as a containerized service on Railway or any Docker-compatible infrastructure.

---

## 2. Upstream Repository Audit (`byjoey/cfnew`)

### 2.1 Project Lineage & History
1. **Ancestry**:
   - `zizifn/edgetunnel`: Original implementation of VLESS over Cloudflare Workers WebSockets using `cloudflare:sockets`.
   - `cmliu/edgetunnel`: Introduced ProxyIP pools, reverse proxy addresses, and subscription generation.
   - `byjoey/cfnew`: Added Trojan protocol support, xHTTP transport, ECH (Encrypted Client Hello), graphical terminal panel, Cloudflare KV state persistence, client User-Agent auto-detection, and residential chain (`家宽链式` via Mihomo dialer-proxy and VPN Gate).
2. **Current Upstream Version**: v3.1 (Compatibility Date: `2026-01-20`).

### 2.2 File Inventory in `byjoey/cfnew`
- **`明文源吗`** ("Cleartext Source"): The full un-obfuscated JavaScript source code (~9,335 lines, 445 KB). Contains the entire runtime logic: VLESS packet parser, Trojan parser, xHTTP handler, WebSocket upgrade handler, SOCKS5 client, HTTP CONNECT client, DoH resolver, KV configuration manager, HTML/CSS/JS frontend dashboard, and subscription serializers for Clash, Sing-box, Surge, Loon, Quantumult X, etc.
- **`少年你相信光吗`** ("Obfuscated Source"): Identical logic to `明文源吗`, processed through JavaScript obfuscation/minification for deployment evasion.
- **`edgetunnel经典轻量版`**: A minimal, self-contained standalone version (~1,129 lines) implementing basic VLESS WebSocket proxying, SOCKS5 outbound, and simple Base64 / Clash residential chain subscription.
- **`snippets`**: A simplified variant tailored for Cloudflare Snippets (lightweight routing and headers).
- **`README.md` & `فارسی.md`**: Upstream documentation in Chinese and Persian detailing deployment, environment variables, path routing, and configuration parameters.
- **`.github/workflows`**: Automated packaging and release pipelines for Cloudflare Pages zip bundles.

### 2.3 Deconstructed Upstream Architecture & Logic

#### A. Protocol & Transport Layer
1. **VLESS over WebSocket**:
   - Client initiates HTTP request with header `Upgrade: websocket`.
   - Worker accepts WebSocket connection via `new WebSocketPair()`.
   - First binary message contains the VLESS header:
     - `Byte 0`: Protocol Version (0x00).
     - `Bytes 1..16`: 16-byte UUID (compared against configured `u` / `认证令牌`).
     - `Byte 17`: Addon info length `M` (typically 0).
     - `Bytes 18+M`: Command (`0x01` = TCP stream, `0x02` = UDP/DNS, `0x03` = Mux).
     - Next 2 bytes: Port in big-endian unsigned 16-bit integer.
     - Next 1 byte: Address type (`0x01` = IPv4 4 bytes, `0x02` = Domain 1-byte length prefix, `0x03` = IPv6 16 bytes).
     - Target address payload.
     - Remainder of packet: Client initial payload (e.g. TLS ClientHello or HTTP request).
   - Response header: `[version, 0]` (2 bytes) sent back to client before proxying begins.
2. **Trojan over WebSocket**:
   - First 56 bytes: Hex-encoded SHA224 hash of the Trojan password.
   - CRLF delimiter (`\r\n`).
   - Command byte (`0x01` TCP, `0x03` UDP associate).
   - Address type, Address, Port, and CRLF delimiter (`\r\n`).
   - Remainder: Payload.
3. **xHTTP (Extended HTTP Transport)**:
   - Client sends HTTP POST requests with chunked streaming body and simulated gRPC headers (`application/grpc`, `X-Accel-Buffering: no`).
   - Random query padding and header padding (`X-Padding`) to disguise traffic patterns from deep packet inspection.
4. **Outbound Relay & ProxyIP**:
   - Direct TCP socket connection using `connect()` API.
   - SOCKS5 outbound support with optional authentication (`user:pass@host:port`).
   - HTTP / HTTPS CONNECT outbound tunnel support (`http://` and `https://` schemes with Basic auth).
   - Fallback logic (`qj` mode):
     - Default: Proxy first, fallback to direct.
     - `no`: Direct first, fallback to proxy.
     - `only`: Proxy only, terminate on failure (strict IP leakage prevention).
   - Built-in ProxyIP pools: Cloudflare official Anycast pool (10 verified IP subnets) and regional fallback domains (`UHJveHlJUC...` base64 encoded endpoints for HK, US, SG, JP, KR, DE, SE, NL, FI, GB, Oracle, DigitalOcean, Vultr, Multacom).

#### B. Storage & Configuration State
- Upstream uses Cloudflare Workers KV bound to variable `C`.
- Key `c`: JSON string containing configuration dictionary (`u`, `p`, `s`, `d`, `wk`, `ev`, `et`, `ex`, `ech`, `customDNS`, `customECHDomain`, `alpn`, `yx`, `yxURL`, `scu`, `ena`, `epd`, `epi`, `egi`, `ae`, `rm`, `qj`, `dkby`, `yxby`, `jk`).
- Key `c_ver`: Epoch timestamp string (used for short-window cross-isolate cache invalidation).

#### C. Upstream Inherent Limitations
1. **Single-User Architecture**: Only one global UUID and password exists per deployment. No user quotas, expirations, or multi-tenant separation.
2. **Missing ShadowSocks**: Only supports VLESS and Trojan; lacks native ShadowSocks proxy capabilities.
3. **No Database**: Limited to Workers KV JSON blob with no relational schema, indexing, or audit logging.
4. **Cloudflare Runtime Lock-in**: Hard dependency on `cloudflare:sockets` and Cloudflare-specific APIs prevents self-hosting on standard VPS, Docker, or Railway.

---

## 3. MILICONFIG Target Architecture

MILICONFIG completely replaces the Cloudflare runtime dependencies with an enterprise-grade, asynchronous Python 3.12+ backend.

```
                           +----------------------------------------+
                           |           Internet Clients             |
                           +----------------------------------------+
                                        |              |
                    HTTPS / WSS / xHTTP |              | ShadowSocks TCP/UDP
                                        v              v
+-----------------------------------------------------------------------------------+
| Railway / Docker Container Environment                                            |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                            Uvicorn Web Server                               |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  |                      FastAPI Core Application                         |  |  |
|  |  |                                                                       |  |  |
|  |  |  [ Web UI & Admin Panel ]   [ Subscription Engine ]   [ REST API ]    |  |  |
|  |  |  - Glassmorphic Neon UI     - Auto User-Agent Detect  - Auth (JWT)    |  |  |
|  |  |  - Multi-User Management    - Clash / Sing-box / V2   - Users & Nodes |  |  |
|  |  |  - Node & ProxyIP Control   - miliconfig-prefixed     - Settings/Logs |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |                                                                             |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  |                      Transport & Protocol Layer                       |  |  |
|  |  |  - WebSocket Endpoint (VLESS / Trojan multiplexer)                    |  |  |
|  |  |  - xHTTP Streaming Endpoint (POST chunked + padding)                  |  |  |
|  |  |  - Direct TCP/TLS Relay & Multi-Protocol Authenticator               |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                      ShadowSocks Asyncio Engine                             |  |
|  |  - Native Python TCP & UDP Relay Server                                     |  |
|  |  - Standard AEAD Ciphers (chacha20-poly1305, aes-256-gcm, aes-128-gcm)      |  |
|  |  - Per-User Credentials & Dynamic Multi-Port Listener                       |  |
|  +-----------------------------------------------------------------------------+  |
|                                       |                                           |
|                                       v                                           |
|  +-----------------------------------------------------------------------------+  |
|  |                      Outbound Networking & Routing Engine                   |  |
|  |  - Direct TCP Socket Relay                                                  |  |
|  |  - SOCKS5 Outbound Client (with Auth)                                       |  |
|  |  - HTTP/HTTPS CONNECT Tunnel Client                                         |  |
|  |  - ProxyIP Pool Manager & Failover Rotator                                  |  |
|  |  - Async DNS Resolver (DoH, UDP, TCP)                                       |  |
|  |  - Rule-Based Routing (Domain, CIDR, Port, Mode qj)                         |  |
|  +-----------------------------------------------------------------------------+  |
|                                       |                                           |
|                                       v                                           |
|  +-----------------------------------------------------------------------------+  |
|  |                      Database & State Management                            |  |
|  |  - SQLAlchemy 2.0 ORM (PostgreSQL in Production, SQLite in Dev)              |  |
|  |  - Alembic Schema Migrations                                                |  |
|  |  - Real-Time Traffic Accounting & Session Tracking                          |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 4. Key Engineering Tenets
1. **Zero Runtime Cloudflare Dependency**: Replaces `cloudflare:sockets` with Python's standard `asyncio.open_connection()` and asynchronous socket pooling.
2. **Strict Client-Facing Node Naming**: Every node exposed via subscription or client configuration begins with `miliconfig` (e.g. `miliconfig-01`, `miliconfig • VLESS`, `miliconfig • ShadowSocks`).
3. **True Multi-Tenancy**: Real user models, database-backed authentication, per-user traffic counters, expiry dates, and device limits.
4. **Real Protocol Implementations**: Honest, production-grade protocol implementations with no mocked latency or dummy configs.
