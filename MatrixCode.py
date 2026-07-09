#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MatrixCode Module - NFC Code Management

This module provides functions for updating NFC codes for users and equipment
in the rental system database.
"""

from models import User, Equipment
from database import SessionLocal


def update_user_codes():
    """
    Updates NFC codes for all users.
    
    Generates NFC codes in format: id_us_name_id_dep (in lowercase)
    Skips users with missing required data (name or id_dep)
    Overwrites existing NFC codes with new values
    
    Returns:
        dict: {
            'success': bool,
            'updated_count': int,
            'message': str,
            'error': str | None
        }
    """
    # Uses the shared engine from database.py (matrixcode-engine-leak) instead
    # of creating a new one per call that was never disposed.
    session = SessionLocal()

    try:
        # Get all users from users table
        users = session.query(User).all()
        updated_count = 0
        
        for user in users:
            # Check for required fields (name, id_dep)
            if user.name and user.id_dep:
                # Generate NFC code in format id_us_name_id_dep in lowercase
                nfc_code = f"{user.id_us}_{user.name}_{user.id_dep}".lower()
                
                # Update nfc field (overwrite existing values)
                user.nfc = nfc_code
                updated_count += 1
        
        # Save changes to database
        session.commit()
        
        return {
            'success': True,
            'updated_count': updated_count,
            'message': f'Successfully updated {updated_count} user NFC codes',
            'error': None
        }
        
    except Exception as e:
        # Handle exceptions and rollback transactions
        session.rollback()
        return {
            'success': False,
            'updated_count': 0,
            'message': 'Error updating user NFC codes',
            'error': str(e)
        }
        
    finally:
        # Close database session
        session.close()

def update_equipment_codes():
    """
    Updates NFC codes for all equipment.
    
    Generates NFC codes in format: id_eq_name_serialnum (in lowercase)
    Skips equipment with missing required data (name or serialnum)
    Overwrites existing NFC codes with new values
    
    Returns:
        dict: {
            'success': bool,
            'updated_count': int,
            'message': str,
            'error': str | None
        }
    """
    # Uses the shared engine from database.py (matrixcode-engine-leak) instead
    # of creating a new one per call that was never disposed.
    session = SessionLocal()

    try:
        # Get all equipment from equipment table
        equipment_items = session.query(Equipment).all()
        updated_count = 0
        
        for equipment in equipment_items:
            # Check for required fields (name, serialnum)
            if equipment.name and equipment.serialnum:
                # Generate NFC code in format id_eq_name_serialnum in lowercase
                nfc_code = f"{equipment.id_eq}_{equipment.name}_{equipment.serialnum}".lower()
                
                # Update nfc field (overwrite existing values)
                equipment.nfc = nfc_code
                updated_count += 1
        
        # Save changes to database
        session.commit()
        
        return {
            'success': True,
            'updated_count': updated_count,
            'message': f'Successfully updated {updated_count} equipment NFC codes',
            'error': None
        }
        
    except Exception as e:
        # Handle exceptions and rollback transactions
        session.rollback()
        return {
            'success': False,
            'updated_count': 0,
            'message': 'Error updating equipment NFC codes',
            'error': str(e)
        }
        
    finally:
        # Close database session
        session.close()