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


def _user_display(user):
    """Unique dropdown label for a user (M9) - includes the ID so two users
    with the same name/department can't be confused with each other, and is
    used identically for both building the options dict and computing the
    pre-selected value so they match char-for-char."""
    dep_name = user.department.name if user.department else 'No Department'
    suffix = '' if user.status else ' (inactive)'
    return f"{user.name} ({dep_name}) [#{user.id_us}]{suffix}"


def _equipment_display(equipment):
    """Unique dropdown label for an equipment unit (M9) - see _user_display."""
    serial = equipment.serialnum if equipment.serialnum else 'No S/N'
    suffix = '' if equipment.status else ' (inactive)'
    return f"{equipment.name} (S/N: {serial}) [#{equipment.id_eq}]{suffix}"

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

            # Delete the dialog element once hidden (unbounded-dialog-accumulation)
            dialog.on('hide', dialog.delete)
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
                
                # Get ALL users and equipment for dropdowns, including inactive
                # ones (M10) - otherwise a rental for a departed user or
                # retired device becomes edit-locked, even for a comment-only change.
                users = crud.get_all_users_including_inactive(fresh_db)
                equipment_list = crud.get_all_equipment_including_inactive(fresh_db)

                # Validate that we have users and equipment available
                if not users:
                    ui.notify('No users found in the system. Cannot edit rental record.', color='negative')
                    return

                if not equipment_list:
                    ui.notify('No equipment found in the system. Cannot edit rental record.', color='negative')
                    return

                # Build display-string -> ID lookup dicts (M9) so saving resolves
                # the dropdown selection by ID, not by re-matching a (possibly
                # non-unique) display string against the list.
                users_by_display = {}
                for u in users:
                    users_by_display[_user_display(u)] = u.id_us
                user_options = list(users_by_display.keys())

                equipment_by_display = {}
                for eq in equipment_list:
                    equipment_by_display[_equipment_display(eq)] = eq.id_eq
                equipment_options = list(equipment_by_display.keys())

                # Capture the rental's actual current IDs (M10) - used later to
                # detect a no-op selection so save_rental_changes can avoid
                # re-validating an unchanged-but-inactive user/equipment.
                original_user_id = fresh_rental.user_id
                original_equipment_id = fresh_rental.equipment_id

                # Create variables to store form values with error handling.
                # Built with the exact same helpers as the options dicts above,
                # so the value matches one of the options char-for-char.
                try:
                    user_value = _user_display(fresh_rental.user) if fresh_rental.user else None
                except AttributeError:
                    user_value = None
                    print(f"Warning: Rental {fresh_rental.id_re} has invalid user reference")

                try:
                    equipment_value = _equipment_display(fresh_rental.equipment) if fresh_rental.equipment else None
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
                    
                    # User selection dropdown (options/value built above via
                    # the shared _user_display helper - M9/M10)
                    user_select = ui.select(
                        label='User',
                        options=user_options,
                        value=user_value
                    ).classes('w-full q-mb-sm')

                    # Equipment selection dropdown (options/value built above
                    # via the shared _equipment_display helper - M9/M10)
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
                    
                    # Rental end datetime input with clear button
                    with ui.row().classes('w-full q-mb-sm items-end'):
                        rental_end_input = ui.input(
                            'Rental End',
                            value=rental_end_value,
                            placeholder='Leave empty if not returned'
                        ).props('type=datetime-local').classes('flex-grow')
                        
                        # Clear button for rental end date
                        ui.button(
                            'Clear',
                            on_click=lambda: rental_end_input.set_value('')
                        ).classes('q-ml-sm').props('size=sm color=secondary')
                    
                    # Comment text input
                    comment_input = ui.textarea(
                        'Comment',
                        value=comment_value,
                        placeholder='Optional comment'
                    ).classes('w-full q-mb-sm')
                    
                    with ui.row().classes('justify-between'):
                        # Delete button on the left
                        ui.button(
                            'Delete Record', 
                            icon='delete',
                            on_click=lambda: delete_rental_record(
                                fresh_rental.id_re,
                                edit_dialog,
                                parent_dialog
                            )
                        ).classes('bg-negative')
                        
                        # Cancel and Save buttons on the right
                        with ui.row():
                            ui.button('Cancel', on_click=edit_dialog.close).classes('q-mr-sm')
                            ui.button('Save', on_click=lambda: save_rental_changes(
                                fresh_rental.id_re,
                                user_select.value,
                                equipment_select.value,
                                rental_start_input.value,
                                rental_end_input.value,
                                comment_input.value,
                                users_by_display,
                                equipment_by_display,
                                original_user_id,
                                original_equipment_id,
                                edit_dialog,
                                parent_dialog
                            )).classes('bg-primary')
                        
                # Delete the dialog element once hidden (unbounded-dialog-accumulation)
                edit_dialog.on('hide', edit_dialog.delete)
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


def save_rental_changes(rental_id, user_display, equipment_display, rental_start_str, rental_end_str, comment,
                         users_by_display, equipment_by_display, original_user_id, original_equipment_id,
                         dialog, parent_dialog=None):
    """
    Saves changes to the rental record in the database with comprehensive validation and error handling.

    Args:
        rental_id: Rental ID
        user_display: Selected user dropdown display string
        equipment_display: Selected equipment dropdown display string
        rental_start_str: Rental start datetime string
        rental_end_str: Rental end datetime string (can be empty)
        comment: Comment text
        users_by_display: dict mapping each user dropdown display string to its user ID (M9)
        equipment_by_display: dict mapping each equipment dropdown display string to its equipment ID (M9)
        original_user_id: the rental's user_id before editing (M10 - used to detect a no-op selection)
        original_equipment_id: the rental's equipment_id before editing (M10 - see above)
        dialog: Dialog to close after saving
        parent_dialog: Parent dialog to close if needed
    """
    # Input validation - check for required fields
    validation_errors = []

    if not user_display or user_display.strip() == '':
        validation_errors.append('User selection is required')

    if not equipment_display or equipment_display.strip() == '':
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
                # Resolve the dropdown selections back to IDs by exact display
                # string (M9) instead of re-matching a possibly non-unique name.
                selected_user_id = users_by_display.get(user_display)
                if selected_user_id is None:
                    ui.notify(f'Selected user "{user_display}" not found in system', color='negative')
                    return

                selected_equipment_id = equipment_by_display.get(equipment_display)
                if selected_equipment_id is None:
                    ui.notify(f'Selected equipment "{equipment_display}" not found in system', color='negative')
                    return

                # Only pass an ID through to update_rental when it actually
                # changed (M10). update_rental re-validates that the target is
                # active whenever an ID is given, which would otherwise block
                # saving an unrelated change (e.g. just the comment) on a
                # rental whose user/equipment has since been deactivated.
                user_id = selected_user_id if selected_user_id != original_user_id else None
                equipment_id = selected_equipment_id if selected_equipment_id != original_equipment_id else None

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
                # Special handling for clearing rental_end - we need to explicitly pass None
                # even when the field is empty to clear the database value
                if not rental_end_str or rental_end_str.strip() == '':
                    # Force clear the rental_end field by setting it to a special marker
                    # that the crud function will recognize as "clear this field"
                    rental_end_to_pass = 'CLEAR_FIELD'
                    print(f"DEBUG: Clearing rental_end for rental {rental_id}")
                else:
                    rental_end_to_pass = rental_end
                    print(f"DEBUG: Setting rental_end to {rental_end} for rental {rental_id}")
                
                updated_rental = crud.update_rental(
                    session, 
                    rental_id, 
                    user_id=user_id,
                    equipment_id=equipment_id,
                    rental_start=rental_start,
                    rental_end=rental_end_to_pass,
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


def delete_rental_record(rental_id, dialog, parent_dialog=None):
    """
    Deletes a rental record from the database after confirmation.
    
    Args:
        rental_id: ID of the rental record to delete
        dialog: Current edit dialog to close
        parent_dialog: Parent dialog to close if needed
    """
    def confirm_delete():
        try:
            # Create a new session for this operation
            with SessionLocal() as session:
                # Check if rental record exists before deleting
                existing_rental = crud.get_rental(session, rental_id)
                if not existing_rental:
                    ui.notify(f'Rental record with ID {rental_id} no longer exists in database', color='negative')
                    return
                
                # Delete the rental record
                success = crud.delete_rental(session, rental_id)
                
                if success:
                    ui.notify(f'Rental record ID {rental_id} successfully deleted', color='positive')
                    dialog.close()
                    
                    # If parent dialog exists, close it too
                    if parent_dialog:
                        parent_dialog.close()
                    
                    # Reopen the rental list with refreshed data
                    ui.timer(0.1, edit_rentals_dialog, once=True)
                else:
                    ui.notify('Failed to delete rental record - record not found', color='negative')
                    
        except Exception as e:
            ui.notify(f'Error deleting rental record: {str(e)}', color='negative')
            print(f"Error in delete_rental_record: {str(e)}")
    
    # Show confirmation dialog
    with ui.dialog() as confirm_dialog, ui.card():
        ui.label(f'Are you sure you want to delete rental record ID {rental_id}?').classes('text-h6 q-mb-md')
        ui.label('This action cannot be undone!').classes('text-negative q-mb-md')
        
        with ui.row().classes('justify-end'):
            ui.button('Cancel', on_click=confirm_dialog.close).classes('q-mr-sm')
            ui.button('Delete', on_click=lambda: [confirm_delete(), confirm_dialog.close()]).classes('bg-negative')

    # Delete the dialog element once hidden (unbounded-dialog-accumulation)
    confirm_dialog.on('hide', confirm_dialog.delete)
    confirm_dialog.open()