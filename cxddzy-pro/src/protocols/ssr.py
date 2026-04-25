"""
ShadowsocksR protocol parser
"""
import base64
from typing import Optional
from src.core.node import Node, Protocol
from src.utils.logger import log


def parse_ssr(url: str, source_url: Optional[str] = None) -> Optional[Node]:
    """Parse SSR URL to Node object"""
    try:
        if not url.startswith("ssr://"):
            return None

        encoded = url[6:]  # Remove 'ssr://' prefix

        # Add padding
        missing_padding = len(encoded) % 4
        if missing_padding:
            encoded += "=" * (4 - missing_padding)

        decoded = base64.b64decode(encoded).decode("utf-8")

        # Parse format: server:port:protocol:method:obfs:password_base64/?params
        if "/?" in decoded:
            main_part, params_str = decoded.split("/?", 1)
        else:
            main_part = decoded
            params_str = ""

        parts = main_part.split(":")
        if len(parts) < 6:
            return None

        server = parts[0]
        port = int(parts[1])
        protocol = parts[2]
        cipher = parts[3]
        obfs = parts[4]

        # Password is base64 encoded
        password_b64 = parts[5]
        missing_padding = len(password_b64) % 4
        if missing_padding:
            password_b64 += "=" * (4 - missing_padding)
        password = base64.b64decode(password_b64).decode("utf-8")

        # Parse parameters
        params = {}
        if params_str:
            for param in params_str.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    # Decode base64 values
                    try:
                        missing_padding = len(value) % 4
                        if missing_padding:
                            value += "=" * (4 - missing_padding)
                        params[key] = base64.b64decode(value).decode("utf-8")
                    except:
                        params[key] = value

        obfs_param = params.get("obfsparam", "")
        protocol_param = params.get("protoparam", "")
        remarks = params.get("remarks", f"{server}:{port}")

        node = Node(
            name=remarks,
            protocol=Protocol.SSR,
            server=server,
            port=port,
            cipher=cipher,
            password=password,
            obfs=obfs,
            obfs_param=obfs_param,
            protocol_param=protocol,
            source_url=source_url,
        )

        return node

    except Exception as e:
        log.error(f"Failed to parse SSR URL: {e}")
        return None
