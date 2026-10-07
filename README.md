# MILICONFIG

[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Railway](https://img.shields.io/badge/Railway-Deploy-0B0D0E.svg)](https://railway.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**MILICONFIG** is a high-performance, asynchronous Python-based proxy server, management dashboard, and multi-format subscription generator. It is the sovereign, cloud-agnostic rewrite of the Cloudflare-bound [`byjoey/cfnew`](https://github.com/byjoey/cfnew) project, redesigned from the ground up for containerized deployment on **Railway**, Docker, and modern Linux environments.

[🇮🇷 فارسی (Persian Documentation)](./README.fa.md)

---

## Key Highlights

- **Zero Cloudflare Lock-in**: Fully implemented in pure Python (FastAPI + Asyncio) without dependencies on Cloudflare Workers, Pages, or proprietary `cloudflare:sockets` runtime APIs.
- **Enterprise Multi-User Core**: Real relational database backing with user accounts, custom UUIDs, expiry dates, upload/download bandwidth quotas, and session tracking.
- **Real Protocol Implementations**:
  - **VLESS**: Binary packet parser with UUID auth, TCP stream, and UDP/DNS proxying.
  - **Trojan**: SHA224 password hashing, CRLF frame validation, and streaming.
  - **xHTTP**: HTTP POST chunked streaming transport with anti-DPI randomized padding headers.
  - **ShadowSocks (AEAD)**: Native Python asyncio TCP & UDP server supporting `chacha20-ietf-poly1305`, `aes-256-gcm`, and `aes-128-gcm` with per-user credentials.
- **Client-Facing Node Naming**: All client-visible nodes are strictly prefixed with `miliconfig` (e.g. `miliconfig-01 • US Premium`, `miliconfig • VLESS`, `miliconfig • ShadowSocks`).
- **Universal Subscription Engine**:
  - Automatically identifies client `User-Agent` (Clash, Sing-box, V2RayNG, Shadowrocket, Surge, Loon, etc.).
  - Emits native Clash/Mihomo YAML, Sing-box JSON (v1.12+), and Base64 link lists.
  - Explicit target overrides via `?target=clash`, `?target=singbox`, `?target=v2ray`.
- **Dark Glassmorphic UI**: High-end Neon Green & Dark Carbon SaaS control panel with zero simulated or fake metrics.
- **Production-Ready & Railway-Ready**: Runs straight from GitHub on Railway using standard Dockerfile with dynamic `$PORT` binding.

---

## Architecture Overview

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
+-----------------------------------------------------------------------------------+
```

---

## Quick Start

### 1. Local Development
```bash
# Clone the repository
git clone https://github.com/your-username/miliconfig.git
cd miliconfig

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open [http://localhost:8000](http://localhost:8000) in your browser.
Default credentials:
- **Username**: `admin`
- **Password**: `miliconfig_admin_2026`

---

### 2. Docker & Docker Compose
To run MILICONFIG along with a dedicated PostgreSQL database:
```bash
# Start the full stack
docker compose up -d

# Check logs
docker compose logs -f miliconfig
```
The application will automatically initialize the database schema and be accessible at port `8000`.

---

### 3. Railway Deployment

MILICONFIG is fully pre-configured for Railway:
1. Log in to [Railway.app](https://railway.app/).
2. Create a **New Project** and select **Deploy from GitHub repo**.
3. Choose your `miliconfig` repository.
4. Add a **PostgreSQL** database service within the project.
5. In your MILICONFIG service settings:
   - Railway will automatically detect `Dockerfile` and `railway.toml`.
   - Set the environment variable `DATABASE_URL` referencing the PostgreSQL service (or Railway will inject it automatically).
   - Change `SECRET_KEY`, `ADMIN_PASSWORD`, and `JWT_SECRET`.
6. Click **Deploy**. Railway will assign a public domain and route traffic to the container.

---

## Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `PORT` | Web and proxy listening port | `8000` |
| `DATABASE_URL` | SQLite or PostgreSQL connection string | `sqlite:///./miliconfig.db` |
| `SECRET_KEY` | Application encryption secret | Random hex string |
| `JWT_SECRET` | Admin session JWT signature key | Random hex string |
| `ADMIN_USERNAME` | Superadmin username | `admin` |
| `ADMIN_PASSWORD` | Superadmin password | `miliconfig_admin_2026` |
| `PUBLIC_BASE_URL` | Public HTTPS URL for subscription generation | `http://localhost:8000` |
| `DEFAULT_DOMAIN` | Fallback SNI/Host domain | `localhost` |
| `ENABLE_SHADOWSOCKS` | Enable background ShadowSocks server | `true` |
| `SS_PORT` | ShadowSocks TCP/UDP listening port | `8388` |
| `SS_DEFAULT_METHOD`| Default AEAD cipher | `chacha20-ietf-poly1305` |
| `OUTBOUND_MODE` | Outbound mode (`""`, `no`, `only`) | `""` |
| `OUTBOUND_PROXY` | Upstream proxy (`socks5://...` or `http://...`)| `""` |
| `DNS_SERVERS` | Upstream DNS / DoH endpoints | `1.1.1.1,8.8.8.8,https://223.5.5.5/dns-query`|

---

## Migration from `byjoey/cfnew`

If you are migrating from an existing Cloudflare Worker / Pages deployment of `cfnew`, use the automated migration script:

```bash
# Migrate from an exported Cloudflare KV JSON file
python -m app.migrate_cfnew --file cfnew_kv_export.json

# Or migrate directly from environment variables:
export u="your-uuid"
export p="104.16.0.1:443"
export s="socks5://user:pass@host:1080"
export yx="1.1.1.1:443#Singapore,8.8.8.8:443#Google"
python -m app.migrate_cfnew --from-env
```

The migration utility will:
1. Create a dedicated user for the cfnew UUID.
2. Import upstream proxy and routing settings.
3. Import ProxyIPs and preferred IP lists as nodes prefixed with `miliconfig • `.
4. Configure DoH DNS endpoints.

---

## Testing

Run the test suite:
```bash
python scripts/run_tests.py
```
Test suite coverage:
- `test_auth.py`: Password hashing, JWT creation/verification, rate limiting.
- `test_users.py`: User lifecycle, quotas, UUID/token resets, traffic recording.
- `test_vless.py`: VLESS v0 binary parsing, commands, address types.
- `test_trojan.py`: Trojan SHA224 hash computation and frame parsing.
- `test_shadowsocks.py`: AEAD crypto (ChaCha20-Poly1305, AES-GCM), live server integration.
- `test_subscription.py`: Base64, Clash, Sing-box formats, User-Agent detection, `miliconfig-` naming enforcement.
- `test_dns.py`: Async DoH resolution, system resolver, cache.
- `test_routing.py`: Rule-based outbound routing (domain, CIDR, port).
- `test_proxyip.py`: ProxyIP pool management and health tracking.
- `test_migration.py`: Automated cfnew KV configuration migration.

---

## License

This project is licensed under the MIT License.
