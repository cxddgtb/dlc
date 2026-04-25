"""
Smart deduplication for nodes
"""
from typing import List, Dict
from collections import defaultdict
from src.core.node import Node
from src.utils.logger import log


class Deduplicator:
    """Intelligent node deduplication with quality scoring"""

    def __init__(self, strategy: str = "best"):
        """
        Args:
            strategy: 'best' (keep best score), 'first' (keep first seen)
        """
        self.strategy = strategy

    def deduplicate(self, nodes: List[Node]) -> List[Node]:
        """
        Remove duplicate nodes based on hash
        For duplicates, keep the one with best score
        """
        if not nodes:
            return []

        # Group by hash
        groups: Dict[str, List[Node]] = defaultdict(list)
        for node in nodes:
            groups[node.get_hash()].append(node)

        # Select best from each group
        unique_nodes = []
        for hash_key, group in groups.items():
            if len(group) == 1:
                unique_nodes.append(group[0])
            else:
                # Keep the one with highest score or lowest latency
                best = self._select_best(group)
                unique_nodes.append(best)

        log.info(f"Deduplication: {len(nodes)} -> {len(unique_nodes)} nodes")
        return unique_nodes

    def _select_best(self, nodes: List[Node]) -> Node:
        """Select the best node from a group of duplicates"""
        if self.strategy == "first":
            return nodes[0]

        # Default: select by score/latency
        scored = []
        for node in nodes:
            score = node.score
            if node.latency:
                # Lower latency is better
                score += (1000 - node.latency) / 10
            scored.append((score, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def remove_similar_servers(
        self, nodes: List[Node], max_per_server: int = 3
    ) -> List[Node]:
        """
        Limit number of nodes per server to avoid concentration
        """
        server_groups: Dict[str, List[Node]] = defaultdict(list)

        for node in nodes:
            server_groups[node.server].append(node)

        result = []
        for server, server_nodes in server_groups.items():
            # Sort by score and take top N
            server_nodes.sort(key=lambda n: n.score, reverse=True)
            result.extend(server_nodes[:max_per_server])

        log.info(
            f"Server limit: {len(nodes)} -> {len(result)} nodes "
            f"(max {max_per_server} per server)"
        )
        return result
