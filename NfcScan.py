from nicegui import ui
from collections import deque
import asyncio
from sqlalchemy.orm import Session
import crud
from models import User, Equipment, Rental
from database import SessionLocal
from smartcard.System import readers
from smartcard.util import toHexString
import time
from smartcard.Exceptions import CardConnectionException, NoCardException

db = SessionLocal()
scanning_active = False  # Global flag to control card scanning

def get_card_uid():
    """
    Reads UID from a card using CCID reader
    
    Returns:
        Card UID as string or None if no card detected
    """
    try:
        rdrs = readers()
        if not rdrs:
            print("No PC/SC readers found")
            return None
            
        reader = rdrs[0]
        conn = reader.createConnection()
        conn.connect()
        
        # Command to get UID
        GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        data, sw1, sw2 = conn.transmit(GET_UID)
        
        if sw1 == 0x90 and sw2 == 0x00:
            uid = toHexString(data).replace(' ', '').lower()  # Convert to lowercase
            print("Card UID:", uid)
            conn.disconnect()
            return uid
        
        conn.disconnect()
        return None
    except (CardConnectionException, NoCardException):
        return None
    except Exception as e:
        print(f"Error reading card: {str(e)}")
        return None

async def get_nfc_input(prompt_message: str) -> str:
    """
    Opens a dialog box with a prompt and waits for NFC card to be scanned.

    Args:
        prompt_message: Message displayed in the dialog box.

    Returns:
        Card UID as string.
    """
    global scanning_active
    result = ""
    dialog = ui.dialog()
    closed = asyncio.Future()
    stop_scanning = False

    async def scan_card():
        nonlocal result, stop_scanning
        scanning_active = True  # Enable card scanning
        print("Scanning started")  # Debug print
        
        while not stop_scanning:
            uid = get_card_uid()
            if uid:
                result = uid
                input_display.text = "✓ Card scanned successfully"
                input_display.style('color: green')
                await asyncio.sleep(1)  # Show success message for 1 second
                stop_scanning = True  # Stop scanning after successful scan
                dialog.close()
                closed.set_result(None)
                break
            await asyncio.sleep(0.1)  # Reduced sleep time for more responsive scanning

    def close_dialog():
        nonlocal stop_scanning
        stop_scanning = True
        scanning_active = False  # Disable card scanning when dialog is closed
        dialog.close()
        closed.set_result(None)

    with dialog, ui.card().style('width: 350px;'):
        with ui.row().classes('w-full justify-center items-center'):
            ui.label(prompt_message).style('font-size: 24px; font-weight: bold; text-align: center')
            #ui.button(icon='close', on_click=close_dialog).props('flat round')
        with ui.separator():
            pass
        input_display = ui.label("Waiting for scan...").classes('w-full justify-center items-center').style('font-size: 16px; text-align: center')
        
        # Start the card scanning task
        asyncio.create_task(scan_card())

    dialog.open()
    await closed  # Wait until dialog is closed (via card scan or cancel button)
    scanning_active = False  # Ensure scanning is disabled after dialog closes
    return result

async def nfc_equipment_rental_workflow(update_callback=None):
    """
    Process of creating a new rental or returning equipment using NFC:
    1. Equipment scanning
    2. Checking equipment rental status
    3. If rented - return, if not - continue rental process:
       3.1. Scanning user pass
       3.2. Confirming rental and creating record
       
    Args:
        update_callback: Callback function for updating equipment lists
    """
    if db is None:
        ui.notify("Database connection error", color="negative")
        return
    
    # Get equipment NFC
    equipment_nfc = await get_nfc_input("Scan device")
    if not equipment_nfc:
        ui.notify("Device scanning cancelled", color="warning")
        return
    
    # Find equipment by NFC
    equipment = crud.find_equipment_by_nfc(db, equipment_nfc)
    if not equipment:
        ui.notify(f"Equipment not found", color="negative")
        #ui.notify(f"Equipment with NFC {equipment_nfc} not found", color="negative") #for debug
        return
    
    # Check if equipment is already rented
    rental = crud.is_equipment_rented(db, equipment.id_eq)
    
    if rental:
        # Equipment is already rented, show return dialog
        dialog = ui.dialog()
        confirmed = asyncio.Future()
        
        def on_confirm():
            crud.return_equipment(db, rental.id_re)
            ui.notify('Equipment successfully returned', color="positive")
            dialog.close()
            confirmed.set_result(True)
            # Update equipment lists after return
            if update_callback:
                update_callback()
        
        def on_cancel():
            dialog.close()
            confirmed.set_result(False)
        
        with dialog, ui.card():
            with ui.row().classes('w-full justify-between items-center'):
                ui.label(text='Equipment Return').style('font-size: 200%')
                ui.button(icon='close', on_click=on_cancel).props('flat round')
            with ui.separator():
                pass

            with ui.row().classes('w-full justify-between items-center'):
                ui.label(f"{equipment.name}").style('font-weight: bold; font-size: 16px')
                ui.label(f"{equipment.etype.name if equipment.etype else 'Unknown'}")
            with ui.separator():
                pass
            ui.html(f"Rented by: <b>{rental.user.name}</b>")
            ui.label(f"Department: {rental.user.department.name}")
            ui.label(f"Rented since: {rental.rental_start.strftime('%Y-%m-%d %H:%M')}")
            with ui.separator():
                pass
            if rental.comment:
                ui.label("Comment:").style('margin-top: 10px; font-weight: bold')
                ui.label(rental.comment).style('white-space: pre-wrap')
            
            ui.button('Confirm Return', on_click=on_confirm).props('unelevated color=primary')
        
        dialog.open()
        await confirmed
        
    else:
        # Equipment is not rented, continue rental process
        # Show message before scanning user card
        # dialog = ui.dialog()
        # with dialog, ui.card():
        #     #ui.label("Equipment scanned successfully").style('color: green; font-size: 16px')
        #     ui.label("Please scan user card").style('margin-top: 10px')
        # dialog.open()
        # await asyncio.sleep(1)  # Wait for 1 second
        # dialog.close()  # Close the success dialog
        
        # Get user NFC
        user_nfc = await get_nfc_input("Scan your pass")
        if not user_nfc:
            ui.notify("Pass scanning cancelled", color="warning")
            return
        
        # Find user by NFC
        user = crud.find_user_by_nfc(db, user_nfc)
        if not user:
            ui.notify(f"User not found", color="negative")
            #ui.notify(f"User with NFC {user_nfc} not found", color="negative") #for debug
            return
        
        # Show confirmation dialog
        dialog = ui.dialog()
        confirmed = asyncio.Future()
        
        comment_text = ""
        
        def on_confirm():
            dialog.close()
            confirmed.set_result(True)
        
        def on_cancel():
            dialog.close()
            confirmed.set_result(False)
        
        def on_comment_change(e):
            nonlocal comment_text
            comment_text = e.value
        
        with dialog, ui.card():
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Rental Confirmation').style('font-size: 200%')
                ui.button(icon='close', on_click=on_cancel).props('flat round')
            
            with ui.separator():
                pass

            ui.label('User:').style('font-weight: bold; font-size: 16px')
            ui.label(f"{user.name}").style('font-weight: bold')
            ui.label(f"Department: {user.department.name}")

            with ui.separator():
                pass
            
            ui.label('Equipment:').style('font-weight: bold; font-size: 16px')
            with ui.row().classes('w-full justify-between items-center'):
                ui.label(f"{equipment.name}").style('font-weight: bold')
                ui.label(f"{equipment.etype.name if equipment.etype else 'Not specified'}")
            ui.label(f"S/N: {equipment.serialnum or 'Not specified'}")


            with ui.separator():
                pass
                
            ui.input('Comment (optional)', on_change=on_comment_change).style('width: 100%')
            
            ui.button('Confirm Rental', on_click=on_confirm).props('unelevated color=primary')
        
        dialog.open()
        
        # Wait for confirmation result
        result = await confirmed
        
        if result:
            try:
                # Create rental record
                rental = crud.create_rental(db, user.id_us, equipment.id_eq, comment_text)
                ui.notify("Rental successfully created", color="positive")
                # Update equipment lists after rental
                if update_callback:
                    update_callback()
            except Exception as e:
                ui.notify(f"Error creating rental: {str(e)}", color="negative")
        else:
            ui.notify("Operation cancelled", color="warning")

