import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nicegui import ui
import crud
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Department

# Create a single DB instance
db = SessionLocal()

def edit_departments_dialog():
    """
    Opens a dialog for selecting and editing departments.
    """
    try:
        # Create a fresh session to ensure we get updated data
        with SessionLocal() as fresh_db:
            with ui.dialog() as dialog, ui.card().style('width: 600px; height: 800px'):
                ui.label('Select a department to edit').classes('text-h6 q-mb-md, w-540')
                
                # Create a scroll area for the department list
                with ui.scroll_area().style('height: 750px'):
                    # Get the list of all departments from the fresh DB session
                    departments = crud.get_all_departments_including_inactive(fresh_db)
                    # Sort departments alphabetically by name
                    departments = sorted(departments, key=lambda x: x.name.lower())
                    
                    # Create a card for each department
                    for department in departments:
                        with ui.card().classes('cursor-pointer').style('width: 100%;') as card:
                            with ui.row().classes('text-left'):
                                ui.icon('check_box' if department.status == True else 'check_box_outline_blank').classes(f'text-2xl {"text-green-500" if department.status else "text-red-500"}')                                  
                                ui.label(f'{department.name}').style('font-size: 110%; font-weight: bold')
                            
                            # Separate function to create a handler for each department
                            def make_handler(dept):
                                return lambda: show_edit_form_for_department(dept, dialog)
                            
                            card.on('click', make_handler(department))
                
                ui.button('Close', on_click=dialog.close).classes('q-mt-md')
            
            dialog.open()
        
    except Exception as e:
        ui.notify(f'Error opening the department list: {str(e)}', color='negative')
        print(f"Error in edit_departments_dialog: {str(e)}")  # for debugging


def show_edit_form_for_department(department, parent_dialog=None):
    """
    Creates and shows the department edit form.
    
    Args:
        department: Department object to edit
        parent_dialog: Parent dialog that opened this form
    """
    try:
        # Create a fresh session to get updated data
        with SessionLocal() as fresh_db:
            # Get fresh department data
            fresh_department = crud.get_department_including_inactive(fresh_db, department.id_dep)
            
            if not fresh_department:
                ui.notify(f'The department no longer exists in the database', color='negative')
                if parent_dialog:
                    parent_dialog.close()
                return
            
            # Create variables to store changes
            name_value = fresh_department.name
            status_value = fresh_department.status

            
            # Use dialog directly
            with ui.dialog() as edit_dialog, ui.card().classes('w-96'):
                ui.label(f'Editing department: {fresh_department.name}').classes('text-h6 q-mb-md')
                
                # Name edit field
                name_input = ui.input('Name', value=name_value).classes('w-full q-mb-sm')
                
                # Status switch
                with ui.row().classes('items-center q-mb-md'):
                    ui.label('Status (active):')
                    status_switch = ui.switch('', value=status_value)
                
                with ui.row().classes('justify-end'):
                    ui.button('Cancel', on_click=edit_dialog.close).classes('q-mr-sm')
                    ui.button('Apply', on_click=lambda: apply_changes(
                        fresh_department.id_dep,
                        name_input.value,
                        status_switch.value,
                        edit_dialog,
                        parent_dialog
                    )).classes('bg-primary')
                    
            # Open the new dialog
            edit_dialog.open()
            #ui.notify(f'Edit form opened for department: {fresh_department.name}', color='positive')
        
    except Exception as e:
        ui.notify(f'Error opening the edit form: {str(e)}', color='negative')
        print(f"Error in show_edit_form_for_department: {str(e)}")  # for debugging


def apply_changes(department_id, new_name, new_status, dialog, parent_dialog=None):
    """
    Applies changes to the department in the database.
    
    Args:
        department_id: Department ID
        new_name: New department name
        new_status: New department status
        dialog: Dialog to close after saving
        parent_dialog: Parent dialog to close if needed
    """
    try:
        # Create a new session for this operation
        with SessionLocal() as session:
            # Get the department first to verify it exists
            department = crud.get_department_including_inactive(session, department_id)
            
            if not department:
                ui.notify('Failed to update department - department not found', color='negative')
                return
                
            # Update department with new values
            department.name = new_name
            department.status = new_status
            session.commit()
            
            ui.notify(f'Department {new_name} successfully updated', color='positive')
            dialog.close()
            
            # If parent dialog exists, close it too
            if parent_dialog:
                parent_dialog.close()
            
            # Reopen the department list with refreshed data
            ui.timer(0.1, edit_departments_dialog, once=True)
    except Exception as e:
        ui.notify(f'Error updating: {str(e)}', color='negative')
        print(f"Error in apply_changes: {str(e)}")  # for debugging


def create_departments_edit_button(container=None):
    """
    Creates a button to open the department edit dialog.
    
    Args:
        container: Container where the button will be placed.
                  If None, the button is added to the current UI context.
    
    Returns:
        Button object
    """
    def safe_call_dialog(e):
        try:
            edit_departments_dialog()
        except Exception as e:
            ui.notify(f'Error opening dialog: {str(e)}', color='negative')
            print(f"Error calling dialog: {str(e)}")  # for debugging
    
    if container:
        with container:
            button = ui.button('Edit Departments', 
                              on_click=safe_call_dialog,
                              icon='edit').classes('bg-primary')
    else:
        button = ui.button('Edit Departments', 
                          on_click=safe_call_dialog,
                          icon='edit').classes('bg-primary')
    
    return button
