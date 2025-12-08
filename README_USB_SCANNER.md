# USB HID Scanner Integration - Documentation Index

## Overview

The WenglorMEL Rental System now supports USB HID Vendor Mode scanner integration for improved stability and reliability. This document serves as the main entry point for all scanner-related documentation.

## What's New

The system has been upgraded from keyboard emulation mode to USB HID Vendor Mode, providing:

- **More Stable Communication**: Direct USB HID protocol communication
- **Better Error Detection**: Clear error messages and status feedback
- **Flexible Configuration**: Easy VID/PID configuration for different scanner models
- **Mode Switching**: Ability to fall back to keyboard mode if needed
- **GUI Configuration**: User-friendly interface for scanner setup
- **Comprehensive Logging**: Detailed logs for troubleshooting

## Documentation Structure

### For Users

**[USB Scanner User Guide](USB_SCANNER_USER_GUIDE.md)** - Start here for daily operations
- Scanning workflow
- Scanner modes (USB HID vs Keyboard)
- Configuration utility usage
- Error messages and what they mean
- Best practices
- FAQ

### For Administrators

**[USB Scanner Setup Guide](USB_SCANNER_SETUP_GUIDE.md)** - Initial setup and configuration
- Installation instructions
- VID/PID configuration
- Platform-specific requirements (Windows, Linux, macOS)
- Verification steps

**[USB Scanner Troubleshooting Guide](USB_SCANNER_TROUBLESHOOTING.md)** - Problem resolution
- Connection issues
- Permission issues (especially Linux)
- Communication errors
- Configuration problems
- Fallback procedures
- Diagnostic tools

## Quick Start

### For End Users

1. Connect your scanner to a USB port
2. Launch the WenglorMEL Rental System
3. Start scanning - it works automatically!
4. If you encounter issues, see the [User Guide](USB_SCANNER_USER_GUIDE.md)

### For Administrators

1. Follow the [Setup Guide](USB_SCANNER_SETUP_GUIDE.md) to install and configure
2. Verify the scanner is detected: Admin Panel → Scanner Settings
3. Test the connection with a sample barcode
4. If issues occur, consult the [Troubleshooting Guide](USB_SCANNER_TROUBLESHOOTING.md)

## Key Features

### USB HID Vendor Mode (Default)

- Direct USB communication with scanner
- Stable and reliable operation
- Clear status feedback
- Recommended for production use

**Requirements**:
- Scanner must support USB HID Vendor Mode
- Correct VID/PID configuration (default: VID=4602, PID=33282)

### Keyboard Mode (Fallback)

- Scanner emulates keyboard input
- Works with any keyboard-mode scanner
- Available as backup option
- Useful for troubleshooting

### GUI Configuration Interface

Access via Admin Panel → Scanner Settings:
- View current configuration
- List connected USB devices
- Select and save scanner VID/PID
- Test connection
- Switch between modes
- View connection status

### Command-Line Configuration Utility

`configure_scanner.py` provides:
- Status checking
- Device enumeration
- VID/PID configuration
- Mode switching
- Connection testing
- Configuration backup/restore

## System Requirements

### Software

- Python 3.8 or higher
- hidapi library (included in requirements.txt)
- WenglorMEL Rental System

### Hardware

- USB HID-compatible scanner
- USB port on host computer
- Scanner configured for USB HID Vendor Mode

### Platform Support

- **Windows**: Full support, no additional setup
- **Linux**: Full support, may require udev rules for permissions
- **macOS**: Full support, no additional setup

## Default Configuration

| Setting | Value |
|---------|-------|
| Scanner Mode | usb_vendor |
| Vendor ID (VID) | 4602 (0x11FA) |
| Product ID (PID) | 33282 (0x8202) |
| Timeout | 30 seconds |
| Read Size | 64 bytes |
| Encoding | UTF-8 |

## Configuration File

Location: `scanner_config.json` (application root directory)

The configuration file is created automatically with default values on first run. You can modify it using:
- GUI: Admin Panel → Scanner Settings
- Command-line: `configure_scanner.py`
- Manual editing (not recommended)

## Log Files

Location: `logs/scanner.log`

The log file contains detailed information about:
- Scanner connection attempts
- USB operations
- Read operations
- Errors and warnings
- Configuration changes

Useful for troubleshooting and diagnostics.

## Common Tasks

### Check Scanner Status

**GUI Method**:
1. Open Admin Panel
2. Click "Scanner Settings"
3. View connection status

**Command-Line Method**:
```bash
python configure_scanner.py --status
```

### Configure a New Scanner

**GUI Method**:
1. Connect the scanner
2. Open Admin Panel → Scanner Settings
3. Click "Refresh Devices"
4. Select your scanner from the list
5. Click "Save Configuration"
6. Click "Test Connection" to verify

**Command-Line Method**:
```bash
# List connected devices
python configure_scanner.py --list-devices

# Set VID and PID
python configure_scanner.py --set-vid <VID> --set-pid <PID>

# Test connection
python configure_scanner.py --test-connection
```

### Switch to Keyboard Mode

**GUI Method**:
1. Open Admin Panel → Scanner Settings
2. Select "Keyboard" mode
3. Click "Save Configuration"

**Command-Line Method**:
```bash
python configure_scanner.py --set-mode keyboard
```

### Troubleshoot Connection Issues

1. Verify scanner is connected: Check USB cable and port
2. Check configuration: `python configure_scanner.py --status`
3. List devices: `python configure_scanner.py --list-devices`
4. Test connection: Admin Panel → Scanner Settings → Test Connection
5. Check logs: `logs/scanner.log`
6. See [Troubleshooting Guide](USB_SCANNER_TROUBLESHOOTING.md) for detailed steps

## Getting Help

### Documentation Resources

- **[User Guide](USB_SCANNER_USER_GUIDE.md)**: Daily operations and workflows
- **[Setup Guide](USB_SCANNER_SETUP_GUIDE.md)**: Installation and configuration
- **[Troubleshooting Guide](USB_SCANNER_TROUBLESHOOTING.md)**: Problem resolution

### Diagnostic Information

When reporting issues, collect:
- Output of `python configure_scanner.py --status`
- Output of `python configure_scanner.py --list-devices`
- Contents of `logs/scanner.log`
- Contents of `scanner_config.json`
- Operating system and version
- Scanner manufacturer and model

### Emergency Fallback

If USB mode is not working:

```bash
# Switch to keyboard mode immediately
python configure_scanner.py --set-mode keyboard
```

Then consult the [Troubleshooting Guide](USB_SCANNER_TROUBLESHOOTING.md) to resolve the USB issue.

## Technical Details

### Architecture

```
Application Layer (main.py)
         ↓
Scanner Interface (NfcScan.py)
         ↓
    Mode Router
    ↙         ↘
USB HID      Keyboard
Scanner      Mode
    ↓
Configuration System
(scanner_config.json)
```

### USB Communication

- Uses `hidapi` library for cross-platform USB HID support
- Direct communication via HID reports
- Automatic device detection and connection
- Graceful error handling and recovery

### Data Flow

1. Application requests scan input
2. System checks scanner mode configuration
3. Routes to appropriate implementation (USB HID or keyboard)
4. Scanner reads barcode/Data Matrix code
5. Data is parsed and converted to lowercase
6. Result is returned to application
7. Application processes the code (find user/equipment)

## Backward Compatibility

The new USB HID integration maintains full backward compatibility:

- Same async interface (`get_nfc_input()`)
- Same dialog appearance and behavior
- Same timeout values
- Same data format (lowercase string)
- Keyboard mode still available as fallback

Existing rental workflows require no changes.

## Future Enhancements

Potential improvements for future versions:

- Support for multiple scanners simultaneously
- Automatic scanner detection and configuration
- Scanner firmware version detection
- Advanced barcode format validation
- Scanner health monitoring
- Cloud-based configuration management

## Version History

### Version 2.1 (Current)

- Added USB HID Vendor Mode support
- Implemented GUI configuration interface
- Added command-line configuration utility
- Created comprehensive documentation
- Maintained keyboard mode as fallback
- Added detailed logging and diagnostics

### Version 2.0 (Previous)

- Keyboard emulation mode only
- Basic scanner integration

## License and Support

This documentation is part of the WenglorMEL Rental System.

For support, contact your system administrator or IT department.

---

**Last Updated**: December 2024  
**Documentation Version**: 1.0  
**System Version**: 2.1
