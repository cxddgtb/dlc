"""
Unit tests for Node data model
"""
import pytest
from src.core.node import Node, Protocol


def test_node_creation():
    """Test basic node creation"""
    node = Node(
        name="Test Node",
        protocol=Protocol.VMESS,
        server="example.com",
        port=443,
        uuid="test-uuid"
    )

    assert node.name == "Test Node"
    assert node.protocol == Protocol.VMESS
    assert node.server == "example.com"
    assert node.port == 443
    assert node.uuid == "test-uuid"


def test_node_hash():
    """Test node hash generation"""
    node1 = Node(
        name="Node 1",
        protocol=Protocol.VMESS,
        server="example.com",
        port=443,
        uuid="uuid1"
    )

    node2 = Node(
        name="Node 2",
        protocol=Protocol.VMESS,
        server="example.com",
        port=443,
        uuid="uuid1"
    )

    # Same server+port+uuid should have same hash
    assert node1.get_hash() == node2.get_hash()


def test_node_equality():
    """Test node equality comparison"""
    node1 = Node(
        name="Node 1",
        protocol=Protocol.SS,
        server="server1.com",
        port=8080,
        password="pass1"
    )

    node2 = Node(
        name="Node 2",
        protocol=Protocol.SS,
        server="server1.com",
        port=8080,
        password="pass1"
    )

    node3 = Node(
        name="Node 3",
        protocol=Protocol.SS,
        server="server2.com",
        port=8080,
        password="pass2"
    )

    assert node1 == node2
    assert node1 != node3


def test_vmess_to_clash():
    """Test Vmess node to Clash dict conversion"""
    node = Node(
        name="Vmess Test",
        protocol=Protocol.VMESS,
        server="vmess.example.com",
        port=443,
        uuid="test-uuid",
        aid=0,
        cipher="auto",
        network="ws",
        tls=True,
        path="/path",
        host="host.com"
    )

    clash_dict = node.to_clash_dict()

    assert clash_dict["name"] == "Vmess Test"
    assert clash_dict["type"] == "vmess"
    assert clash_dict["server"] == "vmess.example.com"
    assert clash_dict["port"] == 443
    assert clash_dict["uuid"] == "test-uuid"
    assert clash_dict["tls"] is True


def test_ss_to_clash():
    """Test SS node to Clash dict conversion"""
    node = Node(
        name="SS Test",
        protocol=Protocol.SS,
        server="ss.example.com",
        port=8080,
        cipher="aes-256-gcm",
        password="password123"
    )

    clash_dict = node.to_clash_dict()

    assert clash_dict["name"] == "SS Test"
    assert clash_dict["type"] == "ss"
    assert clash_dict["cipher"] == "aes-256-gcm"
    assert clash_dict["password"] == "password123"


def test_trojan_to_clash():
    """Test Trojan node to Clash dict conversion"""
    node = Node(
        name="Trojan Test",
        protocol=Protocol.TROJAN,
        server="trojan.example.com",
        port=443,
        password="trojan-pass",
        tls=True,
        sni="sni.example.com"
    )

    clash_dict = node.to_clash_dict()

    assert clash_dict["name"] == "Trojan Test"
    assert clash_dict["type"] == "trojan"
    assert clash_dict["password"] == "trojan-pass"
    assert clash_dict["sni"] == "sni.example.com"


def test_score_calculation():
    """Test node score calculation"""
    node = Node(
        name="Test",
        protocol=Protocol.VMESS,
        server="example.com",
        port=443
    )

    # No latency/speed info - base score
    node.calculate_score()
    assert node.score == 50.0

    # Low latency should increase score
    node.latency = 50
    node.calculate_score()
    assert node.score > 50.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
