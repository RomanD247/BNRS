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
    Opens a dialog box with a prompt and waits for keyboard input (virtual keyboard scanner).

    Args:
        prompt_message: Message displayed in the dialog box.

    Returns:
        Scanned data as string.
    """
    result = ""
    dialog = ui.dialog()
    closed = asyncio.Future()

    def on_input_submit():
        nonlocal result
        if input_field.value.strip():
            result = input_field.value.strip().lower()
            dialog.close()
            closed.set_result(None)

    def on_cancel():
        dialog.close()
        closed.set_result(None)

    def on_input_change(e):
        # Update display when input changes
        if input_field.value:
            display_label.text = f"Scanning: {input_field.value}"
        else:
            display_label.text = "Ready to scan..."

    with dialog, ui.card().style('width: 350px;'):
        with ui.row().classes('w-full justify-center items-center'):
            ui.label(prompt_message).style('font-size: 24px; font-weight: bold; text-align: center')
        with ui.separator():
            pass
        
        display_label = ui.label("Ready to scan...").classes('w-full justify-center items-center').style('font-size: 16px; text-align: center; margin: 20px 0;')
        
        # Invisible input field that maintains focus
        input_field = ui.input().style('position: absolute; top: -1000px; left: -1000px;').props('autofocus')
        input_field.on('keydown.enter', on_input_submit)
        input_field.on('input', on_input_change)
        
        with ui.row().classes('w-full justify-end'):
            ui.button('Cancel', on_click=on_cancel).props('flat')

    dialog.open()
    
    # Aggressive focus maintenance
    async def maintain_focus():
        while not closed.done():
            await asyncio.sleep(0.1)
            if not closed.done():
                input_field.run_method('focus')
    
    asyncio.create_task(maintain_focus())
    
    await closed  # Wait until dialog is closed
    return result

async def get_user_input_with_selection():
    """
    Shows dialog that simultaneously waits for NFC input (virtual keyboard) 
    and provides manual user selection from dropdown
    
    Returns:
        User object or None if cancelled
    """
    dialog = ui.dialog()
    result = asyncio.Future()
    selected_user = None
    nfc_input_value = ""
    
    def on_cancel():
        dialog.close()
        result.set_result(None)
    
    def on_manual_select():
        if selected_user:
            dialog.close()
            result.set_result(selected_user)
        else:
            ui.notify("Please select a user", color="warning")
    
    def on_user_select_change(e):
        nonlocal selected_user
        if e.value in users_dict:
            selected_user = users_dict[e.value]
        else:
            selected_user = None
    
    def on_nfc_input_submit():
        nonlocal nfc_input_value
        if nfc_input_field.value.strip():
            nfc_input_value = nfc_input_field.value.strip().lower()
            # Find user by NFC
            user = crud.find_user_by_nfc(db, nfc_input_value)
            if user:
                dialog.close()
                result.set_result(user)
            else:
                ui.notify("User not found", color="negative")
                nfc_input_field.set_value("")
                nfc_display_label.text = "Ready to scan..."
    
    def on_nfc_input_change(e):
        # Update display when input changes
        if nfc_input_field.value:
            nfc_display_label.text = f"Scanning: {nfc_input_field.value}"
        else:
            nfc_display_label.text = "Ready to scan..."
    
    # Get all users for dropdown
    users = crud.get_all_users(db)
    users_dict = {}
    options = []
    
    for user in sorted(users, key=lambda x: x.name):
        display_text = f"{user.name} ({user.department.name})"
        users_dict[display_text] = user
        options.append(display_text)
    
    with dialog, ui.card().style('width: 450px;'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('Select User').style('font-size: 150%')
            ui.button(icon='close', on_click=on_cancel).props('flat round')
        
        ui.separator()
        
        # NFC scanning section
        ui.label('Scan Data Matrix Code:').style('font-weight: bold; margin: 10px 0 5px 0;')
        nfc_display_label = ui.label("Ready to scan...").style('font-size: 16px; text-align: center; margin: 5px 0; padding: 10px; border: 1px dashed #ccc; border-radius: 4px;')
        
        # Invisible input field for NFC scanning
        nfc_input_field = ui.input().style('position: absolute; top: -1000px; left: -1000px;').props('autofocus')
        nfc_input_field.on('keydown.enter', on_nfc_input_submit)
        nfc_input_field.on('input', on_nfc_input_change)
        
        ui.separator()
        ui.label('OR').classes('text-center').style('margin: 10px 0;')
        ui.separator()
        
        # Manual selection section
        ui.label('Select from list:').style('font-weight: bold; margin: 10px 0 5px 0;')
        user_select = ui.select(
            options=options,
            label='Select user',
            with_input=True,
            on_change=on_user_select_change
        ).style('width: 100%; margin: 5px 0;')
        
        ui.button('Confirm Selection', on_click=on_manual_select).style('width: 100%; margin: 5px 0;')
    
    dialog.open()
    
    # Aggressive focus maintenance for NFC input
    async def maintain_focus():
        while not result.done():
            await asyncio.sleep(0.1)
            if not result.done():
                nfc_input_field.run_method('focus')
    
    asyncio.create_task(maintain_focus())
    
    # Wait for user choice
    choice = await result
    return choice

async def get_user_selection():
    """
    Shows dialog for user selection - either by NFC scan or manual selection from dropdown
    
    Returns:
        User object or None if cancelled
    """
    dialog = ui.dialog()
    result = asyncio.Future()
    selected_user = None
    
    def on_cancel():
        dialog.close()
        result.set_result(None)
    
    def on_nfc_scan():
        dialog.close()
        result.set_result("nfc_scan")
    
    def on_manual_select():
        if selected_user:
            dialog.close()
            result.set_result(selected_user)
        else:
            ui.notify("Please select a user", color="warning")
    
    def on_user_select_change(e):
        nonlocal selected_user
        if e.value in users_dict:
            selected_user = users_dict[e.value]
        else:
            selected_user = None
    
    # Get all users for dropdown
    users = crud.get_all_users(db)
    users_dict = {}
    options = []
    
    for user in sorted(users, key=lambda x: x.name):
        display_text = f"{user.name} ({user.department.name})"
        users_dict[display_text] = user
        options.append(display_text)
    
    with dialog, ui.card().style('width: 400px;'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('Select User').style('font-size: 150%')
            ui.button(icon='close', on_click=on_cancel).props('flat round')
        
        ui.separator()
        
        ui.label('Choose how to identify the user:').style('margin: 10px 0;')
        
        # NFC scan option
        with ui.row().classes('w-full items-center'):
            ui.button('Scan Data Matrix Code', icon='qr_code', on_click=on_nfc_scan).style('width: 100%; margin: 5px 0;')
        
        ui.separator()
        ui.label('OR').classes('text-center').style('margin: 10px 0;')
        ui.separator()
        
        # Manual selection option
        ui.label('Select from list:').style('margin: 10px 0;')
        user_select = ui.select(
            options=options,
            label='Select user',
            with_input=True,
            on_change=on_user_select_change
        ).style('width: 100%; margin: 5px 0;')
        
        ui.button('Confirm Selection', on_click=on_manual_select).style('width: 100%; margin: 5px 0;')
    
    dialog.open()
    
    # Wait for user choice
    choice = await result
    
    if choice == "nfc_scan":
        # Proceed with NFC scanning
        user_nfc = await get_nfc_input("Scan your pass")
        if not user_nfc:
            return None
        
        # Find user by NFC
        user = crud.find_user_by_nfc(db, user_nfc)
        if not user:
            ui.notify(f"User not found", color="negative")
            return None
        
        return user
    elif choice:
        # User was selected manually
        return choice
    else:
        # Cancelled
        return None

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
        # Show user input dialog (simultaneous NFC scan and manual selection)
        user = await get_user_input_with_selection()
        if not user:
            ui.notify("User selection cancelled", color="warning")
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

