import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nicegui import ui
import crud
from sqlalchemy.orm import Session
from database import SessionLocal

# Create a single DB instance
db = SessionLocal()

def edit_users_dialog():
    """
    Opens a dialog for selecting and editing users.
    """
    try:
        # Create a fresh session to ensure we get updated data
        with SessionLocal() as fresh_db:
            with ui.dialog() as dialog, ui.card().style('width: 600px; height: 800px'):
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('Select a user to edit').classes('text-h6 q-mb-md, w-540')
                    ui.button(icon='close', on_click=dialog.close).props('flat round')
                
                # Create a scroll area for the user list
                with ui.scroll_area().style('height: 750px'): #.classes('h-96'):
                    # Get the list of all users from the fresh DB session
                    users = crud.get_all_users_including_inactive(fresh_db)
                    
                    # Create a card for each user
                    for user in users:
                        with ui.card().classes('q-mb-sm cursor-pointer') as card:
                            with ui.row().classes('text-left'):
                                ui.icon('check_box' if user.status == True else 'check_box_outline_blank').classes('text-2xl')
                                #ui.checkbox(value=True if user.status == True else False).props('disable')
                                with ui.column():
                                    ui.label(f'Name: {user.name}')
                                    ui.label(f'Department: {user.department.name}') 
                            # Separate function to create a handler for each user
                            def make_handler(u):
                                return lambda: show_edit_form_for_user(u, dialog)
                            
                            card.on('click', make_handler(user))
            
            dialog.open()
        
    except Exception as e:
        ui.notify(f'Error opening user list: {str(e)}', color='negative')
        print(f"Error in edit_users_dialog: {str(e)}")  # for debugging


def show_edit_form_for_user(user, parent_dialog=None):
    """
    Creates and shows the user edit form.
    
    Args:
        user: User object to edit
        parent_dialog: Parent dialog that opened this form
    """
    try:
        # Create a fresh session to get updated data
        with SessionLocal() as fresh_db:
            # Get data with fresh session
            departments = crud.get_all_departments(fresh_db)
            
            # Get fresh user data
            fresh_user = crud.get_user_including_inactive(fresh_db, user.id_us)
            if not fresh_user:
                ui.notify(f'User no longer exists in database', color='negative')
                if parent_dialog:
                    parent_dialog.close()
                return
            
            # Create variables to store changes
            name_value = fresh_user.name
            department_value = fresh_user.department.name
            status_value = fresh_user.status
            
            # Close all open dialogs
            ui.notify(f'Preparing form for: {fresh_user.name}', color='info')
            
            # Use dialog directly
            with ui.dialog() as edit_dialog, ui.card().classes('w-96'):
                ui.label(f'Editing user: {fresh_user.name}').classes('text-h6 q-mb-md')
                
                # Name edit field
                name_input = ui.input('Name', value=name_value).classes('w-full q-mb-sm')
                
                # Department selection dropdown
                department_select = ui.select(
                    label='Department',
                    options=[dept.name for dept in departments],
                    value=department_value
                ).classes('w-full q-mb-sm')
                
                # Status switch
                with ui.row().classes('items-center q-mb-md'):
                    ui.label('Status (active):')
                    status_switch = ui.switch('', value=status_value)
                
                with ui.row().classes('justify-end'):
                    ui.button('Cancel', on_click=edit_dialog.close).classes('q-mr-sm')
                    ui.button('Apply', on_click=lambda: apply_changes(
                        fresh_user.id_us,
                        name_input.value,
                        department_select.value,
                        status_switch.value,
                        edit_dialog,
                        parent_dialog
                    )).classes('bg-primary')
                    
            # Open the new dialog
            edit_dialog.open()
            ui.notify(f'Edit form opened for user: {fresh_user.name}', color='positive')
        
    except Exception as e:
        ui.notify(f'Error opening edit form: {str(e)}', color='negative')
        print(f"Error in show_edit_form_for_user: {str(e)}")  # for debugging


# This function is no longer used directly
def open_edit_form(user, parent_dialog):
    """
    Deprecated function, use show_edit_form_for_user instead
    """
    try:
        parent_dialog.close()
        show_edit_form_for_user(user)
    except Exception as e:
        ui.notify(f'Error: {str(e)}', color='negative')


def apply_changes(user_id, new_name, new_department, new_status, dialog, parent_dialog=None):
    """
    Applies changes to the user in the database.
    
    Args:
        user_id: User ID
        new_name: New user name
        new_department: New department name
        new_status: New user status
        dialog: Dialog to close after saving
        parent_dialog: Parent dialog to close if needed
    """
    try:
        # Create a new session for this operation
        with SessionLocal() as session:
            # Update user with new session
            updated_user = crud.update_user(session, user_id, name=new_name, dep=new_department, status=new_status, get_user_func=crud.get_user_including_inactive)
            
            if updated_user:
                ui.notify(f'User {new_name} successfully updated', color='positive')
                dialog.close()
                
                # If parent dialog exists, close it too
                if parent_dialog:
                    parent_dialog.close()
                
                # Reopen the user list with refreshed data
                ui.timer(0.1, edit_users_dialog, once=True)
            else:
                ui.notify('Failed to update user - user not found', color='negative')
    except Exception as e:
        ui.notify(f'Error during update: {str(e)}', color='negative')
        print(f"Error in apply_changes: {str(e)}")  # for debugging



