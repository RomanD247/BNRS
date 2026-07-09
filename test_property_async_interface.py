"""
Property-Based Test for Async Interface Compatibility

Feature: usb-hid-vendor-scanner, Property 9: Async interface compatibility
Validates: Requirements 3.5

This test verifies that get_nfc_input() maintains the same async interface
regardless of scanner mode (usb_vendor or keyboard).
"""

import asyncio
import inspect
from hypothesis import given, strategies as st, settings
from scanner_config import get_scanner_mode, set_scanner_mode
from NfcScan import get_nfc_input


def test_async_interface_signature():
    """
    Test that get_nfc_input maintains correct async function signature
    regardless of mode.

    This is a basic test to ensure the function exists and has the right signature.
    """
    print("\n=== Testing Async Interface Signature ===")

    # Verify function is async
    assert inspect.iscoroutinefunction(get_nfc_input), \
        "get_nfc_input must be an async function (coroutine)"
    print("✓ get_nfc_input is an async function")

    # Verify function signature
    sig = inspect.signature(get_nfc_input)
    params = list(sig.parameters.keys())

    assert len(params) == 1, \
        f"get_nfc_input must have exactly 1 parameter, got {len(params)}"
    assert params[0] == "prompt_message", \
        f"Parameter must be named 'prompt_message', got '{params[0]}'"
    print("✓ Function signature is correct: async def get_nfc_input(prompt_message: str)")

    # Verify return annotation (if present)
    return_annotation = sig.return_annotation
    if return_annotation != inspect.Signature.empty:
        # The function now returns tuple[str, str] for (data, status)
        assert str(return_annotation) == 'tuple[str, str]', \
            f"Return type should be tuple[str, str], got {return_annotation}"
        print("✓ Return type annotation is correct: tuple[str, str]")


@given(st.sampled_from(["usb_vendor", "keyboard"]))
@settings(max_examples=100, deadline=None)
def test_async_interface_compatibility_across_modes(mode: str):
    """
    **Feature: usb-hid-vendor-scanner, Property 9: Async interface compatibility**
    **Validates: Requirements 3.5**

    Property: For any scanner mode (usb_vendor or keyboard), get_nfc_input()
    must maintain the same async interface - it must be a coroutine function
    with the same signature.

    This property verifies that:
    1. The function is always async (coroutine function)
    2. The function signature remains consistent across modes
    3. The function accepts a prompt_message parameter
    4. The function returns an awaitable that resolves to a string
    """
    # Save original mode
    original_mode = get_scanner_mode()

    try:
        # Set the test mode
        set_scanner_mode(mode)

        # Verify the function is still async
        assert inspect.iscoroutinefunction(get_nfc_input), \
            f"get_nfc_input must be async in {mode} mode"

        # Verify signature remains consistent
        sig = inspect.signature(get_nfc_input)
        params = list(sig.parameters.keys())

        assert len(params) == 1, \
            f"get_nfc_input must have 1 parameter in {mode} mode, got {len(params)}"
        assert params[0] == "prompt_message", \
            f"Parameter must be 'prompt_message' in {mode} mode, got '{params[0]}'"

        # Verify the function can be called and returns a coroutine
        # We don't actually await it since that would require UI interaction
        result = get_nfc_input("test prompt")
        assert inspect.iscoroutine(result), \
            f"get_nfc_input must return a coroutine in {mode} mode"

        # Clean up the coroutine to avoid warnings
        result.close()

    finally:
        # Restore original mode
        set_scanner_mode(original_mode)


@given(st.text(min_size=1, max_size=100))
@settings(max_examples=100, deadline=None)
def test_async_interface_accepts_various_prompts(prompt_message: str):
    """
    **Feature: usb-hid-vendor-scanner, Property 9: Async interface compatibility**
    **Validates: Requirements 3.5**

    Property: For any valid prompt message string, get_nfc_input() must accept
    it as a parameter and return a coroutine without raising an exception.

    This verifies that the interface is stable across different input strings.
    """
    # Call the function with the generated prompt
    # We don't await it since that would require UI interaction
    result = get_nfc_input(prompt_message)

    # Verify it returns a coroutine
    assert inspect.iscoroutine(result), \
        f"get_nfc_input must return a coroutine for prompt: {prompt_message[:50]}"

    # Clean up the coroutine
    result.close()


def test_async_interface_mode_independence():
    """
    Test that the async interface is independent of mode switching.

    This test verifies that switching modes multiple times doesn't break
    the async interface.
    """
    print("\n=== Testing Async Interface Mode Independence ===")

    # Save original mode
    original_mode = get_scanner_mode()

    try:
        modes = ["usb_vendor", "keyboard", "usb_vendor", "keyboard"]

        for mode in modes:
            set_scanner_mode(mode)

            # Verify function is still async
            assert inspect.iscoroutinefunction(get_nfc_input), \
                f"get_nfc_input must remain async after switching to {mode}"

            # Verify it returns a coroutine
            result = get_nfc_input("test")
            assert inspect.iscoroutine(result), \
                f"get_nfc_input must return coroutine in {mode} mode"
            result.close()

            print(f"✓ Async interface maintained in {mode} mode")

        print("✓ Async interface is independent of mode switching")

    finally:
        # Restore original mode
        set_scanner_mode(original_mode)


def main():
    """Run all async interface compatibility tests"""
    print("=" * 70)
    print("Property-Based Test: Async Interface Compatibility")
    print("Feature: usb-hid-vendor-scanner, Property 9")
    print("Validates: Requirements 3.5")
    print("=" * 70)

    try:
        # Run basic signature test
        test_async_interface_signature()

        # Run mode independence test
        test_async_interface_mode_independence()

        # Run property-based tests
        print("\n=== Running Property-Based Tests ===")
        print("Testing async interface across different modes (100 examples)...")
        test_async_interface_compatibility_across_modes()
        print("✓ Async interface compatibility test passed")

        print("\nTesting async interface with various prompts (100 examples)...")
        test_async_interface_accepts_various_prompts()
        print("✓ Prompt acceptance test passed")

        print("\n" + "=" * 70)
        print("✓ All async interface compatibility tests passed!")
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
    # Standalone script mode: no pytest, so conftest.py's autouse
    # isolated_scanner_config fixture never runs - redirect CONFIG_FILE
    # ourselves so this invocation (up to 100x via the hypothesis-decorated
    # tests in main()) can't rewrite the live scanner_config.json
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
