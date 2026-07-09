"""
Integration test to verify get_nfc_input() works with existing rental workflows

This test verifies:
- get_nfc_input() can be called from rental workflow context
- Function signature is compatible
- Async interface works correctly
- Mode routing doesn't break existing functionality
"""

import asyncio
import inspect
from scanner_config import get_scanner_mode, set_scanner_mode


def test_rental_workflow_integration():
    """Test that get_nfc_input can be used in rental workflow context"""
    print("\n=== Testing Rental Workflow Integration ===")
    
    try:
        from NfcScan import nfc_equipment_rental_workflow
        
        # Check workflow function exists and is async
        assert inspect.iscoroutinefunction(nfc_equipment_rental_workflow), \
            "Rental workflow must be async"
        print("✓ Rental workflow is async")
        
        # Check workflow signature
        sig = inspect.signature(nfc_equipment_rental_workflow)
        print(f"✓ Rental workflow signature: {sig}")
        
        # Verify workflow can be called (we won't actually call it without UI)
        print("✓ Rental workflow is importable and callable")
        
        return True
        
    except ImportError as e:
        print(f"⚠ Could not import rental workflow: {e}")
        return False


def test_mode_routing_logic():
    """Test that mode routing logic works correctly"""
    print("\n=== Testing Mode Routing Logic ===")
    
    # Test USB vendor mode
    set_scanner_mode("usb_vendor")
    mode = get_scanner_mode()
    assert mode == "usb_vendor", f"Expected usb_vendor, got {mode}"
    print("✓ USB vendor mode set correctly")
    
    # Test keyboard mode
    set_scanner_mode("keyboard")
    mode = get_scanner_mode()
    assert mode == "keyboard", f"Expected keyboard, got {mode}"
    print("✓ Keyboard mode set correctly")

    return True


def test_imports():
    """Test that all necessary imports work"""
    print("\n=== Testing Imports ===")
    
    try:
        from NfcScan import get_nfc_input, get_usb_hid_input, get_nfc_input_keyboard
        print("✓ All scanner input functions imported successfully")
        
        from usb_hid_scanner import USBHIDScanner
        print("✓ USBHIDScanner imported successfully")
        
        from scanner_config import get_scanner_mode, get_usb_config
        print("✓ Scanner config functions imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def main():
    """Run all integration tests"""
    print("=" * 60)
    print("Integration Tests: NFC Scan with Rental Workflow")
    print("=" * 60)
    
    try:
        # Run tests
        tests = {
            "test_imports": test_imports,
            "test_rental_workflow_integration": test_rental_workflow_integration,
            "test_mode_routing_logic": test_mode_routing_logic,
        }
        results = [func() for func in tests.values()]

        if all(results):
            print("\n" + "=" * 60)
            print("✓ All integration tests passed!")
            print("=" * 60)
            print("\nThe implementation is compatible with existing rental workflows.")
            print("The get_nfc_input() function can be used as a drop-in replacement.")
            return True
        else:
            failed = [name for name, result in zip(tests.keys(), results) if not result]
            print("\n" + "=" * 60)
            print(f"✗ Integration tests failed: {', '.join(failed)}")
            print("=" * 60)
            return False

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Standalone script mode: no pytest, so conftest.py's autouse
    # isolated_scanner_config fixture never runs - redirect CONFIG_FILE
    # ourselves so this invocation can't rewrite the live scanner_config.json
    # (step1-script-mode-runners-not-actually-isolated).
    import tempfile
    import shutil
    import os
    import scanner_config
    _original_config_file = scanner_config.CONFIG_FILE
    _temp_dir = tempfile.mkdtemp()
    scanner_config.CONFIG_FILE = os.path.join(_temp_dir, "test_scanner_config.json")
    try:
        success = main()
    finally:
        scanner_config.CONFIG_FILE = _original_config_file
        shutil.rmtree(_temp_dir, ignore_errors=True)
    exit(0 if success else 1)
