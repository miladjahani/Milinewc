import fnmatch
import ipaddress
from typing import Optional, List
from app.services.repository import repo

class RoutingEngine:
    def match_rule(self, host: str, port: int, protocol: str = "tcp") -> str:
        """
        Evaluate configured routing rules against destination host and port.
        Returns: 'direct', 'proxy', 'reject', or 'fallback'.
        """
        rules = repo.list_routing_rules()
        for rule in rules:
            # Check protocol
            if rule.protocol and rule.protocol.lower() != protocol.lower():
                continue

            # Check port
            if rule.port and rule.port != port:
                continue

            # Check domain pattern (e.g. *.ir, google.com)
            if rule.domain_pattern:
                if fnmatch.fnmatch(host.lower(), rule.domain_pattern.lower()):
                    return rule.outbound

            # Check IP CIDR
            if rule.ip_cidr:
                try:
                    ip_obj = ipaddress.ip_address(host)
                    network = ipaddress.ip_network(rule.ip_cidr, strict=False)
                    if ip_obj in network:
                        return rule.outbound
                except ValueError:
                    pass

        return "direct"

routing_engine = RoutingEngine()
