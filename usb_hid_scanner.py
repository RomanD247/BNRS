"""
USB HID Scanner Module

This module provides USB HID communication functionality for barcode/Data Matrix scanners
operating in USB HID Vendor Mode. It handles device connection, data reading, and parsing
of HID reports from scanner devices.

Requirements: 1.1, 1.2, 1.3, 1.4, 4.1, 4.2, 4.3, 6.4
"""

import hid
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class USBDeviceInfo:
    """Information about a USB HID device"""
    vid: int
    pid: int
    manufacturer: str
    product: str
    serial_number: str
    path: bytes


@dataclass
class ScanResult:
    """Result of a scan operation"""
    success: bool
    data: Optional[str]
    error: Optional[str]
    timestamp: datetime


class USBHIDScanner:
    """
    USB HID Scanner class for communicating with barcode/Data Matrix scanners
    in USB HID Vendor Mode.
    
    This class handles:
    - Device connection and disconnection
    - Reading data from HID reports
    - Parsing and converting scanned data
    - Error handling for USB operations
    """
    
    def __init__(self, vid: int, pid: int, timeout: int = 30):
        """
        Initialize USB HID Scanner
        
        Args:
            vid: Vendor ID of the scanner device
            pid: Product ID of the scanner device
            timeout: Default timeout in seconds for read operations
        """
        self.vid = vid
        self.pid = pid
        self.timeout = timeout
        self.device = None
        self._connected = False
        self._cancel_requested = False

        logger.info(f"USBHIDScanner initialized with VID=0x{vid:04x}, PID=0x{pid:04x}, timeout={timeout}s")

    def cancel(self) -> None:
        """
        Request that an in-progress read_scan() return early.

        Checked once per poll iteration inside read_scan()'s loop, so the
        blocking read releases the device shortly after this is called
        instead of waiting out the full timeout.
        """
        self._cancel_requested = True

    def connect(self) -> bool:
        """
        Connect to the USB HID scanner device
        
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            PermissionError: If USB access is denied due to insufficient permissions
            
        Requirements: 1.1, 4.1, 4.5
        """
        try:
            logger.info(f"Attempting to connect to device VID=0x{self.vid:04x}, PID=0x{self.pid:04x}")
            
            # Try to open the device
            self.device = hid.device()
            self.device.open(self.vid, self.pid)
            
            # Set non-blocking mode
            self.device.set_nonblocking(1)
            
            self._connected = True
            logger.info(f"Successfully connected to device VID=0x{self.vid:04x}, PID=0x{self.pid:04x}")
            
            # Get device info for logging
            manufacturer = self.device.get_manufacturer_string()
            product = self.device.get_product_string()
            logger.info(f"Device info - Manufacturer: {manufacturer}, Product: {product}")
            
            return True
            
        except IOError as e:
            error_msg = str(e).lower()
            
            # Check if it's a permission error
            if "permission" in error_msg or "access" in error_msg or "denied" in error_msg:
                logger.error(f"Permission denied accessing device VID=0x{self.vid:04x}, PID=0x{self.pid:04x}: {e}")
                self._connected = False
                self.device = None
                raise PermissionError(f"USB access denied: {e}")
            
            logger.error(f"Failed to connect to device VID=0x{self.vid:04x}, PID=0x{self.pid:04x}: {e}")
            self._connected = False
            self.device = None
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to device: {e}")
            self._connected = False
            self.device = None
            return False
    
    def disconnect(self) -> None:
        """
        Disconnect from the USB HID scanner device
        
        Requirements: 1.1
        """
        if self.device is not None:
            try:
                logger.info(f"Disconnecting from device VID=0x{self.vid:04x}, PID=0x{self.pid:04x}")
                self.device.close()
                logger.info("Device disconnected successfully")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self.device = None
                self._connected = False
        else:
            logger.debug("Disconnect called but device was not connected")
    
    def read_scan(self, timeout: Optional[int] = None) -> Optional[str]:
        """
        Read scanned data from the device
        
        Args:
            timeout: Timeout in seconds (uses default if not specified)
            
        Returns:
            Scanned data as lowercase string, or None if timeout/error
            
        Requirements: 1.2, 4.2, 4.4
        """
        if not self._connected or self.device is None:
            logger.error("Cannot read: device not connected")
            return None
        
        if timeout is None:
            timeout = self.timeout

        logger.debug(f"Starting read operation with timeout={timeout}s")

        import time
        start_time = time.time()
        accumulated_data = bytearray()
        self._cancel_requested = False

        try:
            while True:
                if self._cancel_requested:
                    logger.info("Read cancelled")
                    return None

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    logger.warning(f"Read timeout after {elapsed:.2f}s")
                    return None

                # Try to read data
                data = self.device.read(64)  # Read up to 64 bytes
                
                if data:
                    logger.debug(f"Read {len(data)} bytes from device")
                    accumulated_data.extend(data)
                    
                    # Check if we have a complete scan (typically ends with newline or null)
                    if b'\n' in accumulated_data or b'\r' in accumulated_data or b'\x00' in accumulated_data:
                        logger.debug("Complete scan detected")
                        break
                else:
                    # No data available, sleep briefly to avoid busy waiting
                    time.sleep(0.01)
                
                # Check if device is still connected
                if not self._check_connection():
                    logger.error("Device disconnected during read operation")
                    self._connected = False
                    return None
            
            # Parse and return the data
            result = self._parse_hid_report(accumulated_data)
            return result
            
        except IOError as e:
            logger.error(f"IO error during read: {e}")
            # Device may have been disconnected
            self._connected = False
            return None
        except Exception as e:
            logger.error(f"Unexpected error during read: {e}")
            return None
    
    def _check_connection(self) -> bool:
        """
        Check if device is still connected
        
        Returns:
            True if connected, False otherwise
        """
        try:
            # Try to get manufacturer string as a connection check
            if self.device is not None:
                self.device.get_manufacturer_string()
                return True
        except Exception as e:
            logger.debug(f"Connection check failed: {e}")
            return False
        return False
    
    def _parse_hid_report(self, data: bytearray) -> Optional[str]:
        """
        Parse HID report and extract scanned data
        
        Args:
            data: Raw bytes from HID report
            
        Returns:
            Parsed string data, or None if parsing fails
            
        Requirements: 1.3, 4.3
        """
        try:
            logger.debug(f"Parsing HID report: {len(data)} bytes")
            
            # Remove null bytes, newlines, and carriage returns
            cleaned_data = data.replace(b'\x00', b'').replace(b'\n', b'').replace(b'\r', b'')
            
            # Try to decode as UTF-8
            try:
                decoded = cleaned_data.decode('utf-8')
                logger.debug(f"Successfully decoded data: '{decoded}'")
            except UnicodeDecodeError as e:
                logger.error(f"Failed to decode data as UTF-8: {e}")
                return None
            
            # Strip whitespace and control characters
            result = self._strip_control_characters(decoded)
            
            # Convert to lowercase
            result = result.lower()
            
            if result:
                logger.info(f"Successfully parsed scan: '{result}'")
                return result
            else:
                logger.warning("Parsed data is empty after cleaning")
                return None
                
        except Exception as e:
            logger.error(f"Error parsing HID report: {e}")
            return None
    
    def _strip_control_characters(self, text: str) -> str:
        """
        Strip whitespace and control characters from text
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Remove control characters (ASCII 0-31 and 127)
        cleaned = ''.join(char for char in text if ord(char) >= 32 and ord(char) != 127)
        
        if cleaned != text:
            logger.debug(f"Stripped control characters from text (length: {len(text)} -> {len(cleaned)})")
        
        return cleaned
    
    def is_connected(self) -> bool:
        """
        Check if scanner is currently connected
        
        Returns:
            True if connected, False otherwise
        """
        logger.debug(f"Connection status check: {self._connected}")
        return self._connected
    
    @staticmethod
    def list_devices() -> List[Dict]:
        """
        List all available HID devices on the system
        
        Returns:
            List of dictionaries containing device information
            
        Requirements: 1.1
        """
        try:
            devices = hid.enumerate()
            logger.info(f"Found {len(devices)} HID devices")
            return devices
        except Exception as e:
            logger.error(f"Error enumerating HID devices: {e}")
            return []
