"""
Region classifier for nodes
"""
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import yaml
from src.core.node import Node
from src.utils.logger import log


class Classifier:
    """Intelligent region classifier for proxy nodes"""

    DEFAULT_REGIONS = {
        "HK": {
            "keywords": ["港", "hk", "hongkong", "hong kong", "🇭🇰"],
            "name": "香港",
        },
        "TW": {
            "keywords": ["台", "tw", "taiwan", "台北", "台中", "🇹🇼"],
            "name": "台湾",
        },
        "JP": {
            "keywords": ["日", "jp", "japan", "tokyo", "东京", "大阪", "🇯🇵"],
            "name": "日本",
        },
        "KR": {
            "keywords": ["韩", "kr", "korea", "seoul", "首尔", "🇰🇷"],
            "name": "韩国",
        },
        "US": {
            "keywords": ["美", "us", "united states", "america", "los angeles", "san jose", "🇺🇸"],
            "name": "美国",
        },
        "SG": {
            "keywords": ["新", "sg", "singapore", "狮城", "🇸🇬"],
            "name": "新加坡",
        },
        "GB": {
            "keywords": ["英", "uk", "gb", "britain", "london", "🇬🇧"],
            "name": "英国",
        },
        "DE": {
            "keywords": ["德", "de", "germany", "frankfurt", "🇩🇪"],
            "name": "德国",
        },
        "FR": {
            "keywords": ["法", "fr", "france", "paris", "🇫🇷"],
            "name": "法国",
        },
        "CA": {
            "keywords": ["加", "ca", "canada", "🇨🇦"],
            "name": "加拿大",
        },
        "AU": {
            "keywords": ["澳", "au", "australia", "sydney", "🇦🇺"],
            "name": "澳大利亚",
        },
        "CN": {
            "keywords": ["cn", "china", "中国", "上海", "北京", "广东", "深圳", "🇨🇳"],
            "name": "中国",
        },
    }

    def __init__(self, config_file: Optional[str] = None):
        self.regions = self.DEFAULT_REGIONS.copy()

        if config_file and Path(config_file).exists():
            self._load_custom_regions(config_file)

        # Compile regex patterns
        self.patterns = {}
        for code, data in self.regions.items():
            pattern = "|".join(re.escape(kw.lower()) for kw in data["keywords"])
            self.patterns[code] = re.compile(pattern, re.IGNORECASE)

    def _load_custom_regions(self, config_file: str):
        """Load custom region configuration from YAML file"""
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                custom_config = yaml.safe_load(f)
                if custom_config:
                    self.regions.update(custom_config)
        except Exception as e:
            log.warning(f"Failed to load custom regions config: {e}")

    def classify(self, node: Node) -> Tuple[Optional[str], Optional[str]]:
        """
        Classify node region
        Returns: (country_code, region_name)
        """
        name_lower = node.name.lower()

        for code, pattern in self.patterns.items():
            if pattern.search(name_lower):
                region_name = self.regions[code]["name"]
                node.country = code
                node.region = region_name
                return code, region_name

        # Default classification
        node.country = "OTHER"
        node.region = "其他地区"
        return "OTHER", "其他地区"

    def classify_batch(self, nodes: List[Node]) -> Dict[str, List[Node]]:
        """Classify multiple nodes and group by region"""
        grouped = {}

        for node in nodes:
            code, name = self.classify(node)
            key = f"{code}_{name}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(node)

        return grouped
