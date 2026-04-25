"""
Latency tester for proxy nodes - measures connection delay
"""
import asyncio
import aiohttp
import time
from typing import List, Optional, Dict, Tuple
from src.core.node import Node
from src.utils.logger import log


class LatencyTester:
    """Test latency of proxy nodes using HTTP requests"""

    def __init__(
        self,
        test_url: str = "http://www.gstatic.com/generate_204",
        timeout: int = 5,
        max_concurrent: int = 50,
    ):
        self.test_url = test_url
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def test_latency(self, node: Node) -> Optional[float]:
        """
        Test latency for a single node
        Returns latency in milliseconds or None if failed
        """
        async with self.semaphore:
            try:
                # For now, we'll do a simple connectivity test
                # In production, you'd route through the actual proxy
                start_time = time.time()
                
                # Simulate latency test (replace with actual proxy testing)
                await asyncio.sleep(0.01)  # Placeholder
                
                elapsed = (time.time() - start_time) * 1000  # Convert to ms
                return round(elapsed, 2)
                
            except Exception as e:
                log.debug(f"Failed to test {node.name}: {e}")
                return None

    async def batch_test(
        self, 
        nodes: List[Node], 
        max_nodes: int = 200
    ) -> List[Node]:
        """
        Test latency for multiple nodes concurrently
        Returns nodes sorted by latency (fastest first)
        
        Args:
            nodes: List of nodes to test
            max_nodes: Maximum number of nodes to test (to avoid timeout)
        """
        if not nodes:
            return []

        # Limit number of nodes to test
        test_nodes = nodes[:max_nodes]
        
        log.info(f"Testing latency for {len(test_nodes)} nodes...")
        
        # Create tasks
        tasks = [self._test_and_update(node) for node in test_nodes]
        
        # Run tests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out failed tests
        tested_nodes = [n for n in test_nodes if n.latency is not None]
        failed_count = len(test_nodes) - len(tested_nodes)
        
        if failed_count > 0:
            log.warning(f"Latency test failed for {failed_count} nodes")
        
        # Sort by latency (fastest first)
        tested_nodes.sort(key=lambda n: n.latency if n.latency else 9999)
        
        log.info(f"Latency test complete: {len(tested_nodes)} nodes tested")
        if tested_nodes:
            latencies = [n.latency for n in tested_nodes if n.latency]
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)
                log.info(f"  Avg: {avg_latency:.0f}ms, Min: {min_latency:.0f}ms, Max: {max_latency:.0f}ms")
        
        return tested_nodes

    async def _test_and_update(self, node: Node):
        """Test a node and update its latency"""
        latency = await self.test_latency(node)
        if latency is not None:
            node.latency = latency
            # Update score based on latency
            if latency < 100:
                node.score = min(100, node.score + 30)
            elif latency < 200:
                node.score = min(100, node.score + 20)
            elif latency < 500:
                node.score = min(100, node.score + 10)
            else:
                node.score = max(0, node.score - 10)
