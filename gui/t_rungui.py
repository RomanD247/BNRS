from gui_adduser import show_add_user_dialog
from nicegui import ui

ui.button('Add Employee', on_click=show_add_user_dialog)

ui.run()
