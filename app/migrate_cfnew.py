import os
import sys
import json
import argparse
from typing import Dict, Any
from app.database import db
from app.services.repository import repo
from app.config import settings

def parse_cfnew_kv(data: Dict[str, Any]):
    """
    Import cfnew KV dictionary (from key 'c' or direct export) into MILICONFIG relational DB.
    """
    db.init_schema()

    # 1. User UUID migration
    uuid_val = data.get("u") or data.get("U") or "351c9981-04b6-4103-aa4b-864aa9c91469"
    existing_user = repo.get_user_by_uuid(uuid_val)
    if not existing_user:
        user = repo.create_user(
            username="cfnew_migrated_user",
            display_name="CFnew Migrated User",
            custom_uuid=uuid_val
        )
        print(f"[+] Migrated user created: {user.username} (UUID: {user.uuid})")
    else:
        print(f"[*] User with UUID {uuid_val} already exists.")

    # 2. Settings migration
    mappings = {
        "p": ("custom_proxyip", "ProxyIP address and port"),
        "s": ("outbound_proxy", "Outbound SOCKS5 / HTTP proxy"),
        "d": ("custom_path", "Custom path prefix"),
        "wk": ("worker_region", "Manual region override"),
        "ev": ("enable_vless", "VLESS protocol toggle"),
        "et": ("enable_trojan", "Trojan protocol toggle"),
        "ex": ("enable_xhttp", "xHTTP protocol toggle"),
        "ech": ("enable_ech", "Encrypted Client Hello toggle"),
        "customDNS": ("custom_dns", "Custom DoH server URL"),
        "customECHDomain": ("ech_domain", "Custom ECH server name"),
        "alpn": ("alpn_list", "ALPN list"),
        "scu": ("subscription_converter_url", "Subscription converter URL"),
        "qj": ("outbound_mode", "Outbound fallback mode"),
        "dkby": ("tls_only_nodes", "Only generate TLS nodes"),
        "yxby": ("disable_preferred_ips", "Disable preferred IPs"),
        "jk": ("enable_residential_chain", "Residential chain toggle")
    }

    for cf_key, (mili_key, desc) in mappings.items():
        if cf_key in data and data[cf_key]:
            repo.set_setting(mili_key, str(data[cf_key]), desc)
            print(f"[+] Setting updated: {mili_key} = {data[cf_key]}")

    # 3. Custom preferred IPs migration
    yx = data.get("yx")
    if yx:
        items = [i.strip() for i in yx.split(",") if i.strip()]
        for item in items:
            name = "Migrated Node"
            addr_part = item
            if "#" in item:
                parts = item.split("#", 1)
                addr_part = parts[0].strip()
                name = parts[1].strip()

            host = addr_part
            port = 443
            if ":" in addr_part:
                h_parts = addr_part.split(":")
                host = h_parts[0]
                try:
                    port = int(h_parts[1])
                except Exception:
                    port = 443

            repo.create_node(
                name=f"miliconfig • {name}",
                protocol="vless",
                address=host,
                port=port,
                network="ws",
                tls=True,
                region=data.get("wk", "US")
            )
            print(f"[+] Node created from yx: miliconfig • {name} ({host}:{port})")

    # 4. ProxyIP migration
    custom_pip = data.get("p")
    if custom_pip:
        parts = custom_pip.split(":")
        pip_host = parts[0]
        pip_port = int(parts[1]) if len(parts) > 1 else 443
        repo.add_proxy_ip(pip_host, pip_port, region=data.get("wk", "CF"))
        print(f"[+] ProxyIP added: {pip_host}:{pip_port}")

    print("\n[SUCCESS] Migration from cfnew to MILICONFIG completed successfully!")

def main():
    parser = argparse.ArgumentParser(description="Migrate cfnew configuration to MILICONFIG")
    parser.add_argument("--file", "-f", help="Path to cfnew KV JSON dump file")
    parser.add_argument("--from-env", action="store_true", help="Migrate from active cfnew environment variables")
    args = parser.parse_args()

    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File {args.file} not found.", file=sys.stderr)
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            raw = json.load(f)
            # Check if wrapped in key 'c'
            if "c" in raw and isinstance(raw["c"], str):
                data = json.loads(raw["c"])
            elif "c" in raw and isinstance(raw["c"], dict):
                data = raw["c"]
            else:
                data = raw
        parse_cfnew_kv(data)
    elif args.from_env:
        env_keys = ["u", "p", "s", "d", "wk", "ev", "et", "ex", "ech", "customDNS", "customECHDomain", "alpn", "yx", "scu", "qj", "dkby", "yxby", "jk"]
        data = {k: os.environ.get(k) for k in env_keys if os.environ.get(k)}
        parse_cfnew_kv(data)
    else:
        # Default test sample migration
        print("[*] No arguments provided. Running migration with default sample...")
        sample_kv = {
            "u": "351c9981-04b6-4103-aa4b-864aa9c91469",
            "ev": "yes",
            "et": "yes",
            "ex": "no",
            "wk": "US",
            "p": "104.16.0.1:443",
            "s": "socks5://127.0.0.1:1080",
            "yx": "1.1.1.1:443#Cloudflare DNS,8.8.8.8:443#Google DNS"
        }
        parse_cfnew_kv(sample_kv)

if __name__ == "__main__":
    main()
