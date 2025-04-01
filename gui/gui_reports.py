from nicegui import ui
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import get_user_rental_statistics
from database import SessionLocal

db = SessionLocal()

def show_rental_statistics():
    with ui.dialog() as dialog:
        with ui.card().style('width: 1500px !important'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('User Rental Statistics')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            # Get data from database
            user_stats = get_user_rental_statistics(db)
            
            # Define columns for the table
            columns = [
                {'field': 'name', 'headerName': 'User Name', 'sortable': True},
                {'field': 'department', 'headerName': 'Department', 'sortable': True},
                {'field': 'total_rental_time', 'headerName': 'Total Rental Time', 'sortable': True, 'sort': 'desc'}
            ]
            
            # Create the table
            ui.aggrid({
                'columnDefs': columns,
                'rowData': user_stats,
                'rowSelection': 'single',
                'pagination': True,
                'paginationPageSize': 10,
                'domLayout': 'autoHeight'
            })
    dialog.open()

# Create button to show the report
ui.button('Show Rental Statistics', on_click=show_rental_statistics).props('color=primary')

ui.run()

