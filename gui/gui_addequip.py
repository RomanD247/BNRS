from nicegui import ui
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import create_equipment, create_etype, get_all_etypes, get_etype_by_name
from database import SessionLocal

db = SessionLocal()

# Load equipment types from database
def load_etypes():
    etypes = get_all_etypes(db)
    return [et.name for et in etypes]

data = load_etypes()

def show_add_etype_dialog(main_dropdown, main_data, main_selected_label, filter_callback=None):
    def add_etype():
        new_et = new_et_input.value.strip()
        if not new_et:
            ui.notify('Please enter an equipment type name!', type='warning')
            return
        
        if new_et in main_data:
            ui.notify('This equipment type already exists!', type='warning')
            return
            
        try:
            create_etype(db, new_et)
            main_data.append(new_et)
            new_et_input.value = ''
            ui.notify(f'Equipment type {new_et} added successfully!')
            
            # Update dropdown items
            main_dropdown.clear()
            with main_dropdown:
                for item in main_data:
                    ui.item(item, on_click=lambda item=item: (main_selected_label.set_text(f'{item}'))).style('width: 300px')
            
            # Call the callback to update the filter dropdown in the main interface
            if filter_callback:
                filter_callback()
                
            dialog.close()
        except Exception as e:
            ui.notify(f'Error adding equipment type: {e}', type='error')

    with ui.dialog().props('persistent') as dialog, ui.card():
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(text='Adding a new equipment type').style('font-size: 200%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        ui.label(text='Enter equipment type name:')
        new_et_input = ui.input(label='Equipment type name')
        ui.separator()
        ui.button(text='Add equipment type', on_click=add_etype).style('width: 300px')

    dialog.open()

def show_add_equipment_dialog(filter_callback=None, lists_update_callback=None):
    def add_equipment():
        name = name_input.value.strip()
        serialnum = serialnum_input.value.strip()
        etype_name = selected_label.text.replace('Selected: ', '').strip()

        if not name or etype_name == 'None':
            ui.notify('Please enter a name and select an equipment type!', type='warning')
            return

        try:
            etype = get_etype_by_name(db, etype_name)
            if not etype:
                ui.notify(f'Equipment type {etype_name} not found!', type='error')
                return
            create_equipment(db, name=name, serialnum=serialnum, etype_id=etype.id_et)
            ui.notify(f'Equipment {name} added successfully!')
            
            # Call the lists update callback to refresh equipment lists
            if lists_update_callback:
                lists_update_callback()
                
            dialog.close()
        except Exception as e:
            ui.notify(f'Error: {e}', type='error')

    with ui.dialog().props('persistent') as dialog, ui.card():
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(text='Adding new equipment').style('font-size: 200%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        ui.label(text='Enter equipment name:')
        name_input = ui.input(label='Name').style('width: 300px')
        ui.separator()
        ui.label(text='Enter serial number:')
        serialnum_input = ui.input(label='Serial number').style('width: 300px')
        ui.separator()
        ui.label(text='Choose equipment type from the dropdown:')
        with ui.row():
            dropdown = ui.dropdown_button('Choose equipment type', auto_close=True)
            with dropdown:
                for item in data:
                    ui.item(item, on_click=lambda item=item: (selected_label.set_text(f'{item}'))).style('width: 300px')
            ui.button(text='+', on_click=lambda: show_add_etype_dialog(dropdown, data, selected_label, filter_callback))
        selected_label = ui.label('You must choose equipment type!')
        ui.separator() 
        ui.button(text='Add new equipment', on_click=add_equipment).style('width: 300px; margin-left: 30px')
        ui.button(text='Import equipment from CSV', on_click=lambda: show_import_equipment_dialog(lists_update_callback)).style('width: 300px; margin-left: 30px')
    dialog.open()

def show_import_equipment_dialog(callback=None):
    """
    Shows a dialog to import equipment from a CSV file.
    
    Format: name;serialnum;etype
    Status is set to True by default.
    
    Args:
        callback: Optional function to call after successful import to refresh equipment lists
    """
    uploaded_file = None
    
    async def handle_upload(event):
        nonlocal uploaded_file
        uploaded_file = event.content
        file_info.set_text(f"File uploaded: {event.name}")
        preview_button.visible = True
        import_button.visible = True
        
    async def preview_csv():
        if not uploaded_file:
            ui.notify('Please upload a file first!', type='warning')
            return
            
        try:
            import pandas as pd
            import io
            
            # Read the content of the temporary file
            content = uploaded_file.read()
            # Reset file pointer for future reading
            uploaded_file.seek(0)
            
            # Decode the content
            try:
                # Try UTF-8 first
                csv_content = io.StringIO(content.decode('utf-8'))
            except UnicodeDecodeError:
                # Fallback to other encodings
                try:
                    csv_content = io.StringIO(content.decode('latin-1'))
                except:
                    csv_content = io.StringIO(content.decode('cp1251'))
                    
            # Read CSV with semicolon delimiter
            df = pd.read_csv(csv_content, sep=';', names=['name', 'serialnum', 'etype'])
            
            # Get first 5 rows for preview or all rows if less than 5
            preview_data = df.head(5).to_string(index=False)
            preview_text.set_text(f"Preview (first 5 rows):\n\n{preview_data}")
            preview_text.visible = True
            
            # Count total rows
            total_rows = len(df)
            stats_text.set_text(f"Total rows to import: {total_rows}")
            stats_text.visible = True
            
        except Exception as e:
            ui.notify(f'Preview error: {e}', type='error')
            
    async def import_equipment():
        if not uploaded_file:
            ui.notify('Please upload a file first!', type='warning')
            return
            
        try:
            import pandas as pd
            import io
            
            # Read the content of the temporary file
            content = uploaded_file.read()
            # Reset file pointer for future reading
            uploaded_file.seek(0)
            
            # Decode the content
            try:
                # Try UTF-8 first
                csv_content = io.StringIO(content.decode('utf-8'))
            except UnicodeDecodeError:
                # Fallback to other encodings
                try:
                    csv_content = io.StringIO(content.decode('latin-1'))
                except:
                    csv_content = io.StringIO(content.decode('cp1251'))
                    
            # Read CSV with semicolon delimiter
            df = pd.read_csv(csv_content, sep=';', names=['name', 'serialnum', 'etype'])
            
            # Validate all equipment types before proceeding with import
            missing_etypes = []
            existing_etypes = {et.name: et for et in get_all_etypes(db)}
            
            for index, row in df.iterrows():
                etype_name = row['etype'].strip() if not pd.isna(row['etype']) else None
                if etype_name and etype_name not in existing_etypes:
                    missing_etypes.append(etype_name)
            
            # If any equipment type is missing, stop the import
            if missing_etypes:
                unique_missing = list(set(missing_etypes))
                ui.notify(f'Import aborted! The following equipment types do not exist: {", ".join(unique_missing)}', type='error')
                return
            
            # Counters for statistics
            added = 0
            errors = 0
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    # Check etype and get id
                    etype_name = row['etype'].strip() if not pd.isna(row['etype']) else None
                    etype_id = None
                    
                    if etype_name:
                        # Get the equipment type (it's already validated to exist)
                        etype = existing_etypes[etype_name]
                        etype_id = etype.id_et
                    
                    # Create equipment with status = True by default
                    create_equipment(
                        db, 
                        name=row['name'].strip() if not pd.isna(row['name']) else "Unnamed",
                        serialnum=row['serialnum'].strip() if not pd.isna(row['serialnum']) else None,
                        etype_id=etype_id
                    )
                    added += 1
                    
                except Exception as e:
                    errors += 1
                    continue  # Continue import even if there's an error
            
            # Show import result
            ui.notify(f'Import completed: {added} records added, {errors} errors', type='positive')
            
            # Call callback function on successful import
            if callback and added > 0:
                callback()
                
            # Close the dialog
            dialog.close()
                
        except Exception as e:
            ui.notify(f'Import error: {e}', type='error')
                
    with ui.dialog().props('persistent') as dialog, ui.card().classes('w-96'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(text='Import equipment from CSV').style('font-size: 150%')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        
        ui.label('Select a CSV file to import')
        ui.label('Format: name;serialnum;etype')
        
        ui.upload(label='Upload CSV', on_upload=handle_upload).props('accept=.csv')
        file_info = ui.label('')
        
        preview_button = ui.button('Preview file', on_click=preview_csv)
        preview_button.visible = False
        
        preview_text = ui.label('')
        preview_text.visible = False
        
        stats_text = ui.label('')
        stats_text.visible = False
        
        ui.separator()
        
        import_button = ui.button('Import', on_click=import_equipment)
        import_button.visible = False
        import_button.style('width: 300px; margin-top: 10px;')

    dialog.open()