from nicegui import ui
import datetime

def create_gui():
    data = [
        {"name": "Name 11", "device": "Device A", "date": datetime.date(2025, 3, 20)},
        {"name": "Name 2", "device": "Device B", "date": datetime.date(2025, 3, 21)},
        {"name": "Name 3", "device": "Device C", "date": datetime.date(2025, 3, 22)},
        {"name": "Name 3", "device": "Device C", "date": datetime.date(2025, 3, 22)},
        {"name": "Name 3", "device": "Device C", "date": datetime.date(2025, 3, 22)},
        {"name": "Name 3", "device": "Device C", "date": datetime.date(2025, 3, 22)},
        {"name": "Name 3", "device": "Device C", "date": datetime.date(2025, 3, 22)},
        {"name": "Name 3", "device": "Device C", "date": datetime.date(2025, 3, 22)},
        {"name": "Name 3", "device": "Device C", "date": datetime.date(2025, 3, 22)},
        {"name": "Name 3", "device": "Device C", "date": datetime.date(2025, 3, 22)},
        {"name": "Name 3", "device": "Device C", "date": datetime.date(2025, 3, 22)},
        
    ]

    def show_details(item):
        with ui.dialog().style('width: 700px') as dialog, ui.card():
            ui.label(f"Name: {item['name']}")
            ui.label(f"Device: {item['device']}")
            ui.label(f"Date: {item['date']}")
            ui.button("Close", on_click=dialog.close)
        dialog.open()

    with ui.scroll_area().style('border: 2px solid black; padding: 10px; height: 800px; width: 500px'):
        with ui.column():
            for item in data:
                card = ui.card().style('width: 450px; cursor: pointer;')
                card.on('click', lambda _, item=item: show_details(item))
                with card:
                    ui.label(item['device']).style('font-weight: bold; font-size: 150%; margin-top: -0.5em')
                    ui.label(f"Name: {item['name']}").style(' margin-top: -1em')
                    ui.label(f"Rented date: {item['date']}").style(' margin-bottom: -1em; margin-top: -1em')


                    # from nicegui import ui
# import datetime

# def main():
#     # Пример данных
#     data = [
#         {"name": "Name 11", "device": "Device A", "date": datetime.date(2025, 3, 20)},
#         {"name": "Name 2", "device": "Device B", "date": datetime.date(2025, 3, 21)},
#         {"name": "Name 3", "device": "Device C", "date": datetime.date(2025, 3, 22)},
#         {"name": "Name 4", "device": "Device D", "date": datetime.date(2025, 3, 23)},
#         {"name": "Name 4", "device": "Device D", "date": datetime.date(2025, 3, 23)},
#         {"name": "Name 5", "device": "Device D", "date": datetime.date(2025, 3, 23)},
#         {"name": "Name 6", "device": "Device D", "date": datetime.date(2025, 3, 23)},
#         {"name": "Name 7", "device": "Device D", "date": datetime.date(2025, 3, 23)},
#         {"name": "Name 4", "device": "Device D", "date": datetime.date(2025, 3, 23)},
#         {"name": "Name 4", "device": "Device D", "date": datetime.date(2025, 3, 23)},
#         {"name": "Name 4", "device": "Device D", "date": datetime.date(2025, 3, 23)},
#         {"name": "Name 4", "device": "Device D", "date": datetime.date(2025, 3, 23)},
#         {"name": "Name 4", "device": "Device D", "date": datetime.date(2025, 3, 23)},
#         {"name": "Name 4", "device": "Device D", "date": datetime.date(2025, 3, 23)},
#         {"name": "Name 4", "device": "Device D", "date": datetime.date(2025, 3, 23)},
#     ]

#     def show_details(item):
#         """Открывает диалоговое окно с информацией об элементе."""
#         with ui.dialog().style('width: 700px') as dialog, ui.card():
#             ui.label(f"Имя: {item['name']}")
#             ui.label(f"Устройство: {item['device']}")
#             ui.label(f"Дата: {item['date']}")
#             ui.button("Закрыть", on_click=dialog.close)
#         dialog.open()

#     # Построение интерфейса
#     ui.label("Список элементов").style('font-size: 1.5em')
#     with ui.scroll_area().style('border: 2px solid black; padding: 10px; height: 800px; width: 500px'):
#         with ui.column():
#             for item in data:
#                 card = ui.card().style('width: 450px; cursor: pointer;')
#                 card.on('click', lambda _, item=item: show_details(item))
#                 with card:
#                     ui.label(item['name']).style('font-weight: bold; margin-bottom: -1em; bottom: 50px; margin-top: -0.5em')
#                     ui.label(f"Устройство: {item['device']}").style(' margin-top: -0.5em')
#                     ui.label(f"Дата: {item['date']}").style('margin-bottom: -0.5em')

#     ui.run()

# if __name__ in {"__main__", "__mp_main__"}:
#     main()


