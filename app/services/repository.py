import datetime
import uuid
import secrets
from typing import Optional, List, Dict, Any
from app.database import db
from app.models.models import (
    User, Admin, Node, ShadowSocksCredential, Subscription,
    TrafficUsage, Session, AuditLog, ProxyIP, Region, Setting,
    RoutingRule, DNSProfile
)

class Repository:
    def __init__(self, database=None):
        self.db = database or db

    # ---------------- USER OPERATIONS ----------------
    def list_users(self) -> List[User]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users ORDER BY id ASC")
        rows = cur.fetchall()
        conn.close()
        return [User.from_row(r) for r in rows]

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return User.from_row(row) if row else None

    def get_user_by_uuid(self, u_str: str) -> Optional[User]:
        if not u_str:
            return None
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE LOWER(uuid) = LOWER(?)", (u_str.strip(),))
        row = cur.fetchone()
        conn.close()
        return User.from_row(row) if row else None

    def get_user_by_sub_token(self, token: str) -> Optional[User]:
        if not token:
            return None
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE subscription_token = ?", (token.strip(),))
        row = cur.fetchone()
        conn.close()
        return User.from_row(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[User]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username.strip(),))
        row = cur.fetchone()
        conn.close()
        return User.from_row(row) if row else None

    def create_user(self, username: str, display_name: str, traffic_limit: int = 0,
                    device_limit: int = 0, expires_at: Optional[str] = None,
                    custom_uuid: Optional[str] = None) -> User:
        user_uuid = custom_uuid or str(uuid.uuid4())
        sub_token = secrets.token_hex(16)
        now = datetime.datetime.utcnow().isoformat()
        
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (username, display_name, uuid, subscription_token, status,
                               expires_at, traffic_limit, upload, download, device_limit,
                               created_at, updated_at)
            VALUES (?, ?, ?, ?, 'active', ?, ?, 0, 0, ?, ?, ?)
        """, (username, display_name, user_uuid, sub_token, expires_at, traffic_limit, device_limit, now, now))
        user_id = cur.lastrowid
        conn.commit()
        conn.close()
        
        # Also auto-create a ShadowSocks credential for the user
        self.create_or_update_ss(user_id=user_id, password=secrets.token_hex(12))
        return self.get_user_by_id(user_id)

    def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        fields = []
        values = []
        for k, v in kwargs.items():
            fields.append(f"{k} = ?")
            values.append(v)
        if not fields:
            return self.get_user_by_id(user_id)
        
        fields.append("updated_at = ?")
        values.append(datetime.datetime.utcnow().isoformat())
        values.append(user_id)
        
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", tuple(values))
        conn.commit()
        conn.close()
        return self.get_user_by_id(user_id)

    def delete_user(self, user_id: int) -> bool:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        affected = cur.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def reset_user_uuid(self, user_id: int) -> str:
        new_uuid = str(uuid.uuid4())
        self.update_user(user_id, uuid=new_uuid)
        return new_uuid

    def reset_user_sub_token(self, user_id: int) -> str:
        new_token = secrets.token_hex(16)
        self.update_user(user_id, subscription_token=new_token)
        return new_token

    def record_user_traffic(self, user_id: int, upload_bytes: int, download_bytes: int):
        conn = self.db.get_connection()
        cur = conn.cursor()
        now = datetime.datetime.utcnow().isoformat()
        cur.execute("""
            UPDATE users SET upload = upload + ?, download = download + ?, last_seen_at = ?, updated_at = ?
            WHERE id = ?
        """, (upload_bytes, download_bytes, now, now, user_id))
        cur.execute("""
            INSERT INTO traffic_usage (user_id, bytes_uploaded, bytes_downloaded, timestamp)
            VALUES (?, ?, ?, ?)
        """, (user_id, upload_bytes, download_bytes, now))
        conn.commit()
        conn.close()

    # ---------------- ADMIN OPERATIONS ----------------
    def get_admin_by_username(self, username: str) -> Optional[Admin]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM admins WHERE username = ?", (username.strip(),))
        row = cur.fetchone()
        conn.close()
        return Admin.from_row(row) if row else None

    def create_admin(self, username: str, password_hash: str, role: str = "superadmin") -> Admin:
        conn = self.db.get_connection()
        cur = conn.cursor()
        now = datetime.datetime.utcnow().isoformat()
        cur.execute("""
            INSERT INTO admins (username, password_hash, role, created_at)
            VALUES (?, ?, ?, ?)
        """, (username, password_hash, role, now))
        admin_id = cur.lastrowid
        conn.commit()
        conn.close()
        return Admin(id=admin_id, username=username, password_hash=password_hash, role=role, created_at=now)

    # ---------------- NODE OPERATIONS ----------------
    def list_nodes(self, enabled_only: bool = False) -> List[Node]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        if enabled_only:
            cur.execute("SELECT * FROM nodes WHERE enabled = 1 ORDER BY id ASC")
        else:
            cur.execute("SELECT * FROM nodes ORDER BY id ASC")
        rows = cur.fetchall()
        conn.close()
        return [Node.from_row(r) for r in rows]

    def get_node_by_id(self, node_id: int) -> Optional[Node]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
        row = cur.fetchone()
        conn.close()
        return Node.from_row(row) if row else None

    def create_node(self, name: str, protocol: str, address: str, port: int,
                    network: str = "ws", tls: bool = True, path: str = "/",
                    host: str = "", sni: str = "", alpn: str = "",
                    proxyip: Optional[str] = None, region: str = "US",
                    enabled: bool = True, uuid_str: Optional[str] = None,
                    password: Optional[str] = None) -> Node:
        # Enforce miliconfig client-facing name prefix
        clean_name = name.strip()
        if not clean_name.lower().startswith("miliconfig"):
            clean_name = f"miliconfig • {clean_name}"
            
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO nodes (name, protocol, address, port, uuid, password, path, host,
                               sni, alpn, network, tls, proxyip, region, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (clean_name, protocol, address, port, uuid_str, password, path, host,
              sni, alpn, network, 1 if tls else 0, proxyip, region, 1 if enabled else 0))
        node_id = cur.lastrowid
        conn.commit()
        conn.close()
        return self.get_node_by_id(node_id)

    def update_node(self, node_id: int, **kwargs) -> Optional[Node]:
        if "name" in kwargs and kwargs["name"]:
            name = kwargs["name"].strip()
            if not name.lower().startswith("miliconfig"):
                kwargs["name"] = f"miliconfig • {name}"
        fields = []
        values = []
        for k, v in kwargs.items():
            if k == "tls":
                v = 1 if v else 0
            elif k == "enabled":
                v = 1 if v else 0
            fields.append(f"{k} = ?")
            values.append(v)
        if not fields:
            return self.get_node_by_id(node_id)
        values.append(node_id)
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(f"UPDATE nodes SET {', '.join(fields)} WHERE id = ?", tuple(values))
        conn.commit()
        conn.close()
        return self.get_node_by_id(node_id)

    def delete_node(self, node_id: int) -> bool:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        affected = cur.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    # ---------------- SHADOWSOCKS OPERATIONS ----------------
    def get_ss_by_user_id(self, user_id: int) -> Optional[ShadowSocksCredential]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM shadowsocks_credentials WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return ShadowSocksCredential.from_row(row) if row else None

    def list_all_active_ss(self) -> List[ShadowSocksCredential]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT sc.* FROM shadowsocks_credentials sc
            JOIN users u ON u.id = sc.user_id
            WHERE sc.enabled = 1 AND u.status = 'active'
        """)
        rows = cur.fetchall()
        conn.close()
        return [ShadowSocksCredential.from_row(r) for r in rows]

    def create_or_update_ss(self, user_id: int, password: str, method: str = "chacha20-ietf-poly1305",
                            port: Optional[int] = None, server: str = "127.0.0.1", udp: bool = True) -> ShadowSocksCredential:
        existing = self.get_ss_by_user_id(user_id)
        target_port = port or 8388
        conn = self.db.get_connection()
        cur = conn.cursor()
        if existing:
            cur.execute("""
                UPDATE shadowsocks_credentials
                SET password = ?, method = ?, port = ?, server = ?, udp = ?, enabled = 1
                WHERE user_id = ?
            """, (password, method, target_port, server, 1 if udp else 0, user_id))
        else:
            cur.execute("""
                INSERT INTO shadowsocks_credentials (user_id, method, password, server, port, udp, enabled)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (user_id, method, password, server, target_port, 1 if udp else 0))
        conn.commit()
        conn.close()
        return self.get_ss_by_user_id(user_id)

    # ---------------- PROXY IP OPERATIONS ----------------
    def list_proxy_ips(self, active_only: bool = False) -> List[ProxyIP]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        if active_only:
            cur.execute("SELECT * FROM proxy_ips WHERE is_active = 1 ORDER BY latency_ms ASC")
        else:
            cur.execute("SELECT * FROM proxy_ips ORDER BY id ASC")
        rows = cur.fetchall()
        conn.close()
        return [ProxyIP.from_row(r) for r in rows]

    def add_proxy_ip(self, address: str, port: int = 443, region: str = "CF", latency_ms: float = 0.0) -> ProxyIP:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO proxy_ips (address, port, region, is_active, latency_ms)
            VALUES (?, ?, ?, 1, ?)
        """, (address.strip(), port, region.upper(), latency_ms))
        pip_id = cur.lastrowid
        conn.commit()
        conn.close()
        return ProxyIP(id=pip_id, address=address, port=port, region=region, is_active=True, latency_ms=latency_ms)

    def delete_proxy_ip(self, pip_id: int) -> bool:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM proxy_ips WHERE id = ?", (pip_id,))
        affected = cur.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def update_proxy_ip_latency(self, pip_id: int, latency_ms: float, is_active: bool = True):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE proxy_ips SET latency_ms = ?, is_active = ? WHERE id = ?
        """, (latency_ms, 1 if is_active else 0, pip_id))
        conn.commit()
        conn.close()

    # ---------------- SETTINGS OPERATIONS ----------------
    def get_setting(self, key: str, default: str = "") -> str:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else default

    def set_setting(self, key: str, value: str, description: str = ""):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO settings (key, value, description)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, description = excluded.description
        """, (key, value, description))
        conn.commit()
        conn.close()

    def get_all_settings(self) -> Dict[str, str]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM settings")
        rows = cur.fetchall()
        conn.close()
        return {r["key"]: r["value"] for r in rows}

    # ---------------- ROUTING RULES ----------------
    def list_routing_rules(self) -> List[RoutingRule]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM routing_rules ORDER BY id ASC")
        rows = cur.fetchall()
        conn.close()
        return [RoutingRule.from_row(r) for r in rows]

    def create_routing_rule(self, name: str, domain_pattern: Optional[str] = None,
                            ip_cidr: Optional[str] = None, port: Optional[int] = None,
                            protocol: Optional[str] = None, source: Optional[str] = None,
                            outbound: str = "direct") -> RoutingRule:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO routing_rules (name, domain_pattern, ip_cidr, port, protocol, source, outbound)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, domain_pattern, ip_cidr, port, protocol, source, outbound))
        rid = cur.lastrowid
        conn.commit()
        conn.close()
        return RoutingRule(id=rid, name=name, domain_pattern=domain_pattern, ip_cidr=ip_cidr,
                           port=port, protocol=protocol, source=source, outbound=outbound)

    def delete_routing_rule(self, rule_id: int) -> bool:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM routing_rules WHERE id = ?", (rule_id,))
        affected = cur.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    # ---------------- DNS PROFILES ----------------
    def list_dns_profiles(self) -> List[DNSProfile]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM dns_profiles ORDER BY is_default DESC, id ASC")
        rows = cur.fetchall()
        conn.close()
        return [DNSProfile.from_row(r) for r in rows]

    def create_dns_profile(self, name: str, server_url: str, protocol: str = "doh", is_default: bool = False) -> DNSProfile:
        conn = self.db.get_connection()
        cur = conn.cursor()
        if is_default:
            cur.execute("UPDATE dns_profiles SET is_default = 0")
        cur.execute("""
            INSERT INTO dns_profiles (name, server_url, protocol, is_default)
            VALUES (?, ?, ?, ?)
        """, (name, server_url, protocol, 1 if is_default else 0))
        pid = cur.lastrowid
        conn.commit()
        conn.close()
        return DNSProfile(id=pid, name=name, server_url=server_url, protocol=protocol, is_default=is_default)

    # ---------------- SESSIONS & AUDIT LOGS ----------------
    def record_session(self, user_id: Optional[int], client_ip: str, user_agent: str, protocol: str = "vless"):
        conn = self.db.get_connection()
        cur = conn.cursor()
        now = datetime.datetime.utcnow().isoformat()
        cur.execute("""
            INSERT INTO sessions (user_id, client_ip, user_agent, protocol, connected_at, last_activity, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (user_id, client_ip, user_agent, protocol, now, now))
        conn.commit()
        conn.close()

    def list_active_sessions(self) -> List[Session]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM sessions WHERE is_active = 1 ORDER BY connected_at DESC LIMIT 50")
        rows = cur.fetchall()
        conn.close()
        return [Session.from_row(r) for r in rows]

    def log_audit(self, event: str, details: str, admin_id: Optional[int] = None, ip: str = ""):
        conn = self.db.get_connection()
        cur = conn.cursor()
        now = datetime.datetime.utcnow().isoformat()
        cur.execute("""
            INSERT INTO audit_logs (timestamp, admin_id, event, details, ip)
            VALUES (?, ?, ?, ?, ?)
        """, (now, admin_id, event, details, ip))
        conn.commit()
        conn.close()

    def list_audit_logs(self, limit: int = 50) -> List[AuditLog]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [AuditLog.from_row(r) for r in rows]

    # ---------------- REAL SYSTEM METRICS (NO FAKE DATA) ----------------
    def get_system_stats(self) -> Dict[str, Any]:
        conn = self.db.get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'active'")
        active_users = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM nodes")
        total_nodes = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM nodes WHERE enabled = 1")
        healthy_nodes = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM sessions WHERE is_active = 1")
        active_sessions = cur.fetchone()[0]
        
        cur.execute("SELECT COALESCE(SUM(upload), 0), COALESCE(SUM(download), 0) FROM users")
        traffic_row = cur.fetchone()
        total_upload = traffic_row[0]
        total_download = traffic_row[1]
        
        cur.execute("SELECT COUNT(*) FROM shadowsocks_credentials WHERE enabled = 1")
        active_ss_users = cur.fetchone()[0]

        conn.close()
        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_nodes": total_nodes,
            "healthy_nodes": healthy_nodes,
            "active_sessions": active_sessions,
            "total_upload_bytes": total_upload,
            "total_download_bytes": total_download,
            "active_ss_users": active_ss_users,
            "system_status": "operational"
        }

repo = Repository()
