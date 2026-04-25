"""
Archive manager for storing test results and node history
"""
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.core.node import Node
from src.utils.logger import log


class Archiver:
    """Archive test results and node statistics"""

    def __init__(self, archive_dir: str = "archive"):
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def save_test_results(
        self,
        nodes: List[Node],
        test_type: str = "full",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Save test results to JSON file
        
        Args:
            nodes: List of tested nodes
            test_type: Type of test (latency, speed, full)
            metadata: Additional metadata to save
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_{test_type}_{timestamp}.json"
        filepath = self.archive_dir / filename

        # Prepare data
        test_data = {
            "timestamp": timestamp,
            "test_type": test_type,
            "total_nodes": len(nodes),
            "metadata": metadata or {},
            "nodes": [],
        }

        # Add node data
        for node in nodes:
            node_data = {
                "name": node.name,
                "protocol": node.protocol.value,
                "server": node.server,
                "port": node.port,
                "latency": node.latency,
                "speed": node.speed,
                "score": node.score,
                "country": node.country,
                "source_url": node.source_url,
            }
            test_data["nodes"].append(node_data)

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)

        log.info(f"Test results saved: {filepath} ({len(nodes)} nodes)")
        return filepath

    def save_statistics(
        self,
        nodes: List[Node],
        stats: Dict[str, Any],
    ) -> Path:
        """
        Save comprehensive statistics
        
        Args:
            nodes: List of all nodes
            stats: Statistics dictionary
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stats_{timestamp}.json"
        filepath = self.archive_dir / filename

        # Calculate additional statistics
        latencies = [n.latency for n in nodes if n.latency is not None]
        speeds = [n.speed for n in nodes if n.speed is not None]
        scores = [n.score for n in nodes]

        full_stats = {
            "timestamp": timestamp,
            "summary": {
                "total_nodes": len(nodes),
                "nodes_with_latency": len(latencies),
                "nodes_with_speed": len(speeds),
            },
            "latency": {
                "min": min(latencies) if latencies else None,
                "max": max(latencies) if latencies else None,
                "avg": sum(latencies) / len(latencies) if latencies else None,
            },
            "speed": {
                "min": min(speeds) if speeds else None,
                "max": max(speeds) if speeds else None,
                "avg": sum(speeds) / len(speeds) if speeds else None,
            },
            "score": {
                "min": min(scores) if scores else None,
                "max": max(scores) if scores else None,
                "avg": sum(scores) / len(scores) if scores else None,
            },
            "details": stats,
        }

        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(full_stats, f, indent=2, ensure_ascii=False)

        log.info(f"Statistics saved: {filepath}")
        return filepath

    def save_csv_report(
        self,
        nodes: List[Node],
        filename: Optional[str] = None,
    ) -> Path:
        """
        Save node data as CSV for easy analysis
        
        Args:
            nodes: List of nodes to save
            filename: Optional custom filename
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nodes_{timestamp}.csv"

        filepath = self.archive_dir / filename

        # Write CSV
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "Name", "Protocol", "Server", "Port", 
                "Latency (ms)", "Speed (MB/s)", "Score",
                "Country", "Source"
            ])
            
            # Data rows
            for node in nodes:
                writer.writerow([
                    node.name,
                    node.protocol.value,
                    node.server,
                    node.port,
                    node.latency or "",
                    node.speed or "",
                    round(node.score, 2),
                    node.country or "",
                    node.source_url or "",
                ])

        log.info(f"CSV report saved: {filepath} ({len(nodes)} nodes)")
        return filepath

    def cleanup_old_archives(self, keep_days: int = 7):
        """
        Remove archives older than specified days
        
        Args:
            keep_days: Number of days to keep archives
        """
        now = datetime.now()
        removed = 0

        for filepath in self.archive_dir.glob("*"):
            if filepath.is_file():
                # Get file age
                file_time = datetime.fromtimestamp(filepath.stat().st_mtime)
                age_days = (now - file_time).days

                if age_days > keep_days:
                    filepath.unlink()
                    removed += 1

        if removed > 0:
            log.info(f"Cleaned up {removed} old archive files (kept {keep_days} days)")

    def get_archive_list(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get list of recent archives
        
        Args:
            limit: Maximum number of entries to return
        """
        archives = []
        
        for filepath in sorted(self.archive_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                archives.append({
                    "filename": filepath.name,
                    "path": str(filepath),
                    "timestamp": data.get("timestamp", ""),
                    "type": data.get("test_type", "unknown"),
                    "nodes": data.get("total_nodes", 0),
                })
            except Exception as e:
                log.warning(f"Failed to read archive {filepath}: {e}")

        return archives
