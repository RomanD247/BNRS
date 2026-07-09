"""
Read-Only Web Viewer for Equipment Rental System
Provides network-accessible view of equipment status without modification capabilities.
Each user has independent filter settings (per-session state).
"""
from nicegui import ui, app
import sys
import os
import datetime

# Add parent directory to path to import from main project
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from paths import APP_DIR
from crud import get_available_equipment, get_active_rentals, get_all_etypes
from crud import get_available_equipment_by_type, get_active_rentals_by_equipment_type
from models import Rental, Equipment, User
from sqlalchemy.orm import joinedload

# This viewer is read-only by design (it must never write to rental.db), so
# it gets its own engine bound to a true read-only SQLite connection instead
# of importing/reusing the main app's read-write `database.SessionLocal`.
# That also means this module never calls Base.metadata.create_all() - a
# read-only connection couldn't create tables anyway, and a viewer has no
# business doing so.
#
# Absolute path resolution mirrors database.py (via paths.APP_DIR) so the
# viewer finds the live rental.db regardless of its own working directory.
#
# The main DB runs in WAL mode (see database.py's connect listener); this
# combination (mode=ro + WAL) was verified directly against the live
# rental.db before adopting it here: real SELECTs (including joinedload
# relationship queries via crud.py) succeed, and any write attempt raises
# "attempt to write a readonly database" at the sqlite3 layer - enforced by
# the OS/SQLite, not just by convention.
_DB_PATH = (APP_DIR / "rental.db").as_posix()
VIEWER_DATABASE_URL = f"sqlite:///file:{_DB_PATH}?mode=ro&uri=true"
viewer_engine = create_engine(VIEWER_DATABASE_URL)
SessionLocal = sessionmaker(bind=viewer_engine)

# State management for filters (per-user session)
class ViewerState:
    def __init__(self):
        with SessionLocal() as db:
            self.available_equipment = get_available_equipment(db)
            self.rented_equipment = get_active_rentals(db)
            self.etypes = get_all_etypes(db)
        self.selected_etype_id = None
        self.name_filter = ""
        self.etype_map = {}
        self.filter_select = None
        self.name_filter_input = None

        # Build etype_map
        for etype in self.etypes:
            self.etype_map[etype.name] = etype.id_et

    def set_name_filter(self, filter_text):
        """Set the name filter and update the filter state"""
        self.name_filter = filter_text.lower().strip() if filter_text else ""

    def refresh_data(self):
        """Refresh all data from database"""
        with SessionLocal() as db:
            self.etypes = get_all_etypes(db)
        self.etype_map = {etype.name: etype.id_et for etype in self.etypes}

def get_user_state():
    """Get or create state for current user session"""
    if 'viewer_state' not in app.storage.user:
        # Initialize with simple serializable values
        app.storage.user['viewer_state'] = {
            'selected_etype_id': None,
            'name_filter': ""
        }
    
    # Create a fresh ViewerState instance and populate it with stored values
    state = ViewerState()
    state.selected_etype_id = app.storage.user['viewer_state']['selected_etype_id']
    state.name_filter = app.storage.user['viewer_state']['name_filter']
    
    return state

def save_user_state(state):
    """Save user state filter values to storage"""
    app.storage.user['viewer_state'] = {
        'selected_etype_id': state.selected_etype_id,
        'name_filter': state.name_filter
    }

def create_equipment_card(equipment, is_rented=False):
    """Create a card for equipment display (matching main app style)"""
    if is_rented:
        # Taller card for rented equipment with more info
        card = ui.card().style('width: 450px; min-height: 115px;')
    else:
        card = ui.card().style('width: 450px; height: 115px;')
    
    with card:
        if is_rented:
            with ui.row().classes('w-full justify-between items-center').style('margin-top: -10px'):
                ui.label(f"{equipment.equipment.name}").style('font-size: 18px; font-weight: bold')
                ui.label(f"{equipment.equipment.etype.name if equipment.equipment.etype else 'Unknown'}")
            ui.label(f"S/N: {equipment.equipment.serialnum}").style('margin-top: -18px')
            ui.label(f"Rented by: {equipment.user.name} ({equipment.user.department.name})").style('margin-top: -18px')
            ui.label(f"Rented since: {equipment.rental_start.strftime('%Y-%m-%d %H:%M')}").style('margin-top: -18px')
            if equipment.comment:
                ui.label(f"Comment: {equipment.comment}").style('margin-top: -18px; margin-bottom: -10px; font-style: italic; color: #666')
            else:
                ui.label("").style('margin-bottom: -10px')  # Spacing consistency
        else:
            with ui.row().classes('w-full justify-between items-center').style('margin-top: -5px'):
                ui.label(f"{equipment.name}").style('font-size: 18px; font-weight: bold')
                ui.label(f"{equipment.etype.name if equipment.etype else 'Unknown'}")
            ui.label(f"S/N: {equipment.serialnum}").style('margin-top: -12px; margin-bottom: -10px')
    
    return card

def get_all_rentals(db):
    """Get all rentals for history"""
    return db.query(Rental)\
        .options(joinedload(Rental.equipment).joinedload(Equipment.etype))\
        .options(joinedload(Rental.user).joinedload(User.department))\
        .order_by(Rental.rental_start.desc())\
        .all()

def show_rental_history():
    """Shows rental history in a dialog"""
    with ui.dialog().classes('max-w-6xl') as dialog:
        with ui.card().style('width: 1400px; max-width: none'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Rental History').style('font-size: 24px; font-weight: bold')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            
            # Create table columns
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
            
            # Get rental history data
            rental_history = []
            with SessionLocal() as db:
                rentals = get_all_rentals(db)

            for rental in rentals:
                # Calculate duration
                duration_str = "Active rental"
                if rental.rental_end:
                    duration = rental.rental_end - rental.rental_start
                    days = duration.days
                    hours = duration.seconds // 3600
                    minutes = (duration.seconds % 3600) // 60
                    duration_str = f"{days}d {hours:02}h {minutes:02}m"
                
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
            
            # Search field
            with ui.row().classes('w-full items-center gap-4 py-4'):
                search_input = ui.input('Search in all fields').style('width: 400px')
            
            # Create table
            with ui.card().classes('w-full'):
                table = ui.table(
                    columns=columns,
                    rows=rental_history,
                    row_key='id',
                    title='Rental History',
                    pagination={'rowsPerPage': 10, 'sortBy': 'id', 'descending': True}
                ).classes('w-full')
                
                # Bind search to table filter
                search_input.bind_value(table, 'filter')
            
            ui.label('Click on column headers to sort data').style('font-size: 12px; color: #666; margin-top: 10px')
    
    dialog.open()

def filter_equipment_by_name(equipment_list, name_filter):
    """Filter equipment list by name containing the filter text (case-insensitive)"""
    if not name_filter:
        return equipment_list
    return [eq for eq in equipment_list if name_filter.lower() in eq.name.lower()]

def filter_rentals_by_equipment_name(rental_list, name_filter):
    """Filter rental list by equipment name containing the filter text (case-insensitive)"""
    if not name_filter:
        return rental_list
    return [rental for rental in rental_list if name_filter.lower() in rental.equipment.name.lower()]

def apply_combined_filters(state):
    """Apply both type and name filters simultaneously to equipment lists"""
    # Get base equipment lists (all or filtered by type), each fetch using
    # its own short-lived session (this app is read-only, so per-fetch
    # sessions are simplest and avoid stale cached/identity-mapped data).
    with SessionLocal() as db:
        if state.selected_etype_id is not None:
            available = get_available_equipment_by_type(db, state.selected_etype_id)
            rented = get_active_rentals_by_equipment_type(db, state.selected_etype_id)
        else:
            available = get_available_equipment(db)
            rented = get_active_rentals(db)

    # Apply name filter if active
    if state.name_filter:
        available = filter_equipment_by_name(available, state.name_filter)
        rented = filter_rentals_by_equipment_name(rented, state.name_filter)
    
    # Update state
    state.available_equipment = available
    state.rented_equipment = rented

def update_lists(state, available_container, rented_container):
    """Update both equipment list UI containers based on current state data."""
    # Ensure UI updates reflect current filter state by applying filters if needed
    if state.selected_etype_id is not None or state.name_filter:
        apply_combined_filters(state)
    
    # Clear and repopulate available container
    if available_container:
        available_container.clear()
        with available_container:
            with ui.column():
                # Use data already present in the state
                for equipment in sorted(state.available_equipment, key=lambda x: x.name):
                    create_equipment_card(equipment)
    
    # Clear and repopulate rented container
    if rented_container:
        rented_container.clear()
        with rented_container:
            with ui.column():
                # Use data already present in the state
                for rental in sorted(state.rented_equipment, key=lambda x: x.equipment.name):
                    create_equipment_card(rental, is_rented=True)

def filter_by_etype(e, state, available_container, rented_container):
    """Filter equipment lists by equipment type"""
    selected_name = e.value
    state.selected_etype_id = state.etype_map.get(selected_name)
    
    # Save state to storage
    save_user_state(state)
    
    # Use combined filtering to preserve name filter when type filter changes
    apply_combined_filters(state)
    
    # Update UI with new state data
    update_lists(state, available_container, rented_container)

def on_name_filter_change(filter_text, state, available_container, rented_container):
    """Handle name filter input changes and trigger combined filtering"""
    # Update state with new filter text
    state.set_name_filter(filter_text)
    
    # Save state to storage
    save_user_state(state)
    
    # Apply combined filters (type + name)
    apply_combined_filters(state)
    
    # Update UI lists
    update_lists(state, available_container, rented_container)

def reset_filter(state, available_container, rented_container):
    """Reset both equipment type and name filters to show all equipment"""
    # Clear filter state
    state.selected_etype_id = None
    state.name_filter = ""
    
    # Save cleared state to storage
    save_user_state(state)
    
    # Reset the visual selection in both filter inputs
    if state.filter_select:
        state.filter_select.value = None
        state.filter_select.update()
    if state.name_filter_input:
        state.name_filter_input.value = ""
        state.name_filter_input.update()
    
    # Fetch all data into state (without filters), using a fresh short-lived
    # session for this one read.
    with SessionLocal() as db:
        state.available_equipment = get_available_equipment(db)
        state.rented_equipment = get_active_rentals(db)

    # Update the UI lists
    if available_container:
        available_container.clear()
        with available_container:
            with ui.column():
                for equipment in sorted(state.available_equipment, key=lambda x: x.name):
                    create_equipment_card(equipment)
    
    if rented_container:
        rented_container.clear()
        with rented_container:
            with ui.column():
                for rental in sorted(state.rented_equipment, key=lambda x: x.equipment.name):
                    create_equipment_card(rental, is_rented=True)
    
    ui.notify('Filters reset', type='positive')

def full_refresh(state, available_container, rented_container):
    """Reloads all data from the database and updates the UI."""
    # Preserve current filter state before refresh
    current_etype_id = state.selected_etype_id
    current_name_filter = state.name_filter
    
    # Refresh etypes from DB into state using a fresh short-lived session
    # (no need to expire a cache - a brand-new session has none).
    with SessionLocal() as db:
        state.etypes = get_all_etypes(db)
    state.etype_map = {etype.name: etype.id_et for etype in state.etypes}

    # Restore filter state after refresh
    state.selected_etype_id = current_etype_id
    state.name_filter = current_name_filter

    # Apply active filters after full data refresh to preserve filter state
    apply_combined_filters(state)

    # Update the UI lists
    update_lists(state, available_container, rented_container)

    #ui.notify('Data refreshed successfully!', type='positive')

@ui.page('/')
def main_page():
    """Main page route - each user gets their own state"""
    # Get per-user state
    state = get_user_state()
    
    # Header
    with ui.header().classes('items-center justify-between'):
        ui.label('Equipment Rental System - View Only').style('font-size: 24px')
        ui.label('Read-Only Access').style('font-size: 14px')
    
    # Main content
    with ui.column().style('padding: 20px'):
        # Filters section
        with ui.row().style('width: 100%; gap: 10px; margin-bottom: 20px'):
            state.filter_select = ui.select(
                label='Equipment Type',
                options=[etype.name for etype in state.etypes],
                with_input=True,
                on_change=lambda e: filter_by_etype(e, state, available_container, rented_container)
            ).style('width: 300px')
            
            state.name_filter_input = ui.input(
                label='Search by name',
                placeholder='Type to search...',
                on_change=lambda e: on_name_filter_change(e.value, state, available_container, rented_container)
            ).style('width: 300px')
            
            ui.button('Reset Filters', icon='clear', on_click=lambda: reset_filter(state, available_container, rented_container))
            ui.button('Rental History', icon='history', on_click=show_rental_history, color='secondary')
            #ui.button('Refresh', icon='refresh', on_click=lambda: full_refresh(state, available_container, rented_container), color='primary')
        
        # Equipment display section
        with ui.row().style('width: 100%; gap: 20px'):
            # Available equipment column
            with ui.column().style('flex: 1'):
                ui.label('Available Equipment').style('font-size: 20px; font-weight: bold; color: green; margin-bottom: 10px')
                available_container = ui.column()
            
            # Rented equipment column
            with ui.column().style('flex: 1'):
                ui.label('Currently Rented').style('font-size: 20px; font-weight: bold; color: blue; margin-bottom: 10px')
                rented_container = ui.column()
    
    # Initial data load
    update_lists(state, available_container, rented_container)
    
    # Auto-refresh every 30 seconds
    ui.timer(30.0, lambda: full_refresh(state, available_container, rented_container))

if __name__ == '__main__':
    ui.run(
        # Intentional, accepted exposure: this is an internal, read-only LAN
        # viewer, so binding all interfaces (rather than localhost-only) is
        # by design, not an oversight.
        host='0.0.0.0',  # Listen on all network interfaces
        port=8585,
        title='Equipment Rental Viewer',
        reload=False,
        show=False,  # Don't auto-open browser
        # Mirrors the BNRS_ADMIN_PASSWORD env-var-with-fallback pattern in
        # main.py: falls back to a fixed value (clearly insecure - only
        # session cookies for this read-only viewer depend on it) so
        # existing deployments keep working unchanged out of the box.
        storage_secret=os.environ.get(
            "BNRS_VIEWER_STORAGE_SECRET",
            "rental_viewer_secret_key_change_in_production",  # INSECURE default
        ),
    )
