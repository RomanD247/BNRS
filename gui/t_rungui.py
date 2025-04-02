from gui_changeUser import edit_users_dialog
from gui_changeDep import edit_departments_dialog
from nicegui import ui
from gui_changeEtype import edit_etypes_dialog

# А затем привяжите к кнопке:
ui.button('Редактировать пользователей', on_click=edit_users_dialog)
ui.button('Редактировать отделы', on_click=edit_departments_dialog)
ui.button('Редактировать типы оборудования', on_click=edit_etypes_dialog)
ui.run()