"""
logger_config.py
Configure logging for the TuniLoon application.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_LEVEL = logging.INFO

def setup_logging(level=DEFAULT_LEVEL, log_file='logs/tuniloon.log', max_bytes=10*1024*1024, backup_count=5):
    """
    Configure root logger with console and rotating file handlers.
    
    Args:
        level: Logging level (default: INFO)
        log_file: Path to log file (default: logs/tuniloon.log)
        max_bytes: Max size per log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove any existing handlers from the root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set root logger level
    root_logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Rotating file handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Log startup message
    root_logger.info(f"Logging initialized (level={logging.getLevelName(level)})")

def get_logger(name):
    """Convenience function to get a logger for a module."""
    return logging.getLogger(name)
