from nicegui import ui
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import create_user, create_department, get_all_departments
from database import SessionLocal
from models import Department

db = SessionLocal()

# Loading departments from the database
def load_departments():
    departments = get_all_departments(db)
    return [dep.name for dep in departments]

data = load_departments()

def show_add_department_dialog(main_dropdown, main_data, main_selected_label):
    def add_department():
        new_dep = new_dep_input.value.strip()
        if not new_dep:
            ui.notify('Please enter a department name!', type='warning')
            return
        
        if new_dep in main_data:
            ui.notify('This department already exists!', type='warning')
            return
            
        try:
            create_department(db, new_dep)
            main_data.append(new_dep)
            new_dep_input.value = ''
            ui.notify(f'Department {new_dep} added successfully!')
            
            # Update dropdown items
            main_dropdown.clear()
            with main_dropdown:
                for item in main_data:
                    ui.item(item, on_click=lambda item=item: (main_selected_label.set_text(f'{item}'))).style('width: 300px')
            dialog.close()
        except Exception as e:
            ui.notify(f'Error adding department: {e}', type='error')

    with ui.dialog().props('persistent') as dialog, ui.card():
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(text='Adding a new department').style('font-size: 200%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        ui.label(text='Enter department name:')
        new_dep_input = ui.input(label='Department name')
        ui.separator()
        ui.button(text='Add department', on_click=add_department).style('width: 300px')

    dialog.open()

def show_add_user_dialog():
    def add_user():
        name = name_input.value.strip()
        dep = selected_label.text.replace('Selected: ', '').strip()

        if not name or dep == 'None':
            ui.notify('Please enter a name and select a department!', type='warning')
            return

        try:
            create_user(db, name=name, dep=dep)
            ui.notify(f'User {name} added to {dep}')
            dialog.close()
        except Exception as e:
            ui.notify(f'Error: {e}', type='error')

    with ui.dialog().props('persistent') as dialog, ui.card():
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(text='Adding a new employee').style('font-size: 200%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        ui.label(text='Enter your name:')
        name_input = ui.input(label='Name',).style('width: 300px')
        ui.separator()
        ui.label(text='Choose your department from the dropdown:')
        with ui.row():
            dropdown = ui.dropdown_button('Choose department', auto_close=True, split=True)
            with dropdown:
                for item in data:
                    ui.item(item, on_click=lambda item=item: (selected_label.set_text(f'{item}'))).style('width: 300px')
            ui.button(text='+', on_click=lambda: show_add_department_dialog(dropdown, data, selected_label))
        selected_label = ui.label('You must choose department!')
        ui.separator() 
        ui.button(text='Add new employee', on_click=add_user).style('width: 300px; margin-left: 30px')

    dialog.open()
