"""
Logging utility for Scenario Question Generator.
Gracefully uses Loguru if available, otherwise falls back to Python's built-in logging.
"""
import sys
import logging
from pathlib import Path

# Ensure logs directory exists
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

try:
    from loguru import logger as _loguru_logger

    # Configure Loguru logger
    _loguru_logger.remove()  # Remove default handler

    # Console handler with rich formatting routed to stderr
    _loguru_logger.add(
        sys.stderr,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
    )

    # File handler with rotation
    _loguru_logger.add(
        LOGS_DIR / "app_{time:YYYY-MM-DD}.log",
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    logger = _loguru_logger

    def get_logger(name: str):
        """Return a contextualized logger instance."""
        return logger.bind(name=name)

except ImportError:
    # Standard library logging fallback routed to stderr
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler(LOGS_DIR / "app.log", encoding="utf-8"),
        ],
    )
    logger = logging.getLogger("scenario_generator")

    def get_logger(name: str):
        """Return standard logger instance."""
        return logging.getLogger(name)

__all__ = ["logger", "get_logger"]
