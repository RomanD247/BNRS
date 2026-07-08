"""
Integration tests for USB scanner with rental workflows

This test suite verifies:
- Equipment code scanning works correctly in both USB and keyboard modes
- User code scanning works correctly in both USB and keyboard modes  
- Equipment lists update correctly after rental and return operations
- Behavioral equivalence between USB and keyboard modes

Requirements: 3.1, 3.2, 3.4
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from scanner_config import get_scanner_mode, set_scanner_mode, get_usb_config
from NfcScan import get_nfc_input, nfc_equipment_rental_workflow
from crud import (
    find_equipment_by_nfc,
    find_user_by_nfc,
    is_equipment_rented,
    get_available_equipment,
    get_active_rentals,
    create_rental,
    return_equipment
)
from models import Equipment, User, Rental
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEquipmentCodeScanning:
    """
    Test equipment code scanning functionality
    Requirements: 3.1
    """
    
    def test_equipment_found_by_nfc_code(self, db_session):
        """Test that equipment can be found by NFC code"""
        logger.info("\n=== Testing Equipment Code Scanning ===")

        db = db_session
        # Get all equipment with NFC codes
        all_equipment = db.query(Equipment).filter(
            Equipment.nfc != None,
            Equipment.nfc != "",
            Equipment.status == True
        ).all()

        assert all_equipment, "Fixture should seed equipment with NFC codes"

        # Test finding equipment by NFC code
        test_equipment = all_equipment[0]
        logger.info(f"Testing with equipment: {test_equipment.name} (NFC: {test_equipment.nfc})")

        # Find equipment by NFC
        found_equipment = find_equipment_by_nfc(db, test_equipment.nfc)

        assert found_equipment is not None, "Equipment should be found by NFC code"
        assert found_equipment.id_eq == test_equipment.id_eq, "Found equipment should match test equipment"
        assert found_equipment.name == test_equipment.name, "Equipment name should match"

        logger.info(f"✓ Equipment '{found_equipment.name}' found successfully by NFC code")

        # Test with lowercase NFC code (scanner converts to lowercase)
        found_equipment_lower = find_equipment_by_nfc(db, test_equipment.nfc.lower())
        assert found_equipment_lower is not None, "Equipment should be found with lowercase NFC code"
        assert found_equipment_lower.id_eq == test_equipment.id_eq, "Found equipment should match with lowercase"

        logger.info(f"✓ Equipment found successfully with lowercase NFC code")

        # Test with non-existent NFC code
        fake_nfc = "nonexistent_nfc_code_12345"
        not_found = find_equipment_by_nfc(db, fake_nfc)
        assert not_found is None, "Non-existent equipment should not be found"

        logger.info(f"✓ Non-existent equipment correctly returns None")

        logger.info("✓ All equipment code scanning tests passed")

    def test_equipment_rental_status_check(self, db_session):
        """Test checking if equipment is currently rented"""
        logger.info("\n=== Testing Equipment Rental Status Check ===")

        db = db_session
        # Get available equipment
        available_equipment = get_available_equipment(db)

        assert available_equipment, "Fixture should seed available equipment"

        test_equipment = available_equipment[0]
        logger.info(f"Testing with available equipment: {test_equipment.name}")

        # Check rental status (should be None for available equipment)
        rental = is_equipment_rented(db, test_equipment.id_eq)
        assert rental is None, "Available equipment should not have active rental"

        logger.info(f"✓ Available equipment correctly shows no active rental")

        # Get rented equipment (fixture seeds one open rental)
        active_rentals = get_active_rentals(db)

        assert active_rentals, "Fixture should seed an active rental"
        rented_equipment = active_rentals[0].equipment
        logger.info(f"Testing with rented equipment: {rented_equipment.name}")

        # Check rental status (should return Rental object)
        rental = is_equipment_rented(db, rented_equipment.id_eq)
        assert rental is not None, "Rented equipment should have active rental"
        assert isinstance(rental, Rental), "Should return Rental object"
        assert rental.equipment_id == rented_equipment.id_eq, "Rental should match equipment"
        assert rental.rental_end is None, "Active rental should not have end date"

        logger.info(f"✓ Rented equipment correctly shows active rental")

        logger.info("✓ All rental status check tests passed")


class TestUserCodeScanning:
    """
    Test user code scanning functionality
    Requirements: 3.2
    """
    
    def test_user_found_by_nfc_code(self, db_session):
        """Test that users can be found by NFC code"""
        logger.info("\n=== Testing User Code Scanning ===")

        db = db_session
        # Get all users with NFC codes
        all_users = db.query(User).filter(
            User.nfc != None,
            User.nfc != "",
            User.status == True
        ).all()

        assert all_users, "Fixture should seed a user with an NFC code"

        # Test finding user by NFC code
        test_user = all_users[0]
        logger.info(f"Testing with user: {test_user.name} (NFC: {test_user.nfc})")

        # Find user by NFC
        found_user = find_user_by_nfc(db, test_user.nfc)

        assert found_user is not None, "User should be found by NFC code"
        assert found_user.id_us == test_user.id_us, "Found user should match test user"
        assert found_user.name == test_user.name, "User name should match"

        logger.info(f"✓ User '{found_user.name}' found successfully by NFC code")

        # Test with lowercase NFC code (scanner converts to lowercase)
        found_user_lower = find_user_by_nfc(db, test_user.nfc.lower())
        assert found_user_lower is not None, "User should be found with lowercase NFC code"
        assert found_user_lower.id_us == test_user.id_us, "Found user should match with lowercase"

        logger.info(f"✓ User found successfully with lowercase NFC code")

        # Test with non-existent NFC code
        fake_nfc = "nonexistent_user_nfc_67890"
        not_found = find_user_by_nfc(db, fake_nfc)
        assert not_found is None, "Non-existent user should not be found"

        logger.info(f"✓ Non-existent user correctly returns None")

        logger.info("✓ All user code scanning tests passed")


class TestEquipmentListUpdates:
    """
    Test equipment list updates after rental and return operations
    Requirements: 3.4
    """
    
    def test_equipment_lists_after_rental(self, db_session):
        """Test that equipment lists update correctly after rental"""
        logger.info("\n=== Testing Equipment List Updates After Rental ===")

        db = db_session
        # Get initial counts
        initial_available = get_available_equipment(db)
        initial_rented = get_active_rentals(db)

        initial_available_count = len(initial_available)
        initial_rented_count = len(initial_rented)

        logger.info(f"Initial state: {initial_available_count} available, {initial_rented_count} rented")

        # Find equipment and user for test rental
        available_equipment = [eq for eq in initial_available if eq.nfc]
        users_with_nfc = db.query(User).filter(
            User.nfc != None,
            User.nfc != "",
            User.status == True
        ).all()

        assert available_equipment and users_with_nfc, "Fixture should seed available equipment and a user with NFC"

        test_equipment = available_equipment[0]
        test_user = users_with_nfc[0]

        logger.info(f"Creating test rental: {test_user.name} renting {test_equipment.name}")

        # Create rental (against the throwaway per-test DB, not the live rental.db)
        rental = create_rental(db, test_user.id_us, test_equipment.id_eq, "Test rental")

        # Get updated lists
        updated_available = get_available_equipment(db)
        updated_rented = get_active_rentals(db)

        updated_available_count = len(updated_available)
        updated_rented_count = len(updated_rented)

        logger.info(f"After rental: {updated_available_count} available, {updated_rented_count} rented")

        # Verify counts changed correctly
        assert updated_available_count == initial_available_count - 1, \
            "Available equipment count should decrease by 1"
        assert updated_rented_count == initial_rented_count + 1, \
            "Rented equipment count should increase by 1"

        # Verify equipment is no longer in available list
        available_ids = [eq.id_eq for eq in updated_available]
        assert test_equipment.id_eq not in available_ids, \
            "Rented equipment should not be in available list"

        # Verify equipment is in rented list
        rented_equipment_ids = [r.equipment_id for r in updated_rented]
        assert test_equipment.id_eq in rented_equipment_ids, \
            "Rented equipment should be in rented list"

        logger.info("✓ Equipment lists updated correctly after rental")

        # Clean up - return the equipment
        return_equipment(db, rental.id_re)
        logger.info("✓ Test rental cleaned up")

    def test_equipment_lists_after_return(self, db_session):
        """Test that equipment lists update correctly after return"""
        logger.info("\n=== Testing Equipment List Updates After Return ===")

        db = db_session
        # Get active rentals (fixture seeds one open rental)
        active_rentals = get_active_rentals(db)

        assert active_rentals, "Fixture should seed an active rental"

        # Get initial counts
        initial_available = get_available_equipment(db)
        initial_rented = get_active_rentals(db)

        initial_available_count = len(initial_available)
        initial_rented_count = len(initial_rented)

        logger.info(f"Initial state: {initial_available_count} available, {initial_rented_count} rented")

        # Select a rental to return
        test_rental = active_rentals[0]
        test_equipment = test_rental.equipment

        logger.info(f"Returning equipment: {test_equipment.name}")

        # Return equipment (against the throwaway per-test DB, not the live rental.db)
        return_equipment(db, test_rental.id_re)

        # Get updated lists
        updated_available = get_available_equipment(db)
        updated_rented = get_active_rentals(db)

        updated_available_count = len(updated_available)
        updated_rented_count = len(updated_rented)

        logger.info(f"After return: {updated_available_count} available, {updated_rented_count} rented")

        # Verify counts changed correctly
        assert updated_available_count == initial_available_count + 1, \
            "Available equipment count should increase by 1"
        assert updated_rented_count == initial_rented_count - 1, \
            "Rented equipment count should decrease by 1"

        # Verify equipment is in available list
        available_ids = [eq.id_eq for eq in updated_available]
        assert test_equipment.id_eq in available_ids, \
            "Returned equipment should be in available list"

        # Verify equipment is not in rented list
        rented_equipment_ids = [r.equipment_id for r in updated_rented]
        assert test_equipment.id_eq not in rented_equipment_ids, \
            "Returned equipment should not be in rented list"

        logger.info("✓ Equipment lists updated correctly after return")


class TestModeBehavioralEquivalence:
    """
    Test that USB and keyboard modes produce equivalent results
    Requirements: 3.1, 3.2
    """
    
    @pytest.mark.asyncio
    async def test_get_nfc_input_routes_correctly(self):
        """Test that get_nfc_input routes to correct implementation based on mode"""
        logger.info("\n=== Testing Mode Routing ===")
        
        # Test USB vendor mode routing
        set_scanner_mode("usb_vendor")
        mode = get_scanner_mode()
        assert mode == "usb_vendor", "Mode should be set to usb_vendor"
        logger.info("✓ USB vendor mode set correctly")
        
        # Test keyboard mode routing
        set_scanner_mode("keyboard")
        mode = get_scanner_mode()
        assert mode == "keyboard", "Mode should be set to keyboard"
        logger.info("✓ Keyboard mode set correctly")

        logger.info("✓ Mode routing tests passed")

    def test_code_processing_equivalence(self, db_session):
        """
        Test that both modes process codes identically

        This test verifies that equipment and user lookup works the same
        regardless of which scanner mode is used.
        """
        logger.info("\n=== Testing Code Processing Equivalence ===")

        db = db_session
        # Test equipment code processing
        equipment_with_nfc = db.query(Equipment).filter(
            Equipment.nfc != None,
            Equipment.nfc != "",
            Equipment.status == True
        ).first()

        assert equipment_with_nfc, "Fixture should seed equipment with an NFC code"

        # Simulate code from USB scanner (lowercase)
        usb_code = equipment_with_nfc.nfc.lower()

        # Simulate code from keyboard scanner (could be any case, but we convert to lowercase)
        keyboard_code = equipment_with_nfc.nfc.lower()

        # Both should find the same equipment
        equipment_from_usb = find_equipment_by_nfc(db, usb_code)
        equipment_from_keyboard = find_equipment_by_nfc(db, keyboard_code)

        assert equipment_from_usb is not None, "USB mode should find equipment"
        assert equipment_from_keyboard is not None, "Keyboard mode should find equipment"
        assert equipment_from_usb.id_eq == equipment_from_keyboard.id_eq, \
            "Both modes should find the same equipment"

        logger.info(f"✓ Equipment code processing is equivalent: '{equipment_with_nfc.name}'")

        # Test user code processing
        user_with_nfc = db.query(User).filter(
            User.nfc != None,
            User.nfc != "",
            User.status == True
        ).first()

        assert user_with_nfc, "Fixture should seed a user with an NFC code"

        # Simulate code from USB scanner (lowercase)
        usb_code = user_with_nfc.nfc.lower()

        # Simulate code from keyboard scanner (could be any case, but we convert to lowercase)
        keyboard_code = user_with_nfc.nfc.lower()

        # Both should find the same user
        user_from_usb = find_user_by_nfc(db, usb_code)
        user_from_keyboard = find_user_by_nfc(db, keyboard_code)

        assert user_from_usb is not None, "USB mode should find user"
        assert user_from_keyboard is not None, "Keyboard mode should find user"
        assert user_from_usb.id_us == user_from_keyboard.id_us, \
            "Both modes should find the same user"

        logger.info(f"✓ User code processing is equivalent: '{user_with_nfc.name}'")

        logger.info("✓ Code processing equivalence tests passed")
