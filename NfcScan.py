from nicegui import ui
from collections import deque
import asyncio
from sqlalchemy.orm import Session
import crud
from models import User, Equipment, Rental
from database import SessionLocal

db = SessionLocal()

async def get_nfc_input(prompt_message: str) -> str:
    """
    Opens a dialog box with a prompt and returns the text entered by the user after pressing Enter.

    Args:
        prompt_message: Message displayed in the dialog box.

    Returns:
        Text entered by the user (string).
    """
    result = ""
    all_keys = deque()
    dialog = ui.dialog()
    closed = asyncio.Future()

    def on_key(e):
        nonlocal result
        if not e.action.keyup:
            return

        key_str = str(e.key)

        if e.key == 'Enter':
            result = "".join(list(all_keys))
            keyboard.active = False
            dialog.close()
            closed.set_result(None)  # Unlock waiting
            return

        if len(key_str) == 1 and key_str.isprintable():
            all_keys.append(key_str)
            print("Typed: ", "".join(all_keys))

    def close_dialog():
        keyboard.active = False
        dialog.close()
        closed.set_result(None) # Unlock waiting even when closing without Enter

    with dialog, ui.card():
        ui.label(prompt_message)
        input_display = ui.label()

        def update_display():
            input_display.text = "".join(list(all_keys))

        #ui.timer(0.1, update_display, active=True) # Update input display

        ui.button('Close', on_click=close_dialog)

        keyboard = ui.keyboard(on_key)
        keyboard.active = True

    dialog.open()
    await closed  # Wait until dialog is closed (via Enter or button)
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
        # Get user NFC
        user_nfc = await get_nfc_input("Scan your pass")
        user_nfc = user_nfc.lower()
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

