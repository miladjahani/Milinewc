import datetime
import json
import sqlite3
from typing import Optional, List, Dict, Any
from app.database import db

class ModelBase:
    @classmethod
    def from_row(cls, row: Optional[sqlite3.Row]):
        if not row:
            return None
        d = dict(row)
        obj = cls()
        for k, v in d.items():
            setattr(obj, k, v)
        return obj

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

class User(ModelBase):
    def __init__(self, id=None, username="", display_name="", uuid="", subscription_token="",
                 status="active", expires_at=None, traffic_limit=0, upload=0, download=0,
                 device_limit=0, created_at=None, updated_at=None, last_seen_at=None):
        self.id = id
        self.username = username
        self.display_name = display_name
        self.uuid = uuid
        self.subscription_token = subscription_token
        self.status = status
        self.expires_at = expires_at
        self.traffic_limit = traffic_limit
        self.upload = upload
        self.download = download
        self.device_limit = device_limit
        self.created_at = created_at or datetime.datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.datetime.utcnow().isoformat()
        self.last_seen_at = last_seen_at

class Admin(ModelBase):
    def __init__(self, id=None, username="", password_hash="", role="admin", created_at=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.created_at = created_at or datetime.datetime.utcnow().isoformat()

class Node(ModelBase):
    def __init__(self, id=None, name="", protocol="vless", address="127.0.0.1", port=443,
                 uuid=None, password=None, path="/", host="", sni="", alpn="", network="ws",
                 tls=True, proxyip=None, region="US", enabled=True):
        self.id = id
        self.name = name
        self.protocol = protocol
        self.address = address
        self.port = port
        self.uuid = uuid
        self.password = password
        self.path = path
        self.host = host
        self.sni = sni
        self.alpn = alpn
        self.network = network
        self.tls = 1 if tls else 0
        self.proxyip = proxyip
        self.region = region
        self.enabled = 1 if enabled else 0

class ShadowSocksCredential(ModelBase):
    def __init__(self, id=None, user_id=None, method="chacha20-ietf-poly1305",
                 password="", server="127.0.0.1", port=8388, udp=True, enabled=True):
        self.id = id
        self.user_id = user_id
        self.method = method
        self.password = password
        self.server = server
        self.port = port
        self.udp = 1 if udp else 0
        self.enabled = 1 if enabled else 0

class Subscription(ModelBase):
    def __init__(self, id=None, user_id=None, token="", format="base64", accessed_at=None, user_agent=""):
        self.id = id
        self.user_id = user_id
        self.token = token
        self.format = format
        self.accessed_at = accessed_at or datetime.datetime.utcnow().isoformat()
        self.user_agent = user_agent

class TrafficUsage(ModelBase):
    def __init__(self, id=None, user_id=None, bytes_uploaded=0, bytes_downloaded=0, timestamp=None):
        self.id = id
        self.user_id = user_id
        self.bytes_uploaded = bytes_uploaded
        self.bytes_downloaded = bytes_downloaded
        self.timestamp = timestamp or datetime.datetime.utcnow().isoformat()

class Session(ModelBase):
    def __init__(self, id=None, user_id=None, client_ip="", user_agent="", protocol="vless",
                 connected_at=None, last_activity=None, is_active=True):
        self.id = id
        self.user_id = user_id
        self.client_ip = client_ip
        self.user_agent = user_agent
        self.protocol = protocol
        self.connected_at = connected_at or datetime.datetime.utcnow().isoformat()
        self.last_activity = last_activity or datetime.datetime.utcnow().isoformat()
        self.is_active = 1 if is_active else 0

class AuditLog(ModelBase):
    def __init__(self, id=None, timestamp=None, admin_id=None, event="", details="", ip=""):
        self.id = id
        self.timestamp = timestamp or datetime.datetime.utcnow().isoformat()
        self.admin_id = admin_id
        self.event = event
        self.details = details
        self.ip = ip

class ProxyIP(ModelBase):
    def __init__(self, id=None, address="", port=443, region="CF", is_active=True, latency_ms=0.0):
        self.id = id
        self.address = address
        self.port = port
        self.region = region
        self.is_active = 1 if is_active else 0
        self.latency_ms = latency_ms

class Region(ModelBase):
    def __init__(self, id=None, code="", name="", flag="", is_active=True):
        self.id = id
        self.code = code
        self.name = name
        self.flag = flag
        self.is_active = 1 if is_active else 0

class Setting(ModelBase):
    def __init__(self, key="", value="", description=""):
        self.key = key
        self.value = value
        self.description = description

class RoutingRule(ModelBase):
    def __init__(self, id=None, name="", domain_pattern=None, ip_cidr=None,
                 port=None, protocol=None, source=None, outbound="direct"):
        self.id = id
        self.name = name
        self.domain_pattern = domain_pattern
        self.ip_cidr = ip_cidr
        self.port = port
        self.protocol = protocol
        self.source = source
        self.outbound = outbound

class DNSProfile(ModelBase):
    def __init__(self, id=None, name="", server_url="", protocol="doh", is_default=False):
        self.id = id
        self.name = name
        self.server_url = server_url
        self.protocol = protocol
        self.is_default = 1 if is_default else 0
