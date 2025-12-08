"""
Property-Based Test for GUI Configuration Persistence

Feature: usb-hid-vendor-scanner, Property 17: GUI configuration persistence
Validates: Requirements 8.4, 8.5

This test verifies that device selections made through the GUI configuration
dialog are properly persisted to the configuration file and used for subsequent
scanner connections.
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
import scanner_config
from usb_hid_scanner import USBHIDScanner


# Store original config file path
ORIGINAL_CONFIG_FILE = scanner_config.CONFIG_FILE


def setup_test_config():
    """Set up a temporary configuration file for testing"""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    temp_config = os.path.join(temp_dir, "test_scanner_config.json")
    
    # Point scanner_config to use the temporary file
    scanner_config.CONFIG_FILE = temp_config
    
    return temp_dir, temp_config


def teardown_test_config(temp_dir):
    """Clean up temporary configuration"""
    # Restore original config file path
    scanner_config.CONFIG_FILE = ORIGINAL_CONFIG_FILE
    
    # Remove temporary directory
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


def test_basic_config_persistence():
    """
    Basic test to verify that configuration changes persist to file.
    """
    print("\n=== Testing Basic Configuration Persistence ===")
    
    temp_dir, temp_config = setup_test_config()
    
    try:
        # Set a specific VID/PID
        test_vid = 1234
        test_pid = 5678
        
        print(f"Setting VID={test_vid}, PID={test_pid}")
        success = scanner_config.update_usb_config(vid=test_vid, pid=test_pid)
        assert success, "Failed to update USB config"
        
        # Verify file was created
        assert os.path.exists(temp_config), "Configuration file was not created"
        print("✓ Configuration file created")
        
        # Load configuration from file
        with open(temp_config, 'r') as f:
            saved_config = json.load(f)
        
        # Verify VID/PID were saved
        assert saved_config["usb_vendor"]["vid"] == test_vid, \
            f"VID not saved correctly: expected {test_vid}, got {saved_config['usb_vendor']['vid']}"
        assert saved_config["usb_vendor"]["pid"] == test_pid, \
            f"PID not saved correctly: expected {test_pid}, got {saved_config['usb_vendor']['pid']}"
        
        print(f"✓ VID/PID persisted correctly: {test_vid}/{test_pid}")
        
        # Reload configuration (simulates app restart)
        loaded_config = scanner_config.load_config()
        assert loaded_config["usb_vendor"]["vid"] == test_vid, \
            "VID not loaded correctly after reload"
        assert loaded_config["usb_vendor"]["pid"] == test_pid, \
            "PID not loaded correctly after reload"
        
        print("✓ Configuration reloaded correctly")
        
        return True
        
    finally:
        teardown_test_config(temp_dir)


def test_mode_persistence():
    """
    Test that scanner mode changes persist to file.
    """
    print("\n=== Testing Mode Persistence ===")
    
    temp_dir, temp_config = setup_test_config()
    
    try:
        # Set mode to keyboard
        print("Setting mode to 'keyboard'")
        success = scanner_config.set_scanner_mode("keyboard")
        assert success, "Failed to set scanner mode"
        
        # Verify file was created
        assert os.path.exists(temp_config), "Configuration file was not created"
        
        # Load configuration from file
        with open(temp_config, 'r') as f:
            saved_config = json.load(f)
        
        # Verify mode was saved
        assert saved_config["scanner_mode"] == "keyboard", \
            f"Mode not saved correctly: expected 'keyboard', got {saved_config['scanner_mode']}"
        
        print("✓ Mode persisted correctly: keyboard")
        
        # Reload configuration
        loaded_mode = scanner_config.get_scanner_mode()
        assert loaded_mode == "keyboard", \
            f"Mode not loaded correctly: expected 'keyboard', got {loaded_mode}"
        
        print("✓ Mode reloaded correctly")
        
        # Switch to usb_vendor
        print("Setting mode to 'usb_vendor'")
        success = scanner_config.set_scanner_mode("usb_vendor")
        assert success, "Failed to set scanner mode"
        
        # Reload and verify
        loaded_mode = scanner_config.get_scanner_mode()
        assert loaded_mode == "usb_vendor", \
            f"Mode not loaded correctly: expected 'usb_vendor', got {loaded_mode}"
        
        print("✓ Mode change persisted correctly: usb_vendor")
        
        return True
        
    finally:
        teardown_test_config(temp_dir)


@given(
    vid=st.integers(min_value=1, max_value=65535),
    pid=st.integers(min_value=1, max_value=65535)
)
@settings(max_examples=100, deadline=None)
def test_vid_pid_persistence_property(vid: int, pid: int):
    """
    **Feature: usb-hid-vendor-scanner, Property 17: GUI configuration persistence**
    **Validates: Requirements 8.4, 8.5**
    
    Property: For any valid VID and PID values selected through the GUI
    (simulated by update_usb_config), those values should persist to the
    configuration file and be loaded correctly on subsequent reads.
    
    This property verifies that:
    1. Valid VID/PID values are saved to the configuration file
    2. The saved values can be loaded back correctly
    3. The persistence survives a configuration reload
    """
    temp_dir, temp_config = setup_test_config()
    
    try:
        # Simulate GUI device selection by updating USB config
        success = scanner_config.update_usb_config(vid=vid, pid=pid)
        assert success, f"Failed to update USB config with VID={vid}, PID={pid}"
        
        # Verify configuration file exists
        assert os.path.exists(temp_config), \
            "Configuration file was not created after update"
        
        # Load configuration from file directly
        with open(temp_config, 'r') as f:
            saved_config = json.load(f)
        
        # Verify VID/PID were saved correctly
        saved_vid = saved_config["usb_vendor"]["vid"]
        saved_pid = saved_config["usb_vendor"]["pid"]
        
        assert saved_vid == vid, \
            f"VID not persisted correctly: expected {vid}, got {saved_vid}"
        assert saved_pid == pid, \
            f"PID not persisted correctly: expected {pid}, got {saved_pid}"
        
        # Reload configuration (simulates app restart or config refresh)
        loaded_config = scanner_config.load_config()
        loaded_vid = loaded_config["usb_vendor"]["vid"]
        loaded_pid = loaded_config["usb_vendor"]["pid"]
        
        assert loaded_vid == vid, \
            f"VID not loaded correctly after reload: expected {vid}, got {loaded_vid}"
        assert loaded_pid == pid, \
            f"PID not loaded correctly after reload: expected {pid}, got {loaded_pid}"
        
        # Verify get_usb_config() returns the persisted values
        usb_config = scanner_config.get_usb_config()
        assert usb_config["vid"] == vid, \
            f"get_usb_config() returned wrong VID: expected {vid}, got {usb_config['vid']}"
        assert usb_config["pid"] == pid, \
            f"get_usb_config() returned wrong PID: expected {pid}, got {usb_config['pid']}"
        
    finally:
        teardown_test_config(temp_dir)


@given(
    mode=st.sampled_from(["usb_vendor", "keyboard"])
)
@settings(max_examples=100, deadline=None)
def test_mode_persistence_property(mode: str):
    """
    **Feature: usb-hid-vendor-scanner, Property 17: GUI configuration persistence**
    **Validates: Requirements 8.4, 8.5**
    
    Property: For any valid scanner mode selected through the GUI
    (simulated by set_scanner_mode), that mode should persist to the
    configuration file and be loaded correctly on subsequent reads.
    
    This property verifies that:
    1. Valid mode values are saved to the configuration file
    2. The saved mode can be loaded back correctly
    3. The persistence survives a configuration reload
    """
    temp_dir, temp_config = setup_test_config()
    
    try:
        # Simulate GUI mode selection
        success = scanner_config.set_scanner_mode(mode)
        assert success, f"Failed to set scanner mode to {mode}"
        
        # Verify configuration file exists
        assert os.path.exists(temp_config), \
            "Configuration file was not created after mode change"
        
        # Load configuration from file directly
        with open(temp_config, 'r') as f:
            saved_config = json.load(f)
        
        # Verify mode was saved correctly
        saved_mode = saved_config["scanner_mode"]
        assert saved_mode == mode, \
            f"Mode not persisted correctly: expected {mode}, got {saved_mode}"
        
        # Reload configuration (simulates app restart or config refresh)
        loaded_mode = scanner_config.get_scanner_mode()
        assert loaded_mode == mode, \
            f"Mode not loaded correctly after reload: expected {mode}, got {loaded_mode}"
        
    finally:
        teardown_test_config(temp_dir)


@given(
    vid=st.integers(min_value=1, max_value=65535),
    pid=st.integers(min_value=1, max_value=65535),
    mode=st.sampled_from(["usb_vendor", "keyboard"])
)
@settings(max_examples=100, deadline=None)
def test_combined_config_persistence_property(vid: int, pid: int, mode: str):
    """
    **Feature: usb-hid-vendor-scanner, Property 17: GUI configuration persistence**
    **Validates: Requirements 8.4, 8.5**
    
    Property: For any valid combination of VID, PID, and mode selected through
    the GUI, all values should persist together to the configuration file and
    be loaded correctly on subsequent reads.
    
    This property verifies that:
    1. Multiple configuration changes persist together
    2. No configuration value is lost when others are updated
    3. All values survive a configuration reload
    """
    temp_dir, temp_config = setup_test_config()
    
    try:
        # Simulate GUI configuration: set VID/PID
        success_usb = scanner_config.update_usb_config(vid=vid, pid=pid)
        assert success_usb, f"Failed to update USB config"
        
        # Simulate GUI configuration: set mode
        success_mode = scanner_config.set_scanner_mode(mode)
        assert success_mode, f"Failed to set scanner mode"
        
        # Verify configuration file exists
        assert os.path.exists(temp_config), \
            "Configuration file was not created"
        
        # Load configuration from file directly
        with open(temp_config, 'r') as f:
            saved_config = json.load(f)
        
        # Verify all values were saved correctly
        assert saved_config["usb_vendor"]["vid"] == vid, \
            f"VID not persisted: expected {vid}, got {saved_config['usb_vendor']['vid']}"
        assert saved_config["usb_vendor"]["pid"] == pid, \
            f"PID not persisted: expected {pid}, got {saved_config['usb_vendor']['pid']}"
        assert saved_config["scanner_mode"] == mode, \
            f"Mode not persisted: expected {mode}, got {saved_config['scanner_mode']}"
        
        # Reload configuration (simulates app restart)
        loaded_config = scanner_config.load_config()
        
        # Verify all values loaded correctly
        assert loaded_config["usb_vendor"]["vid"] == vid, \
            f"VID not loaded correctly: expected {vid}, got {loaded_config['usb_vendor']['vid']}"
        assert loaded_config["usb_vendor"]["pid"] == pid, \
            f"PID not loaded correctly: expected {pid}, got {loaded_config['usb_vendor']['pid']}"
        assert loaded_config["scanner_mode"] == mode, \
            f"Mode not loaded correctly: expected {mode}, got {loaded_config['scanner_mode']}"
        
    finally:
        teardown_test_config(temp_dir)


def test_invalid_vid_pid_handling():
    """
    Test that invalid VID/PID values are rejected and defaults are used.
    This ensures the GUI validation works correctly.
    """
    print("\n=== Testing Invalid VID/PID Handling ===")
    
    temp_dir, temp_config = setup_test_config()
    
    try:
        # Test invalid VID (negative) - should use default 4602
        print("Testing invalid VID (negative)")
        scanner_config.update_usb_config(vid=-1, pid=1000)
        
        # Read directly from file to see what was saved
        with open(temp_config, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config["usb_vendor"]["vid"] == 4602, \
            f"Invalid VID should be rejected and default used, got {saved_config['usb_vendor']['vid']}"
        assert saved_config["usb_vendor"]["pid"] == 1000, \
            f"Valid PID should be saved, got {saved_config['usb_vendor']['pid']}"
        print("✓ Negative VID rejected, default used")
        
        # Test invalid VID (too large) - should use default 4602
        print("Testing invalid VID (too large)")
        scanner_config.update_usb_config(vid=70000, pid=2000)
        
        with open(temp_config, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config["usb_vendor"]["vid"] == 4602, \
            f"Invalid VID should be rejected and default used, got {saved_config['usb_vendor']['vid']}"
        assert saved_config["usb_vendor"]["pid"] == 2000, \
            f"Valid PID should be saved, got {saved_config['usb_vendor']['pid']}"
        print("✓ Too large VID rejected, default used")
        
        # Test invalid PID (zero) - should use default 33282
        print("Testing invalid PID (zero)")
        scanner_config.update_usb_config(vid=3000, pid=0)
        
        with open(temp_config, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config["usb_vendor"]["vid"] == 3000, \
            f"Valid VID should be saved, got {saved_config['usb_vendor']['vid']}"
        assert saved_config["usb_vendor"]["pid"] == 33282, \
            f"Invalid PID should be rejected and default used, got {saved_config['usb_vendor']['pid']}"
        print("✓ Zero PID rejected, default used")
        
        # Test invalid PID (too large) - should use default 33282
        print("Testing invalid PID (too large)")
        scanner_config.update_usb_config(vid=4000, pid=100000)
        
        with open(temp_config, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config["usb_vendor"]["vid"] == 4000, \
            f"Valid VID should be saved, got {saved_config['usb_vendor']['vid']}"
        assert saved_config["usb_vendor"]["pid"] == 33282, \
            f"Invalid PID should be rejected and default used, got {saved_config['usb_vendor']['pid']}"
        print("✓ Too large PID rejected, default used")
        
        return True
        
    finally:
        teardown_test_config(temp_dir)


def test_gui_workflow_simulation():
    """
    Simulate a complete GUI workflow:
    1. User opens scanner config dialog
    2. User selects a device from the list
    3. User saves the configuration
    4. Configuration persists and is used for next connection
    """
    print("\n=== Testing Complete GUI Workflow Simulation ===")
    
    temp_dir, temp_config = setup_test_config()
    
    try:
        # Step 1: Load initial configuration (dialog opens)
        print("Step 1: Opening scanner configuration dialog")
        initial_config = scanner_config.load_config()
        initial_vid = initial_config["usb_vendor"]["vid"]
        initial_pid = initial_config["usb_vendor"]["pid"]
        print(f"  Initial config: VID={initial_vid}, PID={initial_pid}")
        
        # Step 2: User selects a device (simulated)
        print("Step 2: User selects a device")
        selected_vid = 5678
        selected_pid = 1234
        print(f"  Selected device: VID={selected_vid}, PID={selected_pid}")
        
        # Step 3: User clicks "Save Configuration"
        print("Step 3: User saves configuration")
        success = scanner_config.update_usb_config(vid=selected_vid, pid=selected_pid)
        assert success, "Failed to save configuration"
        print("  ✓ Configuration saved")
        
        # Step 4: Verify persistence (simulates closing and reopening dialog)
        print("Step 4: Verifying persistence (dialog reopened)")
        reloaded_config = scanner_config.load_config()
        reloaded_vid = reloaded_config["usb_vendor"]["vid"]
        reloaded_pid = reloaded_config["usb_vendor"]["pid"]
        
        assert reloaded_vid == selected_vid, \
            f"VID not persisted: expected {selected_vid}, got {reloaded_vid}"
        assert reloaded_pid == selected_pid, \
            f"PID not persisted: expected {selected_pid}, got {reloaded_pid}"
        
        print(f"  ✓ Configuration persisted: VID={reloaded_vid}, PID={reloaded_pid}")
        
        # Step 5: Verify the persisted config would be used for scanner connection
        print("Step 5: Verifying config used for scanner connection")
        usb_config = scanner_config.get_usb_config()
        assert usb_config["vid"] == selected_vid, \
            "Persisted VID not returned by get_usb_config()"
        assert usb_config["pid"] == selected_pid, \
            "Persisted PID not returned by get_usb_config()"
        print("  ✓ Persisted config would be used for scanner connection")
        
        print("\n✓ Complete GUI workflow simulation passed")
        return True
        
    finally:
        teardown_test_config(temp_dir)


def main():
    """Run all GUI configuration persistence tests"""
    print("=" * 70)
    print("Property-Based Test: GUI Configuration Persistence")
    print("Feature: usb-hid-vendor-scanner, Property 17")
    print("Validates: Requirements 8.4, 8.5")
    print("=" * 70)
    
    try:
        # Run basic tests
        test_basic_config_persistence()
        test_mode_persistence()
        test_invalid_vid_pid_handling()
        test_gui_workflow_simulation()
        
        # Run property-based tests
        print("\n=== Running Property-Based Tests ===")
        
        print("\nTesting VID/PID persistence property (100 examples)...")
        test_vid_pid_persistence_property()
        print("✓ VID/PID persistence property test passed")
        
        print("\nTesting mode persistence property (100 examples)...")
        test_mode_persistence_property()
        print("✓ Mode persistence property test passed")
        
        print("\nTesting combined config persistence property (100 examples)...")
        test_combined_config_persistence_property()
        print("✓ Combined config persistence property test passed")
        
        print("\n" + "=" * 70)
        print("✓ All GUI configuration persistence tests passed!")
        print("=" * 70)
        
        return True
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
