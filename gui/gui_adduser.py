from nicegui import ui
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import create_user, create_department, get_all_departments, find_user_by_nfc
from database import SessionLocal
from NfcScan import get_nfc_input

db = SessionLocal()

# Loading departments from the database
def load_departments():
    departments = get_all_departments(db)
    return [dep.name for dep in departments]

data = load_departments()

# Function to refresh departments list from database
def refresh_departments():
    """Refreshes the departments list from database"""
    global data
    db.expire_all()  # Expire session cache
    data = load_departments()
    return data

def show_add_department_dialog(callback=None):
    """
    Shows a dialog to add a new department.
    
    Args:
        callback: Optional function to call after successful department creation
    """
    def add_department():
        new_dep = new_dep_input.value.strip()
        if not new_dep:
            ui.notify('Please enter a department name!', type='warning')
            return
        
        if new_dep in data:
            ui.notify('This department already exists!', type='warning')
            return
            
        try:
            create_department(db, new_dep)
            data.append(new_dep)
            new_dep_input.value = ''
            ui.notify(f'Department {new_dep} added successfully!')
            
            # Call the callback function if provided
            if callback:
                callback(new_dep)
                
            dialog.close()
        except Exception as e:
            ui.notify(f'Error adding department: {e}', type='error')

    with ui.dialog() as dialog, ui.card():
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(text='Adding a new department').style('font-size: 200%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        ui.label(text='Enter department name:')
        new_dep_input = ui.input(label='Department name')
        ui.separator()
        ui.button(text='Add department', on_click=add_department).style('width: 300px')

    dialog.open()

def show_add_user_dialog(callback=None):
    nfc_value = None
    nfc_label = None

    async def scan_nfc():
        nonlocal nfc_value, nfc_label
        nfc_value = await get_nfc_input("Scan NFC tag")
        if nfc_value:
            # Проверяем, не занят ли уже этот NFC код
            existing_user = find_user_by_nfc(db, nfc_value)
            if existing_user:
                ui.notify(f'NFC tag already registered to user {existing_user.name}', type='warning')
                nfc_value = None
                nfc_label.set_text('NFC: Not set')
            else:
                nfc_label.set_text(f'NFC scanned')
        else:
            nfc_label.set_text('NFC: Not set')

    def add_user():
        name = name_input.value.strip()
        dep = selected_label.text.replace('Selected: ', '').strip()

        if not name or dep == 'None':
            ui.notify('Please enter a name and select a department!', type='warning')
            return

        try:
            create_user(db, name=name, dep=dep, nfc=nfc_value)
            ui.notify(f'User {name} added to {dep}')
            
            # Call the callback function if provided
            if callback:
                callback()
                
            dialog.close()
        except Exception as e:
            ui.notify(f'Error: {e}', type='error')

    with ui.dialog() as dialog, ui.card():
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(text='Adding a new employee').style('font-size: 200%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        ui.label(text='Enter your name:')
        name_input = ui.input(label='Name',).style('width: 300px')
        ui.separator()
        ui.label(text='Choose your department from the dropdown:')
        with ui.row():
            dropdown = ui.dropdown_button('Choose department', auto_close=True)
            with dropdown:
                for item in data:
                    ui.item(item, on_click=lambda item=item: (selected_label.set_text(f'{item}'))).style('width: 300px')
        selected_label = ui.label('You must choose department!')
        
            # Добавляем кнопку и метку для NFC #!NFC_feature
        # ui.separator()
        # with ui.row().classes('w-full justify-between items-center'):
        #     ui.button('Scan NFC', on_click=scan_nfc)
        #     nfc_label = ui.label('NFC: Not set')
        
        ui.separator() 
        ui.button(text='Add new employee', on_click=add_user).style('width: 300px; margin-left: 30px')

    dialog.open()
