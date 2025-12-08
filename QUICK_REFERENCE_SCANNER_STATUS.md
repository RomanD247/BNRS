# Quick Reference: Scanner Status Messages

## What Changed?

The scanner now returns **status information** along with scanned data, allowing for better error messages.

## Return Format

```python
# Old way (before)
equipment_nfc = await get_nfc_input("Scan Device's Code")

# New way (after)
equipment_nfc, scan_status = await get_nfc_input("Scan Device's Code")
```

## Status Values

| Status | Meaning | When It Happens |
|--------|---------|-----------------|
| `"success"` | Scan completed successfully | User scanned a code |
| `"cancelled"` | User cancelled the operation | User clicked Cancel button |
| `"not_connected"` | Scanner device not found | Scanner is unplugged or not configured |
| `"error"` | Other error occurred | Various error conditions |

## Error Messages

### In Rental Workflow (NfcScan.py)

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

### User Experience

| Scenario | Old Message | New Message |
|----------|-------------|-------------|
| Scanner not plugged in | ❌ "Device scanning cancelled" | ✅ "Scanner not connected" |
| User clicks Cancel | ✅ "Device scanning cancelled" | ✅ "Device scanning cancelled" |
| Other errors | ❌ "Device scanning cancelled" | ✅ "Device scanning failed" |

## Code Examples

### Basic Usage

```python
# Scan and check status
data, status = await get_nfc_input("Scan Code")

if status == "success":
    print(f"Scanned: {data}")
elif status == "cancelled":
    print("User cancelled")
elif status == "not_connected":
    print("Scanner not connected")
else:
    print("Error occurred")
```

### Simplified Check

```python
# If you just need to know if it worked
data, status = await get_nfc_input("Scan Code")

if data:
    # Success - process the data
    process_scan(data)
else:
    # Failed - show appropriate message based on status
    show_error_message(status)
```

## Files Modified

- ✅ `NfcScan.py` - Core scanner functions
- ✅ `main.py` - Main application
- ✅ `gui/gui_addequip.py` - Add equipment dialog
- ✅ `gui/gui_adduser.py` - Add user dialog
- ✅ `gui/gui_changeEquip.py` - Edit equipment dialog
- ✅ `gui/gui_changeUser.py` - Edit user dialog

## Testing

Run the test suite:
```bash
pytest test_scanner_status_messages.py -v
```

## Migration Guide

If you have custom code that calls `get_nfc_input()`:

### Before
```python
nfc_value = await get_nfc_input("Scan Code")
if nfc_value:
    # Process scan
else:
    # Show error
```

### After
```python
nfc_value, scan_status = await get_nfc_input("Scan Code")
if nfc_value:
    # Process scan
else:
    # Show specific error based on status
    if scan_status == "cancelled":
        ui.notify("Cancelled", color="warning")
    elif scan_status == "not_connected":
        ui.notify("Scanner not connected", color="negative")
```
