"""
Scanner Logging Configuration Module

This module provides centralized logging configuration for the USB HID scanner system.
It sets up appropriate log levels, formats, and handlers for all scanner-related operations.

Requirements: 6.3
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

from paths import APP_DIR


# Log file path, anchored to the app directory (M2) so launching from a
# different CWD still writes logs next to the app instead of the CWD.
LOG_DIR = APP_DIR / "logs"
LOG_FILE = LOG_DIR / "scanner.log"

# Handlers previously attached to the root logger by setup_logging(), tracked
# so a repeat call can remove exactly these instead of every handler on the
# root logger - other modules here use logging.getLogger(__name__), which
# propagates up to root by default, so a dedicated non-propagating logger
# would silently drop their existing output; staying on the root logger but
# only ever touching handlers we ourselves added keeps that output intact
# while still fixing the "wipes out anything else attached to root" bug.
_managed_handlers: list[logging.Handler] = []


def setup_logging(log_level: str = "INFO", console_output: bool = True, file_output: bool = True,
                   max_bytes: int = 1_000_000, backup_count: int = 3) -> None:
    """
    Configure logging for the scanner system

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: Whether to output logs to console
        file_output: Whether to output logs to file
        max_bytes: Rotate the log file once it reaches this size (bytes)
        backup_count: Number of rotated backups to keep (scanner.log.1, .2, ...)

    Requirements: 6.3
    """
    # Create logs directory if it doesn't exist
    if file_output:
        LOG_DIR.mkdir(exist_ok=True)

    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Define log format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Create formatter
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Get root logger for scanner modules
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove only the handlers we previously added (idempotent re-config)
    # rather than clearing the root logger, which would also drop handlers
    # any other library/caller may have attached.
    for handler in _managed_handlers:
        root_logger.removeHandler(handler)
        handler.close()
    _managed_handlers.clear()

    # Add console handler if requested
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        _managed_handlers.append(console_handler)

    # Add file handler if requested - rotates so logs/ doesn't grow unbounded
    # for the life of the installation.
    if file_output:
        try:
            file_handler = RotatingFileHandler(
                LOG_FILE, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            _managed_handlers.append(file_handler)
        except Exception as e:
            # If file logging fails, at least log to console
            if console_output:
                logging.error(f"Failed to set up file logging: {e}")

    # Log initialization
    logging.info("=" * 80)
    logging.info(f"Scanner logging initialized - Level: {log_level}, Console: {console_output}, File: {file_output}")
    logging.info("=" * 80)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module
    
    Args:
        name: Name of the module (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
