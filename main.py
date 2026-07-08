import sys

if __name__ == "__main__" and "--web-viewer" in sys.argv:
    # The frozen onefile exe has no bundled python.exe to Popen a raw .py
    # file with, so the viewer subprocess (spawned further below) re-invokes
    # this same exe/script with this flag instead of the viewer script path.
    # A frozen build's bundled web_viewer/ unpacks into sys._MEIPASS (a temp
    # extraction dir), not next to the exe - unlike APP_DIR-anchored live
    # state (rental.db, scanner_config.json), it's pure code, never seeded
    # into APP_DIR, so it must be read from _MEIPASS here.
    import os
    import runpy
    _viewer_dir = getattr(sys, "_MEIPASS", "") if getattr(sys, "frozen", False) \
        else os.path.dirname(os.path.abspath(__file__))
    runpy.run_path(os.path.join(_viewer_dir, "web_viewer", "viewer_app.py"), run_name="__main__")
    sys.exit(0)

from nicegui import native, ui, run
from gui.gui_adduser import show_add_user_dialog, show_add_department_dialog, refresh_departments
from gui.gui_addequip import show_add_equipment_dialog
from gui.gui_changeUser import edit_users_dialog
from gui.gui_changeDep import edit_departments_dialog
from gui.gui_changeEtype import edit_etypes_dialog
from gui.gui_changeEquip import edit_equipment_dialog
from gui.gui_changeRental import edit_rentals_dialog
from gui.gui_reports import get_user_report_button, get_equipment_report_button, get_equipment_name_report_button, show_rental_history, get_department_report_button, get_feedback_button
from gui.gui_scanner_config import show_scanner_config_dialog
from NfcScan import nfc_equipment_rental_workflow, get_nfc_input, generate_all_users_codes, generate_all_equipment_codes
from MatrixCode import update_user_codes, update_equipment_codes
from scanner_logging import setup_logging

import asyncio
import os
import time
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import (
    get_available_equipment, get_all_users, create_rental,
    get_active_rentals, return_equipment, get_all_etypes,
    get_available_equipment_by_type, get_active_rentals_by_equipment_type,
    create_feedback, find_user_by_nfc, update_user_nfc, is_equipment_rented
)
from database import SessionLocal, APP_DIR
from models import User

db = SessionLocal()

VERSION = "2.1.5"

# Global containers for lists
available_container = None
rented_container = None

# NiceGUI's native mode re-invokes this module in further descendant
# processes an unbounded/uncertain number of times (confirmed empirically -
# each generation re-runs ui.run(native=True), which spawns another native
# window process). An in-memory flag can't survive that since each generation
# is a separate OS process; an env var does, since child processes inherit
# the parent's environment - so this is checked/set by the viewer-launch
# block below to guarantee the viewer subprocess is only started once no
# matter how deep the reimport chain goes, and read by main() (which may run
# in any generation) to render a status label consistent across all of them.
VIEWER_STARTED_ENV_VAR = "BNRS_VIEWER_STARTED"
VIEWER_LAN_IP_ENV_VAR = "BNRS_VIEWER_LAN_IP"


def _get_lan_ip() -> str:
    """Best-effort discovery of this machine's LAN IP, for the viewer status label."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return 'localhost'

# Create reactive state
class State:
    def __init__(self):
        self.available_equipment = get_available_equipment(db)
        self.rented_equipment = get_active_rentals(db)
        self.users = get_all_users(db)
        self.selected_etype_id = None
        self.etype_map = {}
        self.etypes = get_all_etypes(db)
        self.filter_select = None
        self.name_filter = ""
        self.name_filter_input = None
    
    def refresh_users(self):
        """Updates the list of users from the database"""
        self.users = get_all_users(db)
        return self.users
    
    def refresh_etypes(self):
        """Updates the list of equipment types from the database"""
        self.etypes = get_all_etypes(db)
        
        # Rebuild etype_map
        self.etype_map = {}
        for etype in self.etypes:
            self.etype_map[etype.name] = etype.id_et
            
        return self.etypes
    
    def update_filter_select(self):
        """Updates the equipment type filter dropdown"""
        # First, update the list of types from the database
        self.refresh_etypes()
        
        if self.filter_select:
            etype_options = [etype.name for etype in self.etypes]
            self.filter_select.options = etype_options
            self.filter_select.update()
            ui.notify('Equipment type filter updated.')
    
    def set_name_filter(self, filter_text):
        """Set the name filter and update the filter state"""
        self.name_filter = filter_text.lower().strip() if filter_text else ""

state = State()

# Dark Mode
dark_mode = ui.dark_mode()
def toggle_dark_mode(button):
    dark_mode.value = not dark_mode.value
    if dark_mode.value:
        button.props('icon=light_mode')
    else:
        button.props('icon=dark_mode')

def create_equipment_card(equipment, is_rented=False):
    """Create a card for equipment display"""
    card = ui.card().style('width: 450px; height: 75px; cursor: pointer;')
    
    with card:
        if is_rented:
            with ui.row().classes('w-full justify-between items-center').style('margin-top: -10px'):
                ui.label(f"{equipment.equipment.name}").style('font-size: 18px; font-weight: bold')
                ui.label(f"{equipment.equipment.etype.name if equipment.equipment.etype else 'Unknown'}")
            ui.label(f"S/N: {equipment.equipment.serialnum}").style('margin-top: -18px')
            ui.label(f"Rented by: {equipment.user.name} ({equipment.user.department.name})").style('margin-top: -18px; margin-bottom: -10px')
            #ui.label(f"Rented since: {equipment.rental_start.strftime('%Y-%m-%d %H:%M')}")
        else:
            with ui.row().classes('w-full justify-between items-center').style('margin-top: -5px'):
                ui.label(f"{equipment.name}").style('font-size: 18px; font-weight: bold')
                ui.label(f"{equipment.etype.name if equipment.etype else 'Unknown'}")
            ui.label(f"S/N: {equipment.serialnum}").style('margin-top: -12px; margin-bottom: -10px')
            
    
    return card

def update_lists():
    """Update both equipment list UI containers based on current state data."""
    # Always re-apply filters (M11) - apply_combined_filters() already handles
    # the no-filter case by returning the full lists, so skipping it there
    # left the in-memory lists stale (e.g. a newly added device wouldn't show
    # up until "Refresh all data" was clicked).
    apply_combined_filters()

    # Clear and repopulate available container
    if available_container:
        available_container.clear()
        with available_container:
            with ui.column():
                # Use data already present in the state
                for equipment in sorted(state.available_equipment, key=lambda x: x.name):
                    card = create_equipment_card(equipment)
                    card.on('click', lambda _, e=equipment: show_rent_dialog(e))
    
    # Clear and repopulate rented container
    if rented_container:
        rented_container.clear()
        with rented_container:
            with ui.column():
                # Use data already present in the state
                for rental in sorted(state.rented_equipment, key=lambda x: x.equipment.name):
                    card = create_equipment_card(rental, is_rented=True)
                    card.on('click', lambda _, r=rental: show_return_dialog(r))

def show_rent_dialog(equipment):
    """Show dialog for renting equipment"""
    # Selection is local to this dialog invocation (M8) - a shared
    # state.selected_user survived past dialog close (X button/ESC don't
    # clear it), so a later dialog's Confirm without picking anyone could
    # silently rent to whoever was selected last time.
    selected_user_id = None

    def on_user_select_modified(e):
        nonlocal selected_user_id
        selected_user_id = users_dict.get(e.value)

    def on_confirm():
        if selected_user_id:
            # Disable immediately to close the TOCTOU window between this
            # check and create_rental()'s own guard (M7).
            confirm_button.disable()
            if is_equipment_rented(db, equipment.id_eq):
                ui.notify('This equipment was just rented by someone else.', type='warning')
                dialog.close()
                refresh_with_filters()
                return
            create_rental(db, selected_user_id, equipment.id_eq, comment=comment_field.value)
            ui.notify('Equipment rented successfully!')
            dialog.close()
            refresh_with_filters()
        else:
            ui.notify('Please select a user!', type='warning')
    
    def refresh_users_ui():
        """Updates the user interface after updating the user list"""
        # Updating the user list
        users = state.refresh_users()
        
        # Clearing and updating the user selection field
        nonlocal users_dict, options, user_select
        users_dict = {}
        options = []
        
        for user in sorted(users, key=lambda x: x.name):
            display_text = f"{user.name} ({user.department.name})"
            users_dict[display_text] = user.id_us
            options.append(display_text)
        
        # Update the contents of the drop-down list
        user_select.options = options
        user_select.update()
        #ui.notify('The list of users has been updated.')

    with ui.dialog() as dialog, ui.card().classes('leading-none').style('''
        position: absolute;
        left: 20%;
        top: 20%;
        transform: none;
        width: 450px;
    '''):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(text='Rent equipment').style('font-size: 150%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(f"{equipment.name}").style('font-weight: bold; font-size: 16px')
            ui.label(f"{equipment.etype.name if equipment.etype else 'Unknown'}")
        ui.label(f"S/N: {equipment.serialnum}")
        #ui.label(f"Type: {equipment.etype.name if equipment.etype else 'Unknown'}")
        
        ui.label('Select user:')
        
        users_dict = {}
        options = []
        
        # Use users from the state instead of directly querying the database
        for user in sorted(state.users, key=lambda x: x.name):
            display_text = f"{user.name} ({user.department.name})"
            users_dict[display_text] = user.id_us
            options.append(display_text)
        
        with ui.row().classes('w-full justify-between items-center'):
            user_select = ui.select(
                options=options,
                label='Select user',
                with_input=True,
                on_change=on_user_select_modified
            )
            ui.button('+', on_click=lambda: show_add_user_dialog(refresh_users_ui))
        
        ui.label('Comment (optional):')
        comment_field = ui.input(label='Comment').style('width: 100%')

        confirm_button = ui.button("Confirm", on_click=on_confirm)
    dialog.open()

def show_return_dialog(rental):
    """Show dialog for returning equipment"""
    def on_confirm():
        return_equipment(db, rental.id_re)
        ui.notify('Equipment returned successfully!')
        dialog.close()
        refresh_with_filters()

    with ui.dialog() as dialog, ui.card().style('width: 350px'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(text='Return equipment').style('font-size: 200%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(f"{rental.equipment.name}").style('font-weight: bold; font-size: 16px')
            ui.label(f"{rental.equipment.etype.name if rental.equipment.etype else 'Unknown'}")
        ui.html(f"Rented by: <b>{rental.user.name}</b>")
        ui.label(f"Rented since: {rental.rental_start.strftime('%Y-%m-%d %H:%M')}")
        
        if rental.comment:
            ui.label("Comment:").style('margin-top: 10px; font-weight: bold')
            ui.label(rental.comment).style('white-space: pre-wrap')
        
        ui.button("Confirm Return", on_click=on_confirm)
    dialog.open()

def filter_by_etype(e):
    """Filter equipment lists by equipment type"""
    selected_name = e.value
    state.selected_etype_id = state.etype_map.get(selected_name)

    # update_lists() now always re-applies filters itself (M11), so a
    # separate call here would just re-run the same queries twice.
    update_lists()

def filter_equipment_by_name(equipment_list, name_filter):
    """Filter equipment list by name containing the filter text (case-insensitive)"""
    if not name_filter:
        return equipment_list
    return [eq for eq in equipment_list if name_filter.lower() in eq.name.lower()]

def filter_rentals_by_equipment_name(rental_list, name_filter):
    """Filter rental list by equipment name containing the filter text (case-insensitive)"""
    if not name_filter:
        return rental_list
    return [rental for rental in rental_list if name_filter.lower() in rental.equipment.name.lower()]

def apply_combined_filters():
    """Apply both type and name filters simultaneously to equipment lists"""
    # Get base equipment lists (all or filtered by type)
    if state.selected_etype_id is not None:
        available = get_available_equipment_by_type(db, state.selected_etype_id)
        rented = get_active_rentals_by_equipment_type(db, state.selected_etype_id)
    else:
        available = get_available_equipment(db)
        rented = get_active_rentals(db)
    
    # Apply name filter if active
    if state.name_filter:
        available = filter_equipment_by_name(available, state.name_filter)
        rented = filter_rentals_by_equipment_name(rented, state.name_filter)
    
    # Update state
    state.available_equipment = available
    state.rented_equipment = rented

def on_name_filter_change(filter_text):
    """Handle name filter input changes and trigger combined filtering"""
    # Update state with new filter text
    state.set_name_filter(filter_text)

    # update_lists() now always re-applies filters itself (M11), so a
    # separate call here would just re-run the same queries twice.
    update_lists()

def refresh_with_filters():
    """Refresh equipment data while maintaining current filter state"""
    # Refresh users and etypes from DB into state
    state.refresh_users()
    state.refresh_etypes()

    # update_lists() now always re-applies filters itself (M11), so a
    # separate call here would just re-run the same queries twice.
    update_lists()

def reset_filter():
    """Reset both equipment type and name filters to show all equipment"""
    state.selected_etype_id = None
    state.name_filter = ""
    
    # Reset the visual selection in both filter inputs
    if state.filter_select:
        state.filter_select.set_value(None)
    if state.name_filter_input:
        state.name_filter_input.set_value("")
    
    # Refresh users and etypes from DB into state
    state.refresh_users()
    state.refresh_etypes()

    # update_lists() re-applies filters itself (M11) - with both filters just
    # cleared above, this fetches the full unfiltered lists.
    update_lists()

# Function for full data refresh
def full_refresh():
    """Reloads all data from the database and updates the UI."""
    
    # Preserve current filter state before refresh
    current_etype_id = state.selected_etype_id
    current_name_filter = state.name_filter
    
    # Expire session cache before fetching
    db.expire_all()

    # Refresh users and etypes from DB into state
    state.refresh_users()
    state.refresh_etypes() 

    # Restore filter state after refresh
    state.selected_etype_id = current_etype_id
    state.name_filter = current_name_filter

    # update_lists() re-applies filters itself (M11) using the restored state.
    update_lists()

    # Ensure the filter dropdown options reflect the latest etypes
    if state.filter_select:
        etype_options = [etype.name for etype in state.etypes]
        state.filter_select.options = etype_options
        state.filter_select.update() # Update the UI element
        
        # Restore the visual selection in the type filter if it was active
        if current_etype_id is not None:
            # Find the etype name for the current ID
            for etype in state.etypes:
                if etype.id_et == current_etype_id:
                    state.filter_select.set_value(etype.name)
                    break
    
    # Restore the visual value in the name filter input if it was active
    if state.name_filter_input and current_name_filter:
        state.name_filter_input.set_value(current_name_filter)
    
    # Refresh departments list in gui_adduser module
    refresh_departments()
    ui.notify('Data refreshed successfully!', type='positive')
    
#Fuctions for password for Admin mode
# Admin Panel here
class CodesGenerationDialog:
    """Dialog window for managing Data Matrix codes generation"""
    
    def __init__(self):
        """Dialog window initialization"""
        self.dialog = None
        
    def open(self):
        """Opens the dialog window"""
        with ui.dialog() as self.dialog, ui.card().style('width: 400px'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Data Matrix Codes operations').style('font-size: 150%')
                ui.button(icon='close', on_click=self.dialog.close).props('flat round')
            
            ui.separator()
            
            # Information message
            ui.label('Clicking the button will open a folder selection dialog to save the codes').style('font-size: 14px; color: #666; margin: 10px 0;')
            
            # Main generation buttons
            with ui.row():#.classes('w-full q-gutter-md'):
                ui.button(
                    'Download Users Codes',
                    icon='person',
                    on_click=self.generate_users_codes
                ).style('width: 100px; height: 100px;')
                
                ui.button(
                    'Download Equipments Codes', 
                    icon='inventory',
                    on_click=self.generate_equipment_codes
                ).style('width: 100px; height: 100px;')
            
            ui.separator()

            ui.label('Updating codes for all users or equipment. This operation must be done after changing the Name or the Serial Number.').style('font-size: 14px; color: #666; margin: 10px 0;')
            
            with ui.row():#.classes('w-full q-gutter-md'):
                ui.button(
                    'Update Users Codes',
                    icon='person',
                    on_click=self.handle_update_user_codes
                ).style('width: 100px; height: 100px;')
                
                ui.button(
                    'Update Equipments Codes', 
                    icon='inventory',
                    on_click=self.handle_update_equipment_codes
                ).style('width: 100px; height: 100px;')

            # Status and results
        
        self.dialog.open()

    async def generate_users_codes(self):
        """Handler for generating codes for all users"""
        # Select folder for saving when button is clicked
        def pick_folder():
            root = tk.Tk()
            root.withdraw()  # Hide main window
            root.attributes('-topmost', True)  # Make window on top of all
            root.lift()  # Bring window to front
            root.focus_force()
            
            # Open folder selection dialog
            directory = filedialog.askdirectory(
                title="Select folder to save user codes",
                parent=root
            )
            
            root.destroy()  # Close temporary window
            return directory

        directory = await run.io_bound(pick_folder)
        
        if not directory:
            ui.notify('Folder not selected, operation cancelled', type='warning')
            return
        
        try:
            ui.notify('Starting user codes generation...', type='info')
            
            # Call generation function
            created_count, total_count = generate_all_users_codes(directory)
            
            # Display results
            if created_count > 0:
                ui.notify(f'Successfully created {created_count} out of {total_count} user codes in folder: {directory}', type='positive')
            else:
                ui.notify('Failed to create user codes', type='warning')
                
        except Exception as e:
            error_msg = f'Error generating user codes: {str(e)}'
            ui.notify(error_msg, type='negative')
    
    async def generate_equipment_codes(self):
        """Handler for generating codes for all equipment"""
        # Select folder for saving when button is clicked
        def pick_folder():
            root = tk.Tk()
            root.withdraw()  # Hide main window
            root.attributes('-topmost', True)  # Make window on top of all
            root.lift()  # Bring window to front
            root.focus_force()
            
            # Open folder selection dialog
            directory = filedialog.askdirectory(
                title="Select folder to save equipment codes",
                parent=root
            )
            
            root.destroy()  # Close temporary window
            return directory

        directory = await run.io_bound(pick_folder)
        
        if not directory:
            ui.notify('Folder not selected, operation cancelled', type='warning')
            return
        
        try:
            ui.notify('Starting equipment codes generation...', type='info')
            
            # Call generation function
            created_count, total_count = generate_all_equipment_codes(directory)
            
            # Display results
            if created_count > 0:
                ui.notify(f'Successfully created {created_count} out of {total_count} equipment codes in folder: {directory}', type='positive')
            else:
                ui.notify('Failed to create equipment codes', type='warning')
                
        except Exception as e:
            error_msg = f'Error generating equipment codes: {str(e)}'
            ui.notify(error_msg, type='negative')

    def handle_update_user_codes(self):
        """Handler for updating user codes button."""
        try:
            ui.notify('Starting user NFC codes update...', type='info')
            
            # Call update function from MatrixCode module
            result = update_user_codes()
            
            # Process operation results
            if result['success']:
                success_msg = f"Successfully updated {result['updated_count']} user NFC codes"
                ui.notify(success_msg, type='positive')
            else:
                error_msg = f"Error: {result['message']}"
                if result['error']:
                    error_msg += f" ({result['error']})"
                ui.notify(error_msg, type='negative')
                
        except Exception as e:
            error_msg = f'Unexpected error updating user NFC codes: {str(e)}'
            ui.notify(error_msg, type='negative')

    def handle_update_equipment_codes(self):
        """Handler for updating equipment codes button."""
        try:
            ui.notify('Starting equipment NFC codes update...', type='info')
            
            # Call update function from MatrixCode module
            result = update_equipment_codes()
            
            # Process operation results
            if result['success']:
                success_msg = f"Successfully updated {result['updated_count']} equipment NFC codes"
                ui.notify(success_msg, type='positive')
            else:
                error_msg = f"Error: {result['message']}"
                if result['error']:
                    error_msg += f" ({result['error']})"
                ui.notify(error_msg, type='negative')
                
        except Exception as e:
            error_msg = f'Unexpected error updating equipment NFC codes: {str(e)}'
            ui.notify(error_msg, type='negative')

def open_codes_dialog():
    """Opens the codes generation dialog"""
    dialog = CodesGenerationDialog()
    dialog.open()

def create_password_dialog():
    """Creates dialogs for entering a password and successful entry."""
    password_dialog = ui.dialog().props('persistent')
    success_dialog = ui.dialog()

    with success_dialog:
        with ui.card().style('max-width: none; width: 500px; height: 600px'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Admin panel').style('font-size: 200%; font-weight: bold')
                ui.button(icon='close', on_click=success_dialog.close).props('flat round')
            ui.separator()
            with ui.row():
                ui.label('User options').style('font-size: 150%; font-weight: bold')
                with ui.row().classes('flex-wrap gap-2'):
                    with ui.button(on_click=edit_users_dialog).style('width: 100px; height: 100px;'):
                        ui.icon('person')
                        ui.label('Edit users')
                    with ui.button(on_click=lambda: show_add_department_dialog()).style('width: 100px; height: 100px;'):
                        ui.icon('add')
                        ui.label('Add Department')
                    with ui.button(on_click=edit_departments_dialog).style('width: 100px; height: 100px;'):
                        ui.icon('business')
                        ui.label('Edit deps') 
                ui.separator()
                ui.label('Device options').style('font-size: 150%; font-weight: bold')
                with ui.row().classes('flex-wrap gap-2'):
                    with ui.button(on_click=lambda: show_add_equipment_dialog(filter_callback=state.update_filter_select, lists_update_callback=update_lists)).style('width: 100px; height: 100px;'):
                        ui.icon('add')
                        ui.label('Add Device')
                    with ui.button(on_click=edit_equipment_dialog).style('width: 100px; height: 100px;'):
                        ui.icon('sd_card')
                        ui.label('Edit device') 
                    with ui.button(on_click=edit_etypes_dialog).style('width: 100px; height: 100px;'):
                        ui.icon('inventory_2')
                        ui.label('Edit device type') 
                    #get_feedback_button()
            ui.separator()
            ui.label('Other options').style('font-size: 150%; font-weight: bold')                
            with ui.row():
                with ui.button(on_click=edit_rentals_dialog).style('width: 100px; height: 100px;'):
                    ui.icon('edit_note')
                    ui.label('Edit Rentals')  
                with ui.button(on_click=lambda: open_codes_dialog()).style('width: 100px; height: 100px;'):
                    ui.icon('qr_code')
                    ui.label('Generate Codes')
                with ui.button(on_click=show_scanner_config_dialog).style('width: 100px; height: 100px;'):
                    ui.icon('settings')
                    ui.label('Scanner Settings')
                with ui.button(on_click=full_refresh,  color='warning').tooltip('After editing all data must be refreshed').style('width: 100px; height: 100px'):
                    ui.icon('refresh')
                    ui.label('Refresh all data')  
            ui.separator()
            ui.label('Reports').style('font-size: 150%; font-weight: bold')
            with ui.row():
                get_user_report_button()
                get_equipment_report_button()
                get_equipment_name_report_button()
                get_department_report_button()
    with password_dialog:
        with ui.card().style('''
        position: absolute;
        left: 20%;
        top: 20%;
        transform: none;
        '''):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Enter password:')
                ui.button(icon='close', on_click=password_dialog.close).props('flat round')
            password_input = ui.input(password=True)
            ui.button('Enter', on_click=lambda: check_password(password_input))
    
    def check_password(input_field):
        if input_field.value == "supp":  #Change !password
            password_dialog.close()
            success_dialog.open()
        else:
            ui.notify('Wrong password', color='negative')
        input_field.set_value('')
    
    return password_dialog

def get_long_hold_callbacks():
    """
    Returns callback to handle 5 clicks within 0.4 seconds:
      - on_click: increments counter if clicks are within time window
    """
    password_dialog = create_password_dialog()
    click_count = 0
    last_click_time = 0

    def handle_click(event):
        nonlocal click_count, last_click_time
        now = time.time()
        # If more than 0.8 seconds have passed, start over
        if now - last_click_time > 0.8:
            click_count = 0
        click_count += 1
        last_click_time = now
        if click_count >= 3:
            password_dialog.open()
            click_count = 0  # reset counter

    return handle_click
    
def show_feedback_dialog():
    """Show dialog for submitting user feedback"""
    
    def on_submit():
        # Get values from form
        user_name = name_input.value
        feedback_text = feedback_input.value
        
        # Validate feedback text is not empty
        if not feedback_text or feedback_text.strip() == "":
            ui.notify("Please enter feedback message", type="warning")
            return
        
        # Save feedback to database
        create_feedback(db, feedback_text, user_name)
        ui.notify("Thank you for your feedback!", type="positive")
        dialog.close()
    
    with ui.dialog() as dialog, ui.card().classes('w-96'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label("Submit Feedback").style('font-size: 150%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        
        name_input = ui.input(label="Your Name (optional)")
        
        feedback_input = ui.textarea(label="Feedback*", placeholder="Please enter your feedback here...").props('rows=4').style('width: 100%')
        
        with ui.row().classes('w-full justify-end'):
            ui.button("Submit", on_click=on_submit).props('color=primary')
    
    dialog.open()

def show_add_nfc_dialog():
    """
    Opens a dialog box to add an NFC code to existing users without NFC.
    """
    with SessionLocal() as fresh_db:
        # Get only users without NFC code
        users_without_nfc = fresh_db.query(User).filter(User.nfc == None, User.status == True).all()
        
        if not users_without_nfc:
            ui.notify('No users without Code', color='warning')
            return
            
        # Sort by name
        users_without_nfc = sorted(users_without_nfc, key=lambda x: x.name.lower())
        
        with ui.dialog() as dialog, ui.card().style('''
        position: absolute;
        left: 20%;
        top: 20%;
        transform: none;
        width: 500px;
    '''):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Adding Code to User').style('font-size: 150%')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            
            # Create dropdown list of users
            user_options = [(f"{user.name} ({user.department.name})", user.id_us) for user in users_without_nfc]
            selected_user_id = None
            
            # Find user ID by selected text
            def on_user_select(e):
                nonlocal selected_user_id
                # Search for user ID by selected text
                for option in user_options:
                    if option[0] == e.value:
                        selected_user_id = option[1]
                        break
            
            user_select = ui.select(
                options=[option[0] for option in user_options],
                value=None,
                label='Select user',
                on_change=on_user_select,
                with_input=True
            ).style('width: 100%')
            
            # To store NFC value
            nfc_value = None
            #nfc_label = ui.html('<i class="material-icons" font-weight=bold style="color: red;">check_box_outline_blank</i> <b>Code: Not set</b>')
            
            async def scan_nfc():
                nonlocal nfc_value
                nfc_value, scan_status = await get_nfc_input("Scan a Code")
                nfc_value = nfc_value.lower() if nfc_value else None
                
                if nfc_value:
                    # Check if this NFC code is already taken
                    existing_user = find_user_by_nfc(fresh_db, nfc_value)
                    if existing_user:
                        ui.notify(f'Code already registered to user {existing_user.name}', type='warning')
                        nfc_value = None
                        nfc_label.content = '<i class="material-icons" font-weight=bold style="color: red;">check_box_outline_blank</i> <b>Code: Not set</b>'
                    else:
                        nfc_label.content = '<i class="material-icons" font-weight=bold style="color: green;">check_box</i> <b>Code scanned</b>'
                else:
                    nfc_label.content = '<i class="material-icons" font-weight=bold style="color: red;">check_box_outline_blank</i> <b>Code: Not set</b>'
            
            def on_save():
                nonlocal selected_user_id, nfc_value
                
                if not selected_user_id:
                    ui.notify('User not selected', color='negative')
                    return
                    
                if not nfc_value:
                    ui.notify('Data Matrix Code not scanned', color='negative')
                    return
                
                try:
                    # Updating the user's NFC code
                    update_user_nfc(fresh_db, selected_user_id, nfc_value)
                    ui.notify('Data Matrix Code successfully added to user', color='positive')
                    dialog.close()
                except Exception as e:
                    ui.notify(f'Error during update: {str(e)}', color='negative')
            
            with ui.row().classes('w-full justify-between items-center q-mb-md'):
                ui.button('Scan Data Matrix Code', on_click=scan_nfc)
                nfc_label = ui.html('<i class="material-icons" font-weight=bold style="color: red;">check_box_outline_blank</i> <b>Code: Not set</b>')
            
            with ui.row().classes('justify-end'):
                ui.button('Apply', on_click=on_save).classes('bg-primary')
            
        dialog.open()

def main():
    global available_container, rented_container
    ui.query('body').style('font-family: Helvetica') #Font for the whole app
    # Get the list of equipment types once at startup
    state.etypes = get_all_etypes(db)
    
    # Build a mapping of etype names to their IDs
    for etype in state.etypes:
        state.etype_map[etype.name] = etype.id_et

    with ui.row().style('height: 80vh;'):
        with ui.column().style('width: 300px; padding: 10px; align-items: center; margin-top: 25px'):
            with ui.card():
                ui.html('Instructions').style('font-size: 150%; font-weight: bold')
                ui.html('- To rent equipment, click on the desired equipment card in the <b>"Available Equipment"</b> list.')
                ui.html('- To return equipment, click on the equipment card in the <b>"Rented Equipment"</b> list.')
                ui.html('- To add a new user, press the <b>"+"</b> button next to the user selection field in the Rent dialog.')
                ui.html('- Use the <b>"Filter by Equipment Type"</b> dropdown to filter equipment by type.')
                ui.html('- Access the rental history by clicking the <b>"Rental History"</b> button.')
                ui.html('- To use Barcode Scanner, press the <b>"Scan to Rent"</b> button, then scan the Code on the device. After that scan your personal code if you have it.')
                # ui.html('- If you have any suggestions for the app or have found any bugs, you can leave your anonymous feedback by clicking the <b>“Submit feedback”</b> button.')
            ui.button('Scan to Rent', icon='qr_code', on_click=lambda: nfc_equipment_rental_workflow(reset_filter)).style('width: 100%; height: 65px')   #!NFC_feature
            #ui.button('Attach a code to User', icon='developer_board', on_click=show_add_nfc_dialog).style('width: 100%; height: 65px')
            ui.separator()
            ui.button('Rental History', icon='history', on_click=show_rental_history).style('width: 100%; height: 65px; margin-top: 25px')
            

        with ui.column():
            # Equipment type and name filters
            with ui.row().classes('items-center'):
                ui.label('Filter by Equipment Type:').classes('text-h6')
                etype_options = [etype.name for etype in state.etypes]
                state.filter_select = ui.select(
                    options=etype_options,
                    label='Equipment Type',
                    on_change=filter_by_etype#,                    with_input=True
                ).style('width: 200px; margin-right: 10px;').props('use-chips')
                
                ui.label('Filter by Name:').classes('text-h6').style('margin-left: 20px')
                state.name_filter_input = ui.input(
                    label='Equipment Name',
                    placeholder='Type equipment name...',
                    on_change=lambda e: on_name_filter_change(e.value)
                ).style('width: 200px; margin-right: 10px; margin-left: 10px')
                
                ui.button(icon='clear', on_click=reset_filter).style('height: 40px; margin-left: 20px').tooltip('Clear all filters')
                
                # ui.button(icon='refresh', on_click=full_refresh).props('flat round').tooltip('Refresh all data')
                

            with ui.row():
                #Available list
                with ui.column():
                    ui.label('Available Equipment').classes('text-h5')
                    available_container = ui.scroll_area().style('border: 2px solid black; padding: 10px; height: 800px; width: 500px')
                    with available_container:
                        with ui.column():
                            for equipment in sorted(state.available_equipment, key=lambda x: x.name):
                                card = create_equipment_card(equipment)
                                card.on('click', lambda _, e=equipment: show_rent_dialog(e))
                #Rented list
                with ui.column():
                    ui.label('Rented Equipment').classes('text-h5')
                    rented_container = ui.scroll_area().style('border: 2px solid black; padding: 10px; height: 800px; width: 500px')
                    with rented_container:
                        with ui.column():
                            for rental in sorted(state.rented_equipment, key=lambda x: x.equipment.name):
                                card = create_equipment_card(rental, is_rented=True)
                                card.on('click', lambda _, r=rental: show_return_dialog(r))
    with ui.row().style('position: fixed; right: 25px; top: 25px;'):
        admin_button = ui.button().props('icon=admin_panel_settings').style('width: 150px; height: 150px; opacity: 0;')
        on_click = get_long_hold_callbacks()
        admin_button.on('click', on_click)
    
    # ui.button('Submit Feedback', icon='feedback', on_click=show_feedback_dialog).style('width: 200px; height: 75px; position: fixed; left: 30px; bottom: 30px')
    
    # Web viewer status indicator
    viewer_status = ui.label('').style('position: fixed; left: 30px; bottom: 30px; font-size: 12px; color: #666')
    viewer_lan_ip = os.environ.get(VIEWER_LAN_IP_ENV_VAR)
    if viewer_lan_ip:
        viewer_status.set_text(f'🌐 Web Viewer: http://{viewer_lan_ip}:8585')
        #viewer_status.tooltip('Network access available on port 8585')
    
    with ui.row().style('position: fixed; right: 30px; bottom: 30px'):
        button = ui.button(on_click=lambda: toggle_dark_mode(button))
        # Set the initial icon
        if dark_mode.value:
            button.props('icon=light_mode')
        else:
            button.props('icon=dark_mode')

if __name__ in {'__main__', '__mp_main__'}:
    # Initialize logging system
    setup_logging(log_level="INFO", console_output=True, file_output=True)

    # Start the web viewer in background - guarded by an env var, not just
    # __name__, because NiceGUI's native mode re-invokes this whole module in
    # further descendant processes (confirmed empirically: each generation
    # re-runs ui.run(native=True), which spawns another native-window
    # process, cascading multiple levels deep) - an in-memory flag can't
    # survive that since each generation is a separate OS process, but an
    # env var does, since child processes inherit the parent's environment.
    viewer_process = None
    if not os.environ.get(VIEWER_STARTED_ENV_VAR):
        os.environ[VIEWER_STARTED_ENV_VAR] = "1"
        try:
            if getattr(sys, "frozen", False):
                # Bundled web_viewer/ unpacks into the temp _MEIPASS extraction
                # dir, not next to the exe (APP_DIR) - it's pure code, never
                # seeded into APP_DIR the way rental.db/scanner_config.json are.
                viewer_script = os.path.join(getattr(sys, "_MEIPASS", ""), 'web_viewer', 'viewer_app.py')
            else:
                viewer_script = os.path.join(APP_DIR, 'web_viewer', 'viewer_app.py')
            if os.path.exists(viewer_script):
                if getattr(sys, "frozen", False):
                    # No bundled python.exe in a onefile build - re-invoke the
                    # exe itself; the dispatch at the top of this file catches
                    # the flag and runs only the viewer, then exits.
                    viewer_cmd = [sys.executable, "--web-viewer"]
                else:
                    viewer_cmd = [sys.executable, os.path.abspath(__file__), "--web-viewer"]
                viewer_process = subprocess.Popen(
                    viewer_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                os.environ[VIEWER_LAN_IP_ENV_VAR] = _get_lan_ip()
                print(f"Web viewer started in background (PID: {viewer_process.pid})")
                print(f"Access viewer at: http://{os.environ[VIEWER_LAN_IP_ENV_VAR]}:8585")
        except Exception as e:
            print(f"Could not start web viewer: {e}")

    main()

    try:
        ui.run(reload=False, title=f'WenglorMEL Rental System {VERSION}', favicon='assets/icon.ico', window_size=(1800, 1000), port=15716, native=True)
    finally:
        # Clean up: stop viewer when main app closes
        if viewer_process:
            viewer_process.terminate()
            print("Web viewer stopped")

    # Build: pyinstaller "WenglorMEL Rental System 2.1.5.spec"