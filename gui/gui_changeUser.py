import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nicegui import ui
import crud
from sqlalchemy.orm import Session
from database import SessionLocal
from NfcScan import get_nfc_input, generate_single_user_code_file
from native_dialogs import pick_folder_native

# Create a single DB instance
db = SessionLocal()

def edit_users_dialog():
    """
    Opens a dialog for selecting and editing users.
    """
    try:
        # Create a fresh session to ensure we get updated data
        with SessionLocal() as fresh_db:
            with ui.dialog() as dialog, ui.card().style('width: 600px; height: 800px'):
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('Select a user to edit').classes('text-h6 q-mb-md, w-540')
                    ui.button(icon='close', on_click=dialog.close).props('flat round')
                
                # Create a scroll area for the user list
                with ui.scroll_area().style('height: 750px'):
                    # Get the list of all users from the fresh DB session
                    users = crud.get_all_users_including_inactive(fresh_db)
                    # Sort users alphabetically by name
                    users = sorted(users, key=lambda x: x.name.lower())
                    

                    # Create a card for each user
                    for user in users:
                        with ui.card().classes('cursor-pointer').style('width: 100%;') as card:
                            with ui.row().classes('text-left'):
                                with ui.column():
                                    ui.icon('check_box' if user.status == True else 'check_box_outline_blank').classes(f'text-2xl {"text-green-500" if user.status else "text-red-500"}')
                                    if user.nfc:
                                        ui.icon('qr_code').classes('text-2xl text-orange-500')
                                with ui.column():
                                    ui.label(f'{user.name}').style('font-size: 110%; font-weight: bold')
                                    ui.label(f'{user.department.name}') 
                            # Separate function to create a handler for each user
                            def make_handler(u):
                                return lambda: show_edit_form_for_user(u, dialog)
                            
                            card.on('click', make_handler(user))

            # Delete the dialog element once hidden so repeated opens (this
            # dialog is rebuilt from scratch on every call, including the
            # auto-reopen after Apply) don't accumulate detached DOM nodes
            # forever (unbounded-dialog-accumulation).
            dialog.on('hide', dialog.delete)
            dialog.open()
        
    except Exception as e:
        ui.notify(f'Error opening user list: {str(e)}', color='negative')
        print(f"Error in edit_users_dialog: {str(e)}")  # for debugging


def show_edit_form_for_user(user, parent_dialog=None):
    """
    Creates and shows the user edit form.
    
    Args:
        user: User object to edit
        parent_dialog: Parent dialog that opened this form
    """
    try:
        # Create a fresh session to get updated data
        with SessionLocal() as fresh_db:
            # Get data with fresh session
            departments = crud.get_all_departments_including_inactive(fresh_db)
            
            # Get fresh user data
            fresh_user = crud.get_user_including_inactive(fresh_db, user.id_us)
            if not fresh_user:
                ui.notify(f'User no longer exists in database', color='negative')
                if parent_dialog:
                    parent_dialog.close()
                return
            
            # Create variables to store changes
            name_value = fresh_user.name
            department_value = fresh_user.department.name
            status_value = fresh_user.status
            nfc_value = fresh_user.nfc
            # Captured separately from nfc_value (M14) - lets apply_changes
            # tell "admin re-scanned a new code" apart from "left it untouched".
            original_nfc = fresh_user.nfc
            nfc_label = None

            def refresh_nfc_label():
                has_code = bool(nfc_value) and nfc_value != crud.CLEAR_NFC
                nfc_label.content = (
                    '<i class="material-icons" font-weight=bold style="color: green;">check_box</i> <b>Code scanned</b>'
                    if has_code else
                    '<i class="material-icons" font-weight=bold style="color: red;">check_box_outline_blank</i> <b>Pass: Not set</b>'
                )

            async def scan_nfc():
                nonlocal nfc_value
                scanned_value, scan_status = await get_nfc_input("Scan Data Matrix Code")
                if scan_status != "success":
                    # Cancelled/error - leave the existing code untouched
                    # instead of falsely showing "Not set" (cancelled-scan-code-lie).
                    refresh_nfc_label()
                    return
                scanned_value = scanned_value.lower()
                # Check if this NFC code is already taken by another user
                # (M3: includes soft-deleted users)
                existing_user = crud.find_user_by_nfc_including_inactive(fresh_db, scanned_value)
                if existing_user and existing_user.id_us != fresh_user.id_us:
                    ui.notify(f'Data Matrix Code already registered to user {existing_user.name}', type='warning')
                    refresh_nfc_label()
                    return
                nfc_value = scanned_value
                refresh_nfc_label()

            def clear_code():
                nonlocal nfc_value
                nfc_value = crud.CLEAR_NFC
                refresh_nfc_label()

            async def download_qr_code():
                if not fresh_user.nfc:
                    ui.notify('User has no NFC code saved', type='warning')
                    return

                directory = await pick_folder_native()

                if not directory:
                    return

                success, message = generate_single_user_code_file(fresh_user.id_us, directory)
                if success:
                    ui.notify(f'QR code saved: {message}', type='positive')
                else:
                    ui.notify(f'Failed to save QR code: {message}', type='negative')

            # Use dialog directly
            with ui.dialog() as edit_dialog, ui.card().classes('w-96'):
                ui.label(f'Editing user: {fresh_user.name}').classes('text-h6 q-mb-md')
                
                # Name edit field
                name_input = ui.input('Name', value=name_value).classes('w-full q-mb-sm')
                
                # Department selection dropdown
                department_select = ui.select(
                    label='Department',
                    options=[dept.name for dept in departments],
                    value=department_value
                ).classes('w-full q-mb-sm')
                
                # Status switch
                with ui.row().classes('items-center q-mb-md'):
                    ui.label('Status (active):')
                    status_switch = ui.switch('', value=status_value)
                
                # NFC scanning section
                ui.separator()
                with ui.row().classes('w-full justify-between items-center q-mb-md'):
                    with ui.row():
                        ui.button('Scan Data Matrix Code', on_click=scan_nfc)
                        ui.button('Clear code', on_click=clear_code).props('flat')
                        if fresh_user.nfc:
                            ui.button(icon='download', on_click=download_qr_code).props('flat round').tooltip('Download QR Code')
                    nfc_label = ui.html('<i class="material-icons" font-weight=bold style="color: green;">check_box</i> <b>Code scanned</b>' if nfc_value else '<i class="material-icons" font-weight=bold style="color: red;">check_box_outline_blank</i> <b>Pass: Not set</b>')

                with ui.row().classes('justify-end'):
                    ui.button('Cancel', on_click=edit_dialog.close).classes('q-mr-sm')
                    ui.button('Apply', on_click=lambda: apply_changes(
                        fresh_user.id_us,
                        name_input.value,
                        department_select.value,
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
        
    except Exception as e:
        ui.notify(f'Error opening edit form: {str(e)}', color='negative')
        print(f"Error in show_edit_form_for_user: {str(e)}")  # for debugging


# This function is no longer used directly
def open_edit_form(user, parent_dialog):
    """
    Deprecated function, use show_edit_form_for_user instead
    """
    try:
        parent_dialog.close()
        show_edit_form_for_user(user)
    except Exception as e:
        ui.notify(f'Error: {str(e)}', color='negative')


def apply_changes(user_id, new_name, new_department, new_status, nfc_value, original_nfc, dialog, parent_dialog=None):
    """
    Applies changes to the user in the database.

    Args:
        user_id: User ID
        new_name: New user name
        new_department: New department name
        new_status: New user status
        nfc_value: NFC value as left by the dialog (unchanged unless the admin
            re-scanned, or crud.CLEAR_NFC if the admin clicked "Clear code")
        original_nfc: The user's nfc value when the dialog was opened (M14 - detects a re-scan)
        dialog: Dialog to close after saving
        parent_dialog: Parent dialog to close if needed
    """
    try:
        # Create a new session for this operation
        with SessionLocal() as session:
            # Resync the Data Matrix payload (M14) if name/department changed
            # and the admin didn't re-scan a new code - otherwise the stored
            # nfc keeps encoding the OLD name/department forever, and printed
            # labels silently stop matching what "Update codes" would generate.
            final_nfc = nfc_value
            code_needs_reprint = False
            current_user = crud.get_user_including_inactive(session, user_id)
            if current_user and original_nfc and nfc_value == original_nfc:
                current_department_name = current_user.department.name if current_user.department else None
                if new_name != current_user.name or new_department != current_department_name:
                    department = crud.get_department_by_name_including_inactive(session, new_department)
                    if department:
                        # Mirrors MatrixCode.py's update_user_codes() formula exactly.
                        final_nfc = f"{user_id}_{new_name}_{department.id_dep}".lower()
                        code_needs_reprint = True

            # Update user with new session
            updated_user = crud.update_user(session, user_id, name=new_name, dep=new_department, status=new_status, nfc=final_nfc, get_user_func=crud.get_user_including_inactive)

            if updated_user:
                ui.notify(f'User {new_name} successfully updated', color='positive')
                if code_needs_reprint:
                    ui.notify(
                        "This user's Data Matrix code label is now out of date - regenerate and reprint it.",
                        color='warning', close_button='OK', timeout=0
                    )
                dialog.close()

                # If parent dialog exists, close it too
                if parent_dialog:
                    parent_dialog.close()

                # Reopen the user list with refreshed data
                ui.timer(0.1, edit_users_dialog, once=True)
            else:
                ui.notify('Failed to update user - user not found', color='negative')
    except Exception as e:
        ui.notify(f'Error during update: {str(e)}', color='negative')
        print(f"Error in apply_changes: {str(e)}")  # for debugging



