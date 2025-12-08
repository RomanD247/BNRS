# Scanner Status Differentiation Implementation

## Overview

This document describes the implementation of differentiated error messages for scanner operations, specifically distinguishing between user cancellation and scanner connection failures.

## Problem Statement

Previously, when the scanner was not connected, the system would show the error message "Device scanning cancelled", which was confusing because the user didn't actually cancel the operation - the scanner simply wasn't available.

## Solution

Modified the scanner input functions to return status information along with the scanned data, allowing the calling code to display appropriate error messages based on the actual reason for failure.

## Changes Made

### 1. Modified Return Type

**Function:** `get_usb_hid_input()`
- **Before:** Returns `str` (scanned data or empty string)
- **After:** Returns `tuple[str, str]` (scanned_data, status)

**Function:** `get_nfc_input()`
- **Before:** Returns `str` (scanned data or empty string)
- **After:** Returns `tuple[str, str]` (scanned_data, status)

### 2. Status Values

The status string can have the following values:

- `"success"` - Data was successfully scanned
- `"cancelled"` - User clicked the Cancel button
- `"not_connected"` - Scanner device could not be connected
- `"error"` - Other errors occurred

### 3. Updated Files

#### Core Scanner Module
- **NfcScan.py**
  - Modified `get_usb_hid_input()` to return tuple with status
  - Modified `get_nfc_input()` to return tuple with status
  - Updated rental workflow to show appropriate messages based on status

#### GUI Files
- **gui/gui_addequip.py** - Updated scan_nfc() function
- **gui/gui_adduser.py** - Updated scan_nfc() function
- **gui/gui_changeEquip.py** - Updated scan_nfc() function
- **gui/gui_changeUser.py** - Updated scan_nfc() function

#### Main Application
- **main.py** - Updated scan_nfc() function

### 4. Error Messages

The rental workflow now shows different messages based on the status:

```python
equipment_nfc, scan_status = await get_nfc_input("Scan Device's Code")
if not equipment_nfc:
    if scan_status == "cancelled":
        ui.notify("Device scanning cancelled", color="warning")
    elif scan_status == "not_connected":
        ui.notify("Scanner not connected", color="negative")
    else:
        ui.notify("Device scanning failed", color="negative")
    return
```

## User Experience Improvements

### Before
- Scanner not connected → "Device scanning cancelled" ❌ (confusing)
- User clicks Cancel → "Device scanning cancelled" ✓

### After
- Scanner not connected → "Scanner not connected" ✓ (clear)
- User clicks Cancel → "Device scanning cancelled" ✓ (clear)
- Other errors → "Device scanning failed" ✓ (clear)

## Backward Compatibility

The changes maintain backward compatibility in the following ways:

1. **Keyboard Mode:** The `get_nfc_input_keyboard()` function still returns just a string, but `get_nfc_input()` wraps it to return a tuple
2. **Background Scanner:** The background scanner task in `get_user_input_with_selection()` directly uses `USBHIDScanner` class and doesn't need changes
3. **Tuple Unpacking:** All calling code has been updated to unpack the tuple: `data, status = await get_nfc_input(...)`

## Testing

A new test file `test_scanner_status_messages.py` has been created to verify:
- Return type is tuple with 2 elements
- Status values are correctly set
- Both USB and keyboard modes work correctly
- Cancellation is properly detected

## Implementation Details

### Status Tracking in get_usb_hid_input()

The status is tracked throughout the scanning process:

1. **Initial state:** `status = "error"` (default)
2. **User cancels:** `status = "cancelled"`
3. **Connection fails:** `status = "not_connected"`
4. **Scan succeeds:** `status = "success"`
5. **Retry after error:** `status = "error"` (reset for retry)

### Connection Error Dialog

When the scanner is not connected, the system:
1. Sets `status = "not_connected"`
2. Shows the connection error dialog with troubleshooting steps
3. Offers options to:
   - Retry connection
   - Switch to keyboard mode
   - Cancel operation

If the user chooses to cancel from the connection error dialog, the status is updated to `"cancelled"`.

## Future Enhancements

Possible future improvements:
1. Add more specific error statuses (e.g., "timeout", "permission_denied", "corrupted_data")
2. Create a centralized error message handler
3. Add telemetry to track which errors occur most frequently
4. Implement automatic retry logic for transient errors

## Notes

- The background scanner in `get_user_input_with_selection()` doesn't use the status system since it handles errors internally and shows real-time feedback in the dialog
- The status system is primarily for the simple scan dialogs used in the rental workflow and GUI forms
