import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nicegui import ui
import crud
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Rental
import datetime

# Create a single DB instance
db = SessionLocal()

def edit_rentals_dialog():
    """
    Opens a dialog for selecting and editing rental records.
    """
    try:
        # Create a fresh session to ensure we get updated data
        with SessionLocal() as fresh_db:
            with ui.dialog() as dialog, ui.card().style('max-width: none; width: 1200px; height: 600px'):
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('Select a rental record to edit').classes('text-h6 q-mb-md, w-1140')
                    ui.button(icon='close', on_click=dialog.close).props('flat round')
                
                # Create a scroll area for the rental list
                with ui.scroll_area().style('height: 550px'):
                    try:
                        # Get the list of all rental records from the fresh DB session
                        rentals = crud.get_all_rentals(fresh_db)
                        
                        if not rentals:
                            ui.label('No rental records found').classes('text-center q-mt-lg')
                        else:
                            # Create a table for rental records
                            columns = [
                                {'name': 'id', 'label': 'ID', 'field': 'id_re', 'align': 'left'},
                                {'name': 'user', 'label': 'User Name', 'field': 'user_name', 'align': 'left'},
                                {'name': 'equipment', 'label': 'Equipment Name', 'field': 'equipment_name', 'align': 'left'},
                                {'name': 'start', 'label': 'Start Date', 'field': 'rental_start', 'align': 'left'},
                                {'name': 'end', 'label': 'End Date', 'field': 'rental_end', 'align': 'left'},
                                {'name': 'comment', 'label': 'Comment', 'field': 'comment', 'align': 'left'}
                            ]
                            
                            # Prepare data for the table
                            rows = []
                            for rental in rentals:
                                try:
                                    # Format equipment display with name and serial number
                                    equipment_display = 'Unknown Equipment'
                                    if rental.equipment:
                                        equipment_name = rental.equipment.name
                                        equipment_serial = rental.equipment.serialnum if rental.equipment.serialnum else 'No S/N'
                                        equipment_display = f"{equipment_name} (S/N: {equipment_serial})"
                                    
                                    rows.append({
                                        'id_re': rental.id_re,
                                        'user_name': rental.user.name if rental.user else 'Unknown User',
                                        'equipment_name': equipment_display,
                                        'rental_start': rental.rental_start.strftime('%Y-%m-%d %H:%M:%S') if rental.rental_start else 'No start date',
                                        'rental_end': rental.rental_end.strftime('%Y-%m-%d %H:%M:%S') if rental.rental_end else 'Not returned',
                                        'comment': rental.comment or ''
                                    })
                                except Exception as row_error:
                                    print(f"Error processing rental record {rental.id_re}: {str(row_error)}")
                                    # Add a row with error information
                                    rows.append({
                                        'id_re': rental.id_re,
                                        'user_name': 'Error loading data',
                                        'equipment_name': 'Error loading data',
                                        'rental_start': 'Error',
                                        'rental_end': 'Error',
                                        'comment': f'Error: {str(row_error)}'
                                    })
                            
                            # Create the table
                            table = ui.table(columns=columns, rows=rows, row_key='id_re')
                            table.classes('w-full')
                            
                            # Add click handler for table rows
                            def handle_row_click(event):
                                try:
                                    rental_id = event.args[1]['id_re']
                                    # Find the rental object
                                    selected_rental = next((r for r in rentals if r.id_re == rental_id), None)
                                    if selected_rental:
                                        show_edit_form_for_rental(selected_rental, dialog)
                                    else:
                                        ui.notify(f'Rental record with ID {rental_id} not found', color='negative')
                                except Exception as click_error:
                                    ui.notify(f'Error selecting rental record: {str(click_error)}', color='negative')
                                    print(f"Error in handle_row_click: {str(click_error)}")
                            
                            table.on('rowClick', handle_row_click)
                    
                    except Exception as data_error:
                        ui.notify(f'Error loading rental data: {str(data_error)}', color='negative')
                        print(f"Error loading rental data: {str(data_error)}")
                        ui.label('Failed to load rental records. Please try again.').classes('text-center q-mt-lg text-negative')
            
            dialog.open()
        
    except Exception as e:
        ui.notify(f'Critical error opening rental editor: {str(e)}', color='negative')
        print(f"Critical error in edit_rentals_dialog: {str(e)}")  # for debugging


def show_edit_form_for_rental(rental, parent_dialog=None):
    """
    Creates and shows the rental edit form.
    
    Args:
        rental: Rental object to edit
        parent_dialog: Parent dialog that opened this form
    """
    try:
        # Create a fresh session to get updated data
        with SessionLocal() as fresh_db:
            try:
                # Get fresh rental data
                fresh_rental = crud.get_rental(fresh_db, rental.id_re)
                if not fresh_rental:
                    ui.notify(f'Rental record with ID {rental.id_re} no longer exists in database', color='negative')
                    if parent_dialog:
                        parent_dialog.close()
                    return
                
                # Get all active users and equipment for dropdowns
                users = crud.get_all_users(fresh_db)
                equipment_list = crud.get_all_equipment(fresh_db)
                
                # Validate that we have users and equipment available
                if not users:
                    ui.notify('No active users found. Cannot edit rental record.', color='negative')
                    return
                
                if not equipment_list:
                    ui.notify('No active equipment found. Cannot edit rental record.', color='negative')
                    return
                
                # Create variables to store form values with error handling
                try:
                    user_value = fresh_rental.user.name if fresh_rental.user else None
                except AttributeError:
                    user_value = None
                    print(f"Warning: Rental {fresh_rental.id_re} has invalid user reference")
                
                try:
                    if fresh_rental.equipment:
                        equipment_name = fresh_rental.equipment.name
                        equipment_serial = fresh_rental.equipment.serialnum if fresh_rental.equipment.serialnum else 'No S/N'
                        equipment_value = f"{equipment_name} (S/N: {equipment_serial})"
                    else:
                        equipment_value = None
                except AttributeError:
                    equipment_value = None
                    print(f"Warning: Rental {fresh_rental.id_re} has invalid equipment reference")
                
                try:
                    rental_start_value = fresh_rental.rental_start.strftime('%Y-%m-%dT%H:%M') if fresh_rental.rental_start else ''
                except (AttributeError, ValueError) as date_error:
                    rental_start_value = ''
                    print(f"Warning: Invalid rental start date for rental {fresh_rental.id_re}: {str(date_error)}")
                
                try:
                    rental_end_value = fresh_rental.rental_end.strftime('%Y-%m-%dT%H:%M') if fresh_rental.rental_end else ''
                except (AttributeError, ValueError) as date_error:
                    rental_end_value = ''
                    print(f"Warning: Invalid rental end date for rental {fresh_rental.id_re}: {str(date_error)}")
                
                comment_value = fresh_rental.comment or ''
                
                # Use dialog directly
                with ui.dialog() as edit_dialog, ui.card().classes('w-96'):
                    ui.label(f'Editing rental record: ID {fresh_rental.id_re}').classes('text-h6 q-mb-md')
                    
                    # Read-only rental ID field
                    ui.input('Rental ID', value=str(fresh_rental.id_re)).props('readonly').classes('w-full q-mb-sm')
                    
                    # User selection dropdown
                    user_options = [user.name for user in users]
                    user_select = ui.select(
                        label='User',
                        options=user_options,
                        value=user_value
                    ).classes('w-full q-mb-sm')
                    
                    # Equipment selection dropdown with serial numbers
                    equipment_options = []
                    for eq in equipment_list:
                        serial_display = eq.serialnum if eq.serialnum else 'No S/N'
                        equipment_options.append(f"{eq.name} (S/N: {serial_display})")
                    
                    equipment_select = ui.select(
                        label='Equipment',
                        options=equipment_options,
                        value=equipment_value
                    ).classes('w-full q-mb-sm')
                    
                    # Rental start datetime input
                    rental_start_input = ui.input(
                        'Rental Start',
                        value=rental_start_value
                    ).props('type=datetime-local').classes('w-full q-mb-sm')
                    
                    # Rental end datetime input
                    rental_end_input = ui.input(
                        'Rental End',
                        value=rental_end_value,
                        placeholder='Leave empty if not returned'
                    ).props('type=datetime-local').classes('w-full q-mb-sm')
                    
                    # Comment text input
                    comment_input = ui.textarea(
                        'Comment',
                        value=comment_value,
                        placeholder='Optional comment'
                    ).classes('w-full q-mb-sm')
                    
                    with ui.row().classes('justify-end'):
                        ui.button('Cancel', on_click=edit_dialog.close).classes('q-mr-sm')
                        ui.button('Save', on_click=lambda: save_rental_changes(
                            fresh_rental.id_re,
                            user_select.value,
                            equipment_select.value,
                            rental_start_input.value,
                            rental_end_input.value,
                            comment_input.value,
                            users,
                            equipment_list,
                            edit_dialog,
                            parent_dialog
                        )).classes('bg-primary')
                        
                # Open the new dialog
                edit_dialog.open()
                
            except Exception as form_error:
                ui.notify(f'Error preparing edit form: {str(form_error)}', color='negative')
                print(f"Error preparing edit form: {str(form_error)}")
                if parent_dialog:
                    parent_dialog.close()
        
    except Exception as e:
        ui.notify(f'Critical error opening edit form: {str(e)}', color='negative')
        print(f"Critical error in show_edit_form_for_rental: {str(e)}")  # for debugging


def save_rental_changes(rental_id, user_name, equipment_name, rental_start_str, rental_end_str, comment, users, equipment_list, dialog, parent_dialog=None):
    """
    Saves changes to the rental record in the database with comprehensive validation and error handling.
    
    Args:
        rental_id: Rental ID
        user_name: Selected user name
        equipment_name: Selected equipment name
        rental_start_str: Rental start datetime string
        rental_end_str: Rental end datetime string (can be empty)
        comment: Comment text
        users: List of all users for ID lookup
        equipment_list: List of all equipment for ID lookup
        dialog: Dialog to close after saving
        parent_dialog: Parent dialog to close if needed
    """
    # Input validation - check for required fields
    validation_errors = []
    
    if not user_name or user_name.strip() == '':
        validation_errors.append('User selection is required')
    
    if not equipment_name or equipment_name.strip() == '':
        validation_errors.append('Equipment selection is required')
    
    if not rental_start_str or rental_start_str.strip() == '':
        validation_errors.append('Rental start date is required')
    
    if validation_errors:
        ui.notify(f'Validation failed: {"; ".join(validation_errors)}', color='negative')
        return
    
    try:
        # Create a new session for this operation
        with SessionLocal() as session:
            try:
                # Validate and get user ID
                user_id = None
                if user_name:
                    user = next((u for u in users if u.name == user_name), None)
                    if not user:
                        ui.notify(f'Selected user "{user_name}" not found in system', color='negative')
                        return
                    
                    # Double-check user exists in database
                    db_user = crud.get_user(session, user.id_us)
                    if not db_user:
                        ui.notify(f'Selected user "{user_name}" no longer exists in database', color='negative')
                        return
                    
                    user_id = user.id_us
                
                # Validate and get equipment ID
                equipment_id = None
                if equipment_name:
                    # Extract equipment name from the display format "Name (S/N: Serial)"
                    actual_equipment_name = equipment_name.split(' (S/N:')[0] if ' (S/N:' in equipment_name else equipment_name
                    
                    equipment = next((eq for eq in equipment_list if eq.name == actual_equipment_name), None)
                    if not equipment:
                        ui.notify(f'Selected equipment "{actual_equipment_name}" not found in system', color='negative')
                        return
                    
                    # Double-check equipment exists in database
                    db_equipment = crud.get_equipment(session, equipment.id_eq)
                    if not db_equipment:
                        ui.notify(f'Selected equipment "{actual_equipment_name}" no longer exists in database', color='negative')
                        return
                    
                    equipment_id = equipment.id_eq
                
                # Parse and validate datetime strings
                rental_start = None
                if rental_start_str:
                    try:
                        rental_start = datetime.datetime.fromisoformat(rental_start_str)
                        
                        # Check if start date is too far in the future (more than 1 year)
                        max_future_date = datetime.datetime.now() + datetime.timedelta(days=365)
                        if rental_start > max_future_date:
                            ui.notify('Rental start date cannot be more than 1 year in the future', color='negative')
                            return
                        
                    except ValueError as date_error:
                        ui.notify(f'Invalid rental start date format: {str(date_error)}', color='negative')
                        return
                
                rental_end = None
                if rental_end_str and rental_end_str.strip():
                    try:
                        rental_end = datetime.datetime.fromisoformat(rental_end_str)
                        
                        # Check if end date is too far in the future (more than 1 year)
                        max_future_date = datetime.datetime.now() + datetime.timedelta(days=365)
                        if rental_end > max_future_date:
                            ui.notify('Rental end date cannot be more than 1 year in the future', color='negative')
                            return
                        
                    except ValueError as date_error:
                        ui.notify(f'Invalid rental end date format: {str(date_error)}', color='negative')
                        return
                
                # Validate date range
                if rental_start and rental_end and rental_start > rental_end:
                    ui.notify('Rental start date cannot be later than rental end date', color='negative')
                    return
                
                # Additional date validation - check for reasonable date ranges
                if rental_start and rental_end:
                    duration = rental_end - rental_start
                    # Check if rental duration is more than 2 years (probably an error)
                    if duration.days > 730:
                        ui.notify('Rental duration cannot exceed 2 years. Please check your dates.', color='negative')
                        return
                
                # Validate comment length
                if comment and len(comment) > 500:
                    ui.notify('Comment cannot exceed 500 characters', color='negative')
                    return
                
                # Check if rental record still exists before updating
                existing_rental = crud.get_rental(session, rental_id)
                if not existing_rental:
                    ui.notify(f'Rental record with ID {rental_id} no longer exists in database', color='negative')
                    return
                
                # Update the rental record
                updated_rental = crud.update_rental(
                    session, 
                    rental_id, 
                    user_id=user_id,
                    equipment_id=equipment_id,
                    rental_start=rental_start,
                    rental_end=rental_end,
                    comment=comment
                )
                
                if updated_rental:
                    ui.notify(f'Rental record ID {rental_id} successfully updated', color='positive')
                    dialog.close()
                    
                    # If parent dialog exists, close it too
                    if parent_dialog:
                        parent_dialog.close()
                    
                    # Reopen the rental list with refreshed data
                    ui.timer(0.1, edit_rentals_dialog, once=True)
                else:
                    ui.notify('Failed to update rental record - record not found or update failed', color='negative')
                    
            except ValueError as ve:
                # Handle validation errors from crud.update_rental
                error_msg = str(ve)
                if 'User with ID' in error_msg and 'not found' in error_msg:
                    ui.notify('Selected user no longer exists in the database', color='negative')
                elif 'Equipment with ID' in error_msg and 'not found' in error_msg:
                    ui.notify('Selected equipment no longer exists in the database', color='negative')
                elif 'date' in error_msg.lower():
                    ui.notify(f'Date validation error: {error_msg}', color='negative')
                else:
                    ui.notify(f'Validation error: {error_msg}', color='negative')
                    
            except Exception as db_error:
                # Handle database-specific errors
                error_msg = str(db_error)
                if 'constraint' in error_msg.lower():
                    ui.notify('Database constraint violation. Please check your data and try again.', color='negative')
                elif 'connection' in error_msg.lower():
                    ui.notify('Database connection error. Please try again.', color='negative')
                elif 'timeout' in error_msg.lower():
                    ui.notify('Database operation timed out. Please try again.', color='negative')
                else:
                    ui.notify(f'Database error occurred while saving: {error_msg}', color='negative')
                
                print(f"Database error in save_rental_changes: {str(db_error)}")  # for debugging
                
    except Exception as e:
        # Handle any other unexpected errors
        ui.notify(f'Unexpected error during save operation: {str(e)}', color='negative')
        print(f"Unexpected error in save_rental_changes: {str(e)}")  # for debugging