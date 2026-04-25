"""
Shadowsocks protocol parser
"""
import base64
import urllib.parse
from typing import Optional
from src.core.node import Node, Protocol
from src.utils.logger import log


def parse_ss(url: str, source_url: Optional[str] = None) -> Optional[Node]:
    """Parse Shadowsocks URL to Node object"""
    try:
        if not url.startswith("ss://"):
            return None

        url = url[5:]  # Remove 'ss://' prefix

        # Check if contains @ (new format) or not (old format)
        if "@" in url:
            userinfo_part, rest = url.split("@", 1)
        else:
            # Old format: ss://base64(method:password@server:port)#name
            if "#" in url:
                url_part, name = url.rsplit("#", 1)
            else:
                url_part = url
                name = "SS Node"

            # Add padding
            missing_padding = len(url_part) % 4
            if missing_padding:
                url_part += "=" * (4 - missing_padding)

            decoded = base64.b64decode(url_part).decode("utf-8")

            # Parse method:password@server:port
            if "@" in decoded:
                userinfo_part, rest = decoded.rsplit("@", 1)
            else:
                return None

        # Parse server:port
        if "]" in rest:  # IPv6
            server_end = rest.index("]") + 1
            server = rest[:server_end]
            port_str = rest[server_end + 1:] if server_end < len(rest) else ""
        else:
            parts = rest.rsplit(":", 1)
            if len(parts) != 2:
                return None
            server, port_str = parts

        port = int(port_str.split("#")[0])

        # Decode userinfo
        missing_padding = len(userinfo_part) % 4
        if missing_padding:
            userinfo_part += "=" * (4 - missing_padding)

        try:
            decoded_userinfo = base64.b64decode(userinfo_part).decode("utf-8")
            if ":" in decoded_userinfo:
                cipher, password = decoded_userinfo.split(":", 1)
            else:
                cipher = "aes-256-gcm"
                password = decoded_userinfo
        except:
            cipher = "aes-256-gcm"
            password = userinfo_part

        # Extract name from fragment
        name = "SS Node"
        if "#" in rest:
            name = urllib.parse.unquote(rest.split("#", 1)[1])

        if not server or not port:
            return None

        node = Node(
            name=name,
            protocol=Protocol.SS,
            server=server,
            port=port,
            cipher=cipher,
            password=password,
            source_url=source_url,
        )

        return node

    except Exception as e:
        log.error(f"Failed to parse SS URL: {e}")
        return None
