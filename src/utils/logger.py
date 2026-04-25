"""
Logging configuration using loguru
"""
import sys
from pathlib import Path
from loguru import logger


def setup_logger(log_level: str = "INFO", log_dir: str = "logs"):
    """Setup application logger"""

    # Remove default handler
    logger.remove()

    # Console handler with colored output
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level=log_level,
        colorize=True,
    )

    # File handler with rotation
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_path / "fetch_{time:YYYY-MM-DD}.log",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        level=log_level,
        encoding="utf-8",
    )

    return logger


# Create default logger instance
log = setup_logger()
