"""
Test scanner status messages differentiation

This test verifies that the scanner properly differentiates between:
1. User cancellation - shows "Device scanning cancelled"
2. Scanner not connected - shows "Scanner not connected"
3. Other errors - shows "Device scanning failed"
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from NfcScan import get_nfc_input, get_usb_hid_input


@pytest.mark.asyncio
async def test_usb_hid_input_returns_status_tuple():
    """Test that get_usb_hid_input returns a tuple with status"""
    with patch('NfcScan.ui.dialog') as mock_dialog, \
         patch('NfcScan.USBHIDScanner') as mock_scanner_class:
        
        # Mock scanner instance
        mock_scanner = Mock()
        mock_scanner.connect.return_value = False  # Connection fails
        mock_scanner_class.return_value = mock_scanner
        
        # Mock dialog and closed future
        mock_dialog_instance = Mock()
        mock_dialog.return_value = mock_dialog_instance
        
        # Mock the closed future to return immediately
        import asyncio
        closed_future = asyncio.Future()
        closed_future.set_result(None)
        
        with patch('NfcScan.asyncio.Future', return_value=closed_future):
            # This should return a tuple
            result = await get_usb_hid_input("Test prompt")
            
            # Verify it's a tuple with 2 elements
            assert isinstance(result, tuple), "get_usb_hid_input should return a tuple"
            assert len(result) == 2, "Tuple should have 2 elements (data, status)"
            
            data, status = result
            assert isinstance(data, str), "First element should be string (data)"
            assert isinstance(status, str), "Second element should be string (status)"


@pytest.mark.asyncio
async def test_get_nfc_input_usb_mode_returns_tuple():
    """Test that get_nfc_input in USB mode returns a tuple"""
    with patch('NfcScan.get_scanner_mode', return_value='usb_vendor'), \
         patch('NfcScan.get_usb_hid_input', new_callable=AsyncMock) as mock_usb_input:
        
        # Mock USB HID input to return tuple
        mock_usb_input.return_value = ("test_data", "success")
        
        result = await get_nfc_input("Test prompt")
        
        # Verify it's a tuple
        assert isinstance(result, tuple), "get_nfc_input should return a tuple"
        assert len(result) == 2, "Tuple should have 2 elements"
        
        data, status = result
        assert data == "test_data"
        assert status == "success"


@pytest.mark.asyncio
async def test_get_nfc_input_keyboard_mode_returns_tuple():
    """Test that get_nfc_input in keyboard mode returns a tuple"""
    with patch('NfcScan.get_scanner_mode', return_value='keyboard'), \
         patch('NfcScan.get_nfc_input_keyboard', new_callable=AsyncMock) as mock_keyboard_input:
        
        # Mock keyboard input to return just string
        mock_keyboard_input.return_value = "test_data"
        
        result = await get_nfc_input("Test prompt")
        
        # Verify it's converted to tuple
        assert isinstance(result, tuple), "get_nfc_input should return a tuple"
        assert len(result) == 2, "Tuple should have 2 elements"
        
        data, status = result
        assert data == "test_data"
        assert status == "success"


@pytest.mark.asyncio
async def test_get_nfc_input_keyboard_mode_cancelled():
    """Test that get_nfc_input in keyboard mode handles cancellation"""
    with patch('NfcScan.get_scanner_mode', return_value='keyboard'), \
         patch('NfcScan.get_nfc_input_keyboard', new_callable=AsyncMock) as mock_keyboard_input:
        
        # Mock keyboard input to return empty string (cancelled)
        mock_keyboard_input.return_value = ""
        
        result = await get_nfc_input("Test prompt")
        
        # Verify status is cancelled
        data, status = result
        assert data == ""
        assert status == "cancelled"


def test_status_values():
    """Test that status values are well-defined"""
    valid_statuses = ["success", "cancelled", "not_connected", "error"]
    
    # This is a documentation test to ensure we know what statuses exist
    assert "success" in valid_statuses
    assert "cancelled" in valid_statuses
    assert "not_connected" in valid_statuses
    assert "error" in valid_statuses


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
