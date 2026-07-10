"""
Scanner Configuration GUI Module

This module provides a graphical interface for configuring USB HID scanner settings
in the Admin Panel. It allows administrators to view current configuration, list
connected USB HID devices, select devices, test connections, and switch scanner modes.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8
"""

from nicegui import ui, run
import scanner_config
from usb_hid_scanner import USBHIDScanner
import logging


# Configure logging
logger = logging.getLogger(__name__)


async def show_scanner_config_dialog():
    """
    Display scanner configuration dialog with:
    - Current configuration display
    - List of connected USB HID devices
    - Device selection and VID/PID saving
    - Mode switching (usb_vendor/keyboard)
    - Test connection functionality
    - Connection status indicators
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8
    """
    logger.info("Opening scanner configuration dialog")
    
    # Load current configuration
    config = scanner_config.load_config()
    current_vid = config["usb_vendor"]["vid"]
    current_pid = config["usb_vendor"]["pid"]
    current_mode = config.get("scanner_mode", "usb_vendor")
    
    # State variables for the dialog
    state = {
        "vid": current_vid,
        "pid": current_pid,
        "mode": current_mode,
        "devices": [],
        "connection_status": "unknown"
    }
    
    def check_connection_status():
        """Check if scanner is currently connected.

        Blocking (opens/closes a USB HID handle) - always invoke via
        `run.io_bound(...)` from an async context, never call directly from
        the UI thread.
        """
        try:
            scanner = USBHIDScanner(state["vid"], state["pid"], timeout=5)
            if scanner.connect():
                scanner.disconnect()
                state["connection_status"] = "connected"
                logger.info(f"Scanner connected: VID=0x{state['vid']:04x}, PID=0x{state['pid']:04x}")
                return True
            else:
                state["connection_status"] = "disconnected"
                logger.warning(f"Scanner not connected: VID=0x{state['vid']:04x}, PID=0x{state['pid']:04x}")
                return False
        except PermissionError:
            state["connection_status"] = "permission_error"
            logger.error("Permission error accessing scanner")
            return False
        except Exception as e:
            state["connection_status"] = "error"
            logger.error(f"Error checking connection: {e}")
            return False
    
    with ui.dialog() as dialog, ui.card().style('width: 700px; max-height: 80vh'):
        with ui.row().classes('w-full justify-between items-center no-wrap'):
            ui.label('Scanner Configuration').style('font-size: 150%; font-weight: bold')
            ui.button(icon='close', on_click=dialog.close).props('flat round')
        
        ui.separator()
        
        # Current Configuration Section
        with ui.column().classes('w-full'):
            ui.label('Current Configuration').style('font-size: 120%; font-weight: bold; margin-bottom: 10px')
            
            with ui.row().classes('w-full items-center'):
                ui.label('VID:').style('font-weight: bold; width: 100px')
                vid_label = ui.label(f"{state['vid']} (0x{state['vid']:04X})")
            
            with ui.row().classes('w-full items-center'):
                ui.label('PID:').style('font-weight: bold; width: 100px')
                pid_label = ui.label(f"{state['pid']} (0x{state['pid']:04X})")
            
            with ui.row().classes('w-full items-center'):
                ui.label('Mode:').style('font-weight: bold; width: 100px')
                mode_label = ui.label(state['mode'])
            
            with ui.row().classes('w-full items-center'):
                ui.label('Status:').style('font-weight: bold; width: 100px')
                # Rendered as a loading placeholder first; the dialog opens
                # immediately and the real status is filled in afterwards by
                # update_connection_status(), once the blocking USB probe
                # (run off the UI thread) resolves.
                status_spinner = ui.spinner(size='sm')
                status_label = ui.label('Checking connection...').style('color: gray; font-weight: bold')
                status_icon = ui.icon('help', color='grey')

                async def update_connection_status():
                    """Probe the scanner connection off the UI thread, then
                    reflect the result in the status row above."""
                    await run.io_bound(check_connection_status)
                    status_spinner.set_visibility(False)
                    if state["connection_status"] == "connected":
                        status_label.set_text('Connected')
                        status_label.style('color: green; font-weight: bold')
                        status_icon.props('name=check_circle color=green')
                    elif state["connection_status"] == "permission_error":
                        status_label.set_text('Permission Error')
                        status_label.style('color: orange; font-weight: bold')
                        status_icon.props('name=warning color=orange')
                    else:
                        status_label.set_text('Disconnected')
                        status_label.style('color: red; font-weight: bold')
                        status_icon.props('name=cancel color=red')
        
        ui.separator()
        
        # Device Enumeration Section
        with ui.column().classes('w-full'):
            ui.label('Available USB HID Devices').style('font-size: 120%; font-weight: bold; margin-bottom: 10px')
            
            devices_container = ui.column().classes('w-full')
            
            async def refresh_devices():
                """Refresh the list of connected USB HID devices"""
                logger.info("Refreshing USB HID device list")
                devices_container.clear()

                with devices_container:
                    ui.label('Scanning for devices...').style('color: gray')
                    ui.spinner(size='sm')

                # Get list of devices - run off the UI thread since HID
                # enumeration is a blocking call; the "Scanning..." spinner
                # above has already been sent to the client by the time this
                # awaits, so the dialog doesn't appear frozen while it runs.
                devices = await run.io_bound(USBHIDScanner.list_devices)
                state["devices"] = devices
                
                devices_container.clear()
                
                if not devices:
                    with devices_container:
                        ui.label('No USB HID devices found').style('color: gray; font-style: italic')
                    logger.info("No USB HID devices found")
                    return
                
                logger.info(f"Found {len(devices)} USB HID devices")
                
                with devices_container:
                    # Create table for devices
                    with ui.scroll_area().style('max-height: 300px; width: 100%'):
                        for device in devices:
                            vid = device.get('vendor_id', 0)
                            pid = device.get('product_id', 0)
                            manufacturer = device.get('manufacturer_string', 'Unknown')
                            product = device.get('product_string', 'Unknown')
                            
                            with ui.card().classes('w-full').style('margin-bottom: 10px; padding: 10px'):
                                with ui.row().classes('w-full justify-between items-center'):
                                    with ui.column():
                                        ui.label(f"{product}").style('font-weight: bold')
                                        ui.label(f"Manufacturer: {manufacturer}").style('font-size: 90%; color: gray')
                                        ui.label(f"VID: {vid} (0x{vid:04X}) | PID: {pid} (0x{pid:04X})").style('font-size: 90%')
                                    
                                    ui.button('Select', on_click=lambda v=vid, p=pid: select_device(v, p)).props('color=primary')
            
            def select_device(vid, pid):
                """Select a device and populate VID/PID fields"""
                logger.info(f"Device selected: VID=0x{vid:04x}, PID=0x{pid:04x}")
                state["vid"] = vid
                state["pid"] = pid
                
                # Update labels
                vid_label.set_text(f"{vid} (0x{vid:04X})")
                pid_label.set_text(f"{pid} (0x{pid:04X})")
                
                ui.notify(f'Device selected: VID={vid} (0x{vid:04X}), PID={pid} (0x{pid:04X})', type='info')
            
            with ui.row().classes('w-full'):
                ui.button('Refresh Devices', icon='refresh', on_click=refresh_devices).props('color=primary')

            # Initial device list is populated after the dialog is shown
            # (see the `await refresh_devices()` call below), not here -
            # calling the blocking scan during dialog construction would
            # freeze the UI before this "Refresh Devices" row even renders.

        ui.separator()
        
        # Mode Switching Section
        with ui.column().classes('w-full'):
            ui.label('Scanner Mode').style('font-size: 120%; font-weight: bold; margin-bottom: 10px')
            
            def on_mode_change(e):
                """Handle mode change"""
                new_mode = e.value
                logger.info(f"Mode change requested: {state['mode']} -> {new_mode}")
                state["mode"] = new_mode
                mode_label.set_text(new_mode)
            
            mode_select = ui.select(
                options=['usb_vendor', 'keyboard'],
                value=state['mode'],
                label='Select Mode',
                on_change=on_mode_change
            ).style('width: 200px')
            
            ui.label('USB Vendor: Direct USB HID communication (recommended)').style('font-size: 90%; color: gray')
            ui.label('Keyboard: Legacy keyboard emulation mode (fallback)').style('font-size: 90%; color: gray')
        
        ui.separator()
        
        # Action Buttons Section
        with ui.column().classes('w-full'):
            ui.label('Actions').style('font-size: 120%; font-weight: bold; margin-bottom: 10px')
            
            def test_connection():
                """Test connection with current VID/PID"""
                logger.info(f"Testing connection: VID=0x{state['vid']:04x}, PID=0x{state['pid']:04x}")
                ui.notify('Testing connection...', type='info')
                
                try:
                    scanner = USBHIDScanner(state["vid"], state["pid"], timeout=5)
                    if scanner.connect():
                        scanner.disconnect()
                        state["connection_status"] = "connected"
                        status_label.set_text('Connected')
                        status_label.style('color: green; font-weight: bold')
                        status_icon.props('name=check_circle color=green')
                        ui.notify('Connection successful!', type='positive')
                        logger.info("Connection test successful")
                    else:
                        state["connection_status"] = "disconnected"
                        status_label.set_text('Disconnected')
                        status_label.style('color: red; font-weight: bold')
                        status_icon.props('name=cancel color=red')
                        ui.notify('Connection failed. Check VID/PID and device connection.', type='negative')
                        logger.warning("Connection test failed")
                except PermissionError:
                    state["connection_status"] = "permission_error"
                    status_label.set_text('Permission Error')
                    status_label.style('color: orange; font-weight: bold')
                    status_icon.props('name=warning color=orange')
                    ui.notify('Permission error. Check USB device permissions.', type='warning')
                    logger.error("Permission error during connection test")
                except Exception as e:
                    state["connection_status"] = "error"
                    status_label.set_text('Error')
                    status_label.style('color: red; font-weight: bold')
                    status_icon.props('name=error color=red')
                    ui.notify(f'Error: {str(e)}', type='negative')
                    logger.error(f"Error during connection test: {e}")
            
            def save_configuration():
                """Save configuration to file"""
                logger.info(f"Saving configuration: VID=0x{state['vid']:04x}, PID=0x{state['pid']:04x}, Mode={state['mode']}")
                
                # Validate VID/PID
                if state["vid"] < 1 or state["vid"] > 65535:
                    ui.notify('Invalid VID. Must be between 1 and 65535.', type='warning')
                    logger.warning(f"Invalid VID: {state['vid']}")
                    return
                
                if state["pid"] < 1 or state["pid"] > 65535:
                    ui.notify('Invalid PID. Must be between 1 and 65535.', type='warning')
                    logger.warning(f"Invalid PID: {state['pid']}")
                    return
                
                # Build the complete merged config (VID, PID, AND mode
                # together) and write it with a single save_config() call,
                # so a mid-way failure can't leave a half-saved config
                # (e.g. new VID/PID persisted with the old mode, or vice
                # versa) - unlike calling update_usb_config()/
                # set_scanner_mode() separately, which each load+save on
                # their own.
                config = scanner_config.load_config()
                config["usb_vendor"]["vid"] = state["vid"]
                config["usb_vendor"]["pid"] = state["pid"]
                config["scanner_mode"] = state["mode"]
                success = scanner_config.save_config(config)

                if success:
                    ui.notify('Configuration saved successfully!', type='positive')
                    logger.info("Configuration saved successfully")

                    # Update current configuration display
                    vid_label.set_text(f"{state['vid']} (0x{state['vid']:04X})")
                    pid_label.set_text(f"{state['pid']} (0x{state['pid']:04X})")
                    mode_label.set_text(state['mode'])
                else:
                    ui.notify('Failed to save configuration.', type='negative')
                    logger.error("Failed to save configuration")
            
            def reset_to_defaults():
                """Reset configuration to default values"""
                logger.info("Resetting configuration to defaults")
                
                # Default values
                default_vid = 4602
                default_pid = 33282
                default_mode = "usb_vendor"
                
                state["vid"] = default_vid
                state["pid"] = default_pid
                state["mode"] = default_mode

                # Single merged write (same reasoning as save_configuration()
                # above) - two independent update_usb_config()/
                # set_scanner_mode() calls could leave a half-reset config on
                # a mid-way failure.
                config = scanner_config.load_config()
                config["usb_vendor"]["vid"] = default_vid
                config["usb_vendor"]["pid"] = default_pid
                config["scanner_mode"] = default_mode
                scanner_config.save_config(config)

                # Update UI
                vid_label.set_text(f"{default_vid} (0x{default_vid:04X})")
                pid_label.set_text(f"{default_pid} (0x{default_pid:04X})")
                mode_label.set_text(default_mode)
                mode_select.set_value(default_mode)
                
                ui.notify('Configuration reset to defaults', type='info')
                logger.info("Configuration reset to defaults")
            
            with ui.row().classes('w-full justify-between'):
                ui.button('Test Connection', icon='cable', on_click=test_connection).props('color=primary')
                ui.button('Save Configuration', icon='save', on_click=save_configuration).props('color=positive')
                ui.button('Reset to Defaults', icon='restore', on_click=reset_to_defaults).props('color=warning')
    
    # Reopening this dialog repeatedly (Admin Panel button) would otherwise
    # accumulate detached DOM nodes forever - delete it once hidden.
    dialog.on('hide', dialog.delete)
    dialog.open()
    logger.info("Scanner configuration dialog opened")

    # Only now - with the dialog (and its loading placeholders) already
    # rendered - kick off the blocking USB device enumeration and
    # connection-check calls, each via run.io_bound so they run off the UI
    # thread instead of freezing the window during dialog construction.
    await refresh_devices()
    await update_connection_status()
