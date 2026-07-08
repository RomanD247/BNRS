"""
Property-Based Test for Mode Routing Correctness

Feature: usb-hid-vendor-scanner, Property 14: Mode routing correctness
Validates: Requirements 7.2, 7.3

This test verifies that get_nfc_input() correctly routes to the appropriate
implementation (USB HID or keyboard) based on the scanner_mode configuration.
"""

import asyncio
import inspect
from unittest.mock import patch, MagicMock, AsyncMock
from hypothesis import given, strategies as st, settings
import scanner_config
from scanner_config import get_scanner_mode, set_scanner_mode, load_config
from NfcScan import get_nfc_input


def test_mode_routing_basic():
    """
    Basic test to verify mode routing works for both modes.
    
    This test verifies that:
    1. When mode is "usb_vendor", get_usb_hid_input is called
    2. When mode is "keyboard", get_nfc_input_keyboard is called
    """
    print("\n=== Testing Basic Mode Routing ===")
    
    try:
        from NfcScan import get_nfc_input
        
        # Save original mode
        original_mode = get_scanner_mode()
        
        try:
            # Test USB vendor mode routing
            print("Testing USB vendor mode routing...")
            set_scanner_mode("usb_vendor")
            
            # Mock the USB HID implementation
            with patch('NfcScan.get_usb_hid_input', new_callable=AsyncMock) as mock_usb:
                mock_usb.return_value = ("test_usb_result", "success")

                # Call get_nfc_input
                data, status = asyncio.run(get_nfc_input("test prompt"))

                # Verify USB HID implementation was called
                mock_usb.assert_called_once_with("test prompt")
                assert data == "test_usb_result", \
                    f"Expected 'test_usb_result', got '{data}'"
                assert status == "success", f"Expected status 'success', got '{status}'"
                print("✓ USB vendor mode routes to get_usb_hid_input")
            
            # Test keyboard mode routing
            print("Testing keyboard mode routing...")
            set_scanner_mode("keyboard")
            
            # Mock the keyboard implementation
            with patch('NfcScan.get_nfc_input_keyboard', new_callable=AsyncMock) as mock_keyboard:
                mock_keyboard.return_value = "test_keyboard_result"
                
                # Call get_nfc_input
                data, status = asyncio.run(get_nfc_input("test prompt"))
                
                # Verify keyboard implementation was called
                mock_keyboard.assert_called_once_with("test prompt")
                assert data == "test_keyboard_result", \
                    f"Expected 'test_keyboard_result', got '{data}'"
                assert status == "success", f"Expected status 'success', got '{status}'"
                print("✓ Keyboard mode routes to get_nfc_input_keyboard")
            
            return True
            
        finally:
            # Restore original mode
            set_scanner_mode(original_mode)
            
    except ImportError as e:
        print(f"⚠ Could not import NfcScan (may require UI environment): {e}")
        print("  Skipping basic routing test")
        return True


@given(st.sampled_from(["usb_vendor", "keyboard"]))
@settings(max_examples=100, deadline=None)
def test_mode_routing_correctness(mode: str):
    """
    **Feature: usb-hid-vendor-scanner, Property 14: Mode routing correctness**
    **Validates: Requirements 7.2, 7.3**
    
    Property: For any scanner mode setting (usb_vendor or keyboard), calling
    get_nfc_input() should route to the correct implementation matching that mode.
    
    Specifically:
    - When mode is "usb_vendor", get_usb_hid_input should be called
    - When mode is "keyboard", get_nfc_input_keyboard should be called
    
    This property verifies that the routing logic correctly interprets the
    configuration and dispatches to the appropriate implementation.
    """
    # Save original mode
    original_mode = get_scanner_mode()

    try:
        # Set the test mode
        set_scanner_mode(mode)

        # Verify mode was set correctly
        current_mode = get_scanner_mode()
        assert current_mode == mode, \
            f"Mode not set correctly: expected {mode}, got {current_mode}"

        # Determine which implementation should be called
        if mode == "usb_vendor":
            target_function = 'NfcScan.get_usb_hid_input'
            other_function = 'NfcScan.get_nfc_input_keyboard'
            expected_result = f"usb_result_{mode}"
            mock_return_value = (expected_result, "success")  # USB returns tuple
        else:  # keyboard
            target_function = 'NfcScan.get_nfc_input_keyboard'
            other_function = 'NfcScan.get_usb_hid_input'
            expected_result = f"keyboard_result_{mode}"
            mock_return_value = expected_result  # Keyboard returns string

        # Mock both implementations
        with patch(target_function, new_callable=AsyncMock) as mock_target, \
             patch(other_function, new_callable=AsyncMock) as mock_other:

            mock_target.return_value = mock_return_value
            mock_other.return_value = "wrong_result"

            # Call get_nfc_input
            test_prompt = f"test prompt for {mode}"
            data, status = asyncio.run(get_nfc_input(test_prompt))

            # Verify correct implementation was called
            mock_target.assert_called_once_with(test_prompt)

            # Verify other implementation was NOT called
            mock_other.assert_not_called()

            # Verify result came from correct implementation
            assert data == expected_result, \
                f"Expected result from {mode} mode: {expected_result}, got {data}"
            assert status == "success", f"Expected status 'success', got '{status}'"

    finally:
        # Restore original mode
        set_scanner_mode(original_mode)


@given(
    st.sampled_from(["usb_vendor", "keyboard"]),
    st.text(min_size=1, max_size=100)
)
@settings(max_examples=100, deadline=None)
def test_mode_routing_with_various_prompts(mode: str, prompt: str):
    """
    **Feature: usb-hid-vendor-scanner, Property 14: Mode routing correctness**
    **Validates: Requirements 7.2, 7.3**
    
    Property: For any scanner mode and any prompt message, get_nfc_input()
    should correctly route to the appropriate implementation and pass the
    prompt message through unchanged.
    
    This verifies that routing works correctly regardless of the prompt content.
    """
    # Save original mode
    original_mode = get_scanner_mode()

    try:
        # Set the test mode
        set_scanner_mode(mode)

        # Determine which implementation should be called
        if mode == "usb_vendor":
            target_function = 'NfcScan.get_usb_hid_input'
            mock_return_value = ("test_result", "success")  # USB returns tuple
        else:  # keyboard
            target_function = 'NfcScan.get_nfc_input_keyboard'
            mock_return_value = "test_result"  # Keyboard returns string

        # Mock the target implementation
        with patch(target_function, new_callable=AsyncMock) as mock_target:
            mock_target.return_value = mock_return_value

            # Call get_nfc_input with the generated prompt
            data, status = asyncio.run(get_nfc_input(prompt))

            # Verify correct implementation was called with exact prompt
            mock_target.assert_called_once_with(prompt)

            # Verify result was returned
            assert data == "test_result", \
                f"Expected 'test_result', got '{data}'"
            assert status == "success", f"Expected status 'success', got '{status}'"

    finally:
        # Restore original mode
        set_scanner_mode(original_mode)


def test_mode_routing_fallback():
    """
    Test that invalid/unknown modes fall back to keyboard mode.
    
    This test verifies that if an invalid mode is somehow set in the
    configuration, the system gracefully falls back to keyboard mode.
    """
    print("\n=== Testing Mode Routing Fallback ===")
    
    try:
        from NfcScan import get_nfc_input
        import json
        from pathlib import Path
        
        # Save original mode
        original_mode = get_scanner_mode()
        
        try:
            # Manually set an invalid mode in the config file
            config_path = Path(scanner_config.CONFIG_FILE)
            config = load_config()
            config["scanner_mode"] = "invalid_mode"
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            print("Set invalid mode: 'invalid_mode'")
            
            # Mock the keyboard implementation (fallback)
            with patch('NfcScan.get_nfc_input_keyboard', new_callable=AsyncMock) as mock_keyboard:
                mock_keyboard.return_value = "fallback_result"
                
                # Call get_nfc_input
                data, status = asyncio.run(get_nfc_input("test prompt"))
                
                # Verify keyboard implementation was called (fallback)
                mock_keyboard.assert_called_once_with("test prompt")
                assert data == "fallback_result", \
                    f"Expected 'fallback_result', got '{data}'"
                assert status == "success", f"Expected status 'success', got '{status}'"
                print("✓ Invalid mode correctly falls back to keyboard mode")
            
            return True
            
        finally:
            # Restore original mode
            set_scanner_mode(original_mode)
            
    except ImportError as e:
        print(f"⚠ Could not import NfcScan: {e}")
        print("  Skipping fallback test")
        return True


def test_mode_routing_persistence():
    """
    Test that mode routing persists across multiple calls.
    
    This verifies that the routing decision is made fresh for each call,
    ensuring that mode changes take effect immediately.
    """
    print("\n=== Testing Mode Routing Persistence ===")
    
    try:
        from NfcScan import get_nfc_input
        
        # Save original mode
        original_mode = get_scanner_mode()
        
        try:
            # Set to USB vendor mode
            set_scanner_mode("usb_vendor")
            
            # Make multiple calls
            for i in range(3):
                with patch('NfcScan.get_usb_hid_input', new_callable=AsyncMock) as mock_usb:
                    mock_usb.return_value = (f"result_{i}", "success")
                    data, status = asyncio.run(get_nfc_input(f"prompt_{i}"))
                    mock_usb.assert_called_once_with(f"prompt_{i}")
                    assert data == f"result_{i}"
                    assert status == "success"
            
            print("✓ USB vendor mode routing persists across multiple calls")
            
            # Switch to keyboard mode
            set_scanner_mode("keyboard")
            
            # Make multiple calls
            for i in range(3):
                with patch('NfcScan.get_nfc_input_keyboard', new_callable=AsyncMock) as mock_keyboard:
                    mock_keyboard.return_value = f"result_{i}"
                    data, status = asyncio.run(get_nfc_input(f"prompt_{i}"))
                    mock_keyboard.assert_called_once_with(f"prompt_{i}")
                    assert data == f"result_{i}"
                    assert status == "success"
            
            print("✓ Keyboard mode routing persists across multiple calls")
            
            return True
            
        finally:
            # Restore original mode
            set_scanner_mode(original_mode)
            
    except ImportError as e:
        print(f"⚠ Could not import NfcScan: {e}")
        print("  Skipping persistence test")
        return True


def main():
    """Run all mode routing correctness tests"""
    print("=" * 70)
    print("Property-Based Test: Mode Routing Correctness")
    print("Feature: usb-hid-vendor-scanner, Property 14")
    print("Validates: Requirements 7.2, 7.3")
    print("=" * 70)
    
    try:
        # Run basic tests
        test_mode_routing_basic()
        test_mode_routing_fallback()
        test_mode_routing_persistence()
        
        # Run property-based tests
        print("\n=== Running Property-Based Tests ===")
        print("Testing mode routing correctness (100 examples)...")
        test_mode_routing_correctness()
        print("✓ Mode routing correctness test passed")
        
        print("\nTesting mode routing with various prompts (100 examples)...")
        test_mode_routing_with_various_prompts()
        print("✓ Prompt routing test passed")
        
        print("\n" + "=" * 70)
        print("✓ All mode routing correctness tests passed!")
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
