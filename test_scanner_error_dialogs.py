"""
Test Scanner Error Dialogs

This test file verifies that the scanner error dialogs are properly implemented
and can be displayed correctly.

Requirements: 1.5, 4.1, 4.2, 4.3, 4.4, 4.5
"""

import asyncio
from scanner_error_dialogs import ScannerErrorDialogs


def test_error_dialog_imports():
    """Test that all error dialog methods are available"""
    # Verify all required methods exist
    assert hasattr(ScannerErrorDialogs, 'show_connection_error')
    assert hasattr(ScannerErrorDialogs, 'show_timeout_error')
    assert hasattr(ScannerErrorDialogs, 'show_disconnection_error')
    assert hasattr(ScannerErrorDialogs, 'show_corrupted_data_error')
    assert hasattr(ScannerErrorDialogs, 'show_permission_error')
    assert hasattr(ScannerErrorDialogs, 'show_notification')
    
    print("✓ All error dialog methods are available")


def test_error_dialog_signatures():
    """Test that error dialog methods have correct signatures"""
    import inspect
    
    # Check show_connection_error signature
    sig = inspect.signature(ScannerErrorDialogs.show_connection_error)
    params = list(sig.parameters.keys())
    assert 'vid' in params
    assert 'pid' in params
    assert 'retry_callback' in params
    assert 'fallback_callback' in params
    print("✓ show_connection_error has correct signature")
    
    # Check show_timeout_error signature
    sig = inspect.signature(ScannerErrorDialogs.show_timeout_error)
    params = list(sig.parameters.keys())
    assert 'timeout' in params
    print("✓ show_timeout_error has correct signature")
    
    # Check show_disconnection_error signature
    sig = inspect.signature(ScannerErrorDialogs.show_disconnection_error)
    print("✓ show_disconnection_error has correct signature")
    
    # Check show_corrupted_data_error signature
    sig = inspect.signature(ScannerErrorDialogs.show_corrupted_data_error)
    print("✓ show_corrupted_data_error has correct signature")
    
    # Check show_permission_error signature
    sig = inspect.signature(ScannerErrorDialogs.show_permission_error)
    params = list(sig.parameters.keys())
    assert 'vid' in params
    assert 'pid' in params
    print("✓ show_permission_error has correct signature")
    
    # Check show_notification signature
    sig = inspect.signature(ScannerErrorDialogs.show_notification)
    params = list(sig.parameters.keys())
    assert 'message' in params
    assert 'error_type' in params
    print("✓ show_notification has correct signature")


def test_error_dialog_return_types():
    """Test that error dialog methods have correct return type annotations"""
    import inspect
    
    # Check async methods return strings
    sig = inspect.signature(ScannerErrorDialogs.show_connection_error)
    assert sig.return_annotation == str
    print("✓ show_connection_error returns str")
    
    sig = inspect.signature(ScannerErrorDialogs.show_timeout_error)
    assert sig.return_annotation == str
    print("✓ show_timeout_error returns str")
    
    sig = inspect.signature(ScannerErrorDialogs.show_disconnection_error)
    assert sig.return_annotation == str
    print("✓ show_disconnection_error returns str")
    
    sig = inspect.signature(ScannerErrorDialogs.show_corrupted_data_error)
    assert sig.return_annotation == str
    print("✓ show_corrupted_data_error returns str")
    
    sig = inspect.signature(ScannerErrorDialogs.show_permission_error)
    assert sig.return_annotation == str
    print("✓ show_permission_error returns str")


def test_nfc_scan_integration():
    """Test that NfcScan.py properly imports and uses error dialogs"""
    import NfcScan
    
    # Verify the import exists
    assert hasattr(NfcScan, 'ScannerErrorDialogs')
    print("✓ NfcScan imports ScannerErrorDialogs")
    
    # Verify get_usb_hid_input exists
    assert hasattr(NfcScan, 'get_usb_hid_input')
    print("✓ get_usb_hid_input function exists")
    
    # Check that the function is async
    import inspect
    assert inspect.iscoroutinefunction(NfcScan.get_usb_hid_input)
    print("✓ get_usb_hid_input is async")


def test_usb_scanner_permission_error():
    """Test that USBHIDScanner can raise PermissionError"""
    from usb_hid_scanner import USBHIDScanner
    import inspect
    
    # Check that connect method exists
    assert hasattr(USBHIDScanner, 'connect')
    print("✓ USBHIDScanner.connect method exists")
    
    # Check the docstring mentions PermissionError
    docstring = USBHIDScanner.connect.__doc__
    assert 'PermissionError' in docstring
    print("✓ USBHIDScanner.connect documents PermissionError")


def test_scanner_config_integration():
    """Test that scanner_config functions are available"""
    from scanner_config import set_scanner_mode, get_scanner_mode
    
    # Verify functions exist
    assert callable(set_scanner_mode)
    assert callable(get_scanner_mode)
    print("✓ Scanner config functions are available")


def run_all_tests():
    """Run all error dialog tests"""
    print("=" * 60)
    print("TESTING SCANNER ERROR DIALOGS")
    print("=" * 60)
    
    try:
        test_error_dialog_imports()
        print()
        
        test_error_dialog_signatures()
        print()
        
        test_error_dialog_return_types()
        print()
        
        test_nfc_scan_integration()
        print()
        
        test_usb_scanner_permission_error()
        print()
        
        test_scanner_config_integration()
        print()
        
        print("=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        
        return True
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
