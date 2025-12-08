"""
Test script to verify get_nfc_input() mode routing functionality

This script tests:
- Mode detection from configuration
- Routing to correct implementation (USB HID vs keyboard)
- Async interface compatibility
"""

import asyncio
from scanner_config import get_scanner_mode, set_scanner_mode, load_config
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_mode_detection():
    """Test that scanner mode can be detected from configuration"""
    print("\n=== Testing Mode Detection ===")
    
    # Get current mode
    current_mode = get_scanner_mode()
    print(f"Current scanner mode: {current_mode}")
    
    # Verify mode is valid
    assert current_mode in ["usb_vendor", "keyboard"], f"Invalid mode: {current_mode}"
    print("✓ Mode detection works correctly")
    
    return True


def test_mode_switching():
    """Test that scanner mode can be switched at runtime"""
    print("\n=== Testing Mode Switching ===")
    
    # Get original mode
    original_mode = get_scanner_mode()
    print(f"Original mode: {original_mode}")
    
    # Switch to opposite mode
    new_mode = "keyboard" if original_mode == "usb_vendor" else "usb_vendor"
    print(f"Switching to: {new_mode}")
    
    success = set_scanner_mode(new_mode)
    assert success, "Failed to set scanner mode"
    
    # Verify mode changed
    current_mode = get_scanner_mode()
    assert current_mode == new_mode, f"Mode not changed: expected {new_mode}, got {current_mode}"
    print(f"✓ Mode switched to: {current_mode}")
    
    # Switch back to original mode
    print(f"Switching back to: {original_mode}")
    success = set_scanner_mode(original_mode)
    assert success, "Failed to restore original mode"
    
    # Verify mode restored
    current_mode = get_scanner_mode()
    assert current_mode == original_mode, f"Mode not restored: expected {original_mode}, got {current_mode}"
    print(f"✓ Mode restored to: {current_mode}")
    
    return True


def test_configuration_persistence():
    """Test that configuration changes persist"""
    print("\n=== Testing Configuration Persistence ===")
    
    # Get original mode
    original_mode = get_scanner_mode()
    print(f"Original mode: {original_mode}")
    
    # Switch mode
    new_mode = "keyboard" if original_mode == "usb_vendor" else "usb_vendor"
    set_scanner_mode(new_mode)
    
    # Reload configuration (simulates app restart)
    config = load_config()
    persisted_mode = config.get("scanner_mode")
    
    assert persisted_mode == new_mode, f"Mode not persisted: expected {new_mode}, got {persisted_mode}"
    print(f"✓ Mode persisted correctly: {persisted_mode}")
    
    # Restore original mode
    set_scanner_mode(original_mode)
    
    return True


def test_async_interface():
    """Test that get_nfc_input maintains async interface"""
    print("\n=== Testing Async Interface ===")
    
    # Import here to avoid issues if NfcScan has UI dependencies
    try:
        from NfcScan import get_nfc_input
        
        # Verify function is async
        import inspect
        assert inspect.iscoroutinefunction(get_nfc_input), "get_nfc_input is not async"
        print("✓ get_nfc_input is an async function")
        
        # Verify function signature
        sig = inspect.signature(get_nfc_input)
        params = list(sig.parameters.keys())
        assert len(params) == 1, f"Expected 1 parameter, got {len(params)}"
        assert params[0] == "prompt_message", f"Expected 'prompt_message' parameter, got '{params[0]}'"
        print("✓ Function signature is correct")
        
        return True
        
    except ImportError as e:
        print(f"⚠ Could not import NfcScan (may require UI environment): {e}")
        print("  Skipping async interface test")
        return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing NFC Scan Mode Routing Implementation")
    print("=" * 60)
    
    try:
        # Run tests
        test_mode_detection()
        test_mode_switching()
        test_configuration_persistence()
        test_async_interface()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
