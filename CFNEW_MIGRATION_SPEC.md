# MILICONFIG: CFNEW Migration Specification

## 1. Migration Overview

The original `byjoey/cfnew` project stores state in either:
1. Environment variables configured in Cloudflare Workers / Pages (`wrangler.toml` or dashboard).
2. A single Cloudflare Workers KV namespace bound to variable `C`, containing:
   - Key `c`: JSON string representing the active settings dictionary.
   - Key `c_ver`: Version timestamp string used for cross-isolate invalidation.

**MILICONFIG** replaces this flat KV approach with a structured relational database (SQLite for local dev, PostgreSQL for production on Railway). This specification describes the exact translation from cfnew configuration schemas into MILICONFIG's database models and details the automated migration utility `python -m app.migrate_cfnew`.

---

## 2. Configuration Key Mapping

| cfnew Key | Meaning in cfnew | MILICONFIG Destination & Transformation |
| :--- | :--- | :--- |
| `u` | Primary UUID / Secret Token | Created as Default User in `users` table: `User(username="migrated_user", uuid=u, subscription_token=token)` |
| `p` | Custom ProxyIP (host or host:port) | Stored in `proxy_ips` table as active ProxyIP entity linked to default routing |
| `s` | Outbound proxy (`host:port`, `socks5://...`, `http://...`) | Converted into `routing_rules` and `settings` for default upstream proxy |
| `d` | Custom path (`/mypath`) | Stored in `settings(key='default_path', value=d)` |
| `wk` | Worker region (`US`, `SG`, `JP`, etc.) | Stored in `settings(key='default_region', value=wk)` |
| `ev` | Enable VLESS (`yes`/`no`) | Converted to `settings(key='enable_vless', value=bool)` |
| `et` | Enable Trojan (`yes`/`no`) | Converted to `settings(key='enable_trojan', value=bool)` |
| `ex` | Enable xHTTP (`yes`/`no`) | Converted to `settings(key='enable_xhttp', value=bool)` |
| `tp` | Custom Trojan password | Stored in `users` credential mapping or `settings(key='trojan_password')` |
| `ech` | Enable ECH (`yes`/`no`) | Stored in `settings(key='enable_ech', value=bool)` |
| `customDNS` | DoH URL (e.g. `https://223.5.5.5/dns-query`) | Created as active entry in `dns_profiles` table |
| `customECHDomain` | ECH target domain (`cloudflare-ech.com`) | Stored in `settings(key='ech_domain')` |
| `alpn` | ALPN list (`h3`, `h2`, `http/1.1`) | Stored in `settings(key='alpn_list')` |
| `yx` | Preferred IP/Domain list (`ip:port#name`) | Parsed into individual `nodes` records with `miliconfig-` prefix naming |
| `yxURL` | Remote Preferred IP Source URL | Stored in `settings(key='preferred_ip_source_url')` |
| `scu` | Subscription converter URL | Stored in `settings(key='subscription_converter_url')` |
| `qj` | Outbound routing mode (`""`, `no`, `only`) | Stored in `settings(key='outbound_mode')` |
| `dkby` | Only TLS nodes (`yes`/`no`) | Stored in `settings(key='tls_only_nodes')` |
| `yxby` | Disable all preferred IP features | Stored in `settings(key='disable_preferred_ips')` |
| `rm` | Region matching (`yes`/`no`) | Stored in `settings(key='region_matching')` |
| `ae` | Enable API management (`yes`/`no`) | Stored in `settings(key='enable_api_management')` |
| `jk` | Residential chain (`yes`/`no`) | Stored in `settings(key='enable_residential_chain')` |

---

## 3. Database Schema Models

MILICONFIG implements the following SQLAlchemy relational models:

1. **`User`**:
   - `id`: Integer Primary Key
   - `username`: String(64) Unique
   - `display_name`: String(128)
   - `uuid`: String(36) Unique Index (RFC 4122)
   - `subscription_token`: String(64) Unique Index
   - `status`: Enum (`active`, `disabled`, `expired`)
   - `expires_at`: DateTime (nullable)
   - `traffic_limit`: BigInteger (in bytes, 0 for unlimited)
   - `upload`: BigInteger (in bytes)
   - `download`: BigInteger (in bytes)
   - `device_limit`: Integer (0 for unlimited)
   - `created_at`: DateTime
   - `updated_at`: DateTime
   - `last_seen_at`: DateTime (nullable)

2. **`Admin`**:
   - `id`: Integer Primary Key
   - `username`: String(64) Unique
   - `password_hash`: String(256) (Argon2id / PBKDF2)
   - `role`: String(32) (`superadmin`, `admin`)
   - `created_at`: DateTime

3. **`Node`**:
   - `id`: Integer Primary Key
   - `name`: String(128) (client-facing names strictly formatted as `miliconfig-...`)
   - `protocol`: String(32) (`vless`, `trojan`, `shadowsocks`)
   - `address`: String(255)
   - `port`: Integer
   - `uuid`: String(64) (nullable)
   - `password`: String(255) (nullable)
   - `path`: String(255) (default `/`)
   - `host`: String(255)
   - `sni`: String(255)
   - `alpn`: String(64)
   - `network`: String(32) (`ws`, `tcp`, `xhttp`)
   - `tls`: Boolean
   - `proxyip`: String(255) (nullable)
   - `region`: String(32)
   - `enabled`: Boolean

4. **`ShadowSocksCredential`**:
   - `id`: Integer Primary Key
   - `user_id`: Integer ForeignKey(`users.id`)
   - `method`: String(64) (`chacha20-ietf-poly1305`, `aes-256-gcm`, `aes-128-gcm`)
   - `password`: String(255)
   - `port`: Integer
   - `udp`: Boolean (default True)
   - `enabled`: Boolean

5. **`TrafficUsage`**:
   - `id`: Integer Primary Key
   - `user_id`: Integer ForeignKey(`users.id`)
   - `bytes_uploaded`: BigInteger
   - `bytes_downloaded`: BigInteger
   - `timestamp`: DateTime

6. **`Session`**:
   - `id`: Integer Primary Key
   - `user_id`: Integer ForeignKey(`users.id`)
   - `client_ip`: String(64)
   - `user_agent`: String(255)
   - `connected_at`: DateTime
   - `last_activity`: DateTime
   - `is_active`: Boolean

7. **`ProxyIP`**:
   - `id`: Integer Primary Key
   - `address`: String(255)
   - `port`: Integer
   - `region`: String(32)
   - `is_active`: Boolean
   - `latency_ms`: Float (nullable)

8. **`Setting`**:
   - `key`: String(64) Primary Key
   - `value`: Text
   - `description`: Text

9. **`RoutingRule`**:
   - `id`: Integer Primary Key
   - `name`: String(64)
   - `domain_pattern`: String(255) (nullable)
   - `ip_cidr`: String(64) (nullable)
   - `port`: Integer (nullable)
   - `protocol`: String(32) (nullable)
   - `outbound`: String(64) (`direct`, `proxy`, `reject`, `fallback`)

10. **`DNSProfile`**:
    - `id`: Integer Primary Key
    - `name`: String(64)
    - `server_url`: String(255) (DoH or IP)
    - `protocol`: String(16) (`doh`, `udp`, `tcp`)
    - `is_default`: Boolean

11. **`AuditLog`**:
    - `id`: Integer Primary Key
    - `timestamp`: DateTime
    - `admin_id`: Integer (nullable)
    - `event`: String(64)
    - `details`: Text

---

## 4. Migration Execution Flow (`python -m app.migrate_cfnew`)

```
   +--------------------+     +---------------------------+
   | cfnew KV JSON /    |     | cfnew Environment         |
   | export file        |     | Variables                 |
   +--------------------+     +---------------------------+
             \                             /
              \                           /
               v                         v
        +---------------------------------------+
        |     app.migrate_cfnew CLI Tool        |
        |  1. Parse input source                |
        |  2. Validate UUID and keys            |
        |  3. Create default admin if absent    |
        |  4. Create default user from UUID     |
        |  5. Generate SS credentials           |
        |  6. Parse preferred IPs -> Nodes      |
        |  7. Insert ProxyIPs & DNS profiles    |
        |  8. Commit transaction to database    |
        +---------------------------------------+
                           |
                           v
        +---------------------------------------+
        |   MILICONFIG SQLite / PostgreSQL DB   |
        +---------------------------------------+
```

Command Usage:
```bash
# Migrate from an exported cfnew KV JSON file:
python -m app.migrate_cfnew --file cfnew_kv_export.json

# Migrate directly from active environment variables:
python -m app.migrate_cfnew --from-env
```
