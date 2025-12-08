# USB Scanner Troubleshooting Guide

## Overview

This guide helps you diagnose and resolve common issues with USB HID scanner integration in the WenglorMEL Rental System.

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Permission Issues](#permission-issues)
3. [Communication Errors](#communication-errors)
4. [Configuration Issues](#configuration-issues)
5. [Fallback to Keyboard Mode](#fallback-to-keyboard-mode)
6. [Diagnostic Tools](#diagnostic-tools)

---

## Connection Issues

### Problem: "Scanner Not Found" Error

**Symptoms**:
- Error dialog displays "Could not connect to USB scanner"
- Connection status shows "Disconnected" in Scanner Settings

**Possible Causes and Solutions**:

#### 1. Scanner Not Connected

**Check**:
- Verify the scanner is physically connected to a USB port
- Check that the USB cable is not damaged
- Try a different USB port
- Look for LED indicators on the scanner (if available)

**Solution**:
- Reconnect the scanner
- Try a different USB cable if available
- Ensure the scanner is powered on

#### 2. Incorrect VID/PID Configuration

**Check**:
- Open Scanner Settings and verify the VID/PID values
- Compare with your scanner's actual VID/PID (see setup guide)

**Solution**:
```bash
# List all connected USB HID devices
python configure_scanner.py --list-devices

# Find your scanner in the list and note its VID/PID

# Update configuration with correct values
python configure_scanner.py --set-vid <VID> --set-pid <PID>

# Test the connection
python configure_scanner.py --status
```

#### 3. Scanner in Wrong Mode

**Check**:
- Verify the scanner is configured for USB HID Vendor Mode
- Some scanners can operate in multiple modes (keyboard, vendor, serial)

**Solution**:
- Consult your scanner's manual for mode switching instructions
- Most scanners require scanning a configuration barcode to change modes
- Look for "USB HID Vendor Mode" or "USB COM Mode" settings

#### 4. Device Already in Use

**Check**:
- Another application might be using the scanner
- Multiple instances of the rental system might be running

**Solution**:
- Close other applications that might access the scanner
- Check Task Manager (Windows) or Activity Monitor (macOS) for duplicate processes
- Restart the application

---

## Permission Issues

### Problem: "Permission Denied" or "Access Denied" Error

**Symptoms**:
- Error message mentions permissions or access rights
- Scanner is detected but cannot be opened
- Works with administrator/root privileges but not as regular user

**Platform-Specific Solutions**:

#### Windows

**Rare on Windows**, but if it occurs:

1. Check if antivirus software is blocking USB access
2. Try running the application as Administrator (right-click → Run as Administrator)
3. Check Windows Device Manager for driver issues:
   - Open Device Manager
   - Look for yellow warning icons on USB devices
   - Update or reinstall drivers if needed

#### Linux

**Most common permission issue on Linux**:

**Solution 1: Create udev Rules (Recommended)**

1. Create a udev rules file:
   ```bash
   sudo nano /etc/udev/rules.d/99-scanner.rules
   ```

2. Add these rules (replace VID/PID with your scanner's values in hex):
   ```
   SUBSYSTEM=="usb", ATTRS{idVendor}=="11fa", ATTRS{idProduct}=="8202", MODE="0666"
   SUBSYSTEM=="hidraw", ATTRS{idVendor}=="11fa", ATTRS{idProduct}=="8202", MODE="0666"
   ```

3. Reload udev rules:
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

4. Disconnect and reconnect the scanner

5. Verify permissions:
   ```bash
   ls -l /dev/hidraw*
   ```
   You should see read/write permissions for your user.

**Solution 2: Add User to plugdev Group**

```bash
# Add your user to the plugdev group
sudo usermod -a -G plugdev $USER

# Log out and log back in for changes to take effect
```

**Solution 3: Temporary Fix (Testing Only)**

```bash
# Run with sudo (not recommended for production)
sudo python main.py
```

#### macOS

**Rare on macOS**, but if it occurs:

1. Check System Preferences → Security & Privacy
2. Grant the application permission to access USB devices if prompted
3. Try restarting the application

---

## Communication Errors

### Problem: "Read Timeout" Error

**Symptoms**:
- Scanner connects successfully but times out waiting for input
- Dialog shows "Waiting for scan..." then times out after 30 seconds

**Possible Causes and Solutions**:

#### 1. Scanner Not Triggering

**Check**:
- Is the scanner's trigger button being pressed?
- Is the scanner in the correct mode to read the barcode type?

**Solution**:
- Ensure you're pressing the trigger button
- Check scanner configuration for supported barcode types
- Verify the barcode is within the scanner's reading range

#### 2. Timeout Too Short

**Check**:
- Default timeout is 30 seconds
- Some workflows might need more time

**Solution**:
Edit `scanner_config.json`:
```json
{
  "usb_vendor": {
    "timeout": 60
  }
}
```

### Problem: "Device Disconnected During Operation"

**Symptoms**:
- Scanner works initially but disconnects during use
- Error message: "Scanner disconnected during read operation"

**Possible Causes and Solutions**:

#### 1. Loose USB Connection

**Solution**:
- Check USB cable connection
- Try a different USB port
- Replace USB cable if damaged

#### 2. Power Issues

**Solution**:
- Use a powered USB hub if the scanner requires more power
- Try a USB 2.0 port instead of USB 3.0 (or vice versa)
- Check if the scanner has an external power supply option

#### 3. USB Suspend/Power Saving

**Solution**:

**Windows**:
1. Open Device Manager
2. Find your scanner under "Universal Serial Bus devices"
3. Right-click → Properties → Power Management
4. Uncheck "Allow the computer to turn off this device to save power"

**Linux**:
```bash
# Disable USB autosuspend
echo -1 | sudo tee /sys/module/usbcore/parameters/autosuspend
```

**macOS**:
1. System Preferences → Energy Saver
2. Uncheck "Put hard disks to sleep when possible"

### Problem: "Corrupted Data" or "Invalid Data" Error

**Symptoms**:
- Scanner reads but data is garbled or incomplete
- Error message mentions corrupted or invalid data

**Possible Causes and Solutions**:

#### 1. Barcode Quality Issues

**Solution**:
- Clean the barcode (remove dirt, scratches)
- Ensure adequate lighting
- Hold scanner at correct distance and angle
- Try scanning multiple times

#### 2. Wrong Encoding

**Check**:
- Default encoding is UTF-8
- Some scanners might use different encoding

**Solution**:
Edit `scanner_config.json`:
```json
{
  "usb_vendor": {
    "encoding": "latin-1"
  }
}
```

Common encodings: `utf-8`, `latin-1`, `ascii`, `cp1252`

#### 3. Scanner Configuration

**Solution**:
- Check scanner manual for data format settings
- Ensure scanner is not adding prefixes/suffixes
- Verify scanner is not in a special encoding mode

---

## Configuration Issues

### Problem: Configuration Changes Not Taking Effect

**Symptoms**:
- Changed VID/PID but scanner still not detected
- Mode switch doesn't seem to work

**Solutions**:

#### 1. Configuration File Not Saved

**Check**:
```bash
# Verify configuration file exists and is readable
cat scanner_config.json
```

**Solution**:
- Ensure you have write permissions to the application directory
- Use the GUI or command-line tool to save configuration
- Manually verify the JSON file is valid

#### 2. Application Not Reloading Configuration

**Solution**:
- Close and restart the application
- Configuration changes take effect immediately for most settings
- Some changes might require reopening the scanner dialog

#### 3. Invalid Configuration Values

**Check**:
- VID and PID must be between 1 and 65535
- Mode must be either "usb_vendor" or "keyboard"

**Solution**:
```bash
# Reset to defaults
python configure_scanner.py --reset

# Verify configuration
python configure_scanner.py --status
```

### Problem: Configuration File Corrupted

**Symptoms**:
- Application fails to start
- Error messages about JSON parsing

**Solution**:

1. Delete the corrupted configuration file:
   ```bash
   # Windows
   del scanner_config.json
   
   # Linux/macOS
   rm scanner_config.json
   ```

2. Restart the application (it will create a new file with defaults)

3. Reconfigure your scanner settings

---

## Fallback to Keyboard Mode

If USB HID mode is not working and you need to continue operations, you can fall back to keyboard emulation mode.

### When to Use Keyboard Mode

- USB HID mode is not working after troubleshooting
- Scanner only supports keyboard emulation
- Temporary workaround while resolving USB issues
- Testing or comparison purposes

### Switching to Keyboard Mode

#### Method 1: Using GUI

1. Open Admin Panel → Scanner Settings
2. Find the "Scanner Mode" section
3. Select "Keyboard" from the mode selector
4. Click "Save Configuration"
5. The change takes effect immediately

#### Method 2: Using Command-Line

```bash
python configure_scanner.py --set-mode keyboard
```

#### Method 3: Manual Configuration

Edit `scanner_config.json`:
```json
{
  "scanner_mode": "keyboard"
}
```

### Keyboard Mode Requirements

**Scanner Configuration**:
- Scanner must be configured for HID Keyboard Mode
- Consult scanner manual for mode switching instructions
- Usually requires scanning a configuration barcode

**Application Behavior**:
- Scanner input appears as keyboard typing
- Same dialogs and workflows as USB mode
- May be less stable than USB HID mode

### Switching Back to USB Mode

Once USB issues are resolved:

```bash
python configure_scanner.py --set-mode usb_vendor
```

Or use the GUI Scanner Settings dialog.

---

## Diagnostic Tools

### Built-in Diagnostics

#### 1. Configuration Status Check

```bash
python configure_scanner.py --status
```

Shows:
- Current mode (usb_vendor or keyboard)
- VID and PID values
- Connection status
- Configuration file location

#### 2. Device Enumeration

```bash
python configure_scanner.py --list-devices
```

Shows:
- All connected USB HID devices
- VID, PID, manufacturer, product name for each device
- Helps identify your scanner

#### 3. Test Connection

**GUI Method**:
1. Open Scanner Settings
2. Click "Test Connection" button
3. View result message

**Command-Line Method**:
```bash
python configure_scanner.py --test-connection
```

#### 4. Log File Analysis

Check `logs/scanner.log` for detailed information:

```bash
# View last 50 lines of log
# Windows
powershell -command "Get-Content logs\scanner.log -Tail 50"

# Linux/macOS
tail -n 50 logs/scanner.log
```

**What to Look For**:
- Connection attempts and results
- USB error codes
- Read operation details
- Configuration changes
- Error messages with timestamps

### External Diagnostic Tools

#### Windows

**Device Manager**:
- Check for driver issues
- View device properties
- Update drivers

**USBDeview** (third-party tool):
- Lists all USB devices
- Shows detailed device information
- Available from NirSoft

#### Linux

```bash
# List USB devices
lsusb

# Detailed USB device information
lsusb -v

# Check USB device permissions
ls -l /dev/hidraw*

# Monitor USB events
sudo udevadm monitor

# Check system logs
dmesg | grep -i usb
```

#### macOS

```bash
# List USB devices
system_profiler SPUSBDataType

# Check system logs
log show --predicate 'subsystem == "com.apple.iokit.IOUSBHostFamily"' --last 1h
```

---

## Common Error Messages

### "Device not found (VID: XXXX, PID: XXXX)"

**Meaning**: Scanner with specified VID/PID is not connected or not detected

**Solutions**:
1. Verify scanner is connected
2. Check VID/PID configuration
3. Try different USB port
4. Check permissions (Linux)

### "Failed to open device: Permission denied"

**Meaning**: Application doesn't have permission to access USB device

**Solutions**:
1. Set up udev rules (Linux)
2. Run as administrator (Windows)
3. Check security settings (macOS)

### "Read timeout after 30 seconds"

**Meaning**: No data received from scanner within timeout period

**Solutions**:
1. Ensure scanner trigger is pressed
2. Check scanner is in correct mode
3. Increase timeout in configuration
4. Verify barcode is readable

### "Invalid HID report data"

**Meaning**: Data received from scanner is corrupted or in unexpected format

**Solutions**:
1. Check barcode quality
2. Verify scanner configuration
3. Try different encoding setting
4. Rescan the barcode

### "Scanner disconnected during operation"

**Meaning**: USB connection lost while reading data

**Solutions**:
1. Check USB cable and connection
2. Disable USB power saving
3. Try different USB port
4. Check for power issues

---

## Getting Help

If you've tried all troubleshooting steps and still have issues:

### Information to Collect

1. **System Information**:
   - Operating system and version
   - Python version
   - Application version

2. **Scanner Information**:
   - Scanner manufacturer and model
   - VID and PID values
   - Scanner mode configuration

3. **Error Details**:
   - Exact error message
   - When the error occurs
   - Steps to reproduce

4. **Log Files**:
   - Contents of `logs/scanner.log`
   - System USB logs (if available)

5. **Configuration**:
   - Contents of `scanner_config.json`
   - Output of `python configure_scanner.py --status`

### Diagnostic Command Output

Run these commands and save the output:

```bash
# Configuration status
python configure_scanner.py --status

# List devices
python configure_scanner.py --list-devices

# Test connection
python configure_scanner.py --test-connection

# Check Python and library versions
python --version
python -c "import hid; print(f'hidapi version: {hid.__version__}')"
```

---

## Quick Reference

### Most Common Issues and Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| Scanner not found | Check USB connection, verify VID/PID |
| Permission denied (Linux) | Set up udev rules |
| Read timeout | Press scanner trigger, check barcode |
| Disconnects during use | Disable USB power saving |
| Configuration not working | Reset to defaults, reconfigure |
| All else fails | Switch to keyboard mode |

### Emergency Fallback

```bash
# Switch to keyboard mode immediately
python configure_scanner.py --set-mode keyboard
```

### Reset Everything

```bash
# Reset configuration to defaults
python configure_scanner.py --reset

# Verify reset
python configure_scanner.py --status
```
