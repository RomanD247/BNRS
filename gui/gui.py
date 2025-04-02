from nicegui import ui
from t_guidial import create_gui
from gui_adduser import show_add_user_dialog
from gui_addequip import show_add_equipment_dialog

import asyncio
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import (
    get_available_equipment, get_all_users, create_rental, 
    get_active_rentals, return_equipment, get_all_etypes,
    get_available_equipment_by_type, get_active_rentals_by_equipment_type
)
from database import SessionLocal

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
        # Сначала обновляем список типов из базы данных
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
    card = ui.card().style('width: 450px; cursor: pointer;')
    
    with card:
        if is_rented:
            ui.label(f"{equipment.equipment.name}")
            ui.label(f"Serial: {equipment.equipment.serialnum}")
            ui.label(f"Type: {equipment.equipment.etype.name if equipment.equipment.etype else 'Unknown'}")
            ui.label(f"Rented by: {equipment.user.name} ({equipment.user.department.name})")
            ui.label(f"Rented since: {equipment.rental_start.strftime('%Y-%m-%d %H:%M')}")
        else:
            ui.label(f"{equipment.name}")
            ui.label(f"Serial: {equipment.serialnum}")
            ui.label(f"Type: {equipment.etype.name if equipment.etype else 'Unknown'}")
    
    return card

def update_lists():
    """Update both equipment lists"""
    if state.selected_etype_id is not None:
        state.available_equipment = get_available_equipment_by_type(db, state.selected_etype_id)
        state.rented_equipment = get_active_rentals_by_equipment_type(db, state.selected_etype_id)
    else:
        state.available_equipment = get_available_equipment(db)
        state.rented_equipment = get_active_rentals(db)
    
    available_container.clear()
    with available_container:
        with ui.column():
            for equipment in sorted(state.available_equipment, key=lambda x: x.name):
                card = create_equipment_card(equipment)
                card.on('click', lambda _, e=equipment: show_rent_dialog(e))
    
    rented_container.clear()
    with rented_container:
        with ui.column():
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
            create_rental(db, state.selected_user, equipment.id_eq)
            ui.notify('Equipment rented successfully!')
            dialog.close()
            reset_filter()
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
        ui.notify('The list of users has been updated.')

    with ui.dialog().style('width: 700px') as dialog, ui.card():
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(text='Rent equipment').style('font-size: 200%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        ui.label(f"Rent equipment: {equipment.name}")
        ui.label(f"Serial: {equipment.serialnum}")
        ui.label(f"Type: {equipment.etype.name if equipment.etype else 'Unknown'}")
        
        ui.label('Select user:')
        
        users_dict = {}
        options = []
        
        # Use users from the state instead of directly querying the database
        for user in sorted(state.users, key=lambda x: x.name):
            display_text = f"{user.name} ({user.department.name})"
            users_dict[display_text] = user.id_us
            options.append(display_text)
        
        with ui.row():
            user_select = ui.select(
                options=options,
                label='User',
                with_input=True,
                on_change=on_user_select_modified
            )#.classes('w-full')
            ui.button('+', on_click=lambda: show_add_user_dialog(refresh_users_ui))
        
        ui.button("Confirm", on_click=on_confirm)
    dialog.open()

def show_return_dialog(rental):
    """Show dialog for returning equipment"""
    def on_confirm():
        return_equipment(db, rental.id_re)
        ui.notify('Equipment returned successfully!')
        dialog.close()
        reset_filter()

    with ui.dialog().style('width: 700px') as dialog, ui.card():
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(text='Return equipment').style('font-size: 200%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        ui.label(f"Return equipment: {rental.equipment.name}")
        ui.label(f"Currently rented by: {rental.user.name}")
        ui.label(f"Rented since: {rental.rental_start.strftime('%Y-%m-%d %H:%M')}")
        
        ui.button("Confirm Return", on_click=on_confirm)
    dialog.open()

def filter_by_etype(e):
    """Filter equipment lists by equipment type"""
    selected_name = e.value
    state.selected_etype_id = state.etype_map.get(selected_name)
    update_lists()

def reset_filter():
    """Reset equipment type filter to show all equipment"""
    state.selected_etype_id = None
    update_lists()

#Fuctions for password for Admin mode
def create_password_dialog():
    """Creates dialogs for entering a password and successful entry."""
    password_dialog = ui.dialog()
    success_dialog = ui.dialog()

    with success_dialog:
        with ui.card():
            ui.label('CHANGE TO OTHER FUNCTION!')
            ui.button('OK', on_click=success_dialog.close)

    with password_dialog:
        with ui.card():
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Enter password:')
                ui.button(icon='close', on_click=password_dialog.close).props('flat round')
            password_input = ui.input(password=True)
            ui.button('Enter', on_click=lambda: check_password(password_input))
    
    def check_password(input_field):
        if input_field.value == "1234":  #Change password
            password_dialog.close()
            success_dialog.open()
        else:
            ui.notify('Wrong password', color='negative')
        input_field.set_value('')
    
    return password_dialog

def get_long_hold_callbacks():
    """
    Returns two colbacks to handle a long press:
      - on_mouse_down: starts a timer for 3 seconds to open the dialogue.
      - on_mouse_up: deactivates the timer if the button is released early.
    """
    password_dialog = create_password_dialog()
    hold_timer = None

    def start_hold(event):
        nonlocal hold_timer
        # Start the timer: if the button is held down for 2 seconds, a dialogue box will open.
        hold_timer = ui.timer(2, lambda: password_dialog.open(), once=True)

    def stop_hold(event):
        nonlocal hold_timer
        if hold_timer:
            hold_timer.deactivate()
            hold_timer = None

    return start_hold, stop_hold
    
    
def main():
    global available_container, rented_container
    
    # Get the list of equipment types once at startup
    state.etypes = get_all_etypes(db)
    
    # Build a mapping of etype names to their IDs
    for etype in state.etypes:
        state.etype_map[etype.name] = etype.id_et

    with ui.row().style('height: 80vh;'):
        with ui.column().style('width: 300px; padding: 10px; align-items: center; margin-top: 200px'):
            ui.button('Rent', on_click=lambda: ui.notify('Rent clicked')).style('width: 100px; height: 100px;')
            ui.button('Return', on_click=lambda: ui.notify('Return clicked')).style('width: 100px; height: 100px;')
            ui.button('Edit database', on_click=lambda: ui.notify('Edit database clicked')).style('width: 100px; height: 100px;')
            ui.button('Add Employee', on_click=show_add_user_dialog).style('width: 100px; height: 100px;')
            ui.button('Add Equipment', on_click=lambda: show_add_equipment_dialog(state.update_filter_select)).style('width: 100px; height: 100px;')

        with ui.column():
            # Equipment type filter
            with ui.column():
                ui.label('Filter by Equipment Type:').classes('text-h6')
                etype_options = [etype.name for etype in state.etypes]
                state.filter_select = ui.select(
                    options=etype_options,
                    label='Equipment Type',
                    on_change=filter_by_etype#,                    with_input=True
                ).style('width: 200px; margin-right: 10px;').props('use-chips')
            
            with ui.row():
                #Available list
                with ui.column():
                    ui.label('Available Equipment').classes('text-h5')
                    available_container = ui.scroll_area().style('border: 2px solid black; padding: 10px; height: 600px; width: 500px')
                    with available_container:
                        with ui.column():
                            for equipment in sorted(state.available_equipment, key=lambda x: x.name):
                                card = create_equipment_card(equipment)
                                card.on('click', lambda _, e=equipment: show_rent_dialog(e))
                #Rented list
                with ui.column():
                    ui.label('Rented Equipment').classes('text-h5')
                    rented_container = ui.scroll_area().style('border: 2px solid black; padding: 10px; height: 600px; width: 500px')
                    with rented_container:
                        with ui.column():
                            for rental in sorted(state.rented_equipment, key=lambda x: x.equipment.name):
                                card = create_equipment_card(rental, is_rented=True)
                                card.on('click', lambda _, r=rental: show_return_dialog(r))
    with ui.row().style('position: fixed; right: 25px; top: 25px;'):
        admin_button = ui.button().props('icon=admin_panel_settings').style('width: 150px; height: 150px; opacity: 100;')
        on_md, on_mu = get_long_hold_callbacks()
        admin_button.on('mousedown', on_md)
        admin_button.on('mouseup', on_mu)
    with ui.row().style('position: fixed; right: 30px; bottom: 30px'):
        button = ui.button(on_click=lambda: toggle_dark_mode(button))
        # Set the initial icon
        if dark_mode.value:
            button.props('icon=light_mode')
        else:
            button.props('icon=dark_mode')


if __name__ in {'__main__', '__mp_main__'}:
    main()
    ui.run()
