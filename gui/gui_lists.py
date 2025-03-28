from nicegui import ui
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

# Create reactive state
class State:
    def __init__(self):
        self.available_equipment = get_available_equipment(db)
        self.rented_equipment = get_active_rentals(db)
        self.selected_user = None
        self.selected_etype_id = None  # Changed to store ID instead of name
        # Map of etype names to their IDs for easier lookup
        self.etype_map = {}

state = State()

def create_equipment_card(equipment, is_rented=False):
    """Create a card for equipment display"""
    card = ui.card().style('width: 450px; cursor: pointer;')
    
    with card:
        if is_rented:
            # If it's a rental, use rental.equipment properties
            ui.label(f"{equipment.equipment.name}")
            ui.label(f"Serial111: {equipment.equipment.serialnum}")
            ui.label(f"Type: {equipment.equipment.etype.name if equipment.equipment.etype else 'Unknown'}")
            ui.label(f"Rented by: {equipment.user.name} ({equipment.user.department.name})")
            ui.label(f"Rented since: {equipment.rental_start.strftime('%Y-%m-%d %H:%M')}")
        else:
            # If it's equipment, use properties directly
            ui.label(f"{equipment.name}")
            ui.label(f"Serial222: {equipment.serialnum}")
            ui.label(f"Type: {equipment.etype.name if equipment.etype else 'Unknown'}")
    
    return card

def update_lists():
    """Update both equipment lists"""
    # Get equipment based on filter selection
    if state.selected_etype_id is not None:
        # Use specialized functions for filtering by type
        state.available_equipment = get_available_equipment_by_type(db, state.selected_etype_id)
        state.rented_equipment = get_active_rentals_by_equipment_type(db, state.selected_etype_id)
    else:
        # Get all equipment (no filter)
        state.available_equipment = get_available_equipment(db)
        state.rented_equipment = get_active_rentals(db)
    
    # Clear and update available equipment list
    available_container.clear()
    with available_container:
        with ui.column():
            for equipment in sorted(state.available_equipment, key=lambda x: x.name):
                card = create_equipment_card(equipment)
                card.on('click', lambda _, e=equipment: show_rent_dialog(e))
    
    # Clear and update rented equipment list
    rented_container.clear()
    with rented_container:
        with ui.column():
            for rental in sorted(state.rented_equipment, key=lambda x: x.equipment.name):
                card = create_equipment_card(rental, is_rented=True)
                card.on('click', lambda _, r=rental: show_return_dialog(r))

def show_rent_dialog(equipment):
    """Show dialog for renting equipment"""
    def on_user_select(e):
        # Check if e.value is a tuple and get the second element (ID)
        if isinstance(e.value, tuple) and len(e.value) > 1:
            state.selected_user = e.value[1]
        else:
            state.selected_user = e.value
    
    def on_confirm():
        if state.selected_user:
            create_rental(db, state.selected_user, equipment.id_eq)
            ui.notify('Equipment rented successfully!')
            dialog.close()
            # Сбрасываем фильтр после успешной аренды
            reset_filter()
        else:
            ui.notify('Please select a user!', type='warning')

    with ui.dialog().style('width: 700px') as dialog, ui.card():
        ui.label(f"Rent equipment: {equipment.name}")
        ui.label(f"Serial: {equipment.serialnum}")
        ui.label(f"Type: {equipment.etype.name if equipment.etype else 'Unknown'}")
        
        ui.label('Select user:')
        options = [(f"{user.name} ({user.department.name})", user.id_us) 
                  for user in sorted(get_all_users(db), key=lambda x: x.name)]
        
        ui.select(
            options=options,
            label='User',
            with_input=True,
            on_change=on_user_select
        ).classes('w-full')
        
        ui.button("Confirm", on_click=on_confirm)
        ui.button("Close", on_click=dialog.close)
    dialog.open()

def show_return_dialog(rental):
    """Show dialog for returning equipment"""
    def on_confirm():
        return_equipment(db, rental.id_re)
        ui.notify('Equipment returned successfully!')
        dialog.close()
        # Сбрасываем фильтр после успешного возврата
        reset_filter()

    with ui.dialog().style('width: 700px') as dialog, ui.card():
        ui.label(f"Return equipment: {rental.equipment.name}")
        ui.label(f"Currently rented by: {rental.user.name}")
        ui.label(f"Rented since: {rental.rental_start.strftime('%Y-%m-%d %H:%M')}")
        
        ui.button("Confirm Return", on_click=on_confirm)
        ui.button("Close", on_click=dialog.close)
    dialog.open()

def filter_by_etype(e):
    """Filter equipment lists by equipment type"""
    selected_name = e.value
    
    # Convert selected name to ID using our mapping
    state.selected_etype_id = state.etype_map.get(selected_name)
    update_lists()

def reset_filter():
    """Reset equipment type filter to show all equipment"""
    state.selected_etype_id = None
    update_lists()

# Get the list of equipment types once at startup
etypes = get_all_etypes(db)

# Build a mapping of etype names to their IDs
for etype in etypes:
    state.etype_map[etype.name] = etype.id_et

with ui.row():
    # Equipment type filter
    with ui.column():
        ui.label('Filter by Equipment Type:').classes('text-h6')
        
        with ui.row():
            # Create options as simple strings (names only)
            etype_options = [etype.name for etype in etypes]
            
            # Выпадающий список типов оборудования
            filter_select = ui.select(
                options=etype_options,
                label='Equipment Type',
                on_change=filter_by_etype
            ).style('width: 200px; margin-right: 10px;')
            
            # Кнопка сброса фильтра
            ui.button('Show All', on_click=reset_filter).style('margin-top: 20px;')

# Create lists layout
with ui.row():
    # Available equipment list
    with ui.column():
        ui.label('Available Equipment').classes('text-h5')
        available_container = ui.scroll_area().style('border: 2px solid black; padding: 10px; height: 800px; width: 500px')
        with available_container:
            with ui.column():
                for equipment in sorted(state.available_equipment, key=lambda x: x.name):
                    card = create_equipment_card(equipment)
                    card.on('click', lambda _, e=equipment: show_rent_dialog(e))
    
    # Rented equipment list
    with ui.column():
        ui.label('Rented Equipment').classes('text-h5')
        rented_container = ui.scroll_area().style('border: 2px solid black; padding: 10px; height: 800px; width: 500px')
        with rented_container:
            with ui.column():
                for rental in sorted(state.rented_equipment, key=lambda x: x.equipment.name):
                    card = create_equipment_card(rental, is_rented=True)
                    card.on('click', lambda _, r=rental: show_return_dialog(r))

ui.run()