"""
Base64 encoder for V2Ray subscription format
"""
import base64
from typing import List
from pathlib import Path
from src.core.node import Node
from src.utils.logger import log


class Base64Encoder:
    """Encode nodes to V2Ray subscription format"""

    @staticmethod
    def encode_nodes(nodes: List[Node], output_file: str = "output/list.txt") -> Path:
        """
        Encode nodes to Base64 format (V2Ray subscription)
        Returns path to output file
        """
        if not nodes:
            log.warning("No nodes to encode, creating empty file")
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("")
            return output_path

        # Convert each node to URL
        urls = []
        for node in nodes:
            url = node.to_v2ray_url()
            if url:
                urls.append(url)

        # Join with newlines and encode
        content = "\n".join(urls)
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        # Write to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(encoded)

        log.info(f"Encoded {len(urls)} nodes to Base64: {output_file}")
        return output_path

    @staticmethod
    def encode_raw_urls(nodes: List[Node], output_file: str = "output/list_raw.txt") -> Path:
        """Save raw URLs without Base64 encoding"""
        urls = []
        for node in nodes:
            url = node.to_v2ray_url()
            if url:
                urls.append(url)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(urls))

        log.info(f"Saved {len(urls)} raw URLs: {output_file}")
        return output_path
