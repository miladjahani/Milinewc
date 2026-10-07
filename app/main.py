import os
import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from app.config import settings
from app.database import db
from app.services.repository import repo
from app.security.security import hash_password, verify_access_token
from app.api import auth, users, nodes, subscriptions, admin
from app.transports.websocket.handler import handle_websocket_connection
from app.transports.xhttp.handler import handle_xhttp_request
from app.protocols.shadowsocks.server import ss_server
from app.networking.dns import dns_resolver

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO))
logger = logging.getLogger("miliconfig.main")

app = FastAPI(
    title="MILICONFIG",
    description="Enterprise Multi-Protocol Proxy & Subscription Infrastructure",
    version="1.0.0"
)

# Static and Templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include API Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(nodes.router)
app.include_router(subscriptions.router)
app.include_router(admin.router)

@app.on_event("startup")
async def on_startup():
    logger.info("Initializing MILICONFIG database schema...")
    db.init_schema()

    # Create default superadmin if not exists
    admin_user = repo.get_admin_by_username(settings.ADMIN_USERNAME)
    if not admin_user:
        pwd_hash = hash_password(settings.ADMIN_PASSWORD)
        repo.create_admin(settings.ADMIN_USERNAME, pwd_hash, role="superadmin")
        logger.info(f"Default superadmin '{settings.ADMIN_USERNAME}' created.")

    # Create default user if no users exist
    existing_users = repo.list_users()
    if not existing_users:
        default_user = repo.create_user(
            username="default",
            display_name="Default User",
            custom_uuid="351c9981-04b6-4103-aa4b-864aa9c91469"
        )
        logger.info(f"Initial default user created with UUID {default_user.uuid}")

    # Seed default nodes if none exist
    existing_nodes = repo.list_nodes()
    if not existing_nodes:
        repo.create_node(
            name="miliconfig-01 • US Premium",
            protocol="vless",
            address="127.0.0.1",
            port=settings.PORT,
            network="ws",
            tls=True,
            path="/",
            region="US"
        )
        repo.create_node(
            name="miliconfig-02 • DE Fast",
            protocol="trojan",
            address="127.0.0.1",
            port=settings.PORT,
            network="ws",
            tls=True,
            path="/",
            region="DE"
        )

    # Seed default proxy IPs if none exist
    existing_pips = repo.list_proxy_ips()
    if not existing_pips:
        default_pips = [
            ("172.71.218.190", 443, "CF"),
            ("162.158.228.87", 443, "CF"),
            ("162.158.189.134", 443, "CF"),
            ("162.158.26.63", 443, "CF")
        ]
        for ip, port, reg in default_pips:
            repo.add_proxy_ip(ip, port, reg)

    # Seed default DNS profile
    existing_dns = repo.list_dns_profiles()
    if not existing_dns:
        repo.create_dns_profile("AliDNS DoH", "https://223.5.5.5/dns-query", "doh", is_default=True)
        repo.create_dns_profile("Cloudflare DoH", "https://1.1.1.1/dns-query", "doh", is_default=False)

    # Start ShadowSocks server
    if settings.ENABLE_SHADOWSOCKS:
        asyncio.create_task(ss_server.start())

@app.on_event("shutdown")
async def on_shutdown():
    if settings.ENABLE_SHADOWSOCKS:
        await ss_server.stop()

# ---------------- HEALTH & READINESS ----------------
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "MILICONFIG",
        "version": "1.0.0"
    }

@app.get("/ready")
async def ready_check():
    try:
        # Check DB connection
        conn = db.get_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "ready" if db_ok else "unready",
        "database": "connected" if db_ok else "error",
        "shadowsocks_engine": "running" if ss_server.is_running else "stopped",
        "protocols": {
            "vless": settings.ENABLE_VLESS,
            "trojan": settings.ENABLE_TROJAN,
            "xhttp": settings.ENABLE_XHTTP,
            "shadowsocks": settings.ENABLE_SHADOWSOCKS
        }
    }

# ---------------- UI & WEBPAGE ROUTES ----------------
@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    # Check session cookie
    token = request.cookies.get("miliconfig_token")
    if not token or not verify_access_token(token):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def serve_login(request: Request):
    token = request.cookies.get("miliconfig_token")
    if token and verify_access_token(token):
        return RedirectResponse(url="/")
    return templates.TemplateResponse("login.html", {"request": request})

# ---------------- xHTTP POST ROUTING ----------------
@app.post("/xhttp")
@app.post("/")
async def xhttp_endpoint(request: Request):
    if settings.ENABLE_XHTTP:
        return await handle_xhttp_request(request)
    return Response("xHTTP disabled", status_code=404)

# ---------------- WEBSOCKET ROUTING ----------------
@app.websocket("/ws")
@app.websocket("/")
@app.websocket("/{path_param:path}")
async def websocket_proxy_endpoint(websocket: WebSocket, path_param: str = ""):
    await handle_websocket_connection(websocket, path_param)
