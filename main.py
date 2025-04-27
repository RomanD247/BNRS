from nicegui import native, ui
from gui.gui_adduser import show_add_user_dialog, show_add_department_dialog
from gui.gui_addequip import show_add_equipment_dialog
from gui.gui_changeUser import edit_users_dialog
from gui.gui_changeDep import edit_departments_dialog
from gui.gui_changeEtype import edit_etypes_dialog
from gui.gui_changeEquip import edit_equipment_dialog
from gui.gui_reports import get_user_report_button, get_equipment_report_button, get_equipment_name_report_button, show_rental_history, get_department_report_button, get_feedback_button
from NfcScan import nfc_equipment_rental_workflow, get_nfc_input

import asyncio
import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import (
    get_available_equipment, get_all_users, create_rental, 
    get_active_rentals, return_equipment, get_all_etypes,
    get_available_equipment_by_type, get_active_rentals_by_equipment_type,
    create_feedback, find_user_by_nfc, update_user_nfc
)
from database import SessionLocal
from models import User

db = SessionLocal()

# Global containers for lists
available_container = None
rented_container = None

# Create reactive state
class State:
    def __init__(self):
        self.available_equipment = get_available_equipment(db)
        self.rented_equipment = get_active_rentals(db)
        self.users = get_all_users(db)
        self.selected_user = None
        self.selected_etype_id = None
        self.etype_map = {}
        self.etypes = get_all_etypes(db)
        self.filter_select = None
    
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
    # Data fetching is now done by the caller (full_refresh or filter_by_etype)
    # Only update the UI here
    
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
    def on_user_select_modified(e):
        if e.value in users_dict:
            state.selected_user = users_dict[e.value]
        else:
            state.selected_user = None
    
    def on_confirm():
        if state.selected_user:
            create_rental(db, state.selected_user, equipment.id_eq, comment=comment_field.value)
            ui.notify('Equipment rented successfully!')
            dialog.close()
            reset_filter()
            # Clear the selected user and user select field
            state.selected_user = None
            user_select.set_value(None)
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
        
        ui.button("Confirm", on_click=on_confirm)
    dialog.open()

def show_return_dialog(rental):
    """Show dialog for returning equipment"""
    def on_confirm():
        return_equipment(db, rental.id_re)
        ui.notify('Equipment returned successfully!')
        dialog.close()
        reset_filter()

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
    # Fetch filtered data into state
    if state.selected_etype_id is not None:
        state.available_equipment = get_available_equipment_by_type(db, state.selected_etype_id)
        state.rented_equipment = get_active_rentals_by_equipment_type(db, state.selected_etype_id)
    else:
        # If filter is cleared, fetch all data
        state.available_equipment = get_available_equipment(db)
        state.rented_equipment = get_active_rentals(db)
    # Update UI with new state data
    update_lists()

def reset_filter():
    """Reset equipment type filter to show all equipment"""
    state.selected_etype_id = None
    # Reset the visual selection in the dropdown
    if state.filter_select:
        state.filter_select.set_value(None)
    
    # Fetch all data into state
    state.available_equipment = get_available_equipment(db)
    state.rented_equipment = get_active_rentals(db)

    # Refresh users and etypes from DB into state
    state.refresh_users()
    state.refresh_etypes()

    # Update the UI lists
    update_lists()

# Function for full data refresh
def full_refresh():
    """Reloads all data from the database and updates the UI."""
    
    # Expire session cache before fetching
    db.expire_all()

    # Reset filter selection state
    state.selected_etype_id = None
    if state.filter_select:
        state.filter_select.set_value(None) # Reset the dropdown visually

    # Refresh users and etypes from DB into state
    state.refresh_users()
    state.refresh_etypes() 

    # Fetch ALL equipment lists (available and rented) from DB into state
    state.available_equipment = get_available_equipment(db)
    state.rented_equipment = get_active_rentals(db)

    # Update the UI lists (available_container and rented_container) using data now in state
    update_lists()

    # Ensure the filter dropdown options reflect the latest etypes
    if state.filter_select:
        etype_options = [etype.name for etype in state.etypes]
        state.filter_select.options = etype_options
        state.filter_select.update() # Update the UI element
    
    # Refresh departments list in gui_adduser module
    from gui import gui_adduser
    gui_adduser.refresh_departments()

    ui.notify('Data refreshed successfully!', type='positive')

#Fuctions for password for Admin mode
# Admin Panel here
def create_password_dialog():
    """Creates dialogs for entering a password and successful entry."""
    password_dialog = ui.dialog().props('persistent')
    success_dialog = ui.dialog()

    with success_dialog:
        with ui.card().style('height: 500px'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Admin panel').style('font-size: 150%')
                ui.button(icon='close', on_click=success_dialog.close).props('flat round')
            with ui.row():
                with ui.button(on_click=edit_users_dialog).style('width:100px; height: 100px;'):
                    ui.icon('person')
                    ui.label('Edit users')
                with ui.button(on_click=edit_departments_dialog).style('width: 100px; height: 100px;'):
                    ui.icon('business')
                    ui.label('Edit deps') 
                with ui.button(on_click=edit_equipment_dialog).style('width: 100px; height: 100px;'):
                    ui.icon('sd_card')
                    ui.label('Edit device') 
                with ui.button(on_click=edit_etypes_dialog).style('width: 100px; height: 100px;'):
                    ui.icon('inventory_2')
                    ui.label('Edit device type') 
                with ui.button(on_click=lambda: show_add_equipment_dialog(filter_callback=state.update_filter_select, lists_update_callback=update_lists)).style('width: 100px; height: 100px;'):
                    ui.icon('add')
                    ui.label('Add Device')
                with ui.button(on_click=lambda: show_add_department_dialog()).style('width: 100px; height: 100px;'):
                    ui.icon('add')
                    ui.label('Add Department')
                get_feedback_button()
                with ui.button(on_click=full_refresh,  color='warning').tooltip('After editing all data must be refreshed').style('width: 100px; height: 100px'):
                    ui.icon('refresh')
                    ui.label('Refresh all data') 
            ui.separator()
            ui.label('Reports').style('font-size: 150%')
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
        if input_field.value == "supp":  #Change password
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
            ui.notify('No users without Wenglor Pass', color='warning')
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
                ui.label('Adding Wenglor Pass to User').style('font-size: 150%')
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
            #nfc_label = ui.html('<i class="material-icons" font-weight=bold style="color: red;">check_box_outline_blank</i> <b>Pass: Not set</b>')
            
            async def scan_nfc():
                nonlocal nfc_value
                nfc_value = await get_nfc_input("Scan Wenglor Pass")
                nfc_value = nfc_value.lower() if nfc_value else None
                
                if nfc_value:
                    # Check if this NFC code is already taken
                    existing_user = find_user_by_nfc(fresh_db, nfc_value)
                    if existing_user:
                        ui.notify(f'Wenglor Pass already registered to user {existing_user.name}', type='warning')
                        nfc_value = None
                        nfc_label.content = '<i class="material-icons" font-weight=bold style="color: red;">check_box_outline_blank</i> <b>Pass: Not set</b>'
                    else:
                        nfc_label.content = '<i class="material-icons" font-weight=bold style="color: green;">check_box</i> <b>Pass scanned</b>'
                else:
                    nfc_label.content = '<i class="material-icons" font-weight=bold style="color: red;">check_box_outline_blank</i> <b>Pass: Not set</b>'
            
            def on_save():
                nonlocal selected_user_id, nfc_value
                
                if not selected_user_id:
                    ui.notify('User not selected', color='negative')
                    return
                    
                if not nfc_value:
                    ui.notify('Wenglor Pass not scanned', color='negative')
                    return
                
                try:
                    # Updating the user's NFC code
                    update_user_nfc(fresh_db, selected_user_id, nfc_value)
                    ui.notify('Wenglor Pass successfully added to user', color='positive')
                    dialog.close()
                except Exception as e:
                    ui.notify(f'Error during update: {str(e)}', color='negative')
            
            with ui.row().classes('w-full justify-between items-center q-mb-md'):
                ui.button('Scan Wenglor Pass', on_click=scan_nfc)
                nfc_label = ui.html('<i class="material-icons" font-weight=bold style="color: red;">check_box_outline_blank</i> <b>Pass: Not set</b>')
            
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
                ui.html('- If you have any suggestions for the app or have found any bugs, you can leave your anonymous feedback by clicking the <b>“Submit feedback”</b> button.')
            #get_rental_history_button().style('width: 100%')
            #ui.button('Scan', icon='nfc', on_click=lambda: nfc_equipment_rental_workflow(reset_filter)).style('width: 100%')   #!NFC_feature
            
            ui.button('Scan to Rent', icon='nfc', on_click=lambda: nfc_equipment_rental_workflow(reset_filter)).style('width: 100%; height: 100px')   #!NFC_feature
            ui.button('Attach Wenglor Pass to User', icon='contactless', on_click=show_add_nfc_dialog).style('width: 100%; margin-top: 50px')
            

        with ui.column():
            # Equipment type filter
            with ui.row().classes('items-center'):
                ui.label('Filter by Equipment Type:').classes('text-h6')
                etype_options = [etype.name for etype in state.etypes]
                state.filter_select = ui.select(
                    options=etype_options,
                    label='Equipment Type',
                    on_change=filter_by_etype#,                    with_input=True
                ).style('width: 200px; margin-right: 10px;').props('use-chips')
                # ui.button(icon='refresh', on_click=full_refresh).props('flat round').tooltip('Refresh all data')
                ui.button('Rental History', icon='history', on_click=show_rental_history).style('height: 65px; margin-left: 40px')

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
    
    ui.button('Submit Feedback', icon='feedback', on_click=show_feedback_dialog).style('width: 200px; height: 75px; position: fixed; left: 30px; bottom: 30px')
    with ui.row().style('position: fixed; right: 30px; bottom: 30px'):
        button = ui.button(on_click=lambda: toggle_dark_mode(button))
        # Set the initial icon
        if dark_mode.value:
            button.props('icon=light_mode')
        else:
            button.props('icon=dark_mode')

if __name__ in {'__main__', '__mp_main__'}:
    main()
    ui.run(reload=False, title='WenglorMEL Rental System 2.1', favicon='assets/icon.ico', window_size=(1800, 1000), port=15716, native=True)
    #port=native.find_open_port()
    #nicegui-pack --onefile --windowed --icon=assets/icon.ico --add-data "rental.db:." --name "WenglorMEL Rental System 2.1" main.py