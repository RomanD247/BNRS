"""Shared native-dialog helper (tkinter-tk-in-worker-threads).

Replaces the previous tk.Tk()-via-run.io_bound() folder-picker pattern used
identically in main.py, gui_changeUser.py, and gui_changeEquip.py: building a
Tk root off the main thread is unsafe on Windows and could hang/crash the
app. create_file_dialog() is already async and internally marshals the call
to the real pywebview window thread.
"""
from nicegui import ui, app
import webview


async def pick_folder_native() -> str:
    """Open a native folder-picker dialog via pywebview's own window.

    pywebview's create_file_dialog() has no title parameter for folder
    dialogs (unlike tkinter's askdirectory), so callers can't customize it.
    """
    if app.native.main_window is None:
        ui.notify('Folder picker is only available in the desktop app', type='warning')
        return ''
    dialog_type = webview.FileDialog.FOLDER if hasattr(webview, 'FileDialog') else webview.FOLDER_DIALOG
    result = await app.native.main_window.create_file_dialog(dialog_type)
    return result[0] if result else ''
