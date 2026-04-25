"""
CXDDZY-Pro - Advanced Proxy Node Fetcher v2.0
Main entry point with latency testing, speed testing, and archiving
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.fetcher import Fetcher
from src.core.validator import Validator
from src.core.classifier import Classifier
from src.core.deduplicator import Deduplicator
from src.core.latency_tester import LatencyTester
from src.core.speed_tester import SpeedTester
from src.core.archiver import Archiver
from src.output.yaml_generator import YAMLGenerator
from src.output.base64_encoder import Base64Encoder
from src.utils.logger import log, setup_logger


async def main():
    """Main execution flow with full testing pipeline"""
    start_time = datetime.now()
    log.info("=" * 70)
    log.info("CXDDZY-Pro v2.0 - Advanced Proxy Node Fetcher")
    log.info("Pipeline: Fetch -> Dedup -> Latency(per source) -> Speed(all) -> Archive")
    log.info("=" * 70)

    # Initialize archiver
    archiver = Archiver(archive_dir="archive")
    
    # Clean old archives (keep last 7 days)
    archiver.cleanup_old_archives(keep_days=7)

    # Load sources
    sources_file = Path("config/sources.list")
    if not sources_file.exists():
        log.error(f"Sources file not found: {sources_file}")
        return

    with open(sources_file, "r", encoding="utf-8") as f:
        sources = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    log.info(f"Loaded {len(sources)} sources")

    # ==========================================
    # Step 1: Fetch nodes grouped by source
    # ==========================================
    log.info("\n[Step 1/7] Fetching nodes from sources (grouped)...")
    async with Fetcher(max_concurrent=20, timeout=30, max_retries=3) as fetcher:
        grouped_nodes = await fetcher.fetch_all_sources_grouped(sources, max_per_source=100)
    
    # Also fetch all nodes combined for deduplication
    all_nodes = []
    for nodes in grouped_nodes.values():
        all_nodes.extend(nodes)

    log.info(f"Total raw nodes fetched: {len(all_nodes)} from {len(grouped_nodes)} sources")

    if not all_nodes:
        log.error("No nodes fetched! Sources may be unavailable.")
        all_nodes = []
        grouped_nodes = {}

    # ==========================================
    # Step 2: Deduplicate nodes
    # ==========================================
    log.info("\n[Step 2/7] Deduplicating nodes...")
    deduplicator = Deduplicator(strategy="best")
    
    # Remove exact duplicates
    unique_nodes = deduplicator.deduplicate(all_nodes)
    
    # Remove similar servers (keep max 3 per server)
    unique_nodes = deduplicator.remove_similar_servers(unique_nodes, max_per_server=3)
    
    # Remove highly similar nodes
    unique_nodes = deduplicator.remove_by_similarity(unique_nodes, similarity_threshold=0.95)
    
    # Prioritize by quality (keep top 80%)
    if len(unique_nodes) > 100:
        unique_nodes = deduplicator.prioritize_by_quality(unique_nodes, top_percent=80.0)

    log.info(f"After deduplication: {len(unique_nodes)} nodes")

    if not unique_nodes:
        log.warning("No unique nodes remaining after deduplication!")

    # ==========================================
    # Step 3: Classify regions
    # ==========================================
    log.info("\n[Step 3/7] Classifying node regions...")
    classifier = Classifier()
    classified = classifier.classify_batch(unique_nodes)

    for region, nodes in classified.items():
        log.info(f"  {region}: {len(nodes)} nodes")

    # ==========================================
    # Step 4: Basic validation
    # ==========================================
    log.info("\n[Step 4/7] Validating nodes...")
    validator = Validator()
    valid_nodes = await validator.batch_validate(unique_nodes)

    log.info(f"After validation: {len(valid_nodes)} nodes")

    # ==========================================
    # Step 5: Latency testing (per source, 100 nodes each)
    # ==========================================
    log.info("\n[Step 5/7] Testing latency (first 100 nodes per source)...")
    
    # Re-group validated nodes by source for latency testing
    validated_grouped = {}
    for node in valid_nodes:
        source = node.source_url or "unknown"
        if source not in validated_grouped:
            validated_grouped[source] = []
        validated_grouped[source].append(node)
    
    if validated_grouped:
        latency_tester = LatencyTester(
            test_url="http://www.gstatic.com/generate_204",
            timeout=5,
            max_concurrent=30,
        )
        tested_nodes = await latency_tester.test_by_source(
            validated_grouped, 
            max_per_source=100
        )
        
        if tested_nodes:
            log.info(f"After latency testing: {len(tested_nodes)} nodes responded")
        else:
            log.warning("Latency testing failed - no nodes responded")
            tested_nodes = []
    else:
        tested_nodes = []
        log.warning("Skipping latency test - no valid nodes")

    # ==========================================
    # Step 6: Speed testing (ALL nodes that passed latency)
    # ==========================================
    log.info("\n[Step 6/7] Testing download speed (ALL latency-passed nodes)...")
    if tested_nodes:
        speed_tester = SpeedTester(
            test_url="http://speedtest.tele2.net/1MB.zip",
            timeout=10,
            max_concurrent=5,
        )
        # Set top_n=0 to test ALL nodes that passed latency
        final_nodes = await speed_tester.batch_test(tested_nodes, top_n=0)
        
        if final_nodes:
            log.info(f"After speed testing: {len(final_nodes)} nodes passed (only these will be kept)")
        else:
            log.warning("Speed testing failed - NO nodes passed!")
            final_nodes = []
    else:
        final_nodes = []
        log.warning("Skipping speed test - no latency-tested nodes")

    # Sort final nodes by score (only nodes that passed BOTH tests)
    if final_nodes:
        final_nodes.sort(key=lambda n: n.score, reverse=True)

    # ==========================================
    # Step 7: Generate output files
    # ==========================================
    log.info("\n[Step 7/7] Generating output files...")

    # Generate Base64 format (V2Ray subscription)
    encoder = Base64Encoder()
    encoder.encode_nodes(final_nodes, "output/list.txt")
    encoder.encode_raw_urls(final_nodes, "output/list_raw.txt")

    # Generate Clash YAML configuration
    yaml_gen = YAMLGenerator("config/clash.yml")
    yaml_gen.generate_clash_yaml(final_nodes, "output/list.yml")
    yaml_gen.generate_meta_yaml(final_nodes, "output/list.meta.yml")

    log.info(f"Output files generated: {len(final_nodes)} nodes")

    # ==========================================
    # Archive results
    # ==========================================
    log.info("\n[Archive] Saving test results...")
    
    if final_nodes:
        # Save full test results
        archiver.save_test_results(
            nodes=final_nodes,
            test_type="full",
            metadata={
                "sources_count": len(sources),
                "execution_time": (datetime.now() - start_time).total_seconds(),
            }
        )
        
        # Save statistics
        stats = {
            "sources_processed": len(sources),
            "raw_nodes": len(all_nodes),
            "unique_nodes": len(unique_nodes),
            "latency_passed": len(tested_nodes),
            "speed_passed": len(final_nodes),
            "regions": dict(classified),
        }
        archiver.save_statistics(nodes=final_nodes, stats=stats)
        
        # Save CSV report
        archiver.save_csv_report(final_nodes)

    # ==========================================
    # Final Summary
    # ==========================================
    elapsed = (datetime.now() - start_time).total_seconds()
    log.info("\n" + "=" * 70)
    log.info("EXECUTION SUMMARY")
    log.info("=" * 70)
    log.info(f"  Total time:              {elapsed:.2f}s")
    log.info(f"  Sources processed:       {len(sources)}")
    log.info(f"  Raw nodes fetched:       {len(all_nodes)}")
    log.info(f"  After deduplication:     {len(unique_nodes)}")
    log.info(f"  After validation:        {len(valid_nodes)}")
    log.info(f"  Latency passed:          {len(tested_nodes)}")
    log.info(f"  Speed passed (FINAL):    {len(final_nodes)}")
    log.info(f"  Regions detected:        {len(classified)}")
    
    if final_nodes:
        latencies = [n.latency for n in final_nodes if n.latency]
        speeds = [n.speed for n in final_nodes if n.speed]
        if latencies:
            log.info(f"  Avg latency:             {sum(latencies)/len(latencies):.0f}ms")
        if speeds:
            log.info(f"  Avg speed:               {sum(speeds)/len(speeds):.1f} MB/s")
    
    log.info("=" * 70)
    
    if final_nodes:
        log.info("SUCCESS! All output files saved to output/")
        log.info("Test results archived to archive/")
        log.info(f"Only nodes that PASSED both latency and speed tests are included!")
    else:
        log.warning("WARNING: No nodes passed both tests. Output files will be empty.")
        log.warning("This could mean source URLs are temporarily unavailable.")
        log.warning("Check the logs for more details.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.warning("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        log.exception(f"\nFatal error: {e}")
        sys.exit(1)
