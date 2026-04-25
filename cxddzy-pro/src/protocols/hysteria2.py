"""
Hysteria2 protocol parser
"""
import urllib.parse
from typing import Optional
from src.core.node import Node, Protocol
from src.utils.logger import log


def parse_hysteria2(url: str, source_url: Optional[str] = None) -> Optional[Node]:
    """Parse Hysteria2 URL to Node object"""
    try:
        if not url.startswith("hysteria2://") and not url.startswith("hy2://"):
            return None

        # Normalize prefix
        if url.startswith("hy2://"):
            url = url.replace("hy2://", "hysteria2://")

        parsed = urllib.parse.urlparse(url)

        password = parsed.username or parsed.password
        server = parsed.hostname
        port = parsed.port

        if not server or not port or not password:
            return None

        # Parse query parameters
        params = urllib.parse.parse_qs(parsed.query)

        sni = params.get("sni", [None])[0]
        alpn = params.get("alpn", [None])[0]
        if alpn:
            alpn = alpn.split(",")

        # Extract name from fragment
        name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else f"{server}:{port}"

        node = Node(
            name=name,
            protocol=Protocol.HYSTERIA2,
            server=server,
            port=port,
            password=password,
            sni=sni,
            alpn=alpn or [],
            source_url=source_url,
        )

        return node

    except Exception as e:
        log.error(f"Failed to parse Hysteria2 URL: {e}")
        return None
