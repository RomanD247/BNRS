from nicegui import ui

def main():
    with ui.row().style('height: 100vh'):
        with ui.column().style('width: 200px; background-color: #f0f0f0; padding: 10px;'):
            ui.button('Rent', on_click=lambda: ui.notify('Rent clicked'))
            ui.button('Return', on_click=lambda: ui.notify('Return clicked'))
            ui.button('Edit database', on_click=lambda: ui.notify('Edit database clicked'))

        with ui.row().style('flex: 1; padding: 10px;'):
            with ui.column().style('flex: 10; padding-right: 10px; height: 100%;'):
                ui.label('Rented Equipment!!').style('font-size: 18px; font-weight: bold;')
                with ui.scroll_area().classes('w-32 h-32 border'):
                    for i in range(10):
                        ui.label(f'Rented Item {i+1}')

            with ui.column().style('flex: 1; padding-left: 10px; height: 100%;'):
                ui.label('Available Equipment').style('font-size: 18px; font-weight: bold;')
                with ui.scroll_area().classes('w-32 h-32 border'):
                    for i in range(15):
                        ui.label(f'Available Item {i+1}')

if __name__ in {'__main__', '__mp_main__'}:
    main()
    ui.run()
