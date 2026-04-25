"""
Download speed tester for proxy nodes
"""
import asyncio
import aiohttp
import time
from typing import List, Optional, Dict
from src.core.node import Node
from src.utils.logger import log


class SpeedTester:
    """Test download speed of proxy nodes"""

    def __init__(
        self,
        test_url: str = "http://speedtest.tele2.net/1MB.zip",
        timeout: int = 10,
        max_concurrent: int = 10,
        min_test_size: int = 1024 * 1024,  # 1MB minimum
    ):
        self.test_url = test_url
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.min_test_size = min_test_size
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def test_speed(self, node: Node) -> Optional[float]:
        """
        Test download speed for a single node
        Returns speed in MB/s or None if failed
        """
        async with self.semaphore:
            try:
                start_time = time.time()
                downloaded = 0
                
                # For now, simulate speed test
                # In production, you'd route through the actual proxy
                await asyncio.sleep(0.1)  # Placeholder
                
                elapsed = time.time() - start_time
                if elapsed > 0:
                    # Simulate speed (replace with actual measurement)
                    speed = 5.0  # MB/s placeholder
                    return round(speed, 2)
                
                return None
                
            except Exception as e:
                log.debug(f"Speed test failed for {node.name}: {e}")
                return None

    async def batch_test(
        self, 
        nodes: List[Node], 
        top_n: int = 50
    ) -> List[Node]:
        """
        Test download speed for top nodes
        
        Args:
            nodes: List of nodes (should be pre-sorted by latency)
            top_n: Number of top nodes to test for speed (set to 0 for all)
        """
        if not nodes:
            return []

        # If top_n is 0 or greater than len(nodes), test all nodes
        if top_n == 0 or top_n >= len(nodes):
            test_nodes = nodes
            log.info(f"Testing download speed for ALL {len(test_nodes)} nodes that passed latency...")
        else:
            test_nodes = nodes[:top_n]
            log.info(f"Testing download speed for top {len(test_nodes)} nodes...")
        
        # Create tasks
        tasks = [self._test_and_update(node) for node in test_nodes]
        
        # Run tests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out failed tests - ONLY KEEP nodes that passed speed test
        tested_nodes = [n for n in test_nodes if n.speed is not None]
        failed_count = len(test_nodes) - len(tested_nodes)
        
        if failed_count > 0:
            log.warning(f"Speed test failed for {failed_count} nodes (these will be excluded)")
        
        # Sort by speed (fastest first)
        tested_nodes.sort(key=lambda n: n.speed if n.speed else 0, reverse=True)
        
        log.info(f"Speed test complete: {len(tested_nodes)}/{len(test_nodes)} nodes passed")
        if tested_nodes:
            speeds = [n.speed for n in tested_nodes if n.speed]
            if speeds:
                avg_speed = sum(speeds) / len(speeds)
                max_speed = max(speeds)
                log.info(f"  Avg: {avg_speed:.1f} MB/s, Max: {max_speed:.1f} MB/s")
        
        return tested_nodes

    async def _test_and_update(self, node: Node):
        """Test a node and update its speed"""
        speed = await self.test_speed(node)
        if speed is not None:
            node.speed = speed
            # Update score based on speed
            if speed > 10:
                node.score = min(100, node.score + 20)
            elif speed > 5:
                node.score = min(100, node.score + 10)
            elif speed > 1:
                node.score = min(100, node.score + 5)
