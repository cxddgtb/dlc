"""
CXDDZY-Pro - Advanced Proxy Node Fetcher v2.0
Main entry point
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
from src.output.yaml_generator import YAMLGenerator
from src.output.base64_encoder import Base64Encoder
from src.utils.logger import log, setup_logger


async def main():
    """Main execution flow"""
    start_time = datetime.now()
    log.info("=" * 60)
    log.info("CXDDZY-Pro v2.0 - Advanced Proxy Node Fetcher")
    log.info("=" * 60)

    # Load sources
    sources_file = Path("config/sources.list")
    if not sources_file.exists():
        log.error(f"Sources file not found: {sources_file}")
        return

    with open(sources_file, "r", encoding="utf-8") as f:
        sources = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    log.info(f"Loaded {len(sources)} sources")

    # Step 1: Fetch nodes
    log.info("\n[Step 1/5] Fetching nodes...")
    async with Fetcher(max_concurrent=20, timeout=30, max_retries=3) as fetcher:
        all_nodes = await fetcher.fetch_all_sources(sources)

    log.info(f"Total raw nodes: {len(all_nodes)}")

    if not all_nodes:
        log.error("No nodes fetched!")
        return

    # Step 2: Deduplicate
    log.info("\n[Step 2/5] Deduplicating nodes...")
    deduplicator = Deduplicator(strategy="best")
    unique_nodes = deduplicator.deduplicate(all_nodes)
    unique_nodes = deduplicator.remove_similar_servers(unique_nodes, max_per_server=3)

    log.info(f"Unique nodes: {len(unique_nodes)}")

    # Step 3: Classify regions
    log.info("\n[Step 3/5] Classifying regions...")
    classifier = Classifier()
    classified = classifier.classify_batch(unique_nodes)

    for region, nodes in classified.items():
        log.info(f"  {region}: {len(nodes)} nodes")

    # Step 4: Validate (optional - requires proxy support)
    log.info("\n[Step 4/5] Validating nodes...")
    validator = Validator()
    valid_nodes = await validator.batch_validate(unique_nodes)

    # Sort by score
    valid_nodes.sort(key=lambda n: n.score, reverse=True)

    # Step 5: Generate output files
    log.info("\n[Step 5/5] Generating output files...")

    # Generate Base64 format
    encoder = Base64Encoder()
    encoder.encode_nodes(valid_nodes, "output/list.txt")
    encoder.encode_raw_urls(valid_nodes, "output/list_raw.txt")

    # Generate Clash YAML
    yaml_gen = YAMLGenerator("config/clash.yml")
    yaml_gen.generate_clash_yaml(valid_nodes, "output/list.yml")
    yaml_gen.generate_meta_yaml(valid_nodes, "output/list.meta.yml")

    # Generate statistics
    elapsed = (datetime.now() - start_time).total_seconds()
    log.info("\n" + "=" * 60)
    log.info("Execution Summary:")
    log.info(f"  Total time: {elapsed:.2f}s")
    log.info(f"  Sources processed: {len(sources)}")
    log.info(f"  Raw nodes fetched: {len(all_nodes)}")
    log.info(f"  Unique nodes: {len(unique_nodes)}")
    log.info(f"  Valid nodes: {len(valid_nodes)}")
    log.info(f"  Regions: {len(classified)}")
    log.info("=" * 60)
    log.info("Done! Output files saved to output/")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.warning("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        log.exception(f"Fatal error: {e}")
        sys.exit(1)
