import time
import socket
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.schemas import (
    ProxyIPCreate, ProxyIPResponse, RoutingRuleCreate,
    DNSProfileCreate
)
from app.services.repository import repo
from app.api.auth import get_current_admin
from app.networking.dns import dns_resolver

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/stats")
async def get_stats(admin = Depends(get_current_admin)):
    """Return live system telemetry. Zero simulated or fabricated metrics."""
    return repo.get_system_stats()

# ---------------- PROXY IP ----------------
@router.get("/proxyips", response_model=List[ProxyIPResponse])
async def list_proxyips(admin = Depends(get_current_admin)):
    pips = repo.list_proxy_ips()
    return [ProxyIPResponse(**p.to_dict()) for p in pips]

@router.post("/proxyips", response_model=ProxyIPResponse)
async def add_proxyip(req: ProxyIPCreate, admin = Depends(get_current_admin)):
    pip = repo.add_proxy_ip(address=req.address, port=req.port, region=req.region)
    repo.log_audit("PROXYIP_ADD", f"Added ProxyIP {pip.address}:{pip.port}", admin_id=admin.id)
    return ProxyIPResponse(**pip.to_dict())

@router.delete("/proxyips/{pip_id}")
async def delete_proxyip(pip_id: int, admin = Depends(get_current_admin)):
    repo.delete_proxy_ip(pip_id)
    repo.log_audit("PROXYIP_DELETE", f"Deleted ProxyIP ID {pip_id}", admin_id=admin.id)
    return {"message": "ProxyIP deleted"}

@router.post("/proxyips/{pip_id}/check")
async def check_proxyip(pip_id: int, admin = Depends(get_current_admin)):
    pips = [p for p in repo.list_proxy_ips() if p.id == pip_id]
    if not pips:
        raise HTTPException(status_code=404, detail="ProxyIP not found")
    pip = pips[0]

    start = time.time()
    try:
        ip = await dns_resolver.resolve(pip.address)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.5)
        s.connect((ip, pip.port))
        s.close()
        latency = round((time.time() - start) * 1000, 2)
        repo.update_proxy_ip_latency(pip_id, latency, is_active=True)
        return {"status": "active", "latency_ms": latency}
    except Exception as e:
        repo.update_proxy_ip_latency(pip_id, -1, is_active=False)
        return {"status": "inactive", "error": str(e), "latency_ms": -1}

# ---------------- ROUTING ----------------
@router.get("/routing")
async def list_routing_rules(admin = Depends(get_current_admin)):
    rules = repo.list_routing_rules()
    return [r.to_dict() for r in rules]

@router.post("/routing")
async def create_routing_rule(req: RoutingRuleCreate, admin = Depends(get_current_admin)):
    rule = repo.create_routing_rule(
        name=req.name,
        domain_pattern=req.domain_pattern,
        ip_cidr=req.ip_cidr,
        port=req.port,
        protocol=req.protocol,
        source=req.source,
        outbound=req.outbound
    )
    repo.log_audit("ROUTING_CREATE", f"Created routing rule {rule.name}", admin_id=admin.id)
    return rule.to_dict()

@router.delete("/routing/{rule_id}")
async def delete_routing_rule(rule_id: int, admin = Depends(get_current_admin)):
    repo.delete_routing_rule(rule_id)
    repo.log_audit("ROUTING_DELETE", f"Deleted routing rule ID {rule_id}", admin_id=admin.id)
    return {"message": "Routing rule deleted"}

# ---------------- DNS ----------------
@router.get("/dns")
async def list_dns(admin = Depends(get_current_admin)):
    profiles = repo.list_dns_profiles()
    return [p.to_dict() for p in profiles]

@router.post("/dns")
async def create_dns(req: DNSProfileCreate, admin = Depends(get_current_admin)):
    prof = repo.create_dns_profile(
        name=req.name,
        server_url=req.server_url,
        protocol=req.protocol,
        is_default=req.is_default
    )
    repo.log_audit("DNS_CREATE", f"Created DNS profile {prof.name}", admin_id=admin.id)
    return prof.to_dict()

# ---------------- SETTINGS ----------------
@router.get("/settings")
async def get_settings(admin = Depends(get_current_admin)):
    return repo.get_all_settings()

@router.post("/settings")
async def update_settings(data: Dict[str, str], admin = Depends(get_current_admin)):
    for k, v in data.items():
        repo.set_setting(k, v)
    repo.log_audit("SETTINGS_UPDATE", "Updated system settings", admin_id=admin.id)
    return {"message": "Settings updated successfully"}

# ---------------- LOGS & SESSIONS ----------------
@router.get("/logs")
async def get_logs(limit: int = 50, admin = Depends(get_current_admin)):
    logs = repo.list_audit_logs(limit)
    return [l.to_dict() for l in logs]

@router.get("/sessions")
async def get_sessions(admin = Depends(get_current_admin)):
    sessions = repo.list_active_sessions()
    return [s.to_dict() for s in sessions]
