"""
Test script to verify background scanner functionality in user selection dialog.

This test verifies that:
1. The user selection dialog opens correctly
2. USB HID scanner works in the background while dialog is open
3. Keyboard mode still works with focus maintenance
4. Manual selection still works
"""

import asyncio
import logging
from NfcScan import get_user_input_with_selection
from scanner_config import get_scanner_mode, set_scanner_mode
from database import SessionLocal
import crud

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_user_selection_dialog():
    """Test the user selection dialog with background scanner"""
    
    db = SessionLocal()
    
    try:
        # Get current scanner mode
        current_mode = get_scanner_mode()
        logger.info(f"Current scanner mode: {current_mode}")
        
        # Get a sample equipment for testing
        equipment_list = crud.get_available_equipment(db)
        if not equipment_list:
            logger.error("No equipment available for testing")
            return
        
        test_equipment = equipment_list[0]
        logger.info(f"Testing with equipment: {test_equipment.name}")
        
        # Test the dialog
        logger.info("Opening user selection dialog...")
        logger.info("Dialog should now be waiting for scanner input in the background")
        logger.info("You can either:")
        logger.info("  1. Scan a user code (scanner should work in background)")
        logger.info("  2. Select a user manually from the dropdown")
        logger.info("  3. Click Cancel to close")
        
        selected_user = await get_user_input_with_selection(test_equipment)
        
        if selected_user:
            logger.info(f"✓ User selected: {selected_user.name} ({selected_user.department.name})")
        else:
            logger.info("✗ User selection cancelled")
            
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    # This test needs to be run within the NiceGUI application context
    print("This test should be run from within the main application")
    print("To test manually:")
    print("1. Start the application")
    print("2. Click 'Scan to Rent'")
    print("3. Scan a device code")
    print("4. The 'Select User' dialog should appear")
    print("5. Try scanning a user code - it should work without pressing any buttons")
    print("6. Alternatively, select a user manually from the dropdown")
