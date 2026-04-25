"""
Smart deduplication for nodes with multiple strategies
"""
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from src.core.node import Node
from src.utils.logger import log


class Deduplicator:
    """Intelligent node deduplication with quality scoring and similarity detection"""

    def __init__(self, strategy: str = "best"):
        """
        Args:
            strategy: 'best' (keep best score), 'first' (keep first seen), 'fastest' (keep lowest latency)
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
        removed_count = 0
        for hash_key, group in groups.items():
            if len(group) == 1:
                unique_nodes.append(group[0])
            else:
                removed_count += len(group) - 1
                best = self._select_best(group)
                unique_nodes.append(best)

        log.info(f"Deduplication: {len(nodes)} -> {len(unique_nodes)} nodes (removed {removed_count} exact duplicates)")
        return unique_nodes

    def _select_best(self, nodes: List[Node]) -> Node:
        """Select the best node from a group of duplicates"""
        if self.strategy == "first":
            return nodes[0]
        
        if self.strategy == "fastest":
            valid = [n for n in nodes if n.latency is not None]
            if valid:
                return min(valid, key=lambda n: n.latency)

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
        limited_count = 0
        for server, server_nodes in server_groups.items():
            original_count = len(server_nodes)
            # Sort by score and take top N
            server_nodes.sort(key=lambda n: n.score, reverse=True)
            selected = server_nodes[:max_per_server]
            result.extend(selected)
            limited_count += original_count - len(selected)

        if limited_count > 0:
            log.info(
                f"Server limit: {len(nodes)} -> {len(result)} nodes "
                f"(removed {limited_count} similar servers, max {max_per_server} per server)"
            )
        return result
    
    def remove_by_similarity(
        self, 
        nodes: List[Node], 
        similarity_threshold: float = 0.95,
        min_nodes: int = 100
    ) -> List[Node]:
        """
        Remove highly similar nodes based on name patterns and server IP
        Keeps nodes with better scores when similarity is detected
        
        Args:
            similarity_threshold: Threshold for considering nodes similar (0.0-1.0)
            min_nodes: Minimum number of nodes to keep (skip removal if below this)
        """
        if len(nodes) < min_nodes:
            log.info(f"Skipping similarity removal: only {len(nodes)} nodes (min: {min_nodes})")
            return nodes
        
        removed = 0
        filtered_nodes = []
        
        for node in nodes:
            is_similar = False
            for existing in filtered_nodes:
                # Check server similarity
                server_match = node.server == existing.server
                
                # Check name similarity (simple substring check)
                name_lower = node.name.lower()
                existing_lower = existing.name.lower()
                name_similar = (
                    name_lower in existing_lower or 
                    existing_lower in name_lower or
                    self._calculate_similarity(name_lower, existing_lower) > similarity_threshold
                )
                
                # If both server and name are similar, consider it a duplicate
                if server_match and name_similar:
                    is_similar = True
                    # Keep the one with higher score
                    if node.score > existing.score:
                        filtered_nodes.remove(existing)
                        filtered_nodes.append(node)
                    break
            
            if not is_similar:
                filtered_nodes.append(node)
            else:
                removed += 1
        
        if removed > 0:
            log.info(f"Similarity removal: removed {removed} highly similar nodes")
        
        return filtered_nodes
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity ratio (simple implementation)"""
        if not s1 or not s2:
            return 0.0
        
        # Use character-level comparison
        common = sum(1 for c in s1 if c in s2)
        total = max(len(s1), len(s2))
        return common / total if total > 0 else 0.0

    def prioritize_by_quality(
        self, 
        nodes: List[Node], 
        top_percent: float = 80.0
    ) -> List[Node]:
        """
        Prioritize nodes by quality score and filter out low-quality ones
        
        Args:
            nodes: List of nodes to filter
            top_percent: Keep only top X% of nodes by quality
        """
        if not nodes:
            return []
        
        # Sort by score (descending)
        sorted_nodes = sorted(nodes, key=lambda n: n.score, reverse=True)
        
        # Calculate cutoff index
        cutoff = max(1, int(len(sorted_nodes) * top_percent / 100))
        
        filtered = sorted_nodes[:cutoff]
        removed = len(nodes) - len(filtered)
        
        if removed > 0:
            log.info(f"Quality filter: removed {removed} low-quality nodes, kept {len(filtered)}")
        
        return filtered
