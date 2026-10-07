from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# Auth schemas
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "admin"

# User schemas
class UserCreate(BaseModel):
    username: str
    display_name: str
    traffic_limit: int = 0
    device_limit: int = 0
    expires_at: Optional[str] = None
    custom_uuid: Optional[str] = None

class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    status: Optional[str] = None
    traffic_limit: Optional[int] = None
    device_limit: Optional[int] = None
    expires_at: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    uuid: str
    subscription_token: str
    status: str
    expires_at: Optional[str] = None
    traffic_limit: int
    upload: int
    download: int
    device_limit: int
    created_at: str
    updated_at: str
    last_seen_at: Optional[str] = None

# Node schemas
class NodeCreate(BaseModel):
    name: str
    protocol: str = "vless"
    address: str
    port: int = 443
    network: str = "ws"
    tls: bool = True
    path: str = "/"
    host: str = ""
    sni: str = ""
    alpn: str = ""
    proxyip: Optional[str] = None
    region: str = "US"
    enabled: bool = True
    uuid: Optional[str] = None
    password: Optional[str] = None

class NodeUpdate(BaseModel):
    name: Optional[str] = None
    protocol: Optional[str] = None
    address: Optional[str] = None
    port: Optional[int] = None
    network: Optional[str] = None
    tls: Optional[bool] = None
    path: Optional[str] = None
    host: Optional[str] = None
    sni: Optional[str] = None
    alpn: Optional[str] = None
    proxyip: Optional[str] = None
    region: Optional[str] = None
    enabled: Optional[bool] = None

class NodeResponse(BaseModel):
    id: int
    name: str
    protocol: str
    address: str
    port: int
    network: str
    tls: int
    path: str
    host: str
    sni: str
    alpn: str
    proxyip: Optional[str] = None
    region: str
    enabled: int

# ShadowSocks schemas
class ShadowSocksCreate(BaseModel):
    method: str = "chacha20-ietf-poly1305"
    password: str
    port: int = 8388
    server: str = "127.0.0.1"
    udp: bool = True

class ShadowSocksResponse(BaseModel):
    id: int
    user_id: int
    method: str
    password: str
    server: Optional[str] = "127.0.0.1"
    port: int
    udp: int
    enabled: int

# ProxyIP schemas
class ProxyIPCreate(BaseModel):
    address: str
    port: int = 443
    region: str = "CF"

class ProxyIPResponse(BaseModel):
    id: int
    address: str
    port: int
    region: str
    is_active: int
    latency_ms: float

# Routing rules
class RoutingRuleCreate(BaseModel):
    name: str
    domain_pattern: Optional[str] = None
    ip_cidr: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[str] = None
    source: Optional[str] = None
    outbound: str = "direct"

# DNS profile
class DNSProfileCreate(BaseModel):
    name: str
    server_url: str
    protocol: str = "doh"
    is_default: bool = False
