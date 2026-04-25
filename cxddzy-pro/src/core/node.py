"""
Node data model for proxy nodes
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
import hashlib
import json
from datetime import datetime


class Protocol(Enum):
    """Supported proxy protocols"""
    VMESS = "vmess"
    SS = "ss"
    SSR = "ssr"
    TROJAN = "trojan"
    VLESS = "vless"
    HYSTERIA2 = "hysteria2"


@dataclass
class Node:
    """Proxy node data model with full metadata"""

    # Basic info
    name: str
    protocol: Protocol
    server: str
    port: int

    # Protocol-specific fields
    uuid: Optional[str] = None
    password: Optional[str] = None
    cipher: Optional[str] = None
    network: Optional[str] = None
    path: Optional[str] = None
    host: Optional[str] = None
    tls: bool = False
    sni: Optional[str] = None
    alpn: list = field(default_factory=list)
    aid: Optional[int] = None  # alterId for Vmess
    obfs: Optional[str] = None  # for SSR
    obfs_param: Optional[str] = None  # for SSR
    protocol_param: Optional[str] = None  # for SSR

    # Metadata
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    latency: Optional[float] = None
    speed: Optional[float] = None
    score: float = 0.0

    # Source tracking
    source_url: Optional[str] = None
    added_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_checked: Optional[str] = None

    def to_clash_dict(self) -> Dict[str, Any]:
        """Convert to Clash configuration dictionary"""
        base = {
            "name": self.name,
            "type": self.protocol.value,
            "server": self.server,
            "port": self.port,
        }

        if self.protocol == Protocol.VMESS:
            base.update({
                "uuid": self.uuid or "",
                "alterId": self.aid or 0,
                "cipher": self.cipher or "auto",
                "tls": self.tls,
            })
            if self.network:
                base["network"] = self.network
            if self.path:
                base["ws-path"] = self.path
            if self.host:
                base["ws-headers"] = {"Host": self.host}
            if self.sni:
                base["servername"] = self.sni

        elif self.protocol == Protocol.SS:
            base.update({
                "cipher": self.cipher or "aes-256-gcm",
                "password": self.password or "",
            })

        elif self.protocol == Protocol.SSR:
            base.update({
                "cipher": self.cipher or "aes-256-cfb",
                "password": self.password or "",
                "obfs": self.obfs or "plain",
                "protocol": self.protocol_param or "origin",
            })
            if self.obfs_param:
                base["obfs-param"] = self.obfs_param
            if self.protocol_param:
                base["protocol-param"] = self.protocol_param

        elif self.protocol == Protocol.TROJAN:
            base.update({
                "password": self.password or "",
                "tls": self.tls,
            })
            if self.sni:
                base["sni"] = self.sni
            if self.alpn:
                base["alpn"] = self.alpn

        elif self.protocol == Protocol.VLESS:
            base.update({
                "uuid": self.uuid or "",
                "tls": self.tls,
            })
            if self.network:
                base["network"] = self.network
            if self.sni:
                base["servername"] = self.sni
            if self.path:
                base["ws-opts"] = {"path": self.path}
                if self.host:
                    base["ws-opts"]["headers"] = {"Host": self.host}

        elif self.protocol == Protocol.HYSTERIA2:
            base.update({
                "password": self.password or "",
            })
            if self.sni:
                base["sni"] = self.sni

        return base

    def to_v2ray_url(self) -> str:
        """Convert to V2Ray subscription URL format"""
        import base64
        import urllib.parse

        if self.protocol == Protocol.VMESS:
            vmess_config = {
                "v": "2",
                "ps": self.name,
                "add": self.server,
                "port": str(self.port),
                "id": self.uuid or "",
                "aid": str(self.aid or 0),
                "net": self.network or "tcp",
                "type": "none",
                "host": self.host or "",
                "path": self.path or "",
                "tls": "tls" if self.tls else "",
            }
            json_str = json.dumps(vmess_config)
            encoded = base64.b64encode(json_str.encode()).decode()
            return f"vmess://{encoded}"

        elif self.protocol == Protocol.SS:
            userinfo = base64.b64encode(
                f"{self.cipher}:{self.password}".encode()
            ).decode()
            return f"ss://{userinfo}@{self.server}:{self.port}#{urllib.parse.quote(self.name)}"

        elif self.protocol == Protocol.TROJAN:
            return f"trojan://{self.password}@{self.server}:{self.port}#{urllib.parse.quote(self.name)}"

        elif self.protocol == Protocol.VLESS:
            params = {}
            if self.network:
                params["type"] = self.network
            if self.path:
                params["path"] = self.path
            if self.host:
                params["host"] = self.host
            if self.tls:
                params["security"] = "tls"
            if self.sni:
                params["sni"] = self.sni

            query = urllib.parse.urlencode(params)
            return f"vless://{self.uuid}@{self.server}:{self.port}?{query}#{urllib.parse.quote(self.name)}"

        return ""

    def get_hash(self) -> str:
        """Generate unique hash for deduplication"""
        key = f"{self.protocol.value}:{self.server}:{self.port}"
        if self.uuid:
            key += f":{self.uuid}"
        if self.password:
            key += f":{self.password}"
        return hashlib.md5(key.encode()).hexdigest()

    def calculate_score(self):
        """Calculate node quality score (0-100)"""
        score = 50.0  # Base score

        if self.latency:
            if self.latency < 100:
                score += 30
            elif self.latency < 200:
                score += 20
            elif self.latency < 500:
                score += 10
            else:
                score -= 20

        if self.speed:
            if self.speed > 10:
                score += 20
            elif self.speed > 5:
                score += 10

        self.score = min(100, max(0, score))
        return self.score

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.get_hash() == other.get_hash()

    def __hash__(self):
        return hash(self.get_hash())
