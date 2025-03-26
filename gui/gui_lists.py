from nicegui import ui
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import get_available_equipment, get_all_users, create_rental
from database import SessionLocal

db = SessionLocal()

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
            ui.button("Close", on_click=dialog.close)
        dialog.open()

    def create_equipment_list():
        with ui.scroll_area().style('border: 2px solid black; padding: 10px; height: 800px; width: 500px') as scroll_area:
            with ui.column():
                for equipment in get_available_equipment(db):
                    card = ui.card().style('width: 450px; cursor: pointer;')
                    card.on('click', lambda _, equipment=equipment: rent_equipment(equipment, scroll_area))
                    with card:
                        ui.label(f"{equipment.name}")
                        ui.label(f"Serial: {equipment.serialnum}")
                        ui.label(f"Type: {equipment.etype.name}")
        return scroll_area

    equipment_list = create_equipment_list()

available_equipment_list()
ui.run()