"""
VLESS protocol parser
"""
import urllib.parse
from typing import Optional
from src.core.node import Node, Protocol
from src.utils.logger import log


def parse_vless(url: str, source_url: Optional[str] = None) -> Optional[Node]:
    """Parse VLESS URL to Node object"""
    try:
        if not url.startswith("vless://"):
            return None

        parsed = urllib.parse.urlparse(url)

        uuid = parsed.username
        server = parsed.hostname
        port = parsed.port

        if not server or not port or not uuid:
            return None

        # Parse query parameters
        params = urllib.parse.parse_qs(parsed.query)

        network = params.get("type", ["tcp"])[0]
        security = params.get("security", ["none"])[0]
        path = params.get("path", ["/"])[0]
        host = params.get("host", [None])[0]
        sni = params.get("sni", [None])[0]
        flow = params.get("flow", [None])[0]

        tls = security in ["tls", "xtls"]

        # Extract name from fragment
        name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else f"{server}:{port}"

        node = Node(
            name=name,
            protocol=Protocol.VLESS,
            server=server,
            port=port,
            uuid=uuid,
            network=network,
            tls=tls,
            path=path,
            host=host,
            sni=sni,
            source_url=source_url,
        )

        return node

    except Exception as e:
        log.error(f"Failed to parse VLESS URL: {e}")
        return None
