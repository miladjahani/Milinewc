# MILICONFIG: Docker & Railway Production Specification

## 1. Overview

MILICONFIG is engineered for zero-friction containerized deployment across local development, Docker Compose, and cloud PaaS environments—specifically optimized for **Railway**.

---

## 2. Docker Architecture

### 2.1 Base Image & Hardening
- **Base Image**: `python:3.12-slim-bookworm`
- **Security Principles**:
  - Run as non-root user (`miliconfig:miliconfig`, UID/GID 10001).
  - No build tools left in final image layers (`--no-cache-dir`).
  - Read-only container root support where applicable, with `/tmp` and `/data` volume mounts.
  - Proper signal handling for graceful shutdown (`SIGTERM` initiates connection draining).

### 2.2 Entrypoint & Port Binding
- **Command**:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'
  ```
- **Dynamic Port**: Binds to `$PORT` provided by Railway runtime or defaults to `8000`.

### 2.3 Healthcheck
- Standard Docker HEALTHCHECK configured to query `/health`:
  ```dockerfile
  HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
      CMD python3 -c "import urllib.request, os; port = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/health')" || exit 1
  ```

---

## 3. Docker Compose Configuration

`docker-compose.yml` provides a turnkey local stack including:
1. **`miliconfig`**: Core FastAPI, protocol relays, and subscription engine.
2. **`postgres`**: Production-grade relational database (PostgreSQL 16 Alpine).
3. **`redis`** *(optional)*: In-memory session and rate-limit cache.

### Persistent Volumes
- `postgres_data`: Persists relational tables across container restarts.
- `miliconfig_data`: Stores SQLite fallback database and local backups.

---

## 4. Railway Deployment Specification

### 4.1 Zero-Config Git Deployment
When connecting the MILICONFIG repository to Railway:
1. Railway detects the `Dockerfile` automatically.
2. Configuration file `railway.toml` specifies the build and deploy pipeline.
3. Automatically maps Railway-provided `$PORT` to the Uvicorn listener.

### 4.2 Railway Environment Variables

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `PORT` | Dynamically assigned by Railway | `8000` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/miliconfig` |
| `SECRET_KEY` | Symmetric encryption key | Random 64-character hex |
| `JWT_SECRET` | Admin session JWT secret | Random 64-character hex |
| `SUBSCRIPTION_SECRET` | Token derivation secret | Random 64-character hex |
| `ADMIN_USERNAME` | Initial Superadmin username | `admin` |
| `ADMIN_PASSWORD` | Initial Superadmin password | Secure string (min 12 chars) |
| `PUBLIC_BASE_URL` | Public domain of the service | `https://miliconfig.up.railway.app` |
| `DEFAULT_DOMAIN` | Fallback domain for SNI/Host | Railway default domain or custom |
| `DEFAULT_PATH` | Path prefix for panel/subs | `/` or `/miliconfig` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `DNS_SERVERS` | Fallback upstream DNS list | `1.1.1.1,8.8.8.8,https://223.5.5.5/dns-query` |

### 4.3 Database Strategy on Railway
- **Development / Standalone**: If `DATABASE_URL` is omitted, MILICONFIG defaults to an embedded SQLite database at `/data/miliconfig.db`.
- **Production**: When the Railway PostgreSQL plugin is provisioned, `DATABASE_URL` is populated automatically. MILICONFIG automatically initializes schemas and runs migration routines on startup.

---

## 5. Health & Readiness Endpoints

- **`GET /health`**:
  - Validates process liveness and event loop responsive state.
  - Returns `{"status": "healthy", "timestamp": "...", "version": "1.0.0"}`.
- **`GET /ready`**:
  - Performs active checks on:
    1. Database connectivity (`SELECT 1`).
    2. Outbound networking availability.
    3. ShadowSocks engine listener state.
    4. Subscription generator status.
  - Returns HTTP 200 with breakdown or HTTP 503 if critical dependencies are down.
