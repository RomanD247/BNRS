# USB Scanner User Guide

## Overview

This guide explains how to use the USB HID scanner integration in the WenglorMEL Rental System for daily operations. The system supports both USB HID Vendor Mode and keyboard emulation mode for maximum flexibility.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Scanning Workflow](#scanning-workflow)
3. [Scanner Modes](#scanner-modes)
4. [Configuration Utility](#configuration-utility)
5. [Error Messages](#error-messages)
6. [Best Practices](#best-practices)

---

## Getting Started

### First-Time Setup

Before using the scanner for the first time:

1. **Verify Scanner Connection**
   - Connect the scanner to a USB port
   - Wait for the system to recognize the device
   - Check that any LED indicators on the scanner are active

2. **Check Configuration**
   - Launch the WenglorMEL Rental System
   - Open Admin Panel → Scanner Settings
   - Verify the connection status shows "Connected"
   - If disconnected, see the [Troubleshooting Guide](USB_SCANNER_TROUBLESHOOTING.md)

3. **Test Scanning**
   - Click "Test Connection" in Scanner Settings
   - Scan a test barcode
   - Verify the system captures the code correctly

### Daily Startup

When starting your workday:

1. Connect the scanner to your computer (if not already connected)
2. Launch the WenglorMEL Rental System
3. The scanner will connect automatically
4. Begin your rental operations

**Note**: The scanner connection is established automatically when needed. You don't need to manually connect it each time.

---

## Scanning Workflow

### Equipment Rental Process

#### Step 1: Initiate Rental

1. In the main application, click "Rent Equipment" or navigate to the rental workflow
2. The system will prompt you to scan a user code

#### Step 2: Scan User Code

1. A dialog appears: "Scan User Code"
2. Point the scanner at the user's barcode or Data Matrix code
3. Press the scanner's trigger button
4. The scanner reads the code and sends it to the system
5. The dialog closes automatically when the code is captured
6. The system displays the user's information

**What You'll See**:
- Dialog title: "Scan User Code" or similar
- Status message: "Waiting for scan..."
- Cancel button (if you need to abort)

**Timeout**: If no code is scanned within 30 seconds, the dialog closes automatically. You can try again.

#### Step 3: Scan Equipment Code

1. After user identification, the system prompts for equipment code
2. A dialog appears: "Scan Equipment Code"
3. Point the scanner at the equipment's barcode or Data Matrix code
4. Press the scanner's trigger button
5. The scanner reads the code and sends it to the system
6. The dialog closes automatically when the code is captured
7. The system displays the equipment information

#### Step 4: Confirm Rental

1. Review the rental details displayed
2. Confirm the rental transaction
3. The equipment is now marked as rented to the user

### Equipment Return Process

The return process is similar to rental:

1. Click "Return Equipment" or navigate to the return workflow
2. Scan the user code when prompted
3. Scan the equipment code when prompted
4. Confirm the return transaction
5. The equipment is now marked as available

### Scanning Tips

**For Best Results**:

1. **Distance**: Hold the scanner 4-8 inches from the barcode
2. **Angle**: Keep the scanner perpendicular to the barcode (avoid extreme angles)
3. **Lighting**: Ensure adequate lighting on the barcode
4. **Stability**: Hold the scanner steady while pressing the trigger
5. **Cleanliness**: Keep barcodes clean and free from damage

**If Scanning Fails**:

1. Try scanning again from a different angle
2. Move closer or farther from the barcode
3. Ensure the barcode is not damaged or obscured
4. Check that the scanner's LED/laser is active
5. Verify the barcode type is supported by your scanner

---

## Scanner Modes

The system supports two scanner modes: USB HID Vendor Mode and Keyboard Mode.

### USB HID Vendor Mode (Default)

**Description**: Direct USB communication with the scanner using HID protocol.

**Advantages**:
- More stable and reliable
- Better error detection
- Clearer status feedback
- Recommended for production use

**Requirements**:
- Scanner must support USB HID Vendor Mode
- Correct VID/PID configuration
- USB connection to computer

**When to Use**: This is the default and recommended mode for normal operations.

### Keyboard Mode (Fallback)

**Description**: Scanner emulates keyboard input, typing the scanned code.

**Advantages**:
- Works with any scanner that supports keyboard emulation
- No VID/PID configuration needed
- Simpler setup

**Disadvantages**:
- Less stable than USB HID mode
- Limited error detection
- Can be affected by keyboard focus issues

**When to Use**:
- USB HID mode is not working
- Scanner only supports keyboard emulation
- Temporary workaround during troubleshooting

### Switching Between Modes

#### Using the GUI (Recommended)

1. Open Admin Panel
2. Click "Scanner Settings"
3. Find the "Scanner Mode" section
4. Select the desired mode:
   - "USB Vendor" for USB HID Vendor Mode
   - "Keyboard" for keyboard emulation mode
5. Click "Save Configuration"
6. The change takes effect immediately

**Visual Indicators**:
- Current mode is displayed in the Scanner Settings dialog
- Connection status updates based on the selected mode

#### Using the Command-Line Utility

```bash
# Switch to USB HID Vendor Mode
python configure_scanner.py --set-mode usb_vendor

# Switch to Keyboard Mode
python configure_scanner.py --set-mode keyboard

# Check current mode
python configure_scanner.py --status
```

**Note**: Mode changes take effect immediately. You don't need to restart the application.

### Scanner Hardware Configuration

**Important**: The scanner hardware must also be configured for the correct mode.

**For USB HID Vendor Mode**:
- Configure your scanner for "USB HID Vendor Mode" or "USB COM Mode"
- Consult your scanner's manual for configuration instructions
- Usually requires scanning a configuration barcode

**For Keyboard Mode**:
- Configure your scanner for "USB HID Keyboard Mode" or "Keyboard Emulation"
- This is often the default mode for many scanners

---

## Configuration Utility

The system includes a command-line utility for managing scanner configuration: `configure_scanner.py`

### Common Commands

#### Check Configuration Status

```bash
python configure_scanner.py --status
```

**Output**:
```
Scanner Configuration Status
============================
Mode: usb_vendor
VID: 4602 (0x11FA)
PID: 33282 (0x8202)
Connection: Connected ✓
Timeout: 30 seconds
```

#### List Connected USB Devices

```bash
python configure_scanner.py --list-devices
```

**Output**:
```
Connected USB HID Devices:
==========================
Device 1:
  VID: 4602 (0x11FA)
  PID: 33282 (0x8202)
  Manufacturer: Wenglor
  Product: Scanner Device
  
Device 2:
  VID: 1234 (0x04D2)
  PID: 5678 (0x162E)
  Manufacturer: Example Corp
  Product: USB Device
```

#### Change Scanner VID/PID

```bash
# Set both VID and PID
python configure_scanner.py --set-vid 4602 --set-pid 33282

# Set only VID (PID remains unchanged)
python configure_scanner.py --set-vid 4602

# Set only PID (VID remains unchanged)
python configure_scanner.py --set-pid 33282
```

#### Switch Scanner Mode

```bash
# Switch to USB HID Vendor Mode
python configure_scanner.py --set-mode usb_vendor

# Switch to Keyboard Mode
python configure_scanner.py --set-mode keyboard
```

#### Test Scanner Connection

```bash
python configure_scanner.py --test-connection
```

**Output** (if successful):
```
Testing connection to scanner...
VID: 4602 (0x11FA)
PID: 33282 (0x8202)

✓ Scanner connected successfully!
```

**Output** (if failed):
```
Testing connection to scanner...
VID: 4602 (0x11FA)
PID: 33282 (0x8202)

✗ Connection failed: Device not found
```

#### Reset to Default Configuration

```bash
python configure_scanner.py --reset
```

This resets:
- VID to 4602 (0x11FA)
- PID to 33282 (0x8202)
- Mode to usb_vendor
- Timeout to 30 seconds

#### Export Configuration

```bash
python configure_scanner.py --export config_backup.json
```

Saves the current configuration to a backup file.

#### Import Configuration

```bash
python configure_scanner.py --import config_backup.json
```

Loads configuration from a backup file.

### Configuration File

The configuration is stored in `scanner_config.json` in the application root directory.

**File Structure**:
```json
{
  "scanner_mode": "usb_vendor",
  "usb_vendor": {
    "vid": 4602,
    "pid": 33282,
    "timeout": 30,
    "read_size": 64,
    "encoding": "utf-8"
  },
  "keyboard": {
    "timeout": 30,
    "auto_focus": true
  }
}
```

**Manual Editing**:
You can edit this file directly with a text editor, but it's recommended to use the GUI or command-line utility to avoid syntax errors.

**Important**:
- VID and PID must be decimal integers (not hexadecimal)
- Valid range: 1-65535
- Mode must be either "usb_vendor" or "keyboard"
- Invalid values will be rejected and defaults will be used

---

## Error Messages

### Understanding Error Messages

When something goes wrong, the system displays clear error messages to help you resolve the issue.

#### "Scanner Not Found"

**What It Means**: The system cannot detect a USB scanner with the configured VID/PID.

**What to Do**:
1. Check that the scanner is connected to a USB port
2. Verify the USB cable is not damaged
3. Try a different USB port
4. Check Scanner Settings to verify VID/PID configuration
5. See [Troubleshooting Guide](USB_SCANNER_TROUBLESHOOTING.md) for detailed steps

**Can I Continue Working?**: Yes, switch to keyboard mode as a temporary workaround.

#### "Connection Failed"

**What It Means**: The scanner was detected but the system couldn't establish communication.

**What to Do**:
1. Disconnect and reconnect the scanner
2. Check for permission issues (especially on Linux)
3. Try the "Test Connection" button in Scanner Settings
4. See [Troubleshooting Guide](USB_SCANNER_TROUBLESHOOTING.md) for platform-specific solutions

**Can I Continue Working?**: Yes, switch to keyboard mode as a temporary workaround.

#### "Read Timeout"

**What It Means**: No barcode was scanned within the timeout period (default 30 seconds).

**What to Do**:
1. This is normal if you cancelled or didn't scan anything
2. Try scanning again
3. Ensure you're pressing the scanner's trigger button
4. Verify the barcode is within the scanner's reading range

**Can I Continue Working?**: Yes, just try scanning again.

#### "Scanner Disconnected During Operation"

**What It Means**: The USB connection was lost while waiting for or reading a scan.

**What to Do**:
1. Check the USB cable connection
2. Reconnect the scanner
3. Try again
4. If it happens frequently, see [Troubleshooting Guide](USB_SCANNER_TROUBLESHOOTING.md)

**Can I Continue Working?**: Yes, reconnect the scanner and try again.

#### "Invalid Data Received"

**What It Means**: The scanner sent data but it was corrupted or in an unexpected format.

**What to Do**:
1. Try scanning the barcode again
2. Check that the barcode is clean and not damaged
3. Ensure adequate lighting on the barcode
4. Verify the scanner is configured correctly

**Can I Continue Working?**: Yes, just scan again.

#### "Permission Denied"

**What It Means**: The application doesn't have permission to access the USB device.

**What to Do**:
1. **Linux**: Set up udev rules (see [Setup Guide](USB_SCANNER_SETUP_GUIDE.md))
2. **Windows**: Try running as Administrator
3. **macOS**: Check Security & Privacy settings
4. See [Troubleshooting Guide](USB_SCANNER_TROUBLESHOOTING.md) for detailed instructions

**Can I Continue Working?**: Yes, switch to keyboard mode as a temporary workaround.

### Error Dialog Actions

Most error dialogs provide action buttons:

- **Retry**: Try the operation again (useful for temporary issues)
- **Cancel**: Abort the current operation and return to the main screen
- **Switch to Keyboard Mode**: Temporarily use keyboard mode (if available)
- **Open Settings**: Go directly to Scanner Settings to fix configuration

---

## Best Practices

### Daily Operations

1. **Start of Day**:
   - Connect the scanner before launching the application
   - Verify connection status in Scanner Settings
   - Test with a sample barcode

2. **During Operations**:
   - Keep barcodes clean and visible
   - Hold the scanner steady while scanning
   - Wait for the dialog to close before moving to the next step
   - If a scan fails, try again immediately

3. **End of Day**:
   - The scanner can remain connected
   - No special shutdown procedure required

### Barcode Maintenance

1. **Keep Barcodes Clean**:
   - Wipe barcodes regularly with a soft cloth
   - Avoid getting liquids on barcodes
   - Replace damaged or faded barcodes

2. **Proper Storage**:
   - Store equipment with barcodes facing outward
   - Avoid stacking items on top of barcodes
   - Protect barcodes from scratches and wear

3. **Barcode Placement**:
   - Place barcodes in easily accessible locations
   - Avoid curved surfaces if possible
   - Ensure adequate space around barcodes for scanning

### Scanner Care

1. **Physical Care**:
   - Handle the scanner gently
   - Avoid dropping or striking the scanner
   - Keep the scanner lens clean
   - Store in a safe location when not in use

2. **Cable Management**:
   - Avoid pulling on the USB cable
   - Don't wrap the cable too tightly
   - Keep the cable away from sharp edges
   - Replace damaged cables promptly

3. **Cleaning**:
   - Clean the scanner lens with a soft, lint-free cloth
   - Don't use harsh chemicals or abrasive materials
   - Clean the scanner housing with a slightly damp cloth

### Performance Tips

1. **Optimal Scanning**:
   - Scan from 4-8 inches away
   - Keep the scanner perpendicular to the barcode
   - Ensure good lighting
   - Press the trigger fully and hold steady

2. **Troubleshooting**:
   - If scanning is slow, check barcode quality
   - If errors are frequent, verify scanner configuration
   - Keep the scanner firmware updated (if applicable)
   - Monitor the log file for recurring issues

3. **Mode Selection**:
   - Use USB HID Vendor Mode for best performance
   - Only use Keyboard Mode when necessary
   - Switch back to USB mode once issues are resolved

### When to Get Help

Contact your system administrator or IT support if:

- Scanner consistently fails to connect
- Errors occur frequently during normal operations
- Configuration changes don't resolve issues
- Physical damage to scanner or cables
- Need to configure a new scanner model

---

## Quick Reference

### Scanning Workflow Summary

1. Application prompts for scan
2. Point scanner at barcode
3. Press trigger button
4. Wait for dialog to close (automatic)
5. Verify information displayed
6. Continue with next step

### Common Tasks

| Task | Method |
|------|--------|
| Check connection | Admin Panel → Scanner Settings |
| Switch modes | Scanner Settings → Select mode → Save |
| Test scanner | Scanner Settings → Test Connection |
| View configuration | `python configure_scanner.py --status` |
| Reset settings | `python configure_scanner.py --reset` |

### Default Settings

| Setting | Value |
|---------|-------|
| Mode | USB Vendor |
| VID | 4602 (0x11FA) |
| PID | 33282 (0x8202) |
| Timeout | 30 seconds |

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Cancel scan | ESC key or Cancel button |
| Open Admin Panel | (Application-specific) |

### File Locations

| File | Location |
|------|----------|
| Configuration | `scanner_config.json` |
| Log file | `logs/scanner.log` |
| Setup guide | `USB_SCANNER_SETUP_GUIDE.md` |
| Troubleshooting | `USB_SCANNER_TROUBLESHOOTING.md` |

---

## Additional Resources

- **Setup Guide**: [USB_SCANNER_SETUP_GUIDE.md](USB_SCANNER_SETUP_GUIDE.md) - Initial setup and configuration
- **Troubleshooting Guide**: [USB_SCANNER_TROUBLESHOOTING.md](USB_SCANNER_TROUBLESHOOTING.md) - Detailed problem resolution
- **Scanner Manual**: Consult your scanner's manufacturer documentation for hardware-specific information

---

## Frequently Asked Questions

### Do I need to manually connect the scanner each time?

No, the scanner connects automatically when needed. Just ensure it's plugged into a USB port.

### Can I use multiple scanners?

The current version supports one scanner at a time. The system uses the scanner configured with the specified VID/PID.

### What happens if the scanner disconnects during a rental?

The system will detect the disconnection and display an error message. Reconnect the scanner and try the operation again. Your data is safe.

### Can I use a different scanner model?

Yes, as long as it supports USB HID Vendor Mode. You'll need to configure the correct VID/PID values for your scanner model.

### How do I know which mode my scanner is in?

Check Scanner Settings in the Admin Panel. It displays the current mode and connection status.

### What if keyboard mode doesn't work either?

Ensure your scanner is configured for keyboard emulation mode (hardware setting). Consult your scanner's manual for configuration instructions.

### Can I change the timeout period?

Yes, edit the `timeout` value in `scanner_config.json` or use the configuration utility. The default is 30 seconds.

### Where can I find the scanner logs?

Scanner logs are located in `logs/scanner.log`. They contain detailed information about all scanner operations and errors.

### Do I need administrator privileges to use the scanner?

- **Windows/macOS**: No, standard user privileges are sufficient
- **Linux**: You may need to set up udev rules once (requires sudo), but then standard user privileges are sufficient

### What barcode types are supported?

This depends on your scanner hardware. Most modern scanners support common types like Code 39, Code 128, QR codes, and Data Matrix codes. Consult your scanner's manual for the complete list.
