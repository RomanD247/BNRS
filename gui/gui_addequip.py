from nicegui import ui
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import create_equipment, create_etype, get_all_etypes, get_etype_by_name
from database import SessionLocal

db = SessionLocal()

# Load equipment types from database
def load_etypes():
    etypes = get_all_etypes(db)
    return [et.name for et in etypes]

data = load_etypes()

def show_add_etype_dialog(main_dropdown, main_data, main_selected_label, callback=None):
    def add_etype():
        new_et = new_et_input.value.strip()
        if not new_et:
            ui.notify('Please enter an equipment type name!', type='warning')
            return
        
        if new_et in main_data:
            ui.notify('This equipment type already exists!', type='warning')
            return
            
        try:
            create_etype(db, new_et)
            main_data.append(new_et)
            new_et_input.value = ''
            ui.notify(f'Equipment type {new_et} added successfully!')
            
            # Update dropdown items
            main_dropdown.clear()
            with main_dropdown:
                for item in main_data:
                    ui.item(item, on_click=lambda item=item: (main_selected_label.set_text(f'{item}'))).style('width: 300px')
            
            # Call the callback to update the filter dropdown in the main interface
            if callback:
                callback()
                
            dialog.close()
        except Exception as e:
            ui.notify(f'Error adding equipment type: {e}', type='error')

    with ui.dialog().props('persistent') as dialog, ui.card():
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(text='Adding a new equipment type').style('font-size: 200%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        ui.label(text='Enter equipment type name:')
        new_et_input = ui.input(label='Equipment type name')
        ui.separator()
        ui.button(text='Add equipment type', on_click=add_etype).style('width: 300px')

    dialog.open()

def show_add_equipment_dialog(callback=None):
    def add_equipment():
        name = name_input.value.strip()
        serialnum = serialnum_input.value.strip()
        etype_name = selected_label.text.replace('Selected: ', '').strip()

        if not name or etype_name == 'None':
            ui.notify('Please enter a name and select an equipment type!', type='warning')
            return

        try:
            etype = get_etype_by_name(db, etype_name)
            if not etype:
                ui.notify(f'Equipment type {etype_name} not found!', type='error')
                return
            create_equipment(db, name=name, serialnum=serialnum, etype_id=etype.id_et)
            ui.notify(f'Equipment {name} added successfully!')
            dialog.close()
        except Exception as e:
            ui.notify(f'Error: {e}', type='error')

    with ui.dialog().props('persistent') as dialog, ui.card():
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(text='Adding new equipment').style('font-size: 200%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        ui.label(text='Enter equipment name:')
        name_input = ui.input(label='Name').style('width: 300px')
        ui.separator()
        ui.label(text='Enter serial number:')
        serialnum_input = ui.input(label='Serial number').style('width: 300px')
        ui.separator()
        ui.label(text='Choose equipment type from the dropdown:')
        with ui.row():
            dropdown = ui.dropdown_button('Choose equipment type', auto_close=True, split=True)
            with dropdown:
                for item in data:
                    ui.item(item, on_click=lambda item=item: (selected_label.set_text(f'{item}'))).style('width: 300px')
            ui.button(text='+', on_click=lambda: show_add_etype_dialog(dropdown, data, selected_label, callback))
        selected_label = ui.label('You must choose equipment type!')
        ui.separator() 
        ui.button(text='Add new equipment', on_click=add_equipment).style('width: 300px; margin-left: 30px')

    dialog.open()
