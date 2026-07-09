import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nicegui import ui
import crud
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Equipment
from NfcScan import get_nfc_input, generate_single_equipment_code_file
from native_dialogs import pick_folder_native

# Create a single DB instance
db = SessionLocal()

def edit_equipment_dialog():
    """
    Opens a dialog for selecting and editing equipment.
    """
    try:
        # Create a fresh session to ensure we get updated data
        with SessionLocal() as fresh_db:
            with ui.dialog() as dialog, ui.card().style('width: 600px; height: 800px'):
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('Select equipment to edit').classes('text-h6 q-mb-md, w-540')
                    ui.button(icon='close', on_click=dialog.close).props('flat round')
                
                # Create a scroll area for the equipment list
                with ui.scroll_area().style('height: 750px'):
                    # Get the list of all equipment from the fresh DB session
                    equipment_list = crud.get_all_equipment_including_inactive(fresh_db)
                    
                    # Create a card for each equipment
                    for equipment in equipment_list:
                        with ui.card().classes('cursor-pointer').style('width: 100%;') as card:
                            with ui.row().classes('text-left'):
                                with ui.column():
                                    ui.icon('check_box' if equipment.status == True else 'check_box_outline_blank').classes(f'text-2xl {"text-green-500" if equipment.status else "text-red-500"}')
                                    if equipment.nfc:
                                            ui.icon('qr_code').classes('text-2xl text-orange-500')
                                with ui.column():
                                    ui.label(f'Name: {equipment.name}').classes('text-weight-bold').style('margin-top: -10px')
                                    ui.label(f'S/N: {equipment.serialnum}').style('margin-top: -10px')
                                    ui.label(f'Type: {equipment.etype.name if equipment.etype else "Unknown"}').style('margin-top: -10px; margin-bottom: -10px')
                            
                            # Separate function to create a handler for each equipment
                            def make_handler(eq):
                                return lambda: show_edit_form_for_equipment(eq, dialog)
                            
                            card.on('click', make_handler(equipment))

            # Delete the dialog element once hidden so repeated opens (this
            # dialog is rebuilt from scratch on every call, including the
            # auto-reopen after Apply) don't accumulate detached DOM nodes
            # forever (unbounded-dialog-accumulation).
            dialog.on('hide', dialog.delete)
            dialog.open()
        
    except Exception as e:
        ui.notify(f'Error opening the equipment list: {str(e)}', color='negative')
        print(f"Error in edit_equipment_dialog: {str(e)}")  # for debugging


def show_edit_form_for_equipment(equipment, parent_dialog=None):
    """
    Creates and shows the equipment edit form.
    
    Args:
        equipment: Equipment object to edit
        parent_dialog: Parent dialog that opened this form
    """
    try:
        # Create a fresh session to get updated data
        with SessionLocal() as fresh_db:
            # Get fresh equipment data
            fresh_equipment = fresh_db.query(Equipment).filter(Equipment.id_eq == equipment.id_eq).first()
            
            # Get all equipment types for the dropdown
            etypes = crud.get_all_etypes_including_inactive(fresh_db)
            
            # Create variables to store changes
            name_value = fresh_equipment.name
            serialnum_value = fresh_equipment.serialnum
            etype_value = fresh_equipment.etype.name if fresh_equipment.etype else None
            status_value = fresh_equipment.status
            nfc_value = fresh_equipment.nfc
            # Captured separately from nfc_value (M14) - lets apply_changes
            # tell "admin re-scanned a new code" apart from "left it untouched".
            original_nfc = fresh_equipment.nfc
            nfc_label = None

            def refresh_nfc_label():
                has_code = bool(nfc_value) and nfc_value != crud.CLEAR_NFC
                nfc_label.content = (
                    '<i class="material-icons" font-weight=bold style="color: green;">check_box</i> <b>NFC Tag scanned</b>'
                    if has_code else
                    '<i class="material-icons" font-weight=bold style="color: red;">check_box_outline_blank</i> <b>NFC Tag: Not set</b>'
                )

            async def scan_nfc():
                nonlocal nfc_value
                scanned_value, scan_status = await get_nfc_input("Scan NFC Tag")
                if scan_status != "success":
                    # Cancelled/error - leave the existing code untouched
                    # instead of falsely showing "Not set" (cancelled-scan-code-lie).
                    refresh_nfc_label()
                    return
                scanned_value = scanned_value.lower()
                # Check if this NFC code is already taken by another equipment
                # (M3: includes soft-deleted equipment)
                existing_equipment = crud.find_equipment_by_nfc_including_inactive(fresh_db, scanned_value)
                if existing_equipment and existing_equipment.id_eq != fresh_equipment.id_eq:
                    ui.notify(f'NFC Tag already registered to equipment {existing_equipment.name}', type='warning')
                    refresh_nfc_label()
                    return
                nfc_value = scanned_value
                refresh_nfc_label()

            def clear_code():
                nonlocal nfc_value
                nfc_value = crud.CLEAR_NFC
                refresh_nfc_label()

            async def download_qr_code():
                if not fresh_equipment.nfc:
                    ui.notify('Equipment has no NFC code saved', type='warning')
                    return

                directory = await pick_folder_native()

                if not directory:
                    return

                success, message = generate_single_equipment_code_file(fresh_equipment.id_eq, directory)
                if success:
                    ui.notify(f'QR code saved: {message}', type='positive')
                else:
                    ui.notify(f'Failed to save QR code: {message}', type='negative')
            
            # Use dialog directly
            with ui.dialog() as edit_dialog, ui.card().classes('w-96'):
                ui.label(f'Editing equipment: {fresh_equipment.name}').classes('text-h6 q-mb-md')
                
                # Name edit field
                name_input = ui.input('Name', value=name_value).classes('w-full q-mb-sm')
                
                # Serial number edit field
                serialnum_input = ui.input('Serial Number', value=serialnum_value).classes('w-full q-mb-sm')
                
                # Equipment type selection dropdown
                etype_options = [et.name for et in etypes]
                etype_select = ui.select(
                    label='Equipment Type',
                    options=etype_options,
                    value=etype_value
                ).classes('w-full q-mb-sm')
                
                # Status switch
                with ui.row().classes('items-center q-mb-md'):
                    ui.label('Status (active):')
                    status_switch = ui.switch('', value=status_value)
                
                # NFC scanning section
                ui.separator()
                with ui.row().classes('w-full justify-between items-center q-mb-md'):
                    with ui.row():
                        ui.button('Scan NFC Tag', on_click=scan_nfc)
                        ui.button('Clear code', on_click=clear_code).props('flat')
                        if fresh_equipment.nfc:
                            ui.button(icon='download', on_click=download_qr_code).props('flat round').tooltip('Download QR Code')
                    nfc_label = ui.html('<i class="material-icons" font-weight=bold style="color: green;">check_box</i> <b>NFC Tag scanned</b>' if nfc_value else '<i class="material-icons" font-weight=bold style="color: red;">check_box_outline_blank</i> <b>NFC Tag: Not set</b>')
                
                with ui.row().classes('justify-end'):
                    ui.button('Cancel', on_click=edit_dialog.close).classes('q-mr-sm')
                    ui.button('Apply', on_click=lambda: apply_changes(
                        fresh_equipment.id_eq,
                        name_input.value,
                        serialnum_input.value,
                        etype_select.value,
                        status_switch.value,
                        nfc_value,
                        original_nfc,
                        edit_dialog,
                        parent_dialog
                    )).classes('bg-primary')
                    
            # Delete the dialog element once hidden (unbounded-dialog-accumulation)
            edit_dialog.on('hide', edit_dialog.delete)
            # Open the new dialog
            edit_dialog.open()
            #ui.notify(f'Edit form opened for equipment: {fresh_equipment.name}', color='positive')
        
    except Exception as e:
        ui.notify(f'Error opening the edit form: {str(e)}', color='negative')
        print(f"Error in show_edit_form_for_equipment: {str(e)}")  # for debugging


def apply_changes(equipment_id, new_name, new_serialnum, new_etype, new_status, nfc_value, original_nfc, dialog, parent_dialog=None):
    """
    Applies changes to the equipment in the database.

    Args:
        equipment_id: Equipment ID
        new_name: New equipment name
        new_serialnum: New serial number
        new_etype: New equipment type name
        new_status: New equipment status
        nfc_value: NFC value as left by the dialog (unchanged unless the admin
            re-scanned, or crud.CLEAR_NFC if the admin clicked "Clear code")
        original_nfc: The equipment's nfc value when the dialog was opened (M14 - detects a re-scan)
        dialog: Dialog to close after saving
        parent_dialog: Parent dialog to close if needed
    """
    try:
        # Create a new session for this operation
        with SessionLocal() as session:
            # Get the equipment first to verify it exists
            equipment = session.query(Equipment).filter(Equipment.id_eq == equipment_id).first()

            if not equipment:
                ui.notify('Failed to update equipment - equipment not found', color='negative')
                return

            # Get the equipment type ID
            etype = crud.get_etype_by_name(session, new_etype)
            if not etype:
                ui.notify(f'Equipment type {new_etype} not found', color='negative')
                return

            # Block deactivating equipment that's currently rented (M6) -
            # bypasses crud.delete_equipment's own guard since this dialog
            # flips `status` directly via the ORM.
            if new_status is False and equipment.status is True and crud.is_equipment_rented(session, equipment_id):
                ui.notify(f'Cannot deactivate "{equipment.name}": it is currently rented. Return it first.', color='negative')
                return

            # Resync the Data Matrix payload (M14) if a code-bearing field
            # changed and the admin didn't re-scan a new code - otherwise the
            # stored nfc keeps encoding the OLD name/serial forever, and
            # printed labels silently stop matching what "Update codes" would
            # generate. Skip if serialnum is blank, mirroring MatrixCode.py's
            # own skip for equipment with no serial number.
            final_nfc = nfc_value
            code_needs_reprint = False
            if original_nfc and nfc_value == original_nfc and new_serialnum:
                if new_name != equipment.name or new_serialnum != equipment.serialnum:
                    # Mirrors MatrixCode.py's update_equipment_codes() formula exactly.
                    final_nfc = f"{equipment_id}_{new_name}_{new_serialnum}".lower()
                    code_needs_reprint = True

            # Update equipment with new values
            equipment.name = new_name
            equipment.serialnum = new_serialnum
            equipment.etype_id = etype.id_et
            equipment.status = new_status

            # Update NFC value
            if final_nfc is not None:
                if final_nfc == crud.CLEAR_NFC:
                    # Explicit clear (cancelled-scan-code-lie): a real NULL,
                    # never '' - two cleared units would collide on the
                    # nfc UNIQUE constraint otherwise.
                    equipment.nfc = None
                elif final_nfc:
                    # Check if this NFC code is already taken by another equipment
                    # (M3: includes soft-deleted equipment)
                    existing_equipment = crud.find_equipment_by_nfc_including_inactive(session, final_nfc)
                    if existing_equipment and existing_equipment.id_eq != equipment_id:
                        ui.notify(f'NFC code already registered to equipment {existing_equipment.name}', color='negative')
                        return
                    equipment.nfc = final_nfc

            session.commit()

            ui.notify(f'Equipment {new_name} successfully updated', color='positive')
            if code_needs_reprint:
                ui.notify(
                    "This equipment's Data Matrix code label is now out of date - regenerate and reprint it.",
                    color='warning', close_button='OK', timeout=0
                )
            dialog.close()

            # If parent dialog exists, close it too
            if parent_dialog:
                parent_dialog.close()

            # Reopen the equipment list with refreshed data
            ui.timer(0.1, edit_equipment_dialog, once=True)
    except Exception as e:
        ui.notify(f'Error updating: {str(e)}', color='negative')
        print(f"Error in apply_changes: {str(e)}")  # for debugging