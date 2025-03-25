from nicegui import ui
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import create_user
from database import SessionLocal

data = [
    "CS - Central Sales",
    "CS-TS - Technical Support",
    "DE - Development",
]

db = SessionLocal()

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

    with ui.dialog() as dialog, ui.card():
        ui.label(text='Add new employee').style('font-size: 18px')
        name_input = ui.input(label='Name', placeholder='Enter your name')

        with ui.dropdown_button('Choose your department', auto_close=True, split=True):
            for item in data:
                ui.item(item, on_click=lambda item=item: (selected_label.set_text(f'Selected: {item}')))
        selected_label = ui.label('Selected: None')

        ui.button(text='Add new user', on_click=add_user)
        ui.button(text='Cancel', on_click=dialog.close)

    dialog.open()
