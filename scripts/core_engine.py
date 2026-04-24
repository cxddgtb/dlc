#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NoMoreWalls-Pro | Extreme Core Engine (Final Fixed Version)
修复了 safe_b64_decode 崩溃问题和 SS 节点解析错误 (unknown method: ss)。
增加了 SS 解析结果的校验，自动丢弃非法节点。
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
def safe_b64_decode( str) -> str:
    """修复：参数名统一为 data，增加异常处理"""
    try:
        if not 
            return ""
        data = data.strip()
        # 补齐 Base64 填充
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
    """
    修复：重写 SS 解析逻辑，兼容多种格式，防止 cipher 被错误识别为 'ss'
    """
    try:
        # 移除 ss:// 前缀
        raw_content = link[5:]
        
        # 1. 分离备注 (#)
        remark = ""
        if "#" in raw_content:
            raw_content, remark = raw_content.split("#", 1)
            remark = urllib.parse.unquote(remark)
        
        # 2. 尝试查找 @ 分隔符
        if "@" in raw_content:
            user_info, server_info = raw_content.split("@", 1)
            
            # 解析服务器信息 (host:port)
            # 处理 IPv6 [::1]:port 情况
            if server_info.startswith("["):
                match = re.match(r'\[([^\]]+)\]:(\d+)', server_info)
                if match:
                    server, port = match.group(1), match.group(2)
                else:
                    return None
            else:
                if ":" in server_info:
                    server, port = server_info.rsplit(":", 1)
                else:
                    return None
            
            # 解析用户信息 (cipher:password)
            cipher, password = "", ""
            
            # 尝试 Base64 解码 user_info
            decoded_user = safe_b64_decode(user_info)
            
            if ":" in decoded_user and len(decoded_user) > 2:
                # 解码成功且包含冒号，例如: aes-128-gcm:password
                cipher, password = decoded_user.split(":", 1)
            elif ":" in user_info:
                # 解码失败或为空，尝试直接按明文处理 (SIP002 格式)
                cipher, password = user_info.split(":", 1)
            else:
                return None
                
        else:
            # 3. 没有 @，尝试整体 Base64 解码
            # 格式通常是: base64(method:password@host:port)
            decoded_full = safe_b64_decode(raw_content)
            if "@" in decoded_full:
                u_info, s_info = decoded_full.split("@", 1)
                if ":" in u_info and ":" in s_info:
                    cipher, password = u_info.split(":", 1)
                    server, port = s_info.rsplit(":", 1)
                else:
                    return None
            else:
                return None

        # 4. 校验解析结果 (防止 cipher 为 'ss' 或空)
        if not cipher or cipher.strip() == "" or cipher.strip().lower() == "ss":
            logger.debug(f"Invalid SS cipher detected: '{cipher}'. Skipping node.")
            return None
            
        # 清理端口号中的非法字符（如 ?plugin=...）
        if "?" in port:
            port = port.split("?")[0]

        return {
            "name": remark or f"SS-{server}",
            "type": "ss",
            "server": server,
            "port": int(port),
            "cipher": cipher,
            "password": password,
            "udp": True
        }
    except Exception as e:
        # logger.debug(f"SS parse failed: {e}")
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
            if data and isinstance(data, dict) and "proxies" in 
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
    
    if not tested_nodes:
        logger.warning("No nodes passed speed test. Generating empty config.")
        
    node_names = [n["name"] for n in tested_nodes if n.get("name")]
    
    template["proxies"] = tested_nodes
    
    for group in template.get("proxy-groups", []):
        if group["type"] in ("url-test", "fallback", "load-balance"):
            group["proxies"] = node_names if node_names else ["DIRECT"]
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
    logger.info("🚀 NoMoreWalls-Pro Extreme Engine Start (Final Fixed)")
    logger.info("="*50)
    
    new_nodes = fetch_subscriptions()
    logger.info(f"New parsed nodes: {len(new_nodes)}")
    
    old_nodes = load_archives()
    merged = deduplicate(new_nodes + old_nodes)
    
    if not merged:
        logger.error("No nodes available after merging.")
        generate_config([])
        sys.exit(0)
        
    tested = run_speed_test(merged)
    
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
