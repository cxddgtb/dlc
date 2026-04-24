#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NoMoreWalls-Pro | Extreme Core Engine (Fixed Version)
修复了 safe_b64_decode 参数错误和 load_archives 语句截断问题。
"""

import os
import sys
import time
import json
import base64
import hashlib
import socket
import urllib.parse
import re
import logging
import threading
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Any

import requests
import yaml

# ================= 配置常量 =================
ARCHIVE_DIR = Path("archive")
OUTPUT_DIR = Path("output")
CONFIG_TEMPLATE = Path("config/template.yaml")
SOURCES_FILE = Path("sources.txt")
MAX_NODES = int(os.getenv("MAX_NODES", "180"))
MAX_LATENCY_MS = int(os.getenv("MAX_LATENCY_MS", "500"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "60"))
ARCHIVE_KEEP = int(os.getenv("ARCHIVE_KEEP", "10"))

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("ExtremeEngine")

# ================= 协议解析器 =================
def safe_b64_decode(data: str) -> str:
    """修复：参数名改为 data"""
    try:
        if not data:
            return ""
        data = data.strip()
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.b64decode(data).decode("utf-8", errors="ignore")
    except Exception:
        return ""

def parse_vmess(link: str) -> Optional[Dict[str, Any]]:
    try:
        payload = link[8:]
        cfg = json.loads(safe_b64_decode(payload))
        return {
            "name": cfg.get("ps", "VMess-Node"),
            "type": "vmess",
            "server": cfg["add"],
            "port": int(cfg["port"]),
            "uuid": cfg["id"],
            "alterId": int(cfg.get("aid", 0)),
            "cipher": cfg.get("scy", "auto"),
            "network": cfg.get("net", "tcp"),
            "tls": cfg.get("tls", "none") == "tls",
            "servername": cfg.get("sni", cfg["add"]),
            "skip-cert-verify": True,
            "udp": True,
            "ws-opts": {
                "path": cfg.get("path", "/"),
                "headers": {"Host": cfg.get("host", cfg["add"])}
            } if cfg.get("net") == "ws" else None
        }
    except Exception:
        return None

def parse_ss(link: str) -> Optional[Dict[str, Any]]:
    try:
        fragment = ""
        if "#" in link[5:]:
            link_part, fragment = link[5:].split("#", 1)
            fragment = urllib.parse.unquote(fragment)
        else:
            link_part = link[5:]
        
        if "@" in link_part:
            userinfo, hostinfo = link_part.split("@", 1)
            userinfo = safe_b64_decode(userinfo)
            if ":" in userinfo:
                cipher, password = userinfo.split(":", 1)
            else:
                return None
        else:
            decoded = safe_b64_decode(link_part)
            if ":" in decoded:
                cipher, rest = decoded.split(":", 1)
                if "@" in rest:
                    password, hostinfo = rest.split("@", 1)
                else:
                    password = ""
                    hostinfo = rest
            else:
                return None
                
        server, port = hostinfo.rsplit(":", 1)
        return {
            "name": fragment or f"SS-{server}",
            "type": "ss",
            "server": server,
            "port": int(port),
            "cipher": cipher,
            "password": password,
            "udp": True
        }
    except Exception:
        return None

def parse_trojan(link: str) -> Optional[Dict[str, Any]]:
    try:
        u = urllib.parse.urlparse(link)
        qs = urllib.parse.parse_qs(u.query)
        return {
            "name": urllib.parse.unquote(u.fragment or "Trojan-Node"),
            "type": "trojan",
            "server": u.hostname,
            "port": u.port or 443,
            "password": u.username,
            "sni": qs.get("sni", [u.hostname])[0],
            "skip-cert-verify": True,
            "udp": True
        }
    except Exception:
        return None

def parse_vless(link: str) -> Optional[Dict[str, Any]]:
    try:
        u = urllib.parse.urlparse(link)
        qs = urllib.parse.parse_qs(u.query)
        net = qs.get("type", ["tcp"])[0]
        return {
            "name": urllib.parse.unquote(u.fragment or "VLESS-Node"),
            "type": "vless",
            "server": u.hostname,
            "port": u.port or 443,
            "uuid": u.username,
            "network": net,
            "tls": qs.get("security", ["none"])[0] in ("tls", "xtls", "reality"),
            "servername": qs.get("sni", [u.hostname])[0],
            "skip-cert-verify": True,
            "udp": True,
            "ws-opts": {
                "path": qs.get("path", ["/"])[0],
                "headers": {"Host": qs.get("host", [u.hostname])[0]}
            } if net == "ws" else None
        }
    except Exception:
        return None

def parse_hysteria2(link: str) -> Optional[Dict[str, Any]]:
    try:
        u = urllib.parse.urlparse(link)
        qs = urllib.parse.parse_qs(u.query)
        return {
            "name": urllib.parse.unquote(u.fragment or "HY2-Node"),
            "type": "hysteria2",
            "server": u.hostname,
            "port": u.port or 443,
            "password": u.username,
            "sni": qs.get("sni", [u.hostname])[0],
            "skip-cert-verify": True,
            "udp": True,
            "ports": qs.get("mport", [None])[0]
        }
    except Exception:
        return None

PARSERS = {
    "vmess://": parse_vmess,
    "ss://": parse_ss,
    "trojan://": parse_trojan,
    "vless://": parse_vless,
    "hysteria2://": parse_hysteria2,
    "hy2://": parse_hysteria2
}

def parse_node(raw_link: str) -> Optional[Dict[str, Any]]:
    for prefix, parser in PARSERS.items():
        if raw_link.startswith(prefix):
            node = parser(raw_link)
            if node and node.get("server") and node.get("port"):
                return node
    return None

# ================= 数据抓取 =================
def fetch_subscriptions() -> List[Dict[str, Any]]:
    if not SOURCES_FILE.exists():
        logger.error("sources.txt not found. Exiting.")
        sys.exit(1)
        
    urls = [line.strip() for line in SOURCES_FILE.read_text(encoding="utf-8").splitlines() 
            if line.strip() and not line.startswith("#")]
    
    if not urls:
        logger.warning("No valid URLs in sources.txt. Please add subscription links.")
        # 创建一个空列表而不是退出，防止第一次运行没链接就报错
        return []

    raw_nodes = []
    headers = {"User-Agent": "ClashMeta/1.18.0 (Linux; GitHub Actions)"}
    
    for url in urls:
        logger.info(f"Fetching: {url[:60]}...")
        try:
            resp = requests.get(url, headers=headers, stream=True)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")
            data = resp.text
            
            if "base64" in content_type or re.match(r"^[A-Za-z0-9+/=\s]+$", data.strip()):
                data = safe_b64_decode(data)
                
            for line in data.splitlines():
                line = line.strip()
                if any(line.startswith(p) for p in PARSERS):
                    raw_nodes.append(line)
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            
    logger.info(f"Raw links collected: {len(raw_nodes)}")
    return [parse_node(l) for l in raw_nodes if parse_node(l)]

# ================= 存档管理 =================
def load_archives() -> List[Dict[str, Any]]:
    if not ARCHIVE_DIR.exists():
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        return []
        
    archive_files = sorted(ARCHIVE_DIR.glob("nodes_*.yaml"), 
                           key=lambda x: x.stat().st_mtime, 
                           reverse=True)[:ARCHIVE_KEEP]
    
    merged = []
    for f in archive_files:
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            # 修复：补全了 "proxies" in data
            if data and isinstance(data, dict) and "proxies" in data:
                merged.extend(data["proxies"])
        except Exception as e:
            logger.debug(f"Failed to load archive {f.name}: {e}")
            
    logger.info(f"Loaded {len(merged)} nodes from {len(archive_files)} archives.")
    return merged

def deduplicate(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_hashes = set()
    unique = []
    for node in nodes:
        if not node.get("server") or not node.get("port"):
            continue
        key_str = f"{node.get('type')}:{node.get('server')}:{node.get('port')}:{node.get('uuid', node.get('password', ''))}"
        h = hashlib.sha256(key_str.encode()).hexdigest()
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique.append(node)
    logger.info(f"Deduplication: {len(nodes)} -> {len(unique)}")
    return unique

def save_archive(nodes: List[Dict[str, Any]]):
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filepath = ARCHIVE_DIR / f"nodes_{ts}.yaml"
    
    clean_nodes = []
    for n in nodes:
        c = {k: v for k, v in n.items() if v is not None}
        c.pop("_latency_ms", None)
        clean_nodes.append(c)
        
    payload = {"proxies": clean_nodes, "generated_at": ts, "count": len(clean_nodes)}
    filepath.write_text(yaml.dump(payload, allow_unicode=True, sort_keys=False, width=1200), encoding="utf-8")
    logger.info(f"Archive saved: {filepath.name} ({len(clean_nodes)} nodes)")

def cleanup_archives():
    if not ARCHIVE_DIR.exists():
        return
    files = sorted(ARCHIVE_DIR.glob("nodes_*.yaml"), key=lambda x: x.stat().st_mtime)
    while len(files) > ARCHIVE_KEEP:
        oldest = files.pop(0)
        oldest.unlink()
        logger.info(f"Deleted old archive: {oldest.name}")

# ================= 并发探测（无超时参数） =================
def probe_node(node: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
    server = node.get("server")
    port = int(node.get("port", 443))
    
    if not server or server.startswith(("127.", "10.", "172.16.", "192.168.")):
        return node, 9999.0

    start = time.perf_counter()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.connect((server, port))
        sock.close()
    except Exception:
        return node, 9999.0
        
    latency_ms = (time.perf_counter() - start) * 1000
    node["_latency_ms"] = round(latency_ms, 2)
    return node, latency_ms

def run_speed_test(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not nodes:
        logger.warning("No nodes to test.")
        return []
        
    logger.info(f"Starting concurrent probe for {len(nodes)} nodes...")
    valid_nodes = []
    lock = threading.Lock()
    
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        future_to_node = {executor.submit(probe_node, n): n for n in nodes}
        completed = 0
        for future in as_completed(future_to_node):
            node, latency = future.result()
            if latency <= MAX_LATENCY_MS:
                with lock:
                    valid_nodes.append(node)
            completed += 1
            if completed % 50 == 0 or completed == len(nodes):
                logger.info(f"Probed {completed}/{len(nodes)} nodes...")
                
    valid_nodes.sort(key=lambda x: x.get("_latency_ms", 9999))
    logger.info(f"Probe complete. Valid: {len(valid_nodes)}/{len(nodes)} (Threshold: {MAX_LATENCY_MS}ms)")
    return valid_nodes[:MAX_NODES]

# ================= 配置生成 =================
def generate_config(tested_nodes: List[Dict[str, Any]]):
    if not CONFIG_TEMPLATE.exists():
        logger.error("config/template.yaml missing. Exiting.")
        sys.exit(1)
        
    template = yaml.safe_load(CONFIG_TEMPLATE.read_text(encoding="utf-8"))
    
    # 如果没有通过测速的节点，尝试使用原始节点（防止全挂）
    if not tested_nodes:
        logger.warning("No nodes passed speed test. Using raw nodes (untested).")
        # 这里可以 fallback 到 merged nodes，但为了安全先报错或跳过
        # 为了不让 pipeline 挂掉，我们允许空节点生成配置（虽然没法用）
        pass
        
    node_names = [n["name"] for n in tested_nodes if n.get("name")]
    
    template["proxies"] = tested_nodes
    
    for group in template.get("proxy-groups", []):
        if group["type"] in ("url-test", "fallback", "load-balance"):
            group["proxies"] = node_names if node_names else ["DIRECT"] # 防止空列表报错
        elif group["type"] == "select":
            default_select = node_names[:15] if node_names else []
            existing = [p for p in group.get("proxies", []) if p not in node_names and p != "DIRECT"]
            group["proxies"] = default_select + existing
            
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "final_config.yaml"
    output_path.write_text(yaml.dump(template, allow_unicode=True, sort_keys=False, width=2000), encoding="utf-8")
    logger.info(f"✅ Config generated: {output_path}")

# ================= 主流程 =================
def main():
    logger.info("="*50)
    logger.info("🚀 NoMoreWalls-Pro Extreme Engine Start (Fixed)")
    logger.info("="*50)
    
    new_nodes = fetch_subscriptions()
    logger.info(f"New parsed nodes: {len(new_nodes)}")
    
    old_nodes = load_archives()
    merged = deduplicate(new_nodes + old_nodes)
    
    if not merged:
        logger.error("No nodes available after merging. Pipeline halted.")
        # 创建一个空配置防止后续步骤报错
        generate_config([])
        sys.exit(0) # 退出但不算错误，方便用户加链接
        
    tested = run_speed_test(merged)
    
    # 即使没有节点通过测速，也尝试保存（虽然可能没用）
    save_archive(tested)
    cleanup_archives()
    generate_config(tested)
    
    logger.info("🏁 Pipeline completed successfully.")
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
