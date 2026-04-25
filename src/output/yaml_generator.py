"""
YAML output generator for Clash configuration
"""
import yaml
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
from src.core.node import Node
from src.utils.logger import log


class YAMLGenerator:
    """Generate Clash YAML configuration files"""

    def __init__(self, config_template: str = "config/clash.yml"):
        self.template_path = Path(config_template)
        self.base_config = self._load_template()

    def _load_template(self) -> Dict[str, Any]:
        """Load base configuration template"""
        if self.template_path.exists():
            try:
                with open(self.template_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
            except Exception as e:
                log.warning(f"Failed to load template: {e}")

        # Return minimal default config
        return {
            "port": 7890,
            "socks-port": 7891,
            "mixed-port": 7892,
            "allow-lan": False,
            "mode": "rule",
            "log-level": "info",
            "dns": {
                "enable": True,
                "listen": ":1053",
                "nameserver": ["223.5.5.5", "114.114.114.114"],
                "fallback": ["8.8.8.8", "1.1.1.1"],
            },
        }

    def generate_clash_yaml(
        self, nodes: List[Node], output_file: str = "output/list.yml"
    ):
        """Generate Clash YAML file"""
        config = self.base_config.copy()

        # Convert nodes to Clash format
        proxies = [node.to_clash_dict() for node in nodes] if nodes else []
        config["proxies"] = proxies

        # Generate proxy names list
        proxy_names = [node.name for node in nodes] if nodes else []

        # Setup proxy groups
        if "proxy-groups" not in config:
            config["proxy-groups"] = []

        # Update or create default proxy group
        has_default = False
        for group in config["proxy-groups"]:
            if group.get("name") == "🚀 节点选择":
                group["proxies"] = proxy_names[:50] if proxy_names else ["DIRECT"]
                has_default = True
                break

        if not has_default:
            config["proxy-groups"].append(
                {
                    "name": "🚀 节点选择",
                    "type": "select",
                    "proxies": proxy_names[:50] if proxy_names else ["DIRECT"],
                }
            )

        # Write to file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                config,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )

        log.info(f"Generated Clash YAML: {len(nodes)} nodes -> {output_file}")
        return output_path

    def generate_meta_yaml(
        self, nodes: List[Node], output_file: str = "output/list.meta.yml"
    ):
        """Generate Clash Meta YAML file (with extended features)"""
        config = self.generate_clash_yaml(nodes, output_file)

        # Add Meta-specific features
        meta_config = {}
        with open(output_file, "r", encoding="utf-8") as f:
            meta_config = yaml.safe_load(f)

        # Add sniffer config for Meta
        meta_config["sniffer"] = {
            "enable": True,
            "sniff": {
                "HTTP": {"ports": [80, 8080]},
                "TLS": {"ports": [443, 8443]},
            },
        }

        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(
                meta_config,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )

        log.info(f"Generated Meta YAML: {output_file}")
        return output_file
