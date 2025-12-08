"""
Scanner Logging Configuration Module

This module provides centralized logging configuration for the USB HID scanner system.
It sets up appropriate log levels, formats, and handlers for all scanner-related operations.

Requirements: 6.3
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


# Log file path
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "scanner.log"


def setup_logging(log_level: str = "INFO", console_output: bool = True, file_output: bool = True) -> None:
    """
    Configure logging for the scanner system
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: Whether to output logs to console
        file_output: Whether to output logs to file
        
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
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add console handler if requested
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Add file handler if requested
    if file_output:
        try:
            file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
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
