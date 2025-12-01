from nicegui import ui
from collections import deque
import asyncio
from sqlalchemy.orm import Session
import crud
from models import User, Equipment, Rental
from database import SessionLocal
from smartcard.System import readers
from smartcard.util import toHexString
import time
from smartcard.Exceptions import CardConnectionException, NoCardException
from pylibdmtx.pylibdmtx import encode
from PIL import Image, ImageDraw, ImageFont

db = SessionLocal()
scanning_active = False  # Global flag to control card scanning

def _create_datamatrix_image(data: str, text_lines: list[str]) -> Image.Image | None:
    """
    Creates an image with Data Matrix code and text
    
    Args:
        data: Data to encode in Data Matrix
        text_lines: List of text strings to add below the code
    
    Returns:
        PIL Image object or None on error
    """
    try:
        # Input parameters validation
        if data is None:
            print("Error: Data parameter cannot be None")
            return None
            
        if not isinstance(data, str):
            print("Error: Data parameter must be a string")
            return None
            
        if not data.strip():
            print("Error: Data parameter cannot be empty or contain only whitespace")
            return None
        
        if text_lines is None:
            print("Error: text_lines parameter cannot be None")
            return None
            
        if not isinstance(text_lines, list):
            print("Error: text_lines parameter must be a list")
            return None
        
        # Validation of text_lines content
        for i, line in enumerate(text_lines):
            if line is not None and not isinstance(line, str):
                print(f"Error: text_lines[{i}] must be a string or None")
                return None
        
        # Check data length for Data Matrix
        if len(data.encode('utf-8')) > 2335:  # Maximum size for Data Matrix
            print("Error: Data too long for Data Matrix encoding (max 2335 bytes)")
            return None
        
        # Generate Data Matrix code
        try:
            encoded = encode(data.encode('utf-8'))
        except Exception as e:
            print(f"Error: Failed to encode data to Data Matrix: {str(e)}")
            return None
            
        if not encoded:
            print("Error: Data Matrix encoding returned empty result")
            return None
        
        if not hasattr(encoded, 'width') or not hasattr(encoded, 'height') or not hasattr(encoded, 'pixels'):
            print("Error: Invalid Data Matrix encoding result")
            return None
        
        if encoded.width <= 0 or encoded.height <= 0:
            print("Error: Invalid Data Matrix dimensions")
            return None
        
        # Create image from Data Matrix code
        try:
            code_image = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
        except Exception as e:
            print(f"Error: Failed to create image from Data Matrix bytes: {str(e)}")
            return None
        
        # Scale code to 50x50 pixels
        code_size = 50
        try:
            code_image = code_image.resize((code_size, code_size), Image.NEAREST)
        except Exception as e:
            print(f"Error: Failed to resize Data Matrix image: {str(e)}")
            return None
        
        # Calculate final image dimensions
        margin = 15
        text_spacing = 10
        line_height = 20
        
        # Filter valid text lines
        valid_text_lines = [line for line in text_lines if line and isinstance(line, str) and line.strip()]
        text_height = len(valid_text_lines) * line_height if valid_text_lines else 0
        
        total_width = code_size + 2 * margin
        total_height = code_size + 1 * margin + text_spacing + text_height
        
        # Check reasonable image dimensions
        if total_width > 2000 or total_height > 2000:
            print("Error: Resulting image would be too large")
            return None
        
        # Create final image with white background
        try:
            final_image = Image.new('RGB', (total_width, total_height), 'white')
        except Exception as e:
            print(f"Error: Failed to create final image: {str(e)}")
            return None
        
        # Insert Data Matrix code in center of upper part
        code_x = margin
        code_y = margin
        try:
            final_image.paste(code_image, (code_x, code_y))
        except Exception as e:
            print(f"Error: Failed to paste Data Matrix code into final image: {str(e)}")
            return None
        
        # Add text labels
        if valid_text_lines:
            try:
                draw = ImageDraw.Draw(final_image)
            except Exception as e:
                print(f"Error: Failed to create drawing context: {str(e)}")
                return None
            
            # Try to load system font
            font = None
            try:
                font = ImageFont.truetype("arial.ttf", 12)
            except (OSError, IOError):
                try:
                    font = ImageFont.load_default()
                except Exception as e:
                    print(f"Warning: Failed to load font, using basic text rendering: {str(e)}")
                    font = None
            
            # Add each text line
            text_y = code_y + code_size + text_spacing
            for line in valid_text_lines:
                try:
                    # Center text
                    if font:
                        try:
                            bbox = draw.textbbox((0, 0), line, font=font)
                            text_width = bbox[2] - bbox[0]
                        except Exception:
                            text_width = len(line) * 8  # Fallback for older PIL versions
                    else:
                        text_width = len(line) * 6  # Approximate width for default font
                    
                    text_x = max(0, (total_width - text_width) // 2)
                    
                    if font:
                        draw.text((text_x, text_y), line, fill='black', font=font)
                    else:
                        draw.text((text_x, text_y), line, fill='black')
                    
                    text_y += line_height
                    
                except Exception as e:
                    print(f"Warning: Failed to add text line '{line}': {str(e)}")
                    # Continue with remaining lines
                    text_y += line_height
        
        return final_image
        
    except MemoryError:
        print("Error: Insufficient memory to create Data Matrix image")
        return None
    except Exception as e:
        print(f"Error: Unexpected error creating Data Matrix image: {str(e)}")
        return None

def get_card_uid():
    """
    Reads UID from a card using CCID reader
    
    Returns:
        Card UID as string or None if no card detected
    """
    try:
        rdrs = readers()
        if not rdrs:
            print("No PC/SC readers found")
            return None
            
        reader = rdrs[0]
        conn = reader.createConnection()
        conn.connect()
        
        # Command to get UID
        GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        data, sw1, sw2 = conn.transmit(GET_UID)
        
        if sw1 == 0x90 and sw2 == 0x00:
            uid = toHexString(data).replace(' ', '').lower()  # Convert to lowercase
            print("Card UID:", uid)
            conn.disconnect()
            return uid
        
        conn.disconnect()
        return None
    except (CardConnectionException, NoCardException):
        return None
    except Exception as e:
        print(f"Error reading card: {str(e)}")
        return None

async def get_nfc_input(prompt_message: str) -> str:
    """
    Opens a dialog box with a prompt and waits for keyboard input (virtual keyboard scanner).

    Args:
        prompt_message: Message displayed in the dialog box.

    Returns:
        Scanned data as string.
    """
    result = ""
    dialog = ui.dialog()
    closed = asyncio.Future()

    def on_input_submit():
        nonlocal result
        if input_field.value.strip():
            result = input_field.value.strip().lower()
            dialog.close()
            closed.set_result(None)

    def on_cancel():
        dialog.close()
        closed.set_result(None)

    def on_input_change(e):
        # Update display when input changes
        if input_field.value:
            display_label.text = f"Scanning: {input_field.value}"
        else:
            display_label.text = "Ready to scan..."

    with dialog, ui.card().style('width: 350px;'):
        with ui.row().classes('w-full justify-center items-center'):
            ui.label(prompt_message).style('font-size: 24px; font-weight: bold; text-align: center')
        with ui.separator():
            pass
        
        display_label = ui.label("Ready to scan...").classes('w-full justify-center items-center').style('font-size: 16px; text-align: center; margin: 20px 0;')
        
        # Invisible input field that maintains focus
        input_field = ui.input().style('position: absolute; top: -1000px; left: -1000px;').props('autofocus')
        input_field.on('keydown.enter', on_input_submit)
        input_field.on('input', on_input_change)
        
        with ui.row().classes('w-full justify-end'):
            ui.button('Cancel', on_click=on_cancel).props('flat')

    dialog.open()
    
    # Aggressive focus maintenance
    async def maintain_focus():
        while not closed.done():
            await asyncio.sleep(0.1)
            if not closed.done():
                input_field.run_method('focus')
    
    asyncio.create_task(maintain_focus())
    
    await closed  # Wait until dialog is closed
    return result

async def get_user_input_with_selection(equipment=None):
    """
    Shows dialog that simultaneously waits for NFC input (virtual keyboard) 
    and provides manual user selection from dropdown
    
    Args:
        equipment: Equipment object to display information about (optional)
    
    Returns:
        User object or None if cancelled
    """
    dialog = ui.dialog()
    result = asyncio.Future()
    selected_user = None
    nfc_input_value = ""
    
    def on_cancel():
        dialog.close()
        result.set_result(None)
    
    def on_manual_select():
        if selected_user:
            dialog.close()
            result.set_result(selected_user)
        else:
            ui.notify("Please select a user", color="warning")
    
    def on_user_select_change(e):
        nonlocal selected_user
        if e.value in users_dict:
            selected_user = users_dict[e.value]
        else:
            selected_user = None
    
    def on_nfc_input_submit():
        nonlocal nfc_input_value
        if nfc_input_field.value.strip():
            nfc_input_value = nfc_input_field.value.strip().lower()
            # Find user by NFC
            user = crud.find_user_by_nfc(db, nfc_input_value)
            if user:
                dialog.close()
                result.set_result(user)
            else:
                ui.notify("User not found", color="negative")
                nfc_input_field.set_value("")
                nfc_display_label.text = "Ready to scan..."
    
    def on_nfc_input_change(e):
        # Update display when input changes
        if nfc_input_field.value:
            nfc_display_label.text = f"Scanning: {nfc_input_field.value}"
        else:
            nfc_display_label.text = "Ready to scan..."
    
    # Get all users for dropdown
    users = crud.get_all_users(db)
    users_dict = {}
    options = []
    
    for user in sorted(users, key=lambda x: x.name):
        display_text = f"{user.name} ({user.department.name})"
        users_dict[display_text] = user
        options.append(display_text)
    
    with dialog, ui.card().style('width: 450px;'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('Select User').style('font-size: 150%')
            ui.button(icon='close', on_click=on_cancel).props('flat round')
        
        ui.separator()
        
        # Equipment information section (if equipment is provided)
        if equipment:
            ui.label('Scanned Equipment:').style('margin: 10px 0 5px 0;')
            with ui.row().classes('w-full justify-between items-center').style('border: 1px solid black; padding: 10px;'):
                ui.label(f"{equipment.name}").style('font-weight: bold; font-size: 16px;')
                ui.label(f"S/N: {equipment.serialnum or 'Not specified'}").style('font-weight: bold; font-size: 16px;')
            ui.separator()
        
        # NFC scanning section
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('Scan User\'s Data Matrix Code:').style('font-weight: bold; margin: 10px 0 5px 0; text-decoration: underline;')
            nfc_display_label = ui.label("Ready to scan...").style('font-size: 16px; text-align: center; margin: 5px 0; padding: 10px; border: 1px dashed #ccc; border-radius: 4px;')
        
        # Invisible input field for NFC scanning
        nfc_input_field = ui.input().style('position: absolute; top: -1000px; left: -1000px;').props('autofocus')
        nfc_input_field.on('keydown.enter', on_nfc_input_submit)
        nfc_input_field.on('input', on_nfc_input_change)
        
        ui.separator()
        ui.label('OR').classes('text-center').style('margin: 0px 0;')
        #ui.separator()
        
        # Manual selection section
        ui.label('Select from list:').style('font-weight: bold; margin: 0px 0 0px 0; text-decoration: underline;')
        user_select = ui.select(
            options=options,
            label='Select user',
            #with_input=True,
            on_change=on_user_select_change
        ).style('width: 100%; margin: 5px 0;')
        
        ui.button('Confirm Selection', on_click=on_manual_select).style('width: 100%; margin: 5px 0;')
    
    dialog.open()
    
    # Aggressive focus maintenance for NFC input
    async def maintain_focus():
        while not result.done():
            await asyncio.sleep(0.1)
            if not result.done():
                nfc_input_field.run_method('focus')
    
    asyncio.create_task(maintain_focus())
    
    # Wait for user choice
    choice = await result
    return choice



def generate_user_datamatrix(user_id: int) -> Image.Image | None:
    """
    Generates Data Matrix code for a user
    
    Args:
        user_id: User ID in the database
    
    Returns:
        PIL Image object with Data Matrix code and text or None on error
    """
    try:
        # Input parameter validation
        if user_id is None:
            print("Error: user_id parameter cannot be None")
            return None
            
        if not isinstance(user_id, int):
            print("Error: user_id parameter must be an integer")
            return None
            
        if user_id <= 0:
            print("Error: user_id must be a positive integer")
            return None
        
        # Get user data from database
        user = crud.get_user(db, user_id)
        if not user:
            print(f"Error: User with ID {user_id} not found")
            return None
        
        # Validate presence and correctness of nfc field
        if not user.nfc:
            print(f"Error: User '{user.name}' does not have an NFC code")
            return None
            
        if not isinstance(user.nfc, str):
            print(f"Error: User '{user.name}' has invalid NFC code format")
            return None
            
        if not user.nfc.strip():
            print(f"Error: User '{user.name}' has empty NFC code")
            return None
        
        # Prepare data for code generation
        nfc_data = user.nfc.strip()
        
        # Prepare text labels
        text_lines = []
        if user.name:
            # Split name into words and add each word on a separate line
            name_words = user.name.strip().split()
            text_lines.extend(name_words)
        
        # Call function to create image with Data Matrix code
        image = _create_datamatrix_image(nfc_data, text_lines)
        
        if image is None:
            print(f"Error: Failed to create Data Matrix image for user '{user.name}'")
            return None
        
        return image
        
    except Exception as e:
        print(f"Error: Unexpected error generating Data Matrix for user ID {user_id}: {str(e)}")
        return None

def generate_equipment_datamatrix(equipment_id: int) -> Image.Image | None:
    """
    Generates Data Matrix code for equipment
    
    Args:
        equipment_id: Equipment ID in the database
    
    Returns:
        PIL Image object with Data Matrix code and text or None on error
    """
    try:
        # Input parameter validation
        if equipment_id is None:
            print("Error: equipment_id parameter cannot be None")
            return None
            
        if not isinstance(equipment_id, int):
            print("Error: equipment_id parameter must be an integer")
            return None
            
        if equipment_id <= 0:
            print("Error: equipment_id must be a positive integer")
            return None
        
        # Check database connection
        if db is None:
            print("Error: Database connection is not available")
            return None
        
        # Get equipment data from database
        try:
            equipment = crud.get_equipment(db, equipment_id)
        except Exception as e:
            print(f"Error: Database error while retrieving equipment with ID {equipment_id}: {str(e)}")
            return None
            
        # Check equipment existence in database
        if not equipment:
            print(f"Error: Equipment with ID {equipment_id} not found in database")
            return None
        
        # Check equipment status (active/inactive)
        if hasattr(equipment, 'status') and not equipment.status:
            print(f"Error: Equipment '{equipment.name}' (ID: {equipment_id}) is inactive")
            return None
        
        # Validate presence and correctness of nfc field
        if not hasattr(equipment, 'nfc'):
            print(f"Error: Equipment '{equipment.name}' does not have nfc attribute")
            return None
            
        if equipment.nfc is None:
            print(f"Error: Equipment '{equipment.name}' (ID: {equipment_id}) does not have an NFC code")
            return None
            
        if not isinstance(equipment.nfc, str):
            print(f"Error: Equipment '{equipment.name}' (ID: {equipment_id}) has invalid NFC code format (expected string, got {type(equipment.nfc).__name__})")
            return None
            
        if not equipment.nfc.strip():
            print(f"Error: Equipment '{equipment.name}' (ID: {equipment_id}) has empty NFC code")
            return None
        
        # Additional NFC code validation
        nfc_code = equipment.nfc.strip()
        if len(nfc_code) < 1:
            print(f"Error: Equipment '{equipment.name}' (ID: {equipment_id}) has NFC code that is too short")
            return None
            
        if len(nfc_code) > 255:  # Reasonable NFC code length limit
            print(f"Error: Equipment '{equipment.name}' (ID: {equipment_id}) has NFC code that is too long (max 255 characters)")
            return None
        
        # Check for invalid characters in NFC code
        try:
            nfc_code.encode('utf-8')
        except UnicodeEncodeError:
            print(f"Error: Equipment '{equipment.name}' (ID: {equipment_id}) has NFC code with invalid characters")
            return None
        
        # Validate equipment name for text labels
        if not hasattr(equipment, 'name') or not equipment.name:
            print(f"Warning: Equipment (ID: {equipment_id}) does not have a name, using 'Unknown Equipment'")
            equipment_name = "Unknown Equipment"
        else:
            equipment_name = str(equipment.name).strip()
            if not equipment_name:
                print(f"Warning: Equipment (ID: {equipment_id}) has empty name, using 'Unknown Equipment'")
                equipment_name = "Unknown Equipment"
        
        # Prepare data for code generation
        nfc_data = nfc_code
        
        # Prepare text labels
        text_lines = []
        
        # Add serial number if available
        if hasattr(equipment, 'serialnum') and equipment.serialnum:
            serial_num = str(equipment.serialnum).strip()
            if serial_num:
                # Check if serial number fits on one line with name
                combined_text = f"{equipment_name} {serial_num}"
                if len(combined_text) <= 9:
                    # If total length doesn't exceed 9 characters, add on one line
                    text_lines.append(combined_text)
                else:
                    # If exceeds, add on separate lines
                    text_lines.append(equipment_name)
                    text_lines.append(serial_num)
            else:
                text_lines.append(equipment_name)
        else:
            text_lines.append(equipment_name)
        
        # Validate prepared data before generation
        if not nfc_data:
            print(f"Error: NFC data is empty after validation for equipment '{equipment_name}' (ID: {equipment_id})")
            return None
        
        # Call function to create image with Data Matrix code
        try:
            image = _create_datamatrix_image(nfc_data, text_lines)
        except Exception as e:
            print(f"Error: Failed to create Data Matrix image for equipment '{equipment_name}' (ID: {equipment_id}): {str(e)}")
            return None
        
        if image is None:
            print(f"Error: Failed to create Data Matrix image for equipment '{equipment_name}' (ID: {equipment_id})")
            return None
        
        print(f"Successfully generated Data Matrix code for equipment '{equipment_name}' (ID: {equipment_id})")
        return image
        
    except Exception as e:
        print(f"Error: Unexpected error generating Data Matrix for equipment ID {equipment_id}: {str(e)}")
        return None

async def nfc_equipment_rental_workflow(update_callback=None):
    """
    Process of creating a new rental or returning equipment using NFC:
    1. Equipment scanning
    2. Checking equipment rental status
    3. If rented - return, if not - continue rental process:
       3.1. Scanning user pass
       3.2. Confirming rental and creating record
       
    Args:
        update_callback: Callback function for updating equipment lists
    """
    if db is None:
        ui.notify("Database connection error", color="negative")
        return
    
    # Get equipment NFC
    equipment_nfc = await get_nfc_input("Scan Device's Code")
    if not equipment_nfc:
        ui.notify("Device scanning cancelled", color="warning")
        return
    
    # Find equipment by NFC
    equipment = crud.find_equipment_by_nfc(db, equipment_nfc)
    if not equipment:
        ui.notify(f"Equipment not found", color="negative")
        #ui.notify(f"Equipment with NFC {equipment_nfc} not found", color="negative") #for debug
        return
    
    # Check if equipment is already rented
    rental = crud.is_equipment_rented(db, equipment.id_eq)
    
    if rental:
        # Equipment is already rented, show return dialog
        dialog = ui.dialog()
        confirmed = asyncio.Future()
        
        def on_confirm():
            crud.return_equipment(db, rental.id_re)
            ui.notify('Equipment successfully returned', color="positive")
            dialog.close()
            confirmed.set_result(True)
            # Update equipment lists after return
            if update_callback:
                update_callback()
        
        def on_cancel():
            dialog.close()
            confirmed.set_result(False)
        
        with dialog, ui.card():
            with ui.row().classes('w-full justify-between items-center'):
                ui.label(text='Equipment Return').style('font-size: 200%')
                ui.button(icon='close', on_click=on_cancel).props('flat round')
            with ui.separator():
                pass

            with ui.row().classes('w-full justify-between items-center'):
                ui.label(f"{equipment.name}").style('font-weight: bold; font-size: 16px')
                ui.label(f"{equipment.etype.name if equipment.etype else 'Unknown'}")
            with ui.separator():
                pass
            ui.html(f"Rented by: <b>{rental.user.name}</b>")
            ui.label(f"Department: {rental.user.department.name}")
            ui.label(f"Rented since: {rental.rental_start.strftime('%Y-%m-%d %H:%M')}")
            with ui.separator():
                pass
            if rental.comment:
                ui.label("Comment:").style('margin-top: 10px; font-weight: bold')
                ui.label(rental.comment).style('white-space: pre-wrap')
            
            ui.button('Confirm Return', on_click=on_confirm).props('unelevated color=primary')
        
        dialog.open()
        await confirmed
        
    else:        
        # Show user input dialog (simultaneous NFC scan and manual selection)
        user = await get_user_input_with_selection(equipment)
        if not user:
            ui.notify("User selection cancelled", color="warning")
            return
        
        # Show confirmation dialog
        dialog = ui.dialog()
        confirmed = asyncio.Future()
        
        comment_text = ""
        
        def on_confirm():
            dialog.close()
            confirmed.set_result(True)
        
        def on_cancel():
            dialog.close()
            confirmed.set_result(False)
        
        def on_comment_change(e):
            nonlocal comment_text
            comment_text = e.value
        
        with dialog, ui.card():
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Rental Confirmation').style('font-size: 200%')
                ui.button(icon='close', on_click=on_cancel).props('flat round')
            
            with ui.separator():
                pass

            ui.label('User:').style('font-weight: bold; font-size: 16px')
            ui.label(f"{user.name}").style('font-weight: bold')
            ui.label(f"Department: {user.department.name}")

            with ui.separator():
                pass
            
            ui.label('Equipment:').style('font-weight: bold; font-size: 16px')
            with ui.row().classes('w-full justify-between items-center'):
                ui.label(f"{equipment.name}").style('font-weight: bold')
                ui.label(f"{equipment.etype.name if equipment.etype else 'Not specified'}")
            ui.label(f"S/N: {equipment.serialnum or 'Not specified'}")


            with ui.separator():
                pass
                
            ui.input('Comment (optional)', on_change=on_comment_change).style('width: 100%')
            
            ui.button('Confirm Rental', on_click=on_confirm).props('unelevated color=primary')
        
        dialog.open()
        
        # Wait for confirmation result
        result = await confirmed
        
        if result:
            try:
                # Create rental record
                rental = crud.create_rental(db, user.id_us, equipment.id_eq, comment_text)
                ui.notify("Rental successfully created", color="positive")
                # Update equipment lists after rental
                if update_callback:
                    update_callback()
            except Exception as e:
                ui.notify(f"Error creating rental: {str(e)}", color="negative")
        else:
            ui.notify("Operation cancelled", color="warning")


# Test functions for Data Matrix generation
def test_datamatrix_generation():
    """
    Simple test function to verify Data Matrix code generation for users and equipment.
    
    This function tests:
    - User Data Matrix generation with valid data
    - Equipment Data Matrix generation with valid data
    - Error handling for invalid inputs
    """
    print("Testing Data Matrix generation functions...")
    
    # Test helper function
    print("  Testing _create_datamatrix_image...")
    test_image = _create_datamatrix_image("test_data_123", ["Test User", "Test Department"])
    if test_image and isinstance(test_image, Image.Image):
        print(f"    ✓ Helper function works - Image size: {test_image.size}")
    else:
        print("    ✗ Helper function failed")
    
    # Test with database
    try:
        # Test user generation
        print("  Testing generate_user_datamatrix...")
        users = crud.get_all_users(db)
        if users:
            # Find user with NFC
            user_with_nfc = next((u for u in users if u.nfc and u.nfc.strip()), None)
            if user_with_nfc:
                user_image = generate_user_datamatrix(user_with_nfc.id_us)
                if user_image:
                    print(f"    ✓ User Data Matrix generated for '{user_with_nfc.name}' - Size: {user_image.size}")
                else:
                    print(f"    ✗ Failed to generate user Data Matrix for '{user_with_nfc.name}'")
            else:
                print("    ! No users with NFC codes found")
        else:
            print("    ! No users found in database")
        
        # Test equipment generation
        print("  Testing generate_equipment_datamatrix...")
        equipment_list = crud.get_all_equipment(db)
        if equipment_list:
            # Find equipment with NFC
            equipment_with_nfc = next((e for e in equipment_list if e.nfc and e.nfc.strip()), None)
            if equipment_with_nfc:
                equipment_image = generate_equipment_datamatrix(equipment_with_nfc.id_eq)
                if equipment_image:
                    print(f"    ✓ Equipment Data Matrix generated for '{equipment_with_nfc.name}' - Size: {equipment_image.size}")
                else:
                    print(f"    ✗ Failed to generate equipment Data Matrix for '{equipment_with_nfc.name}'")
            else:
                print("    ! No equipment with NFC codes found")
        else:
            print("    ! No equipment found in database")
            
    except Exception as e:
        print(f"    ✗ Database test failed: {str(e)}")
    
    print("Data Matrix generation tests completed.\n")


def validate_datamatrix_image(image):
    """
    Validate properties of a generated Data Matrix image.
    
    Args:
        image: PIL Image object to validate
    
    Returns:
        bool: True if image passes validation, False otherwise
    """
    if not isinstance(image, Image.Image):
        print("    ✗ Object is not a PIL Image")
        return False
    
    width, height = image.size
    if width < 50 or height < 50:
        print(f"    ✗ Image too small: {width}x{height} (expected at least 50x50)")
        return False
    
    if image.mode not in ['RGB', 'RGBA', 'L']:
        print(f"    ✗ Unexpected image mode: {image.mode}")
        return False
    
    print(f"    ✓ Image validation passed: {width}x{height}, mode: {image.mode}")
    return True


def test_datamatrix_validation():
    """
    Test validation of created Data Matrix images.
    
    This function tests:
    - Image size validation
    - Image format validation
    - Error handling for invalid objects
    """
    print("Testing Data Matrix image validation...")
    
    # Test with valid image
    print("  Testing valid image validation...")
    test_image = _create_datamatrix_image("validation_test", ["Test Validation"])
    if test_image:
        is_valid = validate_datamatrix_image(test_image)
        if is_valid:
            print("    ✓ Valid image passed validation")
        else:
            print("    ✗ Valid image failed validation")
    else:
        print("    ✗ Failed to create test image")
    
    # Test with invalid object
    print("  Testing invalid object validation...")
    is_valid = validate_datamatrix_image("not_an_image")
    if not is_valid:
        print("    ✓ Invalid object correctly rejected")
    else:
        print("    ✗ Invalid object incorrectly accepted")
    
    print("Data Matrix validation tests completed.\n")


def _clean_filename(name: str, max_length: int = 50) -> str:
    """
    Cleans string for use in filename
    
    Args:
        name: Original string to clean
        max_length: Maximum length of resulting string
    
    Returns:
        Cleaned string safe for use in filename
    """
    import re
    import os
    
    if not name or not isinstance(name, str):
        return "unknown"
    
    # Remove extra spaces
    cleaned = name.strip()
    
    if not cleaned:
        return "unknown"
    
    # Replace invalid characters with underscores
    # Invalid characters for Windows: < > : " | ? * \ /
    # Also remove control characters
    cleaned = re.sub(r'[<>:"|?*\\/\x00-\x1f\x7f]', '_', cleaned)
    
    # Replace multiple spaces and underscores with single ones
    cleaned = re.sub(r'[\s_]+', '_', cleaned)
    
    # Remove dots at beginning and end (reserved names in Windows)
    cleaned = cleaned.strip('.')
    
    # Check Windows reserved names
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    if cleaned.upper() in reserved_names:
        cleaned = f"_{cleaned}"
    
    # Limit length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip('_')
    
    # If string is empty after all operations, return default value
    if not cleaned:
        return "unknown"
    
    return cleaned


def _ensure_unique_filename(directory: str, base_name: str, extension: str = ".png") -> str:
    """
    Ensures filename uniqueness in specified directory
    
    Args:
        directory: Path to directory
        base_name: Base filename (without extension)
        extension: File extension (with dot)
    
    Returns:
        Unique filename
    """
    import os
    
    filename = f"{base_name}{extension}"
    full_path = os.path.join(directory, filename)
    
    # If file doesn't exist, return original name
    if not os.path.exists(full_path):
        return filename
    
    # If file exists, add numeric suffix
    counter = 1
    while True:
        filename = f"{base_name}_{counter}{extension}"
        full_path = os.path.join(directory, filename)
        
        if not os.path.exists(full_path):
            return filename
        
        counter += 1
        
        # Protection from infinite loop
        if counter > 9999:
            import time
            timestamp = int(time.time())
            filename = f"{base_name}_{timestamp}{extension}"
            break
    
    return filename


def generate_all_users_codes(output_directory: str) -> tuple[int, int]:
    """
    Generates Data Matrix codes for all users and saves to specified folder
    
    Args:
        output_directory: Path to folder for saving files
    
    Returns:
        Tuple (number of created files, total number of users)
    """
    import os
    
    try:
        # Input parameter validation
        if not output_directory or not isinstance(output_directory, str):
            print("Error: output_directory must be a non-empty string")
            return (0, 0)
        
        # Check directory existence and accessibility
        if not os.path.exists(output_directory):
            try:
                os.makedirs(output_directory, exist_ok=True)
                print(f"Created output directory: {output_directory}")
            except Exception as e:
                print(f"Error: Cannot create output directory '{output_directory}': {str(e)}")
                return (0, 0)
        
        if not os.path.isdir(output_directory):
            print(f"Error: '{output_directory}' is not a directory")
            return (0, 0)
        
        if not os.access(output_directory, os.W_OK):
            print(f"Error: No write permission for directory '{output_directory}'")
            return (0, 0)
        
        # Get all users from database
        try:
            users = crud.get_all_users(db)
        except Exception as e:
            print(f"Error: Failed to retrieve users from database: {str(e)}")
            return (0, 0)
        
        if not users:
            print("Warning: No users found in database")
            return (0, 0)
        
        total_users = len(users)
        print(f"Found {total_users} users in database")
        
        # Filter users with non-empty nfc fields
        users_with_nfc = []
        for user in users:
            if user.nfc and isinstance(user.nfc, str) and user.nfc.strip():
                users_with_nfc.append(user)
            else:
                print(f"Skipping user '{user.name}' (ID: {user.id_us}) - no valid NFC code")
        
        if not users_with_nfc:
            print("Warning: No users with valid NFC codes found")
            return (0, total_users)
        
        print(f"Processing {len(users_with_nfc)} users with valid NFC codes")
        
        # Generate codes for each user
        successful_count = 0
        
        for user in users_with_nfc:
            try:
                print(f"Generating code for user '{user.name}' (ID: {user.id_us})...")
                
                # Generate Data Matrix image
                image = generate_user_datamatrix(user.id_us)
                if image is None:
                    print(f"  Failed to generate Data Matrix for user '{user.name}'")
                    continue
                
                # Prepare filename
                clean_name = _clean_filename(user.name)
                base_filename = f"user_{user.id_us}_{clean_name}"
                
                # Ensure filename uniqueness
                filename = _ensure_unique_filename(output_directory, base_filename, ".png")
                file_path = os.path.join(output_directory, filename)
                
                # Save image
                try:
                    image.save(file_path, "PNG")
                    print(f"  Saved: {filename}")
                    successful_count += 1
                except Exception as e:
                    print(f"  Error saving file '{filename}': {str(e)}")
                    continue
                
            except Exception as e:
                print(f"  Error processing user '{user.name}' (ID: {user.id_us}): {str(e)}")
                continue
        
        print(f"Successfully generated {successful_count} out of {len(users_with_nfc)} Data Matrix codes")
        return (successful_count, total_users)
        
    except Exception as e:
        print(f"Error: Unexpected error in generate_all_users_codes: {str(e)}")
        return (0, 0)


def generate_all_equipment_codes(output_directory: str) -> tuple[int, int]:
    """
    Generates Data Matrix codes for all equipment and saves to specified folder
    
    Args:
        output_directory: Path to folder for saving files
    
    Returns:
        Tuple (number of created files, total number of equipment)
    """
    import os
    
    try:
        # Input parameter validation
        if not output_directory or not isinstance(output_directory, str):
            print("Error: output_directory must be a non-empty string")
            return (0, 0)
        
        # Check directory existence and accessibility
        if not os.path.exists(output_directory):
            try:
                os.makedirs(output_directory, exist_ok=True)
                print(f"Created output directory: {output_directory}")
            except Exception as e:
                print(f"Error: Cannot create output directory '{output_directory}': {str(e)}")
                return (0, 0)
        
        if not os.path.isdir(output_directory):
            print(f"Error: '{output_directory}' is not a directory")
            return (0, 0)
        
        if not os.access(output_directory, os.W_OK):
            print(f"Error: No write permission for directory '{output_directory}'")
            return (0, 0)
        
        # Get all equipment from database
        try:
            equipment_list = crud.get_all_equipment(db)
        except Exception as e:
            print(f"Error: Failed to retrieve equipment from database: {str(e)}")
            return (0, 0)
        
        if not equipment_list:
            print("Warning: No equipment found in database")
            return (0, 0)
        
        total_equipment = len(equipment_list)
        print(f"Found {total_equipment} equipment items in database")
        
        # Filter equipment with non-empty nfc fields
        equipment_with_nfc = []
        for equipment in equipment_list:
            if equipment.nfc and isinstance(equipment.nfc, str) and equipment.nfc.strip():
                equipment_with_nfc.append(equipment)
            else:
                print(f"Skipping equipment '{equipment.name}' (ID: {equipment.id_eq}) - no valid NFC code")
        
        if not equipment_with_nfc:
            print("Warning: No equipment with valid NFC codes found")
            return (0, total_equipment)
        
        print(f"Processing {len(equipment_with_nfc)} equipment items with valid NFC codes")
        
        # Generate codes for each equipment
        successful_count = 0
        
        for equipment in equipment_with_nfc:
            try:
                print(f"Generating code for equipment '{equipment.name}' (ID: {equipment.id_eq})...")
                
                # Generate Data Matrix image
                image = generate_equipment_datamatrix(equipment.id_eq)
                if image is None:
                    print(f"  Failed to generate Data Matrix for equipment '{equipment.name}'")
                    continue
                
                # Prepare filename
                clean_name = _clean_filename(equipment.name)
                base_filename = f"equipment_{equipment.id_eq}_{clean_name}"
                
                # Ensure filename uniqueness
                filename = _ensure_unique_filename(output_directory, base_filename, ".png")
                file_path = os.path.join(output_directory, filename)
                
                # Save image
                try:
                    image.save(file_path, "PNG")
                    print(f"  Saved: {filename}")
                    successful_count += 1
                except Exception as e:
                    print(f"  Error saving file '{filename}': {str(e)}")
                    continue
                
            except Exception as e:
                print(f"  Error processing equipment '{equipment.name}' (ID: {equipment.id_eq}): {str(e)}")
                continue
        
        print(f"Successfully generated {successful_count} out of {len(equipment_with_nfc)} Data Matrix codes")
        return (successful_count, total_equipment)
        
    except Exception as e:
        print(f"Error: Unexpected error in generate_all_equipment_codes: {str(e)}")
        return (0, 0)


def generate_single_user_code_file(user_id: int, output_directory: str) -> tuple[bool, str]:
    """
    Generates Data Matrix code for a single user and saves to specified folder
    
    Args:
        user_id: User ID
        output_directory: Path to folder for saving files
    
    Returns:
        Tuple (success status, message/filename)
    """
    import os
    
    try:
        # Input parameter validation
        if not output_directory or not isinstance(output_directory, str):
            return (False, "Error: output_directory must be a non-empty string")
        
        # Check directory existence and accessibility
        if not os.path.exists(output_directory):
            try:
                os.makedirs(output_directory, exist_ok=True)
            except Exception as e:
                return (False, f"Error: Cannot create output directory: {str(e)}")
        
        if not os.path.isdir(output_directory):
            return (False, "Error: Output path is not a directory")
        
        if not os.access(output_directory, os.W_OK):
            return (False, "Error: No write permission for directory")
        
        # Get user from database
        try:
            user = crud.get_user(db, user_id)
        except Exception as e:
            return (False, f"Error: Failed to retrieve user: {str(e)}")
        
        if not user:
            return (False, "Error: User not found")
            
        if not user.nfc or not user.nfc.strip():
            return (False, "Error: User has no NFC code")
            
        # Generate Data Matrix image
        image = generate_user_datamatrix(user.id_us)
        if image is None:
            return (False, "Error: Failed to generate Data Matrix image")
        
        # Prepare filename
        clean_name = _clean_filename(user.name)
        base_filename = f"user_{user.id_us}_{clean_name}"
        
        # Ensure filename uniqueness
        filename = _ensure_unique_filename(output_directory, base_filename, ".png")
        file_path = os.path.join(output_directory, filename)
        
        # Save image
        try:
            image.save(file_path, "PNG")
            return (True, filename)
        except Exception as e:
            return (False, f"Error saving file: {str(e)}")
            
    except Exception as e:
        return (False, f"Unexpected error: {str(e)}")


def generate_single_equipment_code_file(equipment_id: int, output_directory: str) -> tuple[bool, str]:
    """
    Generates Data Matrix code for a single equipment item and saves to specified folder
    
    Args:
        equipment_id: Equipment ID
        output_directory: Path to folder for saving files
    
    Returns:
        Tuple (success status, message/filename)
    """
    import os
    
    try:
        # Input parameter validation
        if not output_directory or not isinstance(output_directory, str):
            return (False, "Error: output_directory must be a non-empty string")
        
        # Check directory existence and accessibility
        if not os.path.exists(output_directory):
            try:
                os.makedirs(output_directory, exist_ok=True)
            except Exception as e:
                return (False, f"Error: Cannot create output directory: {str(e)}")
        
        if not os.path.isdir(output_directory):
            return (False, "Error: Output path is not a directory")
        
        if not os.access(output_directory, os.W_OK):
            return (False, "Error: No write permission for directory")
        
        # Get equipment from database
        try:
            equipment = crud.get_equipment(db, equipment_id)
        except Exception as e:
            return (False, f"Error: Failed to retrieve equipment: {str(e)}")
        
        if not equipment:
            return (False, "Error: Equipment not found")
            
        if not equipment.nfc or not equipment.nfc.strip():
            return (False, "Error: Equipment has no NFC code")
            
        # Generate Data Matrix image
        image = generate_equipment_datamatrix(equipment.id_eq)
        if image is None:
            return (False, "Error: Failed to generate Data Matrix image")
        
        # Prepare filename
        clean_name = _clean_filename(equipment.name)
        base_filename = f"equipment_{equipment.id_eq}_{clean_name}"
        
        # Ensure filename uniqueness
        filename = _ensure_unique_filename(output_directory, base_filename, ".png")
        file_path = os.path.join(output_directory, filename)
        
        # Save image
        try:
            image.save(file_path, "PNG")
            return (True, filename)
        except Exception as e:
            return (False, f"Error saving file: {str(e)}")
            
    except Exception as e:
        return (False, f"Unexpected error: {str(e)}")


def run_datamatrix_tests():
    """
    Run all Data Matrix generation and validation tests.
    
    This is the main test function that executes all test scenarios
    for the Data Matrix code generation functionality.
    """
    print("=" * 50)
    print("RUNNING DATA MATRIX TESTS")
    print("=" * 50)
    
    try:
        test_datamatrix_generation()
        test_datamatrix_validation()
        
        print("=" * 50)
        print("ALL DATA MATRIX TESTS COMPLETED")
        print("=" * 50)
        
    except Exception as e:
        print(f"ERROR: Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()