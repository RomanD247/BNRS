from nicegui import ui
from t_guidial import create_gui
from gui_adduser import show_add_user_dialog
from gui_addequip import show_add_equipment_dialog


def main():
    with ui.row().style('height: 100vh;'):
        with ui.column().style('width: 300px; background-color: #f0f0f0; padding: 10px; align-items: center;'):
            ui.button('Rent', on_click=lambda: ui.notify('Rent clicked')).style('width: 100px; height: 100px;')
            ui.button('Return', on_click=lambda: ui.notify('Return clicked')).style('width: 100px; height: 100px;')
            ui.button('Edit database', on_click=lambda: ui.notify('Edit database clicked')).style('width: 100px; height: 100px;')
            ui.button('Add Employee', on_click=show_add_user_dialog).style('width: 100px; height: 100px;')
            ui.button('Add Equipment', on_click=show_add_equipment_dialog).style('width: 100px; height: 100px;')

        with ui.column():
            ui.label(text='Rented')
            create_gui()
        with ui.column():
            ui.label(text='Available')
            create_gui()
        with ui.column().style('width: 300px; background-color: #f0f0f0; padding: 10px; margin-top: 100px'):
            ui.label(text='Choose category')
            checkbox = ui.checkbox('weCat3D')
            checkbox = ui.checkbox('ShapeDrive G4')
            checkbox = ui.checkbox('Illumination')


if __name__ in {'__main__', '__mp_main__'}:
    main()
    ui.run()
