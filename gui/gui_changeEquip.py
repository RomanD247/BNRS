import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nicegui import ui
import crud
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Equipment

# Create a single DB instance
db = SessionLocal()

def edit_equipment_dialog():
    """
    Opens a dialog for selecting and editing equipment.
    """
    try:
        # Create a fresh session to ensure we get updated data
        with SessionLocal() as fresh_db:
            with ui.dialog() as dialog, ui.card().style('width: 600px; height: 800px'):
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('Select equipment to edit').classes('text-h6 q-mb-md, w-540')
                    ui.button(icon='close', on_click=dialog.close).props('flat round')
                
                # Create a scroll area for the equipment list
                with ui.scroll_area().style('height: 750px'):
                    # Get the list of all equipment from the fresh DB session
                    equipment_list = crud.get_all_equipment_including_inactive(fresh_db)
                    
                    # Create a card for each equipment
                    for equipment in equipment_list:
                        with ui.card().classes('cursor-pointer').style('width: 100%;') as card:
                            with ui.row().classes('text-left'):
                                ui.icon('check_box' if equipment.status == True else 'check_box_outline_blank').classes(f'text-2xl {"text-green-500" if equipment.status else "text-red-500"}')
                                with ui.column():
                                    ui.label(f'Name: {equipment.name}').classes('text-weight-bold').style('margin-top: -10px')
                                    ui.label(f'S/N: {equipment.serialnum}').style('margin-top: -10px')
                                    ui.label(f'Type: {equipment.etype.name if equipment.etype else "Unknown"}').style('margin-top: -10px; margin-bottom: -10px')
                            
                            # Separate function to create a handler for each equipment
                            def make_handler(eq):
                                return lambda: show_edit_form_for_equipment(eq, dialog)
                            
                            card.on('click', make_handler(equipment))
            
            dialog.open()
        
    except Exception as e:
        ui.notify(f'Error opening the equipment list: {str(e)}', color='negative')
        print(f"Error in edit_equipment_dialog: {str(e)}")  # for debugging


def show_edit_form_for_equipment(equipment, parent_dialog=None):
    """
    Creates and shows the equipment edit form.
    
    Args:
        equipment: Equipment object to edit
        parent_dialog: Parent dialog that opened this form
    """
    try:
        # Create a fresh session to get updated data
        with SessionLocal() as fresh_db:
            # Get fresh equipment data
            fresh_equipment = fresh_db.query(Equipment).filter(Equipment.id_eq == equipment.id_eq).first()
            
            if not fresh_equipment:
                ui.notify(f'The equipment no longer exists in the database', color='negative')
                if parent_dialog:
                    parent_dialog.close()
                return
            
            # Get all equipment types for the dropdown
            etypes = crud.get_all_etypes(fresh_db)
            
            # Create variables to store changes
            name_value = fresh_equipment.name
            serialnum_value = fresh_equipment.serialnum
            etype_value = fresh_equipment.etype.name if fresh_equipment.etype else None
            status_value = fresh_equipment.status

            
            # Use dialog directly
            with ui.dialog() as edit_dialog, ui.card().classes('w-96'):
                ui.label(f'Editing equipment: {fresh_equipment.name}').classes('text-h6 q-mb-md')
                
                # Name edit field
                name_input = ui.input('Name', value=name_value).classes('w-full q-mb-sm')
                
                # Serial number edit field
                serialnum_input = ui.input('Serial Number', value=serialnum_value).classes('w-full q-mb-sm')
                
                # Equipment type selection dropdown
                etype_options = [et.name for et in etypes]
                etype_select = ui.select(
                    label='Equipment Type',
                    options=etype_options,
                    value=etype_value
                ).classes('w-full q-mb-sm')
                
                # Status switch
                with ui.row().classes('items-center q-mb-md'):
                    ui.label('Status (active):')
                    status_switch = ui.switch('', value=status_value)
                
                with ui.row().classes('justify-end'):
                    ui.button('Cancel', on_click=edit_dialog.close).classes('q-mr-sm')
                    ui.button('Apply', on_click=lambda: apply_changes(
                        fresh_equipment.id_eq,
                        name_input.value,
                        serialnum_input.value,
                        etype_select.value,
                        status_switch.value,
                        edit_dialog,
                        parent_dialog
                    )).classes('bg-primary')
                    
            # Open the new dialog
            edit_dialog.open()
            #ui.notify(f'Edit form opened for equipment: {fresh_equipment.name}', color='positive')
        
    except Exception as e:
        ui.notify(f'Error opening the edit form: {str(e)}', color='negative')
        print(f"Error in show_edit_form_for_equipment: {str(e)}")  # for debugging


def apply_changes(equipment_id, new_name, new_serialnum, new_etype, new_status, dialog, parent_dialog=None):
    """
    Applies changes to the equipment in the database.
    
    Args:
        equipment_id: Equipment ID
        new_name: New equipment name
        new_serialnum: New serial number
        new_etype: New equipment type name
        new_status: New equipment status
        dialog: Dialog to close after saving
        parent_dialog: Parent dialog to close if needed
    """
    try:
        # Create a new session for this operation
        with SessionLocal() as session:
            # Get the equipment first to verify it exists
            equipment = session.query(Equipment).filter(Equipment.id_eq == equipment_id).first()
            
            if not equipment:
                ui.notify('Failed to update equipment - equipment not found', color='negative')
                return
            
            # Get the equipment type ID
            etype = crud.get_etype_by_name(session, new_etype)
            if not etype:
                ui.notify(f'Equipment type {new_etype} not found', color='negative')
                return
                
            # Update equipment with new values
            equipment.name = new_name
            equipment.serialnum = new_serialnum
            equipment.etype_id = etype.id_et
            equipment.status = new_status
            session.commit()
            
            ui.notify(f'Equipment {new_name} successfully updated', color='positive')
            dialog.close()
            
            # If parent dialog exists, close it too
            if parent_dialog:
                parent_dialog.close()
            
            # Reopen the equipment list with refreshed data
            ui.timer(0.1, edit_equipment_dialog, once=True)
    except Exception as e:
        ui.notify(f'Error updating: {str(e)}', color='negative')
        print(f"Error in apply_changes: {str(e)}")  # for debugging 