"""
Basic verification test for USBHIDScanner class
"""

import logging
from usb_hid_scanner import USBHIDScanner

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)

def test_initialization():
    """Test that scanner can be initialized"""
    scanner = USBHIDScanner(vid=4602, pid=33282, timeout=30)
    assert scanner.vid == 4602
    assert scanner.pid == 33282
    assert scanner.timeout == 30
    assert not scanner.is_connected()
    print("✓ Initialization test passed")

def test_list_devices():
    """Test that we can list HID devices"""
    devices = USBHIDScanner.list_devices()
    print(f"✓ Found {len(devices)} HID devices")
    
    # Print first few devices for debugging
    for i, device in enumerate(devices[:5]):
        print(f"  Device {i}: VID=0x{device.get('vendor_id', 0):04x}, PID=0x{device.get('product_id', 0):04x}")

def test_parse_hid_report():
    """Test HID report parsing"""
    scanner = USBHIDScanner(vid=4602, pid=33282)
    
    # Test with simple data
    test_data = bytearray(b'TEST123\n')
    result = scanner._parse_hid_report(test_data)
    assert result == "test123", f"Expected 'test123', got '{result}'"
    print("✓ HID report parsing test passed")
    
    # Test with data containing null bytes
    test_data = bytearray(b'ABC\x00\x00DEF\n')
    result = scanner._parse_hid_report(test_data)
    assert result == "abcdef", f"Expected 'abcdef', got '{result}'"
    print("✓ Null byte handling test passed")

def test_strip_control_characters():
    """Test control character stripping"""
    scanner = USBHIDScanner(vid=4602, pid=33282)
    
    # Test with whitespace
    result = scanner._strip_control_characters("  test  ")
    assert result == "test", f"Expected 'test', got '{result}'"
    print("✓ Whitespace stripping test passed")
    
    # Test with control characters
    result = scanner._strip_control_characters("test\x01\x02\x03")
    assert result == "test", f"Expected 'test', got '{result}'"
    print("✓ Control character stripping test passed")

if __name__ == "__main__":
    print("Running basic USBHIDScanner tests...\n")
    
    test_initialization()
    test_list_devices()
    test_parse_hid_report()
    test_strip_control_characters()
    
    print("\n✓ All basic tests passed!")
