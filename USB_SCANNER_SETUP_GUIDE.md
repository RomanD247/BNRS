# USB Scanner Setup Guide

## Overview

This guide covers the setup and configuration of USB HID Vendor Mode scanners for the WenglorMEL Rental System. The system supports direct USB HID communication for improved stability and reliability compared to keyboard emulation mode.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Scanner Configuration](#scanner-configuration)
4. [Platform-Specific Requirements](#platform-specific-requirements)
5. [Verification](#verification)

---

## Prerequisites

### Hardware Requirements

- USB HID-compatible barcode or Data Matrix scanner
- USB port on the host computer
- Scanner configured for USB HID Vendor Mode (not keyboard emulation mode)

### Software Requirements

- Python 3.8 or higher
- WenglorMEL Rental System installed
- Administrator/root access for initial setup (platform-dependent)

---

## Installation

### Step 1: Install hidapi Library

The system uses the `hidapi` library for USB HID communication. This should already be included in the requirements, but you can verify or install it manually:

```bash
pip install hidapi
```

**Note**: The hidapi library is cross-platform and works on Windows, Linux, and macOS.

### Step 2: Verify Installation

To verify that hidapi is installed correctly, run:

```bash
python -c "import hid; print('hidapi installed successfully')"
```

If you see "hidapi installed successfully", the installation is complete.

---

## Scanner Configuration

### Default Configuration

The system comes with default configuration values for the Wenglor scanner:

- **Vendor ID (VID)**: 4602 (0x11FA in hexadecimal)
- **Product ID (PID)**: 33282 (0x8202 in hexadecimal)
- **Scanner Mode**: usb_vendor
- **Timeout**: 30 seconds

### Configuration File

Scanner settings are stored in `scanner_config.json` in the application root directory. The file is created automatically with default values on first run.

**Example configuration file**:

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

### Finding Your Scanner's VID/PID

If you're using a different scanner model, you need to find its VID and PID values.

#### Method 1: Using the GUI Configuration Tool (Recommended)

1. Launch the WenglorMEL Rental System
2. Open the Admin Panel
3. Click "Scanner Settings" button
4. Click "Refresh Devices" to list all connected USB HID devices
5. Find your scanner in the list (look for the manufacturer/product name)
6. Note the VID and PID values displayed
7. Select the device and click "Save Configuration"

#### Method 2: Using the Command-Line Utility

Run the configuration utility to list all connected USB HID devices:

```bash
python configure_scanner.py --list-devices
```

This will display all connected HID devices with their VID, PID, manufacturer, and product information.

#### Method 3: Using System Tools

**Windows**:
1. Open Device Manager
2. Find your scanner under "Human Interface Devices"
3. Right-click → Properties → Details tab
4. Select "Hardware Ids" from the dropdown
5. Look for values like `VID_11FA&PID_8202`

**Linux**:
```bash
lsusb
```
Look for your scanner in the output. The format is `ID VID:PID`.

**macOS**:
1. Click Apple menu → About This Mac → System Report
2. Select "USB" in the sidebar
3. Find your scanner and note the Vendor ID and Product ID

### Configuring VID/PID

#### Method 1: Using the GUI (Recommended)

1. Open Admin Panel → Scanner Settings
2. Enter the VID and PID values (in decimal format)
3. Click "Test Connection" to verify the scanner is detected
4. Click "Save Configuration" to persist the settings

#### Method 2: Using the Command-Line Utility

```bash
# Set VID and PID
python configure_scanner.py --set-vid 4602 --set-pid 33282

# Verify the configuration
python configure_scanner.py --status
```

#### Method 3: Manual Configuration File Editing

Edit `scanner_config.json` directly:

1. Open `scanner_config.json` in a text editor
2. Update the `vid` and `pid` values under `usb_vendor`
3. Save the file
4. Restart the application

**Important**: VID and PID values must be:
- Positive integers
- In the range 1-65535
- In decimal format (not hexadecimal) in the JSON file

---

## Platform-Specific Requirements

### Windows

**No additional setup required**. The hidapi library uses the native Windows HID API, which is available by default.

**Permissions**: Standard user permissions are sufficient for USB HID access on Windows.

### Linux

**Additional setup may be required** for USB device permissions.

#### Option 1: udev Rules (Recommended for Production)

Create a udev rule to grant access to your scanner without requiring root privileges:

1. Create a new udev rules file:
   ```bash
   sudo nano /etc/udev/rules.d/99-scanner.rules
   ```

2. Add the following rule (replace VID and PID with your scanner's values):
   ```
   SUBSYSTEM=="usb", ATTRS{idVendor}=="11fa", ATTRS{idProduct}=="8202", MODE="0666"
   SUBSYSTEM=="hidraw", ATTRS{idVendor}=="11fa", ATTRS{idProduct}=="8202", MODE="0666"
   ```

   **Note**: VID and PID must be in lowercase hexadecimal format in udev rules.

3. Reload udev rules:
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

4. Disconnect and reconnect your scanner

#### Option 2: Run with sudo (Not Recommended for Production)

For testing purposes only, you can run the application with sudo:

```bash
sudo python main.py
```

**Warning**: Running applications with elevated privileges is a security risk and should only be used for testing.

#### Verifying Linux Permissions

To check if your scanner is accessible:

```bash
python configure_scanner.py --list-devices
```

If you see your scanner in the list, permissions are configured correctly.

### macOS

**No additional setup required**. The hidapi library uses IOKit, which is available by default on macOS.

**Permissions**: Standard user permissions are sufficient for USB HID access on macOS.

---

## Verification

### Step 1: Check Scanner Connection

Use the GUI configuration tool:

1. Open Admin Panel → Scanner Settings
2. Check the "Connection Status" indicator
3. If disconnected, click "Test Connection"

Or use the command-line utility:

```bash
python configure_scanner.py --status
```

Expected output:
```
Scanner Configuration Status
============================
Mode: usb_vendor
VID: 4602 (0x11FA)
PID: 33282 (0x8202)
Connection: Connected ✓
```

### Step 2: Test Scanning

1. Open the rental workflow in the application
2. Click to scan an equipment or user code
3. Scan a barcode or Data Matrix code with your scanner
4. Verify that the code is captured correctly

### Step 3: Check Logs

If you encounter issues, check the scanner log file:

```
logs/scanner.log
```

The log contains detailed information about USB operations, connection attempts, and errors.

---

## Next Steps

- If you encounter issues, see the [Troubleshooting Guide](USB_SCANNER_TROUBLESHOOTING.md)
- To switch between USB and keyboard modes, see the [User Documentation](USB_SCANNER_USER_GUIDE.md)
- For configuration utility usage, see the [User Documentation](USB_SCANNER_USER_GUIDE.md)

---

## Quick Reference

### Default Configuration Values

| Setting | Value |
|---------|-------|
| VID | 4602 (0x11FA) |
| PID | 33282 (0x8202) |
| Mode | usb_vendor |
| Timeout | 30 seconds |
| Read Size | 64 bytes |
| Encoding | UTF-8 |

### Configuration File Location

```
scanner_config.json
```

### Log File Location

```
logs/scanner.log
```

### Common Commands

```bash
# List all USB HID devices
python configure_scanner.py --list-devices

# Check current configuration
python configure_scanner.py --status

# Set VID and PID
python configure_scanner.py --set-vid <VID> --set-pid <PID>

# Switch to USB vendor mode
python configure_scanner.py --set-mode usb_vendor

# Switch to keyboard mode
python configure_scanner.py --set-mode keyboard

# Reset to defaults
python configure_scanner.py --reset
```
