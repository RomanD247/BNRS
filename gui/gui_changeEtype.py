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
            with ui.dialog() as dialog, ui.card().style('width: 600px; height: 800px'):
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('Select an equipment type to edit').classes('text-h6 q-mb-md w-540')
                    ui.button(icon='close', on_click=dialog.close).props('flat round')
                
                # Create a scroll area for the equipment types list
                with ui.scroll_area().style('height: 750px'):
                    # Get the list of all equipment types from the fresh DB session
                    etypes = crud.get_all_etypes_including_inactive(fresh_db)
                    
                    # Create a card for each equipment type
                    for etype in etypes:
                        with ui.card().classes('cursor-pointer').style('width: 100%;') as card:
                            with ui.row().classes('text-left'):
                                ui.icon('check_box' if etype.status == True else 'check_box_outline_blank').classes(f'text-2xl {"text-green-500" if etype.status else "text-red-500"}')
                                ui.label(f'{etype.name}').classes('text-weight-bold')
                            
                            # Separate function to create a handler for each equipment type
                            def make_handler(et_id):
                                return lambda: show_edit_form_for_etype(et_id, dialog)
                            
                            card.on('click', make_handler(etype.id_et))

            # Delete the dialog element once hidden (unbounded-dialog-accumulation)
            dialog.on('hide', dialog.delete)
            dialog.open()
        
    except Exception as e:
        ui.notify(f'Error opening the equipment types list: {str(e)}', color='negative')
        print(f"Error in edit_etypes_dialog: {str(e)}")  # for debugging


def show_edit_form_for_etype(etype_id, parent_dialog=None):
    """
    Creates and shows the equipment type edit form.
    
    Args:
        etype_id: ID of Etype object to edit
        parent_dialog: Parent dialog that opened this form
    """
    try:
        # Create a fresh session to get updated data
        with SessionLocal() as fresh_db:
            # Get fresh equipment type data
            fresh_etype = fresh_db.query(Etype).filter(Etype.id_et == etype_id).first()
            
            if not fresh_etype:
                ui.notify(f'The equipment type no longer exists in the database', color='negative')
                if parent_dialog:
                    parent_dialog.close()
                return
            
            # Create variables to store changes
            name_value = fresh_etype.name
            status_value = fresh_etype.status

            # Use dialog directly
            with ui.dialog() as edit_dialog, ui.card().classes('w-96'):
                ui.label(f'Editing equipment type: {fresh_etype.name}').classes('text-h6 q-mb-md')
                
                # Name edit field
                name_input = ui.input('Name', value=name_value).classes('w-full q-mb-sm')
                
                # Status switch
                with ui.row().classes('items-center q-mb-md'):
                    ui.label('Status (active):')
                    status_switch = ui.switch('', value=status_value)
                
                # Bulk Apply button
                ui.button('Apply to All Equipment', on_click=lambda: apply_changes(
                    fresh_etype.id_et,
                    name_input.value,
                    status_switch.value,
                    True, # update_equipment = True
                    edit_dialog,
                    parent_dialog
                )).classes('bg-secondary')
                ui.label('This button will apply the same status to all equipment of this type').classes('text-caption q-mb-md')
                with ui.row().classes('justify-end'):
                    
                    # Standard Apply button (updates only this type)
                    ui.button('Apply', on_click=lambda: apply_changes(
                        fresh_etype.id_et,
                        name_input.value,
                        status_switch.value,
                        False, # update_equipment = False
                        edit_dialog,
                        parent_dialog
                    )).classes('bg-primary q-mr-sm')
                    
                    ui.button('Cancel', on_click=edit_dialog.close).classes('q-mr-sm')

            # Delete the dialog element once hidden (unbounded-dialog-accumulation)
            edit_dialog.on('hide', edit_dialog.delete)
            # Open the new dialog
            edit_dialog.open()
        
    except Exception as e:
        ui.notify(f'Error opening the edit form: {str(e)}', color='negative')
        print(f"Error in show_edit_form_for_etype: {str(e)}")  # for debugging


def apply_changes(etype_id, new_name, new_status, update_equipment, dialog, parent_dialog=None):
    """
    Applies changes to the equipment type in the database.
    
    Args:
        etype_id: Equipment type ID
        new_name: New equipment type name
        new_status: New equipment type status
        update_equipment: Boolean, whether to update status of all equipment of this type
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
            
            # Bulk update equipment if requested
            count = None
            if update_equipment:
                count = crud.update_etype_equipment_status(session, etype_id, new_status)

            session.commit()

            # Notify only after the commit has actually succeeded (bulk-status-commit-order)
            if count is not None:
                ui.notify(f'Updated status for {count} equipment items', color='positive')

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