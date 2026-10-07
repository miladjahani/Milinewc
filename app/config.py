import os
from typing import List

class Settings:
    PORT: int = int(os.environ.get("PORT", "8000"))
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./miliconfig.db")
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "miliconfig-secret-key-super-secure-production-2026")
    ADMIN_USERNAME: str = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "miliconfig_admin_2026")
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "miliconfig-jwt-secret-key-32-chars-long-production")
    SUBSCRIPTION_SECRET: str = os.environ.get("SUBSCRIPTION_SECRET", "miliconfig-sub-secret-key-production")
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    PUBLIC_BASE_URL: str = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    DEFAULT_DOMAIN: str = os.environ.get("DEFAULT_DOMAIN", "localhost")
    DEFAULT_PATH: str = os.environ.get("DEFAULT_PATH", "/")
    DNS_SERVERS: str = os.environ.get("DNS_SERVERS", "1.1.1.1,8.8.8.8,https://223.5.5.5/dns-query")
    
    # ShadowSocks default config
    SS_PORT: int = int(os.environ.get("SS_PORT", "8388"))
    SS_BIND_HOST: str = os.environ.get("SS_BIND_HOST", "0.0.0.0")
    SS_DEFAULT_METHOD: str = os.environ.get("SS_DEFAULT_METHOD", "chacha20-ietf-poly1305")
    SS_DEFAULT_PASSWORD: str = os.environ.get("SS_DEFAULT_PASSWORD", "miliconfig_ss_pass_2026")
    
    # Protocol toggles
    ENABLE_VLESS: bool = os.environ.get("ENABLE_VLESS", "true").lower() in ("true", "1", "yes")
    ENABLE_TROJAN: bool = os.environ.get("ENABLE_TROJAN", "true").lower() in ("true", "1", "yes")
    ENABLE_XHTTP: bool = os.environ.get("ENABLE_XHTTP", "true").lower() in ("true", "1", "yes")
    ENABLE_SHADOWSOCKS: bool = os.environ.get("ENABLE_SHADOWSOCKS", "true").lower() in ("true", "1", "yes")
    
    # Outbound mode: "" (proxy first with fallback), "no" (direct first with proxy fallback), "only" (proxy only)
    OUTBOUND_MODE: str = os.environ.get("OUTBOUND_MODE", "")
    OUTBOUND_PROXY: str = os.environ.get("OUTBOUND_PROXY", "")
    
    @property
    def dns_server_list(self) -> List[str]:
        return [s.strip() for s in self.DNS_SERVERS.split(",") if s.strip()]

settings = Settings()
