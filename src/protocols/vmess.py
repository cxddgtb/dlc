"""
Vmess protocol parser
"""
import base64
import json
from typing import Optional, Dict, Any
from src.core.node import Node, Protocol
from src.utils.logger import log


def parse_vmess(url: str, source_url: Optional[str] = None) -> Optional[Node]:
    """Parse Vmess URL to Node object"""
    try:
        if not url.startswith("vmess://"):
            return None

        encoded = url[8:]  # Remove 'vmess://' prefix

        # Remove any whitespace
        encoded = encoded.strip()

        # Add padding if needed
        missing_padding = len(encoded) % 4
        if missing_padding:
            encoded += "=" * (4 - missing_padding)

        decoded = base64.b64decode(encoded).decode("utf-8", errors="ignore")
        config = json.loads(decoded)

        name = config.get("ps", config.get("add", "Unknown"))
        server = config.get("add", "")
        port = int(config.get("port", 0))
        uuid = config.get("id", "")
        aid = int(config.get("aid", 0))
        network = config.get("net", "tcp")
        tls = config.get("tls", "") in ["tls", "1"]
        path = config.get("path", "")
        host = config.get("host", "")
        sni = config.get("sni", config.get("host", ""))
        cipher = config.get("scy", "auto")

        if not server or not port or not uuid:
            log.warning(f"Invalid Vmess config: {config}")
            return None

        node = Node(
            name=name,
            protocol=Protocol.VMESS,
            server=server,
            port=port,
            uuid=uuid,
            aid=aid,
            cipher=cipher,
            network=network,
            tls=tls,
            path=path,
            host=host,
            sni=sni if sni else None,
            source_url=source_url,
        )

        return node

    except Exception as e:
        log.error(f"Failed to parse Vmess URL: {e}")
        return None
