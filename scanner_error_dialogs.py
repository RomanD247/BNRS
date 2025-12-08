"""
Scanner Error Dialogs Module

This module provides comprehensive error dialogs and user feedback for USB HID scanner
operations. It handles connection failures, communication errors, permission issues,
and provides troubleshooting information.

Requirements: 1.5, 4.1, 4.2, 4.3, 4.4, 4.5
"""

import asyncio
import logging
import platform
from typing import Optional, Callable
from nicegui import ui


# Configure logging
logger = logging.getLogger(__name__)


class ScannerErrorDialogs:
    """
    Provides error dialog functionality for USB HID scanner operations.
    
    This class creates user-friendly error dialogs with troubleshooting information
    for various scanner error conditions.
    """
    
    @staticmethod
    async def show_connection_error(vid: int, pid: int, 
                                   retry_callback: Optional[Callable] = None,
                                   fallback_callback: Optional[Callable] = None) -> str:
        """
        Display connection error dialog when scanner device is not found.
        
        Shows VID/PID information, troubleshooting steps, and offers retry
        and fallback options.
        
        Args:
            vid: Vendor ID of the scanner
            pid: Product ID of the scanner
            retry_callback: Optional callback function to retry connection
            fallback_callback: Optional callback function to switch to keyboard mode
            
        Returns:
            User choice: "retry", "fallback", or "cancel"
            
        Requirements: 1.5, 4.1
        """
        logger.info(f"Showing connection error dialog for VID=0x{vid:04x}, PID=0x{pid:04x}")
        
        dialog = ui.dialog()
        result = asyncio.Future()
        
        def on_retry():
            logger.info("User chose to retry connection")
            dialog.close()
            result.set_result("retry")
        
        def on_fallback():
            logger.info("User chose to switch to keyboard mode")
            dialog.close()
            result.set_result("fallback")
        
        def on_cancel():
            logger.info("User cancelled connection error dialog")
            dialog.close()
            result.set_result("cancel")
        
        with dialog, ui.card().style('width: 500px; max-width: 90vw;'):
            # Header
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('error', size='32px').style('color: #d32f2f;')
                    ui.label('Scanner Not Found').style('font-size: 24px; font-weight: bold; color: #d32f2f;')
                ui.button(icon='close', on_click=on_cancel).props('flat round dense')
            
            ui.separator()
            
            # Error description
            ui.label('Could not connect to USB HID scanner device.').style(
                'font-size: 16px; margin: 10px 0;'
            )
            
            # Device information
            with ui.card().style('background-color: #f5f5f5; padding: 10px; margin: 10px 0;'):
                ui.label('Device Information:').style('font-weight: bold; margin-bottom: 5px;')
                ui.label(f'Vendor ID (VID): 0x{vid:04x} ({vid})').style('font-family: monospace;')
                ui.label(f'Product ID (PID): 0x{pid:04x} ({pid})').style('font-family: monospace;')
            
            # Troubleshooting steps
            ui.label('Troubleshooting Steps:').style('font-weight: bold; margin: 15px 0 5px 0;')
            
            with ui.column().style('margin-left: 20px;'):
                ui.label('1. Check that the scanner is plugged into a USB port').style('margin: 3px 0;')
                ui.label('2. Verify the scanner is powered on (if it has a power switch)').style('margin: 3px 0;')
                ui.label('3. Try unplugging and reconnecting the scanner').style('margin: 3px 0;')
                ui.label('4. Check if the scanner is configured for USB HID Vendor Mode').style('margin: 3px 0;')
                ui.label('5. Verify the VID/PID values match your scanner model').style('margin: 3px 0;')
                
                # Platform-specific advice
                system = platform.system()
                if system == "Linux":
                    ui.label('6. On Linux: Check USB device permissions (may need udev rules)').style(
                        'margin: 3px 0; color: #1976d2;'
                    )
                elif system == "Windows":
                    ui.label('6. On Windows: Check Device Manager for driver issues').style(
                        'margin: 3px 0; color: #1976d2;'
                    )
            
            ui.separator().style('margin: 15px 0;')
            
            # Action buttons
            with ui.row().classes('w-full justify-end gap-2'):
                if fallback_callback:
                    ui.button('Use Keyboard Mode', on_click=on_fallback).props('outline color=primary')
                if retry_callback:
                    ui.button('Retry Connection', on_click=on_retry).props('unelevated color=primary')
                ui.button('Cancel', on_click=on_cancel).props('flat')
        
        dialog.open()
        choice = await result
        
        # Execute callbacks if provided
        if choice == "retry" and retry_callback:
            await retry_callback()
        elif choice == "fallback" and fallback_callback:
            await fallback_callback()
        
        return choice
    
    @staticmethod
    async def show_timeout_error(timeout: int) -> str:
        """
        Display timeout error dialog when no scan is received within timeout period.
        
        Args:
            timeout: Timeout value in seconds
            
        Returns:
            User choice: "retry" or "cancel"
            
        Requirements: 4.4
        """
        logger.info(f"Showing timeout error dialog (timeout={timeout}s)")
        
        dialog = ui.dialog()
        result = asyncio.Future()
        
        def on_retry():
            logger.info("User chose to retry after timeout")
            dialog.close()
            result.set_result("retry")
        
        def on_cancel():
            logger.info("User cancelled after timeout")
            dialog.close()
            result.set_result("cancel")
        
        with dialog, ui.card().style('width: 450px; max-width: 90vw;'):
            # Header
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('schedule', size='32px').style('color: #f57c00;')
                    ui.label('Scan Timeout').style('font-size: 24px; font-weight: bold; color: #f57c00;')
                ui.button(icon='close', on_click=on_cancel).props('flat round dense')
            
            ui.separator()
            
            # Error description
            ui.label(f'No scan data received within {timeout} seconds.').style(
                'font-size: 16px; margin: 10px 0;'
            )
            
            ui.label('Please try again and ensure you scan the code within the timeout period.').style(
                'margin: 10px 0;'
            )
            
            ui.separator().style('margin: 15px 0;')
            
            # Action buttons
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Try Again', on_click=on_retry).props('unelevated color=primary')
                ui.button('Cancel', on_click=on_cancel).props('flat')
        
        dialog.open()
        return await result
    
    @staticmethod
    async def show_disconnection_error() -> str:
        """
        Display disconnection error dialog when scanner is disconnected during operation.
        
        Returns:
            User choice: "retry" or "cancel"
            
        Requirements: 4.2
        """
        logger.info("Showing disconnection error dialog")
        
        dialog = ui.dialog()
        result = asyncio.Future()
        
        def on_retry():
            logger.info("User chose to retry after disconnection")
            dialog.close()
            result.set_result("retry")
        
        def on_cancel():
            logger.info("User cancelled after disconnection")
            dialog.close()
            result.set_result("cancel")
        
        with dialog, ui.card().style('width: 450px; max-width: 90vw;'):
            # Header
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('usb_off', size='32px').style('color: #d32f2f;')
                    ui.label('Scanner Disconnected').style('font-size: 24px; font-weight: bold; color: #d32f2f;')
                ui.button(icon='close', on_click=on_cancel).props('flat round dense')
            
            ui.separator()
            
            # Error description
            ui.label('The scanner was disconnected during the scan operation.').style(
                'font-size: 16px; margin: 10px 0;'
            )
            
            ui.label('Please reconnect the scanner and try again.').style(
                'margin: 10px 0;'
            )
            
            ui.separator().style('margin: 15px 0;')
            
            # Action buttons
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Try Again', on_click=on_retry).props('unelevated color=primary')
                ui.button('Cancel', on_click=on_cancel).props('flat')
        
        dialog.open()
        return await result
    
    @staticmethod
    async def show_corrupted_data_error() -> str:
        """
        Display corrupted data error dialog when invalid data is received.
        
        Returns:
            User choice: "retry" or "cancel"
            
        Requirements: 4.3
        """
        logger.info("Showing corrupted data error dialog")
        
        dialog = ui.dialog()
        result = asyncio.Future()
        
        def on_retry():
            logger.info("User chose to retry after corrupted data")
            dialog.close()
            result.set_result("retry")
        
        def on_cancel():
            logger.info("User cancelled after corrupted data")
            dialog.close()
            result.set_result("cancel")
        
        with dialog, ui.card().style('width: 450px; max-width: 90vw;'):
            # Header
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('warning', size='32px').style('color: #f57c00;')
                    ui.label('Invalid Scan Data').style('font-size: 24px; font-weight: bold; color: #f57c00;')
                ui.button(icon='close', on_click=on_cancel).props('flat round dense')
            
            ui.separator()
            
            # Error description
            ui.label('The scanned data appears to be corrupted or invalid.').style(
                'font-size: 16px; margin: 10px 0;'
            )
            
            ui.label('This may happen if:').style('font-weight: bold; margin: 10px 0 5px 0;')
            with ui.column().style('margin-left: 20px;'):
                ui.label('• The code was not scanned completely').style('margin: 3px 0;')
                ui.label('• The scanner moved during scanning').style('margin: 3px 0;')
                ui.label('• The code is damaged or unclear').style('margin: 3px 0;')
            
            ui.label('Please try scanning again, ensuring the code is clear and the scanner is steady.').style(
                'margin: 10px 0;'
            )
            
            ui.separator().style('margin: 15px 0;')
            
            # Action buttons
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Scan Again', on_click=on_retry).props('unelevated color=primary')
                ui.button('Cancel', on_click=on_cancel).props('flat')
        
        dialog.open()
        return await result
    
    @staticmethod
    async def show_permission_error(vid: int, pid: int) -> str:
        """
        Display permission error dialog when USB access is denied.
        
        Provides platform-specific instructions for granting USB permissions.
        
        Args:
            vid: Vendor ID of the scanner
            pid: Product ID of the scanner
            
        Returns:
            User choice: "retry" or "cancel"
            
        Requirements: 4.5
        """
        logger.info(f"Showing permission error dialog for VID=0x{vid:04x}, PID=0x{pid:04x}")
        
        dialog = ui.dialog()
        result = asyncio.Future()
        
        def on_retry():
            logger.info("User chose to retry after permission error")
            dialog.close()
            result.set_result("retry")
        
        def on_cancel():
            logger.info("User cancelled after permission error")
            dialog.close()
            result.set_result("cancel")
        
        system = platform.system()
        
        with dialog, ui.card().style('width: 550px; max-width: 90vw;'):
            # Header
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('lock', size='32px').style('color: #d32f2f;')
                    ui.label('Permission Denied').style('font-size: 24px; font-weight: bold; color: #d32f2f;')
                ui.button(icon='close', on_click=on_cancel).props('flat round dense')
            
            ui.separator()
            
            # Error description
            ui.label('Insufficient permissions to access the USB scanner device.').style(
                'font-size: 16px; margin: 10px 0;'
            )
            
            # Platform-specific instructions
            if system == "Linux":
                ui.label('Linux: Grant USB Permissions').style('font-weight: bold; margin: 15px 0 5px 0;')
                
                ui.label('You need to create a udev rule to grant access to the scanner:').style('margin: 5px 0;')
                
                with ui.card().style('background-color: #f5f5f5; padding: 10px; margin: 10px 0;'):
                    ui.label('1. Create a udev rule file:').style('font-weight: bold; margin-bottom: 5px;')
                    ui.label('sudo nano /etc/udev/rules.d/99-scanner.rules').style(
                        'font-family: monospace; background-color: #e0e0e0; padding: 5px; margin: 5px 0;'
                    )
                    
                    ui.label('2. Add this line to the file:').style('font-weight: bold; margin: 10px 0 5px 0;')
                    rule_text = f'SUBSYSTEM=="usb", ATTRS{{idVendor}}=="{vid:04x}", ATTRS{{idProduct}}=="{pid:04x}", MODE="0666"'
                    ui.label(rule_text).style(
                        'font-family: monospace; background-color: #e0e0e0; padding: 5px; margin: 5px 0; word-break: break-all;'
                    )
                    
                    ui.label('3. Reload udev rules:').style('font-weight: bold; margin: 10px 0 5px 0;')
                    ui.label('sudo udevadm control --reload-rules && sudo udevadm trigger').style(
                        'font-family: monospace; background-color: #e0e0e0; padding: 5px; margin: 5px 0;'
                    )
                    
                    ui.label('4. Unplug and reconnect the scanner').style('margin: 10px 0 0 0;')
            
            elif system == "Windows":
                ui.label('Windows: Check Driver and Permissions').style('font-weight: bold; margin: 15px 0 5px 0;')
                
                with ui.column().style('margin-left: 20px;'):
                    ui.label('1. Open Device Manager (devmgmt.msc)').style('margin: 3px 0;')
                    ui.label('2. Look for the scanner under "Human Interface Devices"').style('margin: 3px 0;')
                    ui.label('3. Right-click and select "Properties"').style('margin: 3px 0;')
                    ui.label('4. Check if the device is working properly').style('margin: 3px 0;')
                    ui.label('5. Try running the application as Administrator').style('margin: 3px 0;')
            
            elif system == "Darwin":  # macOS
                ui.label('macOS: Grant USB Permissions').style('font-weight: bold; margin: 15px 0 5px 0;')
                
                with ui.column().style('margin-left: 20px;'):
                    ui.label('1. macOS usually grants USB access automatically').style('margin: 3px 0;')
                    ui.label('2. Try unplugging and reconnecting the scanner').style('margin: 3px 0;')
                    ui.label('3. Check System Preferences > Security & Privacy').style('margin: 3px 0;')
                    ui.label('4. Grant permission if prompted').style('margin: 3px 0;')
            
            else:
                ui.label('Please consult your operating system documentation for granting USB device permissions.').style(
                    'margin: 10px 0;'
                )
            
            ui.separator().style('margin: 15px 0;')
            
            # Action buttons
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Try Again', on_click=on_retry).props('unelevated color=primary')
                ui.button('Cancel', on_click=on_cancel).props('flat')
        
        dialog.open()
        return await result
    
    @staticmethod
    def show_notification(message: str, error_type: str = "info"):
        """
        Show a brief notification message.
        
        Args:
            message: Message to display
            error_type: Type of notification ("info", "warning", "error", "success")
        """
        logger.info(f"Showing notification: {error_type} - {message}")
        
        type_map = {
            "info": "info",
            "warning": "warning",
            "error": "negative",
            "success": "positive"
        }
        
        ui.notify(
            message,
            type=type_map.get(error_type, "info"),
            timeout=5000
        )
