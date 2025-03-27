from nicegui import ui
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import get_available_equipment, get_all_users, create_rental
from database import SessionLocal

db = SessionLocal()

def create_equipment_filter(equipment_list, update_equipment_list):
    def on_type_select(e):
        update_equipment_list(equipment_list, e.value)

    with ui.row():
        ui.select(
            options=['weCat3D','ShapeDrive G4'],
            label='Equipment',
            with_input=True,
            on_change=on_type_select
        ).classes('w-full')
        
        ui.button('Show All', on_click=lambda: update_equipment_list(equipment_list))

def available_equipment_list():
    def rent_equipment(equipment, equipment_list):
        users = get_all_users(db)
        selected_user = None
        
        def on_user_select(e):
            nonlocal selected_user
            selected_user = e.value[1]
            
        def on_confirm(equipment_to_rent):
            if selected_user:
                create_rental(db, selected_user, equipment_to_rent.id_eq)
                ui.notify('Equipment rented successfully!')
                dialog.close()
                # Clear and update the equipment list
                equipment_list.clear()
                with equipment_list:
                    with ui.column():
                        for equipment in get_available_equipment(db):
                            card = ui.card().style('width: 450px; cursor: pointer;')
                            card.on('click', lambda _, equipment=equipment: rent_equipment(equipment, equipment_list))
                            with card:
                                ui.label(f"{equipment.name}")
                                ui.label(f"Serial: {equipment.serialnum}")
                                ui.label(f"Type: {equipment.etype.name}")
            else:
                ui.notify('Please select a user!', type='warning')

        with ui.dialog().style('width: 700px') as dialog, ui.card():
            with ui.row().classes('w-full justify-between items-center'):
                ui.label(text='Renting a device').style('font-size: 200%')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            ui.label(f"Name: {equipment.name}")
            ui.label(f"Serial: {equipment.serialnum}")
            ui.label(f"Type: {equipment.etype.name}")
            
            ui.label('Select user:')
            options = [(f"{user.name} ({user.department.name})", user.id_us) for user in users]
            
            ui.select(
                options=options,
                label='User',
                with_input=True,
                on_change=on_user_select
            ).classes('w-full')
            
            ui.button("Confirm", on_click=lambda: on_confirm(equipment))
        dialog.open()

    def update_equipment_list(scroll_area, selected_type=None):
        scroll_area.clear()
        with scroll_area:
            with ui.column():
                equipment_list = get_available_equipment(db)
                if selected_type:
                    equipment_list = [eq for eq in equipment_list if eq.etype.name == selected_type]
                
                for equipment in equipment_list:
                    card = ui.card().style('width: 450px; cursor: pointer;')
                    card.on('click', lambda _, equipment=equipment: rent_equipment(equipment, scroll_area))
                    with card:
                        ui.label(f"{equipment.name}")
                        ui.label(f"Serial: {equipment.serialnum}")
                        ui.label(f"Type: {equipment.etype.name}")

    def create_equipment_list():
        scroll_area = ui.scroll_area().style('border: 2px solid black; padding: 10px; height: 800px; width: 500px')
        update_equipment_list(scroll_area)
        return scroll_area

    equipment_list = create_equipment_list()
    create_equipment_filter(equipment_list, update_equipment_list)
    

available_equipment_list()
ui.run()