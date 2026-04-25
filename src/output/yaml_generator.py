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
        """Generate Clash YAML file with STRICTLY unique proxy names"""
        config = self.base_config.copy()

        # Convert nodes to Clash format with STRICTLY unique names
        used_names = set()
        proxies = []
        unique_names = []
        
        for node in nodes:
            # Clean and validate base name
            base_name = node.name.strip()
            if not base_name or len(base_name) == 0:
                base_name = f"{node.server}:{node.port}"
            
            # Remove any characters that might cause issues
            clean_name = base_name.replace('\n', ' ').replace('\r', ' ').strip()
            if not clean_name:
                clean_name = f"Node-{node.server}-{node.port}"
            
            # Ensure absolutely unique name
            final_name = clean_name
            counter = 1
            
            while final_name in used_names:
                final_name = f"{clean_name}_{counter}"
                counter += 1
            
            # Mark name as used
            used_names.add(final_name)
            
            # Create proxy dict with guaranteed unique name
            proxy_dict = node.to_clash_dict()
            proxy_dict["name"] = final_name
            proxies.append(proxy_dict)
            unique_names.append(final_name)

        config["proxies"] = proxies

        # Setup proxy groups - ONLY reference existing proxy names
        if "proxy-groups" not in config:
            config["proxy-groups"] = []

        # Update ALL proxy groups to only reference existing proxies
        for group in config["proxy-groups"]:
            group_name = group.get("name", "")
            
            # For selector groups, use actual proxy names
            if group.get("type") == "select":
                if group_name == "🚀 节点选择":
                    # Main selector - include strategy groups and top proxies
                    strategy_groups = ["♻️ 自动选择", "🔰 延迟最低", "🎯 负载均衡"]
                    group["proxies"] = strategy_groups + unique_names[:50]
            elif group.get("type") in ["url-test", "load-balance"]:
                # Auto groups should reference all available proxies
                group["proxies"] = unique_names[:200]

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

        log.info(f"Generated Clash YAML: {len(proxies)} proxies -> {output_file}")
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
