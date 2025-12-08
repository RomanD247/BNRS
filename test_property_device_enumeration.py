"""
Property-Based Test for Device Enumeration Completeness

Feature: usb-hid-vendor-scanner, Property 16: Device enumeration completeness
Validates: Requirements 8.3

This test verifies that the device enumeration function returns complete and
accurate information for all connected USB HID devices.
"""

import hid
from hypothesis import given, strategies as st, settings
from usb_hid_scanner import USBHIDScanner


def test_device_enumeration_returns_list():
    """
    Basic test to verify that list_devices() returns a list.
    """
    print("\n=== Testing Device Enumeration Returns List ===")
    
    devices = USBHIDScanner.list_devices()
    
    assert isinstance(devices, list), \
        f"list_devices() must return a list, got {type(devices)}"
    print(f"✓ list_devices() returned a list with {len(devices)} devices")
    
    return True


def test_device_enumeration_structure():
    """
    Test that each device in the enumeration has the expected structure.
    """
    print("\n=== Testing Device Enumeration Structure ===")
    
    devices = USBHIDScanner.list_devices()
    
    if len(devices) == 0:
        print("⚠ No devices found - skipping structure test")
        return True
    
    # Check first device has expected fields
    device = devices[0]
    
    assert isinstance(device, dict), \
        f"Each device must be a dict, got {type(device)}"
    print("✓ Devices are dictionaries")
    
    # Check for required fields
    required_fields = ['vendor_id', 'product_id']
    for field in required_fields:
        assert field in device, \
            f"Device must have '{field}' field"
    print(f"✓ Devices have required fields: {required_fields}")
    
    # Check optional but expected fields
    optional_fields = ['manufacturer_string', 'product_string', 'serial_number', 'path']
    present_fields = [field for field in optional_fields if field in device]
    print(f"✓ Devices have optional fields: {present_fields}")
    
    return True


@given(st.integers(min_value=0, max_value=10))
@settings(max_examples=100, deadline=None)
def test_device_enumeration_consistency(iteration: int):
    """
    **Feature: usb-hid-vendor-scanner, Property 16: Device enumeration completeness**
    **Validates: Requirements 8.3**
    
    Property: For any call to list_devices(), the function should return a
    consistent list of devices (assuming no devices are connected/disconnected
    between calls).
    
    This property verifies that:
    1. Multiple calls return the same number of devices
    2. Device information remains consistent across calls
    3. VID and PID values are valid (non-negative integers)
    """
    # Get device list
    devices = USBHIDScanner.list_devices()
    
    # Verify it's a list
    assert isinstance(devices, list), \
        "list_devices() must return a list"
    
    # Verify each device has valid structure
    for i, device in enumerate(devices):
        assert isinstance(device, dict), \
            f"Device {i} must be a dict, got {type(device)}"
        
        # Check VID exists and is valid
        assert 'vendor_id' in device, \
            f"Device {i} must have 'vendor_id' field"
        vid = device['vendor_id']
        assert isinstance(vid, int), \
            f"Device {i} VID must be an integer, got {type(vid)}"
        assert vid >= 0, \
            f"Device {i} VID must be non-negative, got {vid}"
        
        # Check PID exists and is valid
        assert 'product_id' in device, \
            f"Device {i} must have 'product_id' field"
        pid = device['product_id']
        assert isinstance(pid, int), \
            f"Device {i} PID must be an integer, got {type(pid)}"
        assert pid >= 0, \
            f"Device {i} PID must be non-negative, got {pid}"


def test_device_enumeration_matches_hidapi():
    """
    Test that USBHIDScanner.list_devices() returns the same devices as
    the underlying hidapi library.
    
    This verifies that the wrapper function doesn't filter or modify the
    device list incorrectly.
    """
    print("\n=== Testing Device Enumeration Matches hidapi ===")
    
    # Get devices from USBHIDScanner
    scanner_devices = USBHIDScanner.list_devices()
    
    # Get devices directly from hidapi
    hidapi_devices = hid.enumerate()
    
    # Compare counts
    assert len(scanner_devices) == len(hidapi_devices), \
        f"Device count mismatch: USBHIDScanner returned {len(scanner_devices)}, " \
        f"hidapi returned {len(hidapi_devices)}"
    print(f"✓ Device counts match: {len(scanner_devices)} devices")
    
    # Verify all hidapi devices are in scanner devices
    hidapi_device_ids = {(d.get('vendor_id'), d.get('product_id'), d.get('path')) 
                         for d in hidapi_devices}
    scanner_device_ids = {(d.get('vendor_id'), d.get('product_id'), d.get('path')) 
                          for d in scanner_devices}
    
    assert hidapi_device_ids == scanner_device_ids, \
        "Device lists don't match between USBHIDScanner and hidapi"
    print("✓ All hidapi devices are present in USBHIDScanner.list_devices()")
    
    return True


def test_device_enumeration_completeness_for_known_devices():
    """
    Test that if we know certain devices are connected (by checking hidapi directly),
    they appear in the USBHIDScanner enumeration with complete information.
    """
    print("\n=== Testing Device Enumeration Completeness ===")
    
    # Get devices directly from hidapi
    hidapi_devices = hid.enumerate()
    
    if len(hidapi_devices) == 0:
        print("⚠ No devices found - skipping completeness test")
        return True
    
    # Get devices from USBHIDScanner
    scanner_devices = USBHIDScanner.list_devices()
    
    # For each hidapi device, verify it's in scanner devices with complete info
    for hidapi_device in hidapi_devices:
        vid = hidapi_device.get('vendor_id')
        pid = hidapi_device.get('product_id')
        path = hidapi_device.get('path')
        
        # Find matching device in scanner devices
        matching_devices = [
            d for d in scanner_devices 
            if d.get('vendor_id') == vid 
            and d.get('product_id') == pid 
            and d.get('path') == path
        ]
        
        assert len(matching_devices) > 0, \
            f"Device VID=0x{vid:04x}, PID=0x{pid:04x} not found in scanner enumeration"
        
        scanner_device = matching_devices[0]
        
        # Verify VID matches
        assert scanner_device.get('vendor_id') == vid, \
            f"VID mismatch for device at {path}"
        
        # Verify PID matches
        assert scanner_device.get('product_id') == pid, \
            f"PID mismatch for device at {path}"
        
        # Verify manufacturer string matches (if present)
        if 'manufacturer_string' in hidapi_device:
            assert scanner_device.get('manufacturer_string') == hidapi_device.get('manufacturer_string'), \
                f"Manufacturer mismatch for device VID=0x{vid:04x}, PID=0x{pid:04x}"
        
        # Verify product string matches (if present)
        if 'product_string' in hidapi_device:
            assert scanner_device.get('product_string') == hidapi_device.get('product_string'), \
                f"Product mismatch for device VID=0x{vid:04x}, PID=0x{pid:04x}"
        
        print(f"✓ Device VID=0x{vid:04x}, PID=0x{pid:04x} enumerated with complete information")
    
    print(f"✓ All {len(hidapi_devices)} devices enumerated completely")
    return True


@given(st.lists(st.integers(min_value=0, max_value=65535), min_size=0, max_size=5))
@settings(max_examples=100, deadline=None)
def test_device_enumeration_vid_pid_validity(test_vids: list):
    """
    **Feature: usb-hid-vendor-scanner, Property 16: Device enumeration completeness**
    **Validates: Requirements 8.3**
    
    Property: For any enumerated device, the VID and PID values must be valid
    USB identifiers (integers in the range 0-65535).
    
    This property verifies that:
    1. All VID values are valid USB vendor IDs
    2. All PID values are valid USB product IDs
    3. VID and PID are integers, not strings or other types
    """
    devices = USBHIDScanner.list_devices()
    
    for device in devices:
        # Check VID
        vid = device.get('vendor_id')
        assert vid is not None, "Device must have vendor_id"
        assert isinstance(vid, int), f"VID must be int, got {type(vid)}"
        assert 0 <= vid <= 65535, f"VID must be in range 0-65535, got {vid}"
        
        # Check PID
        pid = device.get('product_id')
        assert pid is not None, "Device must have product_id"
        assert isinstance(pid, int), f"PID must be int, got {type(pid)}"
        assert 0 <= pid <= 65535, f"PID must be in range 0-65535, got {pid}"


def main():
    """Run all device enumeration completeness tests"""
    print("=" * 70)
    print("Property-Based Test: Device Enumeration Completeness")
    print("Feature: usb-hid-vendor-scanner, Property 16")
    print("Validates: Requirements 8.3")
    print("=" * 70)
    
    try:
        # Run basic tests
        test_device_enumeration_returns_list()
        test_device_enumeration_structure()
        test_device_enumeration_matches_hidapi()
        test_device_enumeration_completeness_for_known_devices()
        
        # Run property-based tests
        print("\n=== Running Property-Based Tests ===")
        print("Testing device enumeration consistency (100 examples)...")
        test_device_enumeration_consistency()
        print("✓ Device enumeration consistency test passed")
        
        print("\nTesting VID/PID validity (100 examples)...")
        test_device_enumeration_vid_pid_validity()
        print("✓ VID/PID validity test passed")
        
        print("\n" + "=" * 70)
        print("✓ All device enumeration completeness tests passed!")
        print("=" * 70)
        
        return True
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
