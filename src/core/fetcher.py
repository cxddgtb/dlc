"""
Async fetcher engine for grabbing nodes from multiple sources
"""
import asyncio
import aiohttp
from typing import List, Optional, Set
from src.core.node import Node
from src.utils.logger import log
from src.utils.retry import retry_async
from src.protocols import (
    parse_vmess,
    parse_ss,
    parse_ssr,
    parse_trojan,
    parse_vless,
    parse_hysteria2,
)


class Fetcher:
    """Async node fetcher with connection pooling and concurrency control"""

    def __init__(
        self,
        max_concurrent: int = 20,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.max_retries = max_retries
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        await self.init_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()

    async def init_session(self):
        """Initialize aiohttp session with connection pool"""
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent,
            ttl_dns_cache=300,
            enable_cleanup_closed=True,
        )
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )

    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    async def fetch_source(self, url: str) -> List[Node]:
        """Fetch nodes from a single source"""
        async with self.semaphore:
            try:
                content = await self._fetch_with_retry(url)
                if not content:
                    return []

                nodes = self._parse_content(content, url)
                log.info(f"Fetched {len(nodes)} nodes from {url}")
                return nodes

            except Exception as e:
                log.error(f"Failed to fetch {url}: {e}")
                return []

    async def _fetch_with_retry(self, url: str) -> Optional[str]:
        """Fetch URL content with retry logic"""

        async def _do_fetch():
            async with self.session.get(url, ssl=False) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise Exception(f"HTTP {response.status}")

        try:
            return await retry_async(
                _do_fetch,
                max_retries=self.max_retries,
                exceptions=(aiohttp.ClientError, asyncio.TimeoutError, Exception),
            )
        except Exception as e:
            log.error(f"Failed to fetch {url} after retries: {e}")
            return None

    def _parse_content(self, content: str, source_url: str) -> List[Node]:
        """Parse content to extract nodes"""
        nodes = []

        # Try to detect format
        lines = content.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            node = self._parse_line(line, source_url)
            if node:
                nodes.append(node)

        return nodes

    def _parse_line(self, line: str, source_url: str) -> Optional[Node]:
        """Parse a single line to extract node"""
        if line.startswith("vmess://"):
            return parse_vmess(line, source_url)
        elif line.startswith("ss://"):
            return parse_ss(line, source_url)
        elif line.startswith("ssr://"):
            return parse_ssr(line, source_url)
        elif line.startswith("trojan://"):
            return parse_trojan(line, source_url)
        elif line.startswith("vless://"):
            return parse_vless(line, source_url)
        elif line.startswith("hysteria2://") or line.startswith("hy2://"):
            return parse_hysteria2(line, source_url)

        return None

    async def fetch_all_sources(self, sources: List[str]) -> List[Node]:
        """Fetch nodes from all sources concurrently"""
        log.info(f"Starting to fetch {len(sources)} sources...")

        tasks = [self.fetch_source(url) for url in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_nodes = []
        for result in results:
            if isinstance(result, list):
                all_nodes.extend(result)

        log.info(f"Total fetched nodes: {len(all_nodes)}")
        return all_nodes
