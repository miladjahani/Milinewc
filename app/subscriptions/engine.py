import json
import base64
import yaml
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings
from app.models.models import User, Node, ShadowSocksCredential
from app.services.repository import repo

class SubscriptionEngine:
    def format_client_node_name(self, base_name: str, index: int = 1, region: str = "US", protocol: str = "VLESS") -> str:
        """
        Enforce mandatory MILICONFIG client-facing node naming convention:
        Must start with 'miliconfig'.
        Examples: miliconfig-01, miliconfig-US, miliconfig • VLESS, miliconfig • ShadowSocks
        """
        raw = base_name.strip()
        if raw.lower().startswith("miliconfig"):
            return raw
        return f"miliconfig-{index:02d} • {region} ({protocol})"

    def generate_vless_uri(self, user: User, node: Node, index: int = 1) -> str:
        name = self.format_client_node_name(node.name, index, node.region, "VLESS")
        domain = node.sni or node.host or node.address
        security = "tls" if node.tls else "none"
        alpn_param = f"&alpn={node.alpn}" if node.alpn else ""
        path_encoded = urllib.parse.quote(node.path or "/")

        query_params = (
            f"type={node.network}&security={security}&encryption=none"
            f"&host={domain}&sni={domain}&path={path_encoded}{alpn_param}&fp=chrome"
        )
        tag = urllib.parse.quote(name)
        return f"vless://{user.uuid}@{node.address}:{node.port}?{query_params}#{tag}"

    def generate_trojan_uri(self, user: User, node: Node, index: int = 1) -> str:
        name = self.format_client_node_name(node.name, index, node.region, "Trojan")
        domain = node.sni or node.host or node.address
        security = "tls" if node.tls else "none"
        alpn_param = f"&alpn={node.alpn}" if node.alpn else ""
        path_encoded = urllib.parse.quote(node.path or "/")

        query_params = (
            f"type={node.network}&security={security}"
            f"&host={domain}&sni={domain}&path={path_encoded}{alpn_param}&fp=chrome"
        )
        tag = urllib.parse.quote(name)
        password = node.password or user.uuid
        return f"trojan://{password}@{node.address}:{node.port}?{query_params}#{tag}"

    def generate_shadowsocks_uri(self, user: User, ss_cred: ShadowSocksCredential, index: int = 1) -> str:
        name = f"miliconfig-{index:02d} • SS ({ss_cred.method})"
        user_info = f"{ss_cred.method}:{ss_cred.password}"
        b64_info = base64.urlsafe_b64encode(user_info.encode("utf-8")).decode("utf-8").rstrip("=")
        host = ss_cred.server or settings.DEFAULT_DOMAIN
        tag = urllib.parse.quote(name)
        return f"ss://{b64_info}@{host}:{ss_cred.port}#{tag}"

    def generate_base64_subscription(self, user: User, nodes: List[Node], ss_cred: Optional[ShadowSocksCredential] = None) -> str:
        """Generate standard Base64 URI list for V2Ray, V2RayNG, Shadowrocket, Nekoray."""
        links = []
        for idx, node in enumerate(nodes, start=1):
            if node.protocol.lower() == "vless":
                links.append(self.generate_vless_uri(user, node, idx))
            elif node.protocol.lower() == "trojan":
                links.append(self.generate_trojan_uri(user, node, idx))

        if ss_cred and ss_cred.enabled:
            links.append(self.generate_shadowsocks_uri(user, ss_cred, len(links) + 1))

        raw_text = "\n".join(links)
        return base64.b64encode(raw_text.encode("utf-8")).decode("utf-8")

    def generate_clash_yaml(self, user: User, nodes: List[Node], ss_cred: Optional[ShadowSocksCredential] = None) -> str:
        """Generate Clash / Mihomo YAML subscription."""
        proxies = []
        proxy_names = []

        for idx, node in enumerate(nodes, start=1):
            client_name = self.format_client_node_name(node.name, idx, node.region, node.protocol.upper())
            proxy_names.append(client_name)
            
            p_dict = {
                "name": client_name,
                "type": node.protocol.lower(),
                "server": node.address,
                "port": node.port,
                "uuid": user.uuid if node.protocol.lower() == "vless" else None,
                "password": (node.password or user.uuid) if node.protocol.lower() == "trojan" else None,
                "network": node.network,
                "tls": bool(node.tls),
                "udp": True,
                "client-fingerprint": "chrome"
            }
            if node.tls:
                p_dict["servername"] = node.sni or node.host or node.address
                p_dict["skip-cert-verify"] = False
                if node.alpn:
                    p_dict["alpn"] = [a.strip() for a in node.alpn.split(",") if a.strip()]

            if node.network == "ws":
                p_dict["ws-opts"] = {
                    "path": node.path or "/",
                    "headers": {"Host": node.host or node.address}
                }
            elif node.network == "xhttp":
                p_dict["xhttp-opts"] = {
                    "path": node.path or "/",
                    "headers": {"Host": node.host or node.address}
                }
            
            proxies.append({k: v for k, v in p_dict.items() if v is not None})

        if ss_cred and ss_cred.enabled:
            ss_name = f"miliconfig-{len(proxy_names)+1:02d} • SS ({ss_cred.method})"
            proxy_names.append(ss_name)
            proxies.append({
                "name": ss_name,
                "type": "ss",
                "server": ss_cred.server or settings.DEFAULT_DOMAIN,
                "port": ss_cred.port,
                "cipher": ss_cred.method,
                "password": ss_cred.password,
                "udp": bool(ss_cred.udp)
            })

        auto_group = "⚡ miliconfig • Auto"
        select_group = "🚀 miliconfig • Select"
        
        proxy_groups = [
            {
                "name": select_group,
                "type": "select",
                "proxies": [auto_group] + proxy_names + ["DIRECT"]
            },
            {
                "name": auto_group,
                "type": "url-test",
                "url": "https://www.gstatic.com/generate_204",
                "interval": 300,
                "tolerance": 50,
                "proxies": proxy_names
            }
        ]

        clash_config = {
            "port": 7890,
            "socks-port": 7891,
            "allow-lan": False,
            "mode": "rule",
            "log-level": "info",
            "ipv6": False,
            "dns": {
                "enable": True,
                "enhanced-mode": "fake-ip",
                "nameserver": ["1.1.1.1", "8.8.8.8", "https://223.5.5.5/dns-query"]
            },
            "proxies": proxies,
            "proxy-groups": proxy_groups,
            "rules": [
                "GEOIP,LAN,DIRECT,no-resolve",
                "GEOIP,CN,DIRECT,no-resolve",
                f"MATCH,{select_group}"
            ]
        }
        return yaml.dump(clash_config, sort_keys=False, allow_unicode=True)

    def generate_singbox_json(self, user: User, nodes: List[Node], ss_cred: Optional[ShadowSocksCredential] = None) -> str:
        """Generate Sing-box JSON subscription compatible with v1.12+."""
        outbounds = []
        tags = []

        for idx, node in enumerate(nodes, start=1):
            tag = self.format_client_node_name(node.name, idx, node.region, node.protocol.upper())
            tags.append(tag)

            ob = {
                "type": node.protocol.lower(),
                "tag": tag,
                "server": node.address,
                "server_port": node.port,
            }
            if node.protocol.lower() == "vless":
                ob["uuid"] = user.uuid
            elif node.protocol.lower() == "trojan":
                ob["password"] = node.password or user.uuid

            if node.tls:
                ob["tls"] = {
                    "enabled": True,
                    "server_name": node.sni or node.host or node.address,
                    "insecure": False
                }
                if node.alpn:
                    ob["tls"]["alpn"] = [a.strip() for a in node.alpn.split(",") if a.strip()]

            if node.network == "ws":
                ob["transport"] = {
                    "type": "ws",
                    "path": node.path or "/",
                    "headers": {"Host": node.host or node.address}
                }
            outbounds.append(ob)

        if ss_cred and ss_cred.enabled:
            ss_tag = f"miliconfig-{len(tags)+1:02d} • SS ({ss_cred.method})"
            tags.append(ss_tag)
            outbounds.append({
                "type": "shadowsocks",
                "tag": ss_tag,
                "server": ss_cred.server or settings.DEFAULT_DOMAIN,
                "server_port": ss_cred.port,
                "method": ss_cred.method,
                "password": ss_cred.password
            })

        selector_group = {
            "type": "selector",
            "tag": "🚀 miliconfig • Select",
            "outbounds": ["⚡ miliconfig • Auto"] + tags + ["direct"]
        }
        urltest_group = {
            "type": "urltest",
            "tag": "⚡ miliconfig • Auto",
            "outbounds": tags,
            "url": "https://www.gstatic.com/generate_204",
            "interval": "5m"
        }

        singbox_config = {
            "version": 1,
            "dns": {
                "servers": [
                    {"tag": "dns-remote", "address": "https://1.1.1.1/dns-query", "detour": "🚀 miliconfig • Select"},
                    {"tag": "dns-direct", "address": "223.5.5.5", "detour": "direct"}
                ]
            },
            "inbounds": [
                {"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 2080}
            ],
            "outbounds": [selector_group, urltest_group] + outbounds + [
                {"type": "direct", "tag": "direct"},
                {"type": "block", "tag": "block"}
            ],
            "route": {
                "rules": [
                    {"geoip": ["private"], "outbound": "direct"},
                    {"geosite": ["cn"], "outbound": "direct"},
                    {"geoip": ["cn"], "outbound": "direct"}
                ],
                "final": "🚀 miliconfig • Select"
            }
        }
        return json.dumps(singbox_config, indent=2, ensure_ascii=False)

    def detect_client_format(self, user_agent: str, target_param: Optional[str] = None) -> str:
        """Detect target subscription format based on parameter or User-Agent."""
        if target_param:
            t = target_param.lower()
            if "clash" in t or "meta" in t or "mihomo" in t:
                return "clash"
            if "sing" in t or "singbox" in t:
                return "singbox"
            if "v2ray" in t or "sub" in t or "base64" in t:
                return "base64"
            if "ss" in t:
                return "base64"

        ua = (user_agent or "").lower()
        if any(c in ua for c in ("clash", "meta", "mihomo", "stash", "flclash")):
            return "clash"
        elif "sing-box" in ua or "singbox" in ua:
            return "singbox"
        elif any(c in ua for c in ("v2ray", "v2rayng", "shadowrocket", "neko")):
            return "base64"
        return "base64"

    def build_subscription(self, token: str, user_agent: str = "", target_param: Optional[str] = None) -> Tuple[int, str, str]:
        """
        Generate user subscription in the appropriate format.
        Returns: (status_code, content, content_type)
        """
        user = repo.get_user_by_sub_token(token)
        if not user:
            return 404, "User subscription not found", "text/plain; charset=utf-8"

        if user.status != "active":
            return 403, f"Subscription suspended: user is {user.status}", "text/plain; charset=utf-8"

        nodes = repo.list_nodes(enabled_only=True)
        ss_cred = repo.get_ss_by_user_id(user.id)

        target_format = self.detect_client_format(user_agent, target_param)

        if target_format == "clash":
            content = self.generate_clash_yaml(user, nodes, ss_cred)
            return 200, content, "text/yaml; charset=utf-8"
        elif target_format == "singbox":
            content = self.generate_singbox_json(user, nodes, ss_cred)
            return 200, content, "application/json; charset=utf-8"
        else:
            content = self.generate_base64_subscription(user, nodes, ss_cred)
            return 200, content, "text/plain; charset=utf-8"

subscription_engine = SubscriptionEngine()
