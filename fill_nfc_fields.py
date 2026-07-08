#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script for filling NFC fields in users and equipment tables.

Fill logic:
- For users: nfc = id_us_name_id_dep (all in lowercase)
- For equipment: nfc = id_eq_name_serialnum (all in lowercase)
- Always rewrites existing NFC data to reflect current names/serials
"""

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import User, Equipment, Base
from database import DATABASE_URL

def fill_nfc_fields():
    """Fills NFC fields for users and equipment."""
    
    # Create database connection
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        print("Starting NFC fields filling...")
        
        # Fill NFC for users
        print("\n1. Updating NFC fields for users...")
        users = session.query(User).all()
        users_updated = 0
        
        for user in users:
            if user.name and user.id_dep:
                # Always update NFC field (rewrite current data)
                old_nfc = user.nfc or "not set"
                # Format: id_us_name_id_dep (all in lowercase)
                nfc_value = f"{user.id_us}_{user.name}_{user.id_dep}".lower()
                user.nfc = nfc_value
                users_updated += 1
                print(f"   User ID {user.id_us}: {user.name} -> NFC: {nfc_value} (was: {old_nfc})")
            else:
                print(f"   Skipped user ID {user.id_us}: missing required data")
        
        # Fill NFC for equipment
        print(f"\n2. Updating NFC fields for equipment...")
        equipment_items = session.query(Equipment).all()
        equipment_updated = 0
        
        for equipment in equipment_items:
            if equipment.name and equipment.serialnum:
                # Always update NFC field (rewrite current data)
                old_nfc = equipment.nfc or "not set"
                # Format: id_eq_name_serialnum (all in lowercase)
                nfc_value = f"{equipment.id_eq}_{equipment.name}_{equipment.serialnum}".lower()
                equipment.nfc = nfc_value
                equipment_updated += 1
                print(f"   Equipment ID {equipment.id_eq}: {equipment.name} -> NFC: {nfc_value} (was: {old_nfc})")
            else:
                print(f"   Skipped equipment ID {equipment.id_eq}: missing required data")
        
        # Save changes
        session.commit()
        
        print(f"\n✅ Update completed successfully!")
        print(f"   - Updated users: {users_updated}")
        print(f"   - Updated equipment items: {equipment_updated}")
        
    except Exception as e:
        print(f"\n❌ Error during update: {e}")
        session.rollback()
        
    finally:
        session.close()

def preview_nfc_fields():
    """Preview of what NFC values will be set."""
    
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        print("=== NFC FIELDS PREVIEW ===")
        
        # Preview for users
        print("\n📋 Users:")
        users = session.query(User).all()
        
        for user in users:
            if user.name and user.id_dep:
                nfc_value = f"{user.id_us}_{user.name}_{user.id_dep}".lower()
                current_nfc = user.nfc or "not set"
                print(f"   ID {user.id_us}: {user.name} (department: {user.id_dep}) - WILL BE UPDATED")
                print(f"      Current NFC: {current_nfc}")
                print(f"      New NFC: {nfc_value}")
                print()
            else:
                print(f"   ID {user.id_us}: {user.name} - SKIPPED (no data)")
        
        # Preview for equipment
        print("\n🔧 Equipment:")
        equipment_items = session.query(Equipment).all()
        
        for equipment in equipment_items:
            if equipment.name and equipment.serialnum:
                nfc_value = f"{equipment.id_eq}_{equipment.name}_{equipment.serialnum}".lower()
                current_nfc = equipment.nfc or "not set"
                print(f"   ID {equipment.id_eq}: {equipment.name} (serial: {equipment.serialnum}) - WILL BE UPDATED")
                print(f"      Current NFC: {current_nfc}")
                print(f"      New NFC: {nfc_value}")
                print()
            else:
                print(f"   ID {equipment.id_eq}: {equipment.name} - SKIPPED (no data)")
                
    except Exception as e:
        print(f"❌ Error during preview: {e}")
        
    finally:
        session.close()

if __name__ == "__main__":
    print("NFC Fields Fill Script")
    print("=" * 40)
    
    while True:
        print("\nSelect action:")
        print("1. Preview")
        print("2. Fill NFC fields")
        print("3. Exit")
        
        choice = input("\nEnter number (1-3): ").strip()
        
        if choice == "1":
            preview_nfc_fields()
        elif choice == "2":
            confirm = input("\nAre you sure you want to update NFC fields? (yes/no): ").strip().lower()
            if confirm in ["yes", "y"]:
                fill_nfc_fields()
            else:
                print("Operation cancelled.")
        elif choice == "3":
            print("Exiting program.")
            break
        else:
            print("Invalid choice. Please try again.")