"""
Scanner Configuration Module

This module manages scanner configuration including VID/PID settings, mode selection
(USB vendor vs keyboard), and configuration file persistence.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
"""

import json
import logging
import copy
import os
import shutil
import sys
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from paths import APP_DIR


# Configure logging
logger = logging.getLogger(__name__)


# Configuration file path, anchored to the app directory (M2) so launching
# from a different CWD doesn't read/write the wrong config. Kept as a plain
# string module attribute (not a Path computed elsewhere) so it can still be
# reassigned wholesale, e.g. by the test suite's isolated_scanner_config fixture.
CONFIG_FILE = str(APP_DIR / "scanner_config.json")

# The live scanner_config.json is gitignored (M22) - it's local/site-specific
# runtime state, not source. scanner_config.default.json is the committed
# template; load_config() below already falls back to DEFAULT_CONFIG in code
# when no file exists, so this only matters for one-file frozen builds, which
# unpack bundled data into a temp _MEIPASS dir and need it copied into place
# on first run (mirrors database.py's identical rental.db seeding).
if getattr(sys, "frozen", False) and not Path(CONFIG_FILE).exists():
    bundled_default = Path(getattr(sys, "_MEIPASS", "")) / "scanner_config.default.json"
    if bundled_default.exists():
        shutil.copy(bundled_default, CONFIG_FILE)


# Default configuration values
DEFAULT_CONFIG = {
    "scanner_mode": "usb_vendor",  # or "keyboard"
    "usb_vendor": {
        "vid": 4602,  # 0x11FA
        "pid": 33282,  # 0x8202
        "timeout": 30,
        "read_size": 64,
        "encoding": "utf-8"
    },
    "keyboard": {
        "timeout": 30,
        "auto_focus": True
    }
}


def validate_vid_pid(vid: int, pid: int) -> tuple[int, int]:
    """
    Validate VID/PID values and return valid values or defaults
    
    Args:
        vid: Vendor ID to validate
        pid: Product ID to validate
        
    Returns:
        Tuple of (valid_vid, valid_pid)
        
    Requirements: 2.4
    """
    default_vid = DEFAULT_CONFIG["usb_vendor"]["vid"]
    default_pid = DEFAULT_CONFIG["usb_vendor"]["pid"]
    
    # Valid USB VID/PID range is 1-65535 (0x0001-0xFFFF)
    valid_vid = vid
    valid_pid = pid
    
    if not isinstance(vid, int) or vid < 1 or vid > 65535:
        logger.warning(f"Invalid VID {vid} (type: {type(vid).__name__}), using default {default_vid} (0x{default_vid:04x})")
        valid_vid = default_vid
    
    if not isinstance(pid, int) or pid < 1 or pid > 65535:
        logger.warning(f"Invalid PID {pid} (type: {type(pid).__name__}), using default {default_pid} (0x{default_pid:04x})")
        valid_pid = default_pid
    
    if valid_vid == vid and valid_pid == pid:
        logger.debug(f"VID/PID validation passed: 0x{vid:04x}/0x{pid:04x}")
    
    return valid_vid, valid_pid


@dataclass
class ScannerConfig:
    """Scanner configuration data structure"""
    scanner_mode: str
    usb_vid: int
    usb_pid: int
    usb_timeout: int
    usb_read_size: int
    usb_encoding: str
    keyboard_timeout: int
    keyboard_auto_focus: bool
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'ScannerConfig':
        """Create ScannerConfig from dictionary"""
        return cls(
            scanner_mode=config_dict.get("scanner_mode", "usb_vendor"),
            usb_vid=config_dict.get("usb_vendor", {}).get("vid", 4602),
            usb_pid=config_dict.get("usb_vendor", {}).get("pid", 33282),
            usb_timeout=config_dict.get("usb_vendor", {}).get("timeout", 30),
            usb_read_size=config_dict.get("usb_vendor", {}).get("read_size", 64),
            usb_encoding=config_dict.get("usb_vendor", {}).get("encoding", "utf-8"),
            keyboard_timeout=config_dict.get("keyboard", {}).get("timeout", 30),
            keyboard_auto_focus=config_dict.get("keyboard", {}).get("auto_focus", True)
        )
    
    def to_dict(self) -> Dict:
        """Convert ScannerConfig to dictionary format"""
        return {
            "scanner_mode": self.scanner_mode,
            "usb_vendor": {
                "vid": self.usb_vid,
                "pid": self.usb_pid,
                "timeout": self.usb_timeout,
                "read_size": self.usb_read_size,
                "encoding": self.usb_encoding
            },
            "keyboard": {
                "timeout": self.keyboard_timeout,
                "auto_focus": self.keyboard_auto_focus
            }
        }


def load_config() -> Dict:
    """
    Load configuration from file or return defaults
    
    Returns:
        Configuration dictionary
        
    Requirements: 2.2, 2.3, 2.4
    """
    config_path = Path(CONFIG_FILE)
    
    # If configuration file doesn't exist, return defaults
    if not config_path.exists():
        logger.info(f"Configuration file {CONFIG_FILE} not found, using defaults")
        return copy.deepcopy(DEFAULT_CONFIG)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        logger.info(f"Configuration loaded from {CONFIG_FILE}")
        
        # Merge with defaults to ensure all keys exist (use deep copy to avoid mutating DEFAULT_CONFIG)
        merged_config = copy.deepcopy(DEFAULT_CONFIG)
        # Shallow-recursive merge so missing nested keys (e.g. an old config
        # saved before "read_size" existed) get backfilled from defaults
        # instead of the whole nested dict being replaced wholesale.
        for key, value in config.items():
            if key in merged_config and isinstance(merged_config[key], dict) and isinstance(value, dict):
                merged_config[key].update(value)
            else:
                merged_config[key] = value

        # Validate VID/PID values
        vid = merged_config["usb_vendor"].get("vid", DEFAULT_CONFIG["usb_vendor"]["vid"])
        pid = merged_config["usb_vendor"].get("pid", DEFAULT_CONFIG["usb_vendor"]["pid"])
        valid_vid, valid_pid = validate_vid_pid(vid, pid)
        
        merged_config["usb_vendor"]["vid"] = valid_vid
        merged_config["usb_vendor"]["pid"] = valid_pid
        
        return merged_config
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse configuration file: {e}")
        logger.info("Using default configuration")
        return copy.deepcopy(DEFAULT_CONFIG)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        logger.info("Using default configuration")
        return copy.deepcopy(DEFAULT_CONFIG)


def save_config(config: Dict) -> bool:
    """
    Save configuration to file
    
    Args:
        config: Configuration dictionary to save
        
    Returns:
        True if save successful, False otherwise
        
    Requirements: 2.2
    """
    config_path = Path(CONFIG_FILE)
    # Write to a temp file and rename over the real path so a crash mid-write
    # can never leave scanner_config.json truncated/corrupt.
    tmp_path = config_path.with_suffix('.json.tmp')

    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, config_path)

        logger.info(f"Configuration saved to {CONFIG_FILE}")
        return True

    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False


def get_scanner_mode() -> str:
    """
    Get current scanner mode
    
    Returns:
        Scanner mode string ("usb_vendor" or "keyboard")
        
    Requirements: 2.5
    """
    config = load_config()
    mode = config.get("scanner_mode", "usb_vendor")
    logger.debug(f"Current scanner mode: {mode}")
    return mode


def set_scanner_mode(mode: str) -> bool:
    """
    Set scanner mode
    
    Args:
        mode: Scanner mode ("usb_vendor" or "keyboard")
        
    Returns:
        True if mode set successfully, False otherwise
        
    Requirements: 2.5
    """
    logger.info(f"Attempting to set scanner mode to: {mode}")
    
    if mode not in ["usb_vendor", "keyboard"]:
        logger.error(f"Invalid scanner mode: {mode}. Must be 'usb_vendor' or 'keyboard'")
        return False
    
    config = load_config()
    old_mode = config.get("scanner_mode", "unknown")
    config["scanner_mode"] = mode
    
    success = save_config(config)
    if success:
        logger.info(f"Scanner mode changed from '{old_mode}' to '{mode}'")
    else:
        logger.error(f"Failed to save scanner mode change from '{old_mode}' to '{mode}'")
    
    return success


def get_usb_config() -> Dict:
    """
    Get USB scanner configuration
    
    Returns:
        USB configuration dictionary
        
    Requirements: 2.1
    """
    config = load_config()
    usb_config = config.get("usb_vendor", DEFAULT_CONFIG["usb_vendor"]).copy()
    logger.debug(f"Retrieved USB config: VID=0x{usb_config.get('vid', 0):04x}, PID=0x{usb_config.get('pid', 0):04x}")
    return usb_config


def update_usb_config(vid: Optional[int] = None, pid: Optional[int] = None, **kwargs) -> bool:
    """
    Update USB scanner configuration
    
    Args:
        vid: Vendor ID (optional)
        pid: Product ID (optional)
        **kwargs: Additional configuration parameters (timeout, read_size, encoding)
        
    Returns:
        True if update successful, False otherwise
        
    Requirements: 2.5
    """
    logger.info(f"Updating USB configuration - VID: {vid}, PID: {pid}, kwargs: {kwargs}")
    
    config = load_config()
    
    # Update VID/PID if provided
    if vid is not None or pid is not None:
        current_vid = config["usb_vendor"].get("vid", DEFAULT_CONFIG["usb_vendor"]["vid"])
        current_pid = config["usb_vendor"].get("pid", DEFAULT_CONFIG["usb_vendor"]["pid"])
        
        new_vid = vid if vid is not None else current_vid
        new_pid = pid if pid is not None else current_pid
        
        logger.info(f"Changing VID/PID from 0x{current_vid:04x}/0x{current_pid:04x} to 0x{new_vid:04x}/0x{new_pid:04x}")
        
        # Validate VID/PID
        valid_vid, valid_pid = validate_vid_pid(new_vid, new_pid)
        
        if valid_vid != new_vid or valid_pid != new_pid:
            logger.warning(f"VID/PID validation changed values to 0x{valid_vid:04x}/0x{valid_pid:04x}")
        
        config["usb_vendor"]["vid"] = valid_vid
        config["usb_vendor"]["pid"] = valid_pid
    
    # Update other parameters if provided
    valid_keys = ["timeout", "read_size", "encoding"]
    for key, value in kwargs.items():
        if key in valid_keys:
            old_value = config["usb_vendor"].get(key, "not set")
            config["usb_vendor"][key] = value
            logger.info(f"Updated USB config '{key}' from '{old_value}' to '{value}'")
        else:
            logger.warning(f"Ignoring invalid USB config key: {key}")
    
    success = save_config(config)
    if success:
        logger.info("USB configuration updated and saved successfully")
    else:
        logger.error("Failed to save USB configuration updates")
    
    return success
