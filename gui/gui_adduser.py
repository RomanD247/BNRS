from nicegui import ui
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import (
    create_user, create_department, get_all_departments,
    get_department_by_name_including_inactive, find_user_by_nfc_including_inactive
)
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
        
        existing_dep = get_department_by_name_including_inactive(db, new_dep)
        if existing_dep:
            if existing_dep.status:
                ui.notify('This department already exists!', type='warning')
            else:
                ui.notify('This name belongs to a deactivated department. Reactivate it instead of creating a new one.', type='warning')
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
        with ui.row().classes('w-full justify-between items-center no-wrap'):
            ui.label(text='Adding a new department').style('font-size: 200%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        ui.label(text='Enter department name:')
        new_dep_input = ui.input(label='Department name')
        ui.separator()
        ui.button(text='Add department', on_click=add_department).style('width: 300px')

    dialog.open()

def show_add_user_dialog(callback=None):
    refresh_departments()

    nfc_value = None
    nfc_icon = None
    nfc_text = None
    selected_dep_name = None

    def set_nfc_status(has_code, text):
        # Uses ui.icon()/ui.label() rather than raw ui.html() ligature text -
        # ui.html() content goes through the browser's HTML sanitizer, which
        # strips the material-icons class and leaves the literal ligature
        # text ("check_box") on screen instead of the glyph
        # (sanitizer-strips-icon-ligature-class).
        nfc_icon.set_name('check_box' if has_code else 'check_box_outline_blank')
        nfc_icon.set_text_color('green-500' if has_code else 'red-500')
        nfc_text.set_text(text)

    async def scan_nfc():
        nonlocal nfc_value
        nfc_value, scan_status = await get_nfc_input("Scan Data Matrix Code")
        nfc_value = nfc_value.lower() if nfc_value else None
        if nfc_value:
            # Check if this NFC code is already taken (M3: includes soft-deleted users)
            existing_user = find_user_by_nfc_including_inactive(db, nfc_value)
            if existing_user:
                suffix = '' if existing_user.status else ' (deactivated)'
                ui.notify(f'Data Matrix Code already registered to user {existing_user.name}{suffix}', type='warning')
                nfc_value = None
                set_nfc_status(False, 'Pass: Not set')
            else:
                set_nfc_status(True, 'Code scanned')
        else:
            set_nfc_status(False, 'Pass: Not set')

    def select_department(item):
        nonlocal selected_dep_name
        selected_dep_name = item
        selected_label.set_text(f'{item}')

    def add_user():
        name = name_input.value.strip()

        if not name or not selected_dep_name:
            ui.notify('Please enter a name and select a department!', type='warning')
            return

        try:
            create_user(db, name=name, dep=selected_dep_name, nfc=nfc_value)
            ui.notify(f'User {name} added to {selected_dep_name}')
            
            # Call the callback function if provided
            if callback:
                callback()
                
            dialog.close()
        except Exception as e:
            ui.notify(f'Error: {e}', type='error')

    with ui.dialog() as dialog, ui.card().classes('leading-none').style('''
        position: absolute;
        left: 20%;
        top: 20%;
        transform: none;
    '''):
        with ui.row().classes('w-full justify-between items-center no-wrap'):
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
                    ui.item(item, on_click=lambda item=item: select_department(item)).style('width: 300px')
        selected_label = ui.label('You must choose department!')
        
            # Add a button and tag for NFC #!NFC_feature
        # ui.separator()
        # with ui.row().classes('w-full justify-between items-center'):
        #     ui.button('Scan Data Matrix Code', on_click=scan_nfc)
        #     with ui.row().classes('items-center gap-1'):
        #         nfc_icon = ui.icon('check_box_outline_blank', color='red-500')
        #         nfc_text = ui.label('Pass: Not set').classes('text-bold')
            
            
        ui.separator() 
        ui.button(text='Add new employee', on_click=add_user).style('width: 300px; margin-left: 30px')

    dialog.open()
