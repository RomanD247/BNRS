import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nicegui import ui
import crud
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Etype

# Create a single DB instance
db = SessionLocal()

def edit_etypes_dialog():
    """
    Opens a dialog for selecting and editing equipment types.
    """
    try:
        # Create a fresh session to ensure we get updated data
        with SessionLocal() as fresh_db:
            with ui.dialog() as dialog, ui.card().classes('w-540'):
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('Select an equipment type to edit').classes('text-h6 q-mb-md, w-540')
                    ui.button(icon='close', on_click=dialog.close).props('flat round')
                
                # Create a scroll area for the equipment types list
                with ui.scroll_area().classes('h-96'):
                    # Get the list of all equipment types from the fresh DB session
                    etypes = crud.get_all_etypes_including_inactive(fresh_db)
                    
                    # Create a card for each equipment type
                    for etype in etypes:
                        with ui.card().classes('q-mb-sm cursor-pointer') as card:
                            ui.label(f'Name: {etype.name}').classes('text-weight-bold')
                            ui.label(f'Status: {"Active" if etype.status else "Inactive"}')
                            
                            # Separate function to create a handler for each equipment type
                            def make_handler(et):
                                return lambda: show_edit_form_for_etype(et, dialog)
                            
                            card.on('click', make_handler(etype))
            
            dialog.open()
        
    except Exception as e:
        ui.notify(f'Error opening the equipment types list: {str(e)}', color='negative')
        print(f"Error in edit_etypes_dialog: {str(e)}")  # for debugging


def show_edit_form_for_etype(etype, parent_dialog=None):
    """
    Creates and shows the equipment type edit form.
    
    Args:
        etype: Etype object to edit
        parent_dialog: Parent dialog that opened this form
    """
    try:
        # Create a fresh session to get updated data
        with SessionLocal() as fresh_db:
            # Get fresh equipment type data
            # Since there's no specific function for this in crud, we use a direct query
            fresh_etype = fresh_db.query(Etype).filter(Etype.id_et == etype.id_et).first()
            
            if not fresh_etype:
                ui.notify(f'The equipment type no longer exists in the database', color='negative')
                if parent_dialog:
                    parent_dialog.close()
                return
            
            # Create variables to store changes
            name_value = fresh_etype.name
            status_value = fresh_etype.status
            
            # Notify user
            ui.notify(f'Preparing form for: {fresh_etype.name}', color='info')
            
            # Use dialog directly
            with ui.dialog() as edit_dialog, ui.card().classes('w-96'):
                ui.label(f'Editing equipment type: {fresh_etype.name}').classes('text-h6 q-mb-md')
                
                # Name edit field
                name_input = ui.input('Name', value=name_value).classes('w-full q-mb-sm')
                
                # Status switch
                with ui.row().classes('items-center q-mb-md'):
                    ui.label('Status (active):')
                    status_switch = ui.switch('', value=status_value)
                
                with ui.row().classes('justify-end'):
                    ui.button('Cancel', on_click=edit_dialog.close).classes('q-mr-sm')
                    ui.button('Apply', on_click=lambda: apply_changes(
                        fresh_etype.id_et,
                        name_input.value,
                        status_switch.value,
                        edit_dialog,
                        parent_dialog
                    )).classes('bg-primary')
                    
            # Open the new dialog
            edit_dialog.open()
            ui.notify(f'Edit form opened for equipment type: {fresh_etype.name}', color='positive')
        
    except Exception as e:
        ui.notify(f'Error opening the edit form: {str(e)}', color='negative')
        print(f"Error in show_edit_form_for_etype: {str(e)}")  # for debugging


def apply_changes(etype_id, new_name, new_status, dialog, parent_dialog=None):
    """
    Applies changes to the equipment type in the database.
    
    Args:
        etype_id: Equipment type ID
        new_name: New equipment type name
        new_status: New equipment type status
        dialog: Dialog to close after saving
        parent_dialog: Parent dialog to close if needed
    """
    try:
        # Create a new session for this operation
        with SessionLocal() as session:
            # Get the equipment type first to verify it exists
            etype = session.query(Etype).filter(Etype.id_et == etype_id).first()
            
            if not etype:
                ui.notify('Failed to update equipment type - not found', color='negative')
                return
                
            # Update equipment type with new values
            etype.name = new_name
            etype.status = new_status
            session.commit()
            
            ui.notify(f'Equipment type {new_name} successfully updated', color='positive')
            dialog.close()
            
            # If parent dialog exists, close it too
            if parent_dialog:
                parent_dialog.close()
            
            # Reopen the equipment types list with refreshed data
            ui.timer(0.1, edit_etypes_dialog, once=True)
    except Exception as e:
        ui.notify(f'Error updating: {str(e)}', color='negative')
        print(f"Error in apply_changes: {str(e)}")  # for debugging 