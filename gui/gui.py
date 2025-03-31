from nicegui import ui
from t_guidial import create_gui
from gui_adduser import show_add_user_dialog
from gui_addequip import show_add_equipment_dialog
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
        self.selected_user = None
        self.selected_etype_id = None
        self.etype_map = {}

state = State()

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
        
        for user in sorted(get_all_users(db), key=lambda x: x.name):
            display_text = f"{user.name} ({user.department.name})"
            users_dict[display_text] = user.id_us
            options.append(display_text)
        
        ui.select(
            options=options,
            label='User',
            with_input=True,
            on_change=on_user_select_modified
        ).classes('w-full')
        
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

def main():
    global available_container, rented_container
    
    # Get the list of equipment types once at startup
    etypes = get_all_etypes(db)
    
    # Build a mapping of etype names to their IDs
    for etype in etypes:
        state.etype_map[etype.name] = etype.id_et

    with ui.row().style('height: 100vh;'):
        with ui.column().style('width: 300px; background-color: #f0f0f0; padding: 10px; align-items: center;'):
            ui.button('Rent', on_click=lambda: ui.notify('Rent clicked')).style('width: 100px; height: 100px;')
            ui.button('Return', on_click=lambda: ui.notify('Return clicked')).style('width: 100px; height: 100px;')
            ui.button('Edit database', on_click=lambda: ui.notify('Edit database clicked')).style('width: 100px; height: 100px;')
            ui.button('Add Employee', on_click=show_add_user_dialog).style('width: 100px; height: 100px;')
            ui.button('Add Equipment', on_click=show_add_equipment_dialog).style('width: 100px; height: 100px;')

        with ui.column():
            # Equipment type filter
            with ui.column():
                ui.label('Filter by Equipment Type:').classes('text-h6')
                etype_options = [etype.name for etype in etypes]
                filter_select = ui.select(
                    options=etype_options,
                    label='Equipment Type',
                    on_change=filter_by_etype
                ).style('width: 200px; margin-right: 10px;').props('use-chips')
            
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

if __name__ in {'__main__', '__mp_main__'}:
    main()
    ui.run()
