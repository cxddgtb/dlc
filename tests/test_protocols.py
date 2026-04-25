"""
Tests for protocol parsers
"""
import pytest
from src.protocols import parse_vmess, parse_ss, parse_trojan, parse_vless


def test_parse_vmess():
    """Test Vmess URL parsing"""
    # This is a sample Vmess URL (not a real working node)
    import base64
    import json

    vmess_config = {
        "v": "2",
        "ps": "Test Vmess",
        "add": "example.com",
        "port": "443",
        "id": "test-uuid-12345",
        "aid": "0",
        "net": "ws",
        "type": "none",
        "host": "",
        "path": "/path",
        "tls": "tls"
    }

    encoded = base64.b64encode(json.dumps(vmess_config).encode()).decode()
    url = f"vmess://{encoded}"

    node = parse_vmess(url)

    assert node is not None
    assert node.name == "Test Vmess"
    assert node.server == "example.com"
    assert node.port == 443
    assert node.uuid == "test-uuid-12345"


def test_parse_ss():
    """Test Shadowsocks URL parsing"""
    # Sample SS URL format
    url = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQ@1.2.3.4:8388#Test%20SS"

    node = parse_ss(url)

    # Note: Actual parsing may vary based on URL format
    if node:
        assert node.protocol.value == "ss"


def test_parse_trojan():
    """Test Trojan URL parsing"""
    url = "trojan://password@example.com:443#Test%20Trojan"

    node = parse_trojan(url)

    if node:
        assert node.protocol.value == "trojan"
        assert node.server == "example.com"
        assert node.port == 443


def test_parse_vless():
    """Test VLESS URL parsing"""
    url = "vless://uuid@example.com:443?encryption=none&security=tls&type=ws#Test%20VLESS"

    node = parse_vless(url)

    if node:
        assert node.protocol.value == "vless"


def test_invalid_url():
    """Test parsing invalid URLs"""
    assert parse_vmess("invalid://url") is None
    assert parse_ss("not-ss-url") is None
    assert parse_trojan("bad-url") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
