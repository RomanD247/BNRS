from nicegui import ui
from sqlalchemy.orm import Session
import sys
import os
import csv
import tempfile
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import get_user_rental_statistics, get_equipment_type_statistics, get_equipment_name_statistics, get_all_rentals, get_department_rental_statistics, get_all_feedback
from database import SessionLocal

# Create a global database connection
db = SessionLocal()

# Function for exporting data to CSV
def export_to_csv(data, filename=None):
    if not data:
        ui.notify('No data to export', color='warning')
        return
    
    # If filename is not specified, create a name with timestamp
    if not filename:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.csv"
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', newline='', delete=False, suffix='.csv') as temp_file:
        # Define headers from the first data record
        fieldnames = data[0].keys() if data else []
        
        # Write data to CSV
        writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        
        temp_filepath = temp_file.name
    
    # Prompt user to download the file
    ui.download(temp_filepath, filename=filename)
    
    # Schedule temporary file deletion after download
    def cleanup():
        try:
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
        except Exception as e:
            print(f"Failed to remove temporary file: {e}")
    
    ui.timer(10, cleanup, once=True)

# Function for user report
def show_user_rental_statistics():
    """Shows user rental statistics report"""
    with ui.dialog() as dialog:
        with ui.card().style('max-width: none; width: 800px'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('User Rental Statistics').classes('text-h5')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            
            # Variables for storing selected dates
            start_date = None
            end_date = None
            
            # Create table (ui.table)
            columns = [
                {'name': 'name', 'label': 'User Name', 'field': 'name', 'sortable': True, 'align': 'left'},
                {'name': 'department', 'label': 'Department', 'field': 'department', 'sortable': True, 'align': 'left'},
                {'name': 'rental_count', 'label': 'Total Rentals', 'field': 'rental_count', 'sortable': True, 'align': 'right'},
                {'name': 'total_rental_time', 'label': 'Total Rental Time', 'field': 'total_rental_time', 'sortable': True, 'align': 'left'}
            ]
            
            # Function to update data with filters
            def update_data():
                nonlocal start_date, end_date
                
                # Get data from database with filtering
                user_stats = get_user_rental_statistics(db, start_date, end_date)
                
                # Filter out records with zero rental time
                user_stats = [stat for stat in user_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                # Update table
                table.rows = user_stats
                
                # Apply department filter
                #filter_by_department()
            
            with ui.row().classes('w-full items-center justify-center gap-4 py-4'):
                
                # Create search field
                filtered_data = ui.input('Search in all fields').classes('text-left')

                # Dropdown menu for date filter
                with ui.button('Date Filter', icon='event').props('outline'):
                    with ui.menu().classes('ml-auto') as date_menu:
                        with ui.card():
                            ui.label('Select Date Range').classes('text-h6 q-pa-md')
                            
                            # Field for displaying selected date range
                            date_input = ui.input('Date range').classes('w-full q-px-md')
                            
                            # Date range picker component
                            date_picker = ui.date().props('range').bind_value(
                                date_input,
                                forward=lambda x: f'{x["from"]} - {x["to"]}' if x else None,
                                backward=lambda x: {
                                    'from': x.split(' - ')[0],
                                    'to': x.split(' - ')[1],
                                } if ' - ' in (x or '') else None,
                            )
                            
                            with ui.row().classes('q-pa-md justify-end'):
                                ui.button('Clear', on_click=lambda: date_clear()).props('flat')
                                ui.button('Apply', on_click=lambda: date_apply()).props('color=primary')
                
                
                # Export button with functionality
                ui.button('Export to CSV', icon='download', on_click=lambda: export_to_csv(
                    table.rows, f"user_rental_statistics_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )).props('outline')
            
            # Create table with data
            with ui.card().classes('w-full'):
                # Initial data retrieval without filters
                user_stats = get_user_rental_statistics(db)
                
                # Filter out records with zero rental time
                user_stats = [stat for stat in user_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                # Create table
                table = ui.table(
                    columns=columns,
                    rows=user_stats,
                    row_key='name',
                    title='User Rental Statistics',
                    pagination={'sortBy': 'total_rental_time', 'descending': True}
                ).classes('w-full')

                filtered_data.bind_value(table, 'filter')

                 # Function to apply date filter
                def date_apply():
                    nonlocal start_date, end_date
                    
                    date_range = date_input.value
                    if date_range and ' - ' in date_range:
                        start, end = date_range.split(' - ')
                        # Convert string dates to datetime objects
                        start_date = datetime.datetime.strptime(start, '%Y-%m-%d')
                        # Set end of day for end date
                        end_date = datetime.datetime.strptime(end, '%Y-%m-%d')
                        end_date = end_date.replace(hour=23, minute=59, second=59)
                        
                        # Update data with new filters
                        update_data()
                        # Close menu
                        date_menu.close()
                        
                
                # Function to clear date filter
                def date_clear():
                    nonlocal start_date, end_date
                    start_date = None
                    end_date = None
                    date_input.value = None
                    update_data()
                    date_menu.close()
                
                        
            # Add sorting information
            ui.label('Click on column headers to sort data').classes('text-caption text-grey-7 q-mt-sm')
    
    dialog.open()

# Function for equipment type statistics report
def show_equipment_type_statistics():
    """Shows equipment type statistics report"""
    with ui.dialog() as dialog:
        with ui.card().style('max-width: none; width: 800px'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Device Type Statistics').classes('text-h5')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            
            # Variables for storing selected dates
            start_date = None
            end_date = None
            
            # Create table
            columns = [
                {'name': 'type_name', 'label': 'Device Type', 'field': 'type_name', 'sortable': True, 'align': 'left'},
                {'name': 'rental_count', 'label': 'Total Rentals', 'field': 'rental_count', 'sortable': True, 'align': 'right'},
                {'name': 'total_rental_time', 'label': 'Total Rental Time', 'field': 'total_rental_time', 'sortable': True, 'align': 'right'}
            ]
            
            # Function to update data with filters
            def update_data():
                nonlocal start_date, end_date
                
                # Get data from database with filtering
                type_stats = get_equipment_type_statistics(db, start_date, end_date)
                
                # Filter out records with zero rental time
                type_stats = [stat for stat in type_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                # Update table
                table.rows = type_stats
            
            with ui.row().classes('w-full items-center justify-center gap-4 py-4'):
                # Dropdown menu for date filter
                
                # Create search field
                filtered_data = ui.input('Search in all fields')

                with ui.button('Date Filter', icon='event').props('outline'):
                    with ui.menu().classes('ml-auto') as date_menu:
                        with ui.card():
                            ui.label('Select Date Range').classes('text-h6 q-pa-md')
                            
                            # Field for displaying selected date range
                            date_input = ui.input('Date range').classes('w-full q-px-md')
                            
                            # Date range picker component
                            date_picker = ui.date().props('range').bind_value(
                                date_input,
                                forward=lambda x: f'{x["from"]} - {x["to"]}' if x else None,
                                backward=lambda x: {
                                    'from': x.split(' - ')[0],
                                    'to': x.split(' - ')[1],
                                } if ' - ' in (x or '') else None,
                            )
                            
                            with ui.row().classes('q-pa-md justify-end'):
                                ui.button('Clear', on_click=lambda: date_clear()).props('flat')
                                ui.button('Apply', on_click=lambda: date_apply()).props('color=primary')
                
                # Export button with functionality
                ui.button('Export to CSV', icon='download', on_click=lambda: export_to_csv(
                    table.rows, f"equipment_type_statistics_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )).props('outline')
            
            # Create table with data
            with ui.card().classes('w-full'):
                # Initial data retrieval without filters
                type_stats = get_equipment_type_statistics(db)
                
                # Filter out records with zero rental time
                type_stats = [stat for stat in type_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']

                
                table = ui.table(
                    columns=columns,
                    rows=type_stats,
                    row_key='type_name',
                    title='Device Type Statistics',
                    pagination={'sortBy': 'total_rental_time', 'descending': True}
                ).classes('w-full')
                
                filtered_data.bind_value(table, 'filter')

                # Function to apply date filter
                def date_apply():
                    nonlocal start_date, end_date
                    
                    date_range = date_input.value
                    if date_range and ' - ' in date_range:
                        start, end = date_range.split(' - ')
                        # Convert string dates to datetime objects
                        start_date = datetime.datetime.strptime(start, '%Y-%m-%d')
                        # Set end of day for end date
                        end_date = datetime.datetime.strptime(end, '%Y-%m-%d')
                        end_date = end_date.replace(hour=23, minute=59, second=59)
                        
                        # Update data with new filters
                        update_data()
                        # Close menu
                        date_menu.close()
                        # Update filter button text
                        #date_filter_btn.text = f'Date: {start} - {end}'
                
                # Function to clear date filter
                def date_clear():
                    nonlocal start_date, end_date
                    start_date = None
                    end_date = None
                    date_input.value = None
                    #date_filter_btn.text = 'Date Filter'
                    update_data()
                    date_menu.close()
            
            # Add sorting information
            ui.label('Click on column headers to sort data').classes('text-caption text-grey-7 q-mt-sm')
    
    dialog.open()

# Function for equipment name statistics report
def show_equipment_name_statistics():
    """Shows equipment name statistics report"""
    with ui.dialog() as dialog:
        with ui.card().style('max-width: none; width: 1000px'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Device Name Statistics').classes('text-h5')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            
            # Variables for storing selected dates
            start_date = None
            end_date = None
            
            # Create table
            columns = [
                {'name': 'name', 'label': 'Equipment Name', 'field': 'name', 'sortable': True, 'align': 'left'},
                {'name': 'etype_name', 'label': 'Equipment Type', 'field': 'etype_name', 'sortable': True, 'align': 'left'},
                {'name': 'equipment_count', 'label': 'Count', 'field': 'equipment_count', 'sortable': True, 'align': 'right'},
                {'name': 'rental_count', 'label': 'Total Rentals', 'field': 'rental_count', 'sortable': True, 'align': 'right'},
                {'name': 'total_rental_time', 'label': 'Total Rental Time', 'field': 'total_rental_time', 'sortable': True, 'align': 'right'}
            ]
            
            # Function to update data with filters
            def update_data():
                nonlocal start_date, end_date
                
                # Get data from database with filtering
                name_stats = get_equipment_name_statistics(db, start_date, end_date)
                
                # Filter out records with zero rental time
                name_stats = [stat for stat in name_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                # Update table
                table.rows = name_stats
            
            with ui.row().classes('w-full items-center justify-center gap-4 py-4'):
                
                # Create search field
                filtered_data = ui.input('Search in all fields')
                
                # Dropdown menu for date filter
                with ui.button('Date Filter', icon='event').props('outline'):
                    with ui.menu().classes('ml-auto') as date_menu:
                        with ui.card():
                            ui.label('Select Date Range').classes('text-h6 q-pa-md')
                            
                            # Field for displaying selected date range
                            date_input = ui.input('Date range').classes('w-full q-px-md')
                            
                            # Date range picker component
                            date_picker = ui.date().props('range').bind_value(
                                date_input,
                                forward=lambda x: f'{x["from"]} - {x["to"]}' if x else None,
                                backward=lambda x: {
                                    'from': x.split(' - ')[0],
                                    'to': x.split(' - ')[1],
                                } if ' - ' in (x or '') else None,
                            )
                            
                            with ui.row().classes('q-pa-md justify-end'):
                                ui.button('Clear', on_click=lambda: date_clear()).props('flat')
                                ui.button('Apply', on_click=lambda: date_apply()).props('color=primary')
                
                            
                # Export button with functionality
                ui.button('Export to CSV', icon='download', on_click=lambda: export_to_csv(
                    table.rows, f"equipment_name_statistics_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )).props('outline')
            
            # Create table with data
            with ui.card().classes('w-full'):
                # Initial data retrieval without filters
                name_stats = get_equipment_name_statistics(db)
                
                # Filter out records with zero rental time
                name_stats = [stat for stat in name_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                table = ui.table(
                    columns=columns,
                    rows=name_stats,
                    row_key='name',
                    title='Equipment Name Statistics',
                    pagination={'sortBy': 'total_rental_time', 'descending': True}
                ).classes('w-full')
                
                filtered_data.bind_value(table, 'filter')

                # Function to apply date filter
                def date_apply():
                    nonlocal start_date, end_date
                    
                    date_range = date_input.value
                    if date_range and ' - ' in date_range:
                        start, end = date_range.split(' - ')
                        # Convert string dates to datetime objects
                        start_date = datetime.datetime.strptime(start, '%Y-%m-%d')
                        # Set end of day for end date
                        end_date = datetime.datetime.strptime(end, '%Y-%m-%d')
                        end_date = end_date.replace(hour=23, minute=59, second=59)
                        
                        # Update data with new filters
                        update_data()
                        # Close menu
                        date_menu.close()
                        # Update filter button text
                        #date_filter_btn.text = f'Date: {start} - {end}'
                
                # Function to clear date filter
                def date_clear():
                    nonlocal start_date, end_date
                    start_date = None
                    end_date = None
                    date_input.value = None
                    #date_filter_btn.text = 'Date Filter'
                    update_data()
                    date_menu.close()
            
            # Add sorting information
            ui.label('Click on column headers to sort data').classes('text-caption text-grey-7 q-mt-sm')
    
    dialog.open()

# Function to get user report button
def get_user_report_button():
    """Returns button for user statistics report"""
    with ui.button(on_click=show_user_rental_statistics).props('color=primary').style('width: 100px; height: 100px;'):
        ui.icon('person')
        ui.label('User Report') 
    
# Function to get equipment report button
def get_equipment_report_button():
    """Returns button for equipment type statistics report"""
    with ui.button(on_click=show_equipment_type_statistics).props('color=primary').style('width: 100px; height: 100px;'):
        ui.icon('devices')
        ui.label('Type Report')

# Function to get equipment name report button
def get_equipment_name_report_button():
    """Returns button for equipment name statistics report"""
    with ui.button(on_click=show_equipment_name_statistics).style('width: 100px; height: 100px;'):
        ui.icon('inventory_2')
        ui.label('Devices Report')

# Function to show full rental history
def show_rental_history():
    """Shows full rental history report"""
    with ui.dialog().classes('max-w-5xl') as dialog:
        with ui.card().style('width: 1400px; max-width: none'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Rental History').classes('text-h5')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            
            # Variables for storing selected dates
            start_date = None
            end_date = None
            
            # Create table (ui.table)
            columns = [
                {'name': 'id', 'label': 'ID', 'field': 'id', 'sortable': True, 'align': 'left'},
                {'name': 'equipment', 'label': 'Equipment', 'field': 'equipment', 'sortable': True, 'align': 'left'},
                {'name': 'serialnum', 'label': 'S/N', 'field': 'serialnum', 'sortable': True, 'align': 'left'},
                {'name': 'equipment_type', 'label': 'Type', 'field': 'equipment_type', 'sortable': True, 'align': 'left'},
                {'name': 'user', 'label': 'User', 'field': 'user', 'sortable': True, 'align': 'left'},
                {'name': 'department', 'label': 'Department', 'field': 'department', 'sortable': True, 'align': 'left'},
                {'name': 'rental_start', 'label': 'Rental Start', 'field': 'rental_start', 'sortable': True, 'align': 'left'},
                {'name': 'rental_end', 'label': 'Rental End', 'field': 'rental_end', 'sortable': True, 'align': 'left'},
                {'name': 'duration', 'label': 'Duration', 'field': 'duration', 'sortable': True, 'align': 'left'},
                {'name': 'comment', 'label': 'Comment', 'field': 'comment', 'sortable': True, 'align': 'left'},
            ]
            
            # Get full rental history
            rental_history = []
            
            rentals = get_all_rentals(db)
            for rental in rentals:
                # Prepare data for display
                duration_str = "Active rental"
                if rental.rental_end:
                    # Calculate duration for completed rentals
                    duration = rental.rental_end - rental.rental_start
                    days = duration.days
                    hours = duration.seconds // 3600
                    minutes = (duration.seconds % 3600) // 60
                    duration_str = f"{days}:{hours:02}:{minutes:02}"
                
                rental_history.append({
                    'id': rental.id_re,
                    'equipment': rental.equipment.name,
                    'serialnum': rental.equipment.serialnum or '',
                    'equipment_type': rental.equipment.etype.name if rental.equipment.etype else 'Unknown',
                    'user': rental.user.name,
                    'department': rental.user.department.name if rental.user.department else 'Unknown',
                    'rental_start': rental.rental_start.strftime('%Y-%m-%d %H:%M'),
                    'rental_end': rental.rental_end.strftime('%Y-%m-%d %H:%M') if rental.rental_end else 'Not returned',
                    'duration': duration_str,
                    'comment': rental.comment or ''
                })
            
            # Save original data for filtering
            original_rental_history = rental_history.copy()
            
            # Create variable for table
            table = None
            
            # Function to update data with filters
            def update_data():
                nonlocal start_date, end_date
                
                # Filter data by dates
                filtered_data = original_rental_history.copy()
                
                if start_date and end_date:
                    filtered_data = []
                    for item in original_rental_history:
                        # Convert date string to datetime object
                        rental_start = datetime.datetime.strptime(item['rental_start'], '%Y-%m-%d %H:%M')
                        
                        # Check if date falls within selected range
                        if start_date <= rental_start <= end_date:
                            filtered_data.append(item)
                
                # Update table
                table.rows = filtered_data
                
                # Display information about found records
                ui.notify(f'Found records: {len(filtered_data)} out of {len(original_rental_history)}')
            
            # Function to apply date filter
            def date_apply():
                nonlocal start_date, end_date
                
                date_range = date_input.value
                if date_range and ' - ' in date_range:
                    start, end = date_range.split(' - ')
                    # Convert string dates to datetime objects
                    start_date = datetime.datetime.strptime(start, '%Y-%m-%d')
                    # Set end of day for end date
                    end_date = datetime.datetime.strptime(end, '%Y-%m-%d')
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                    
                    # Update data with new filters
                    update_data()
                    # Close menu
                    date_menu.close()
            
            # Function to clear date filter
            def date_clear():
                nonlocal start_date, end_date
                start_date = None
                end_date = None
                date_input.value = None
                update_data()
                date_menu.close()
            
            with ui.row().classes('w-full items-center justify-between gap-4 py-4'):
                
                # Create search field
                filtered_data = ui.input('Search in all fields')
                
                # Dropdown menu for date filter
                with ui.button('Date Filter', icon='event').props('outline'):
                    with ui.menu().classes('ml-auto') as date_menu:
                        with ui.card():
                            ui.label('Select Date Range').classes('text-h6 q-pa-md')
                            
                            # Field for displaying selected date range
                            date_input = ui.input('Date range').classes('w-full q-px-md')
                            
                            # Date range picker component
                            date_picker = ui.date().props('range').bind_value(
                                date_input,
                                forward=lambda x: f'{x["from"]} - {x["to"]}' if x else None,
                                backward=lambda x: {
                                    'from': x.split(' - ')[0],
                                    'to': x.split(' - ')[1],
                                } if ' - ' in (x or '') else None,
                            )
                            
                            with ui.row().classes('q-pa-md justify-end'):
                                ui.button('Clear', on_click=lambda: date_clear()).props('flat')
                                ui.button('Apply', on_click=lambda: date_apply()).props('color=primary')
                
                # Export button with functionality
                ui.button('Export to CSV', icon='download', on_click=lambda: export_to_csv(
                    table.rows, f"rental_history_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )).props('outline')
            
            # Create table with data
            with ui.card().classes('w-full'):
                table = ui.table(
                    columns=columns,
                    rows=rental_history,
                    row_key='id',
                    title='Rental History',
                    pagination={'rowsPerPage': 8,'sortBy': 'id', 'descending': True}
                ).classes('w-full')
            filtered_data.bind_value(table, 'filter')
            # Add sorting information
            ui.label('Click on column headers to sort data').classes('text-caption text-grey-7 q-mt-sm')
    
    dialog.open()

# Function to get rental history button
def get_rental_history_button():
    """Returns button for viewing rental history"""
    return ui.button('Rental History', icon='history', on_click=show_rental_history).style('height: 60px')

# Function for department statistics report
def show_department_rental_statistics():
    """Shows department rental statistics report"""
    with ui.dialog() as dialog:
        with ui.card().style('max-width: none; width: 1000px'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Department Rental Statistics').classes('text-h5')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            
            # Variables for storing selected dates
            start_date = None
            end_date = None
            
            # Create table
            columns = [
                {'name': 'name', 'label': 'Department Name', 'field': 'name', 'sortable': True, 'align': 'left'},
                {'name': 'rental_count', 'label': 'Total Rentals', 'field': 'rental_count', 'sortable': True, 'align': 'right'},
                {'name': 'total_rental_time', 'label': 'Total Rental Time', 'field': 'total_rental_time', 'sortable': True, 'align': 'right'}
            ]
            
            # Function to update data with filters
            def update_data():
                nonlocal start_date, end_date
                
                # Get data from database with filtering
                dept_stats = get_department_rental_statistics(db, start_date, end_date)
                
                # Filter out records with zero rental time
                dept_stats = [stat for stat in dept_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                # Update table
                table.rows = dept_stats
            
            with ui.row().classes('w-full items-center justify-center gap-4 py-4'):
                
                # Create search field
                filtered_data = ui.input('Search in all fields')
                
                # Dropdown menu for date filter
                with ui.button('Date Filter', icon='event').props('outline'):
                    with ui.menu().classes('ml-auto') as date_menu:
                        with ui.card():
                            ui.label('Select Date Range').classes('text-h6 q-pa-md')
                            
                            # Field for displaying selected date range
                            date_input = ui.input('Date range').classes('w-full q-px-md')
                            
                            # Date range picker component
                            date_picker = ui.date().props('range').bind_value(
                                date_input,
                                forward=lambda x: f'{x["from"]} - {x["to"]}' if x else None,
                                backward=lambda x: {
                                    'from': x.split(' - ')[0],
                                    'to': x.split(' - ')[1],
                                } if ' - ' in (x or '') else None,
                            )
                            
                            with ui.row().classes('q-pa-md justify-end'):
                                ui.button('Clear', on_click=lambda: date_clear()).props('flat')
                                ui.button('Apply', on_click=lambda: date_apply()).props('color=primary')
                
                
                # Export button with functionality
                ui.button('Export to CSV', icon='download', on_click=lambda: export_to_csv(
                    table.rows, f"department_rental_statistics_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )).props('outline')
            
            # Create table with data
            with ui.card().classes('w-full'):
                # Initial data retrieval without filters
                dept_stats = get_department_rental_statistics(db)
                
                # Filter out records with zero rental time
                dept_stats = [stat for stat in dept_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                table = ui.table(
                    columns=columns,
                    rows=dept_stats,
                    row_key='name',
                    title='Department Rental Statistics',
                    pagination={'sortBy': 'total_rental_time', 'descending': True}
                ).classes('w-full')
                
                filtered_data.bind_value(table, 'filter')

                # Function to apply date filter
                def date_apply():
                    nonlocal start_date, end_date
                    
                    date_range = date_input.value
                    if date_range and ' - ' in date_range:
                        start, end = date_range.split(' - ')
                        # Convert string dates to datetime objects
                        start_date = datetime.datetime.strptime(start, '%Y-%m-%d')
                        # Set end of day for end date
                        end_date = datetime.datetime.strptime(end, '%Y-%m-%d')
                        end_date = end_date.replace(hour=23, minute=59, second=59)
                        
                        # Update data with new filters
                        update_data()
                        # Close menu
                        date_menu.close()
                
                # Function to clear date filter
                def date_clear():
                    nonlocal start_date, end_date
                    start_date = None
                    end_date = None
                    date_input.value = None
                    update_data()
                    date_menu.close()
            
            # Add sorting information
            ui.label('Click on column headers to sort data').classes('text-caption text-grey-7 q-mt-sm')
    
    dialog.open()

# Function to get department report button
def get_department_report_button():
    """Returns button for department statistics report"""
    with ui.button(on_click=show_department_rental_statistics).style('width: 100px; height: 100px;'):
        ui.icon('business')
        ui.label('Department Report')

# Function to show feedback entries
def show_feedback_entries():
    """Shows all feedback entries in a table"""
    with ui.dialog() as dialog:
        with ui.card().style('max-width: none; width: 1000px'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Feedback Entries').classes('text-h5')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            
            # Variables for storing selected dates
            start_date = None
            end_date = None
            
            # Create table columns
            columns = [
                {'name': 'id', 'label': 'ID', 'field': 'id', 'sortable': True, 'align': 'left'},
                {'name': 'name', 'label': 'Name', 'field': 'name', 'sortable': True, 'align': 'left'},
                {'name': 'date', 'label': 'Date', 'field': 'date', 'sortable': True, 'align': 'left'},
                {'name': 'feedback', 'label': 'Feedback', 'field': 'feedback', 'sortable': True, 'align': 'left'}
            ]
            
            # Get feedback data
            feedback_data = []
            
            feedbacks = get_all_feedback(db)
            for feedback in feedbacks:
                feedback_data.append({
                    'id': feedback.id_fb,
                    'name': feedback.name or 'Anonymous',
                    'date': feedback.date.strftime('%Y-%m-%d %H:%M'),
                    'feedback': feedback.feedback
                })
            
            # Save original data for filtering
            original_feedback_data = feedback_data.copy()
            
            # Create variable for table
            table = None
            
            # Function to update data with filters
            def update_data():
                nonlocal start_date, end_date
                
                # Filter data by dates
                filtered_data = original_feedback_data.copy()
                
                if start_date and end_date:
                    filtered_data = []
                    for item in original_feedback_data:
                        # Convert date string to datetime object
                        feedback_date = datetime.datetime.strptime(item['date'], '%Y-%m-%d %H:%M')
                        
                        # Check if date falls within selected range
                        if start_date <= feedback_date <= end_date:
                            filtered_data.append(item)
                
                # Update table
                table.rows = filtered_data
            
            # Function to apply date filter
            def date_apply():
                nonlocal start_date, end_date
                
                date_range = date_input.value
                if date_range and ' - ' in date_range:
                    start, end = date_range.split(' - ')
                    # Convert string dates to datetime objects
                    start_date = datetime.datetime.strptime(start, '%Y-%m-%d')
                    # Set end of day for end date
                    end_date = datetime.datetime.strptime(end, '%Y-%m-%d')
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                    
                    # Update data with new filters
                    update_data()
                    # Close menu
                    date_menu.close()
            
            # Function to clear date filter
            def date_clear():
                nonlocal start_date, end_date
                start_date = None
                end_date = None
                date_input.value = None
                update_data()
                date_menu.close()
            
            with ui.row().classes('w-full items-center justify-center gap-4 py-4'):
                
                # Create search field
                filtered_data = ui.input('Search in all fields')
                
                # Dropdown menu for date filter
                with ui.button('Date Filter', icon='event').props('outline'):
                    with ui.menu().classes('ml-auto') as date_menu:
                        with ui.card():
                            ui.label('Select Date Range').classes('text-h6 q-pa-md')
                            
                            # Field for displaying selected date range
                            date_input = ui.input('Date range').classes('w-full q-px-md')
                            
                            # Date range picker component
                            date_picker = ui.date().props('range').bind_value(
                                date_input,
                                forward=lambda x: f'{x["from"]} - {x["to"]}' if x else None,
                                backward=lambda x: {
                                    'from': x.split(' - ')[0],
                                    'to': x.split(' - ')[1],
                                } if ' - ' in (x or '') else None,
                            )
                            
                            with ui.row().classes('q-pa-md justify-end'):
                                ui.button('Clear', on_click=lambda: date_clear()).props('flat')
                                ui.button('Apply', on_click=lambda: date_apply()).props('color=primary')
                
                # Export button with functionality
                ui.button('Export to CSV', icon='download', on_click=lambda: export_to_csv(
                    table.rows, f"feedback_entries_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )).props('outline')
            
            # Create table with data
            with ui.card().classes('w-full'):
                table = ui.table(
                    columns=columns,
                    rows=feedback_data,
                    row_key='id',
                    title='Feedback Entries',
                    pagination={'rowsPerPage': 10, 'sortBy': 'date', 'descending': True}
                ).classes('w-full')
                
                filtered_data.bind_value(table, 'filter')
            
            # Add sorting information
            ui.label('Click on column headers to sort data').classes('text-caption text-grey-7 q-mt-sm')
    
    dialog.open()

# Function to get feedback view button
def get_feedback_button():
    """Returns button for viewing feedback entries"""
    with ui.button(on_click=show_feedback_entries).style('width: 100px; height: 100px;'):
        ui.icon('feedback')
        ui.label('View Feedback')

# If file is run directly, create test interface
if __name__ == '__main__':
    ui.label('Reports Test Page').classes('text-h4')
    with ui.row():
        get_user_report_button()
        get_equipment_report_button()
        get_equipment_name_report_button()
        get_department_report_button()
        get_rental_history_button()
        get_feedback_button()
    ui.run()

