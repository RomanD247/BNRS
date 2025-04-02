from gui_change import edit_users_dialog
from nicegui import ui

# А затем привяжите к кнопке:
ui.button('Редактировать пользователей', on_click=edit_users_dialog)
ui.run()