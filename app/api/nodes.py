import time
import socket
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.schemas import NodeCreate, NodeUpdate, NodeResponse
from app.services.repository import repo
from app.api.auth import get_current_admin
from app.networking.dns import dns_resolver

router = APIRouter(prefix="/api/admin/nodes", tags=["nodes"])

@router.get("", response_model=List[NodeResponse])
async def list_nodes(admin = Depends(get_current_admin)):
    nodes = repo.list_nodes()
    return [NodeResponse(**n.to_dict()) for n in nodes]

@router.post("", response_model=NodeResponse)
async def create_node(req: NodeCreate, admin = Depends(get_current_admin)):
    node = repo.create_node(
        name=req.name,
        protocol=req.protocol,
        address=req.address,
        port=req.port,
        network=req.network,
        tls=req.tls,
        path=req.path,
        host=req.host,
        sni=req.sni,
        alpn=req.alpn,
        proxyip=req.proxyip,
        region=req.region,
        enabled=req.enabled,
        uuid_str=req.uuid,
        password=req.password
    )
    repo.log_audit("NODE_CREATE", f"Created node {node.name} ({node.address}:{node.port})", admin_id=admin.id)
    return NodeResponse(**node.to_dict())

@router.get("/{node_id}", response_model=NodeResponse)
async def get_node(node_id: int, admin = Depends(get_current_admin)):
    node = repo.get_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return NodeResponse(**node.to_dict())

@router.put("/{node_id}", response_model=NodeResponse)
async def update_node(node_id: int, req: NodeUpdate, admin = Depends(get_current_admin)):
    node = repo.get_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    update_dict = {k: v for k, v in req.dict().items() if v is not None}
    updated = repo.update_node(node_id, **update_dict)
    repo.log_audit("NODE_UPDATE", f"Updated node {node.name} (ID: {node.id})", admin_id=admin.id)
    return NodeResponse(**updated.to_dict())

@router.delete("/{node_id}")
async def delete_node(node_id: int, admin = Depends(get_current_admin)):
    node = repo.get_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    repo.delete_node(node_id)
    repo.log_audit("NODE_DELETE", f"Deleted node {node.name} (ID: {node.id})", admin_id=admin.id)
    return {"message": f"Node {node.name} successfully deleted"}

@router.post("/{node_id}/test")
async def test_node(node_id: int, admin = Depends(get_current_admin)):
    """Perform real TCP latency test to node host and port."""
    node = repo.get_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    start = time.time()
    try:
        ip = await dns_resolver.resolve(node.address)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((ip, node.port))
        s.close()
        latency_ms = round((time.time() - start) * 1000, 2)
        return {"status": "online", "latency_ms": latency_ms, "ip": ip}
    except Exception as e:
        return {"status": "offline", "error": str(e), "latency_ms": -1}
