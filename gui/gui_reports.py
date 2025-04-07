from nicegui import ui
from sqlalchemy.orm import Session
import sys
import os
import csv
import tempfile
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import get_user_rental_statistics, get_equipment_type_statistics, get_equipment_name_statistics, get_all_rentals, get_department_rental_statistics
from database import SessionLocal

# Создаем глобальное соединение с БД
db = SessionLocal()

# Функция для экспорта данных в CSV
def export_to_csv(data, filename=None):
    if not data:
        ui.notify('No data to export', color='warning')
        return
    
    # Если имя файла не указано, создаем имя со штампом времени
    if not filename:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.csv"
    
    # Создаем временный файл
    with tempfile.NamedTemporaryFile(mode='w', newline='', delete=False, suffix='.csv') as temp_file:
        # Определяем заголовки из первой записи данных
        fieldnames = data[0].keys() if data else []
        
        # Записываем данные в CSV
        writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        
        temp_filepath = temp_file.name
    
    # Предлагаем пользователю скачать файл
    ui.download(temp_filepath, filename=filename)
    
    # Планируем удаление временного файла после скачивания
    def cleanup():
        try:
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
        except Exception as e:
            print(f"Failed to remove temporary file: {e}")
    
    ui.timer(10, cleanup, once=True)

# Функция отчета по пользователям
def show_user_rental_statistics():
    """Показывает отчет со статистикой аренды пользователей"""
    with ui.dialog().classes('w-full max-w-5xl') as dialog:
        with ui.card().classes('w-full'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('User Rental Statistics').classes('text-h5')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            
            # Переменные для хранения выбранных дат
            start_date = None
            end_date = None
            
            # Создаем таблицу (ui.table)
            columns = [
                {'name': 'name', 'label': 'User Name', 'field': 'name', 'sortable': True, 'align': 'left'},
                {'name': 'department', 'label': 'Department', 'field': 'department', 'sortable': True, 'align': 'left'},
                {'name': 'total_rental_time', 'label': 'Total Rental Time', 'field': 'total_rental_time', 'sortable': True, 'align': 'left'}
            ]
            
            # Функция для обновления данных с учетом фильтров
            def update_data():
                nonlocal start_date, end_date
                
                # Получаем данные из базы данных с фильтрацией
                user_stats = get_user_rental_statistics(db, start_date, end_date)
                
                # Фильтруем записи с нулевым временем аренды
                user_stats = [stat for stat in user_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                # Обновляем таблицу
                table.rows = user_stats
                
                # Применяем фильтр по отделу
                filter_by_department()
            
            with ui.row().classes('w-full items-center justify-center gap-4 py-4'):
                # Фильтр по отделу
                departments = list(set(stat['department'] for stat in get_user_rental_statistics(db)))
                departments.sort()
                departments.insert(0, 'All Departments')
                dep_filter = ui.select(departments, value='All Departments', label='Filter by Department')
                
                # Выпадающее меню для фильтра даты
                with ui.menu().props('auto-close').classes('ml-auto') as date_menu:
                    with ui.card():
                        ui.label('Select Date Range').classes('text-h6 q-pa-md')
                        
                        # Поле для отображения выбранного диапазона дат
                        date_input = ui.input('Date range').classes('w-full q-px-md')
                        
                        # Компонент выбора диапазона дат
                        date_picker = ui.date().props('range').bind_value(
                            date_input,
                            forward=lambda x: f'{x["from"]} - {x["to"]}' if x else None,
                            backward=lambda x: {
                                'from': x.split(' - ')[0],
                                'to': x.split(' - ')[1],
                            } if ' - ' in (x or '') else None,
                        )
                        
                        with ui.row().classes('q-pa-md justify-end'):
                            ui.button('Clear', on_click=lambda: date_clear()).props('flat')
                            ui.button('Apply', on_click=lambda: date_apply()).props('color=primary')
                
                # Кнопка для открытия меню с выбором даты
                date_filter_btn = ui.button('Date Filter', icon='event').props('outline').on_click(lambda: date_menu.open())
                
                # Кнопка экспорта с функциональностью
                ui.button('Export to CSV', icon='download', on_click=lambda: export_to_csv(
                    table.rows, f"user_rental_statistics_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )).props('outline')
            
            # Создаем таблицу с данными
            with ui.card().classes('w-full'):
                # Первоначальное получение данных без фильтров
                user_stats = get_user_rental_statistics(db)
                
                # Фильтруем записи с нулевым временем аренды
                user_stats = [stat for stat in user_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                table = ui.table(
                    columns=columns,
                    rows=user_stats,
                    row_key='name',
                    title='User Rental Statistics',
                    pagination={'sortBy': 'total_rental_time', 'descending': True}
                ).classes('w-full')
                
                # Функция для фильтрации данных по отделу
                def filter_by_department():
                    selected_dep = dep_filter.value
                    filtered_data = table.rows
                    
                    if selected_dep != 'All Departments':
                        filtered_data = [stat for stat in filtered_data if stat['department'] == selected_dep]
                    
                    table.rows = filtered_data
                
                # Функция для применения фильтра дат
                def date_apply():
                    nonlocal start_date, end_date
                    
                    date_range = date_input.value
                    if date_range and ' - ' in date_range:
                        start, end = date_range.split(' - ')
                        # Преобразуем строковые даты в объекты datetime
                        start_date = datetime.datetime.strptime(start, '%Y-%m-%d')
                        # Устанавливаем конец дня для конечной даты
                        end_date = datetime.datetime.strptime(end, '%Y-%m-%d')
                        end_date = end_date.replace(hour=23, minute=59, second=59)
                        
                        # Обновляем данные с новыми фильтрами
                        update_data()
                        # Закрываем меню
                        date_menu.close()
                        # Обновляем текст кнопки фильтра
                        date_filter_btn.text = f'Date: {start} - {end}'
                
                # Функция для очистки фильтра дат
                def date_clear():
                    nonlocal start_date, end_date
                    start_date = None
                    end_date = None
                    date_input.value = None
                    date_filter_btn.text = 'Date Filter'
                    update_data()
                    date_menu.close()
                
                dep_filter.on('update:model-value', lambda: filter_by_department())
            
            # Добавляем информацию о сортировке
            ui.label('Click on column headers to sort data').classes('text-caption text-grey-7 q-mt-sm')
    
    dialog.open()

# Функция отчета по типам оборудования
def show_equipment_type_statistics():
    """Показывает отчет со статистикой по типам оборудования"""
    with ui.dialog() as dialog:
        with ui.card().style('max-width: none; width: 1000px'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Device Type Statistics').classes('text-h5')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            
            # Переменные для хранения выбранных дат
            start_date = None
            end_date = None
            
            # Создаем таблицу
            columns = [
                {'name': 'type_name', 'label': 'Device Type', 'field': 'type_name', 'sortable': True, 'align': 'left'},
                {'name': 'total_rental_time', 'label': 'Total Rental Time', 'field': 'total_rental_time', 'sortable': True, 'align': 'right'}
            ]
            
            # Функция для обновления данных с учетом фильтров
            def update_data():
                nonlocal start_date, end_date
                
                # Получаем данные из базы данных с фильтрацией
                type_stats = get_equipment_type_statistics(db, start_date, end_date)
                
                # Фильтруем записи с нулевым временем аренды
                type_stats = [stat for stat in type_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                # Обновляем таблицу
                table.rows = type_stats
            
            with ui.row().classes('w-full items-center justify-center gap-4 py-4'):
                # Выпадающее меню для фильтра даты
                with ui.menu().props('auto-close').classes('ml-auto') as date_menu:
                    with ui.card():
                        ui.label('Select Date Range').classes('text-h6 q-pa-md')
                        
                        # Поле для отображения выбранного диапазона дат
                        date_input = ui.input('Date range').classes('w-full q-px-md')
                        
                        # Компонент выбора диапазона дат
                        date_picker = ui.date().props('range').bind_value(
                            date_input,
                            forward=lambda x: f'{x["from"]} - {x["to"]}' if x else None,
                            backward=lambda x: {
                                'from': x.split(' - ')[0],
                                'to': x.split(' - ')[1],
                            } if ' - ' in (x or '') else None,
                        )
                        
                        with ui.row().classes('q-pa-md justify-end'):
                            ui.button('Clear', on_click=lambda: date_clear()).props('flat')
                            ui.button('Apply', on_click=lambda: date_apply()).props('color=primary')
                
                # Кнопка для открытия меню с выбором даты
                date_filter_btn = ui.button('Date Filter', icon='event').props('outline').on_click(lambda: date_menu.open())
                
                # Кнопка экспорта с функциональностью
                ui.button('Export to CSV', icon='download', on_click=lambda: export_to_csv(
                    table.rows, f"equipment_type_statistics_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )).props('outline')
            
            # Создаем таблицу с данными
            with ui.card().classes('w-full'):
                # Первоначальное получение данных без фильтров
                type_stats = get_equipment_type_statistics(db)
                
                # Фильтруем записи с нулевым временем аренды
                type_stats = [stat for stat in type_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                table = ui.table(
                    columns=columns,
                    rows=type_stats,
                    row_key='type_name',
                    title='Device Type Statistics',
                    pagination={'sortBy': 'total_rental_time', 'descending': True}
                ).classes('w-full')
                
                # Функция для применения фильтра дат
                def date_apply():
                    nonlocal start_date, end_date
                    
                    date_range = date_input.value
                    if date_range and ' - ' in date_range:
                        start, end = date_range.split(' - ')
                        # Преобразуем строковые даты в объекты datetime
                        start_date = datetime.datetime.strptime(start, '%Y-%m-%d')
                        # Устанавливаем конец дня для конечной даты
                        end_date = datetime.datetime.strptime(end, '%Y-%m-%d')
                        end_date = end_date.replace(hour=23, minute=59, second=59)
                        
                        # Обновляем данные с новыми фильтрами
                        update_data()
                        # Закрываем меню
                        date_menu.close()
                        # Обновляем текст кнопки фильтра
                        date_filter_btn.text = f'Date: {start} - {end}'
                
                # Функция для очистки фильтра дат
                def date_clear():
                    nonlocal start_date, end_date
                    start_date = None
                    end_date = None
                    date_input.value = None
                    date_filter_btn.text = 'Date Filter'
                    update_data()
                    date_menu.close()
            
            # Добавляем информацию о сортировке
            ui.label('Click on column headers to sort data').classes('text-caption text-grey-7 q-mt-sm')
    
    dialog.open()

# Функция отчета по именам оборудования
def show_equipment_name_statistics():
    """Показывает отчет со статистикой по именам оборудования"""
    with ui.dialog() as dialog:
        with ui.card().style('max-width: none; width: 1000px'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Device Name Statistics').classes('text-h5')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            
            # Переменные для хранения выбранных дат
            start_date = None
            end_date = None
            
            # Создаем таблицу
            columns = [
                {'name': 'name', 'label': 'Equipment Name', 'field': 'name', 'sortable': True, 'align': 'left'},
                {'name': 'etype_name', 'label': 'Equipment Type', 'field': 'etype_name', 'sortable': True, 'align': 'left'},
                {'name': 'equipment_count', 'label': 'Count', 'field': 'equipment_count', 'sortable': True, 'align': 'right'},
                {'name': 'total_rental_time', 'label': 'Total Rental Time', 'field': 'total_rental_time', 'sortable': True, 'align': 'right'}
            ]
            
            # Функция для обновления данных с учетом фильтров
            def update_data():
                nonlocal start_date, end_date
                
                # Получаем данные из базы данных с фильтрацией
                name_stats = get_equipment_name_statistics(db, start_date, end_date)
                
                # Фильтруем записи с нулевым временем аренды
                name_stats = [stat for stat in name_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                # Обновляем таблицу
                table.rows = name_stats
            
            with ui.row().classes('w-full items-center justify-center gap-4 py-4'):
                # Выпадающее меню для фильтра даты
                with ui.menu().props('auto-close').classes('ml-auto') as date_menu:
                    with ui.card():
                        ui.label('Select Date Range').classes('text-h6 q-pa-md')
                        
                        # Поле для отображения выбранного диапазона дат
                        date_input = ui.input('Date range').classes('w-full q-px-md')
                        
                        # Компонент выбора диапазона дат
                        date_picker = ui.date().props('range').bind_value(
                            date_input,
                            forward=lambda x: f'{x["from"]} - {x["to"]}' if x else None,
                            backward=lambda x: {
                                'from': x.split(' - ')[0],
                                'to': x.split(' - ')[1],
                            } if ' - ' in (x or '') else None,
                        )
                        
                        with ui.row().classes('q-pa-md justify-end'):
                            ui.button('Clear', on_click=lambda: date_clear()).props('flat')
                            ui.button('Apply', on_click=lambda: date_apply()).props('color=primary')
                
                # Кнопка для открытия меню с выбором даты
                date_filter_btn = ui.button('Date Filter', icon='event').props('outline').on_click(lambda: date_menu.open())
                
                # Кнопка экспорта с функциональностью
                ui.button('Export to CSV', icon='download', on_click=lambda: export_to_csv(
                    table.rows, f"equipment_name_statistics_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )).props('outline')
            
            # Создаем таблицу с данными
            with ui.card().classes('w-full'):
                # Первоначальное получение данных без фильтров
                name_stats = get_equipment_name_statistics(db)
                
                # Фильтруем записи с нулевым временем аренды
                name_stats = [stat for stat in name_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                table = ui.table(
                    columns=columns,
                    rows=name_stats,
                    row_key='name',
                    title='Equipment Name Statistics',
                    pagination={'sortBy': 'total_rental_time', 'descending': True}
                ).classes('w-full')
                
                # Функция для применения фильтра дат
                def date_apply():
                    nonlocal start_date, end_date
                    
                    date_range = date_input.value
                    if date_range and ' - ' in date_range:
                        start, end = date_range.split(' - ')
                        # Преобразуем строковые даты в объекты datetime
                        start_date = datetime.datetime.strptime(start, '%Y-%m-%d')
                        # Устанавливаем конец дня для конечной даты
                        end_date = datetime.datetime.strptime(end, '%Y-%m-%d')
                        end_date = end_date.replace(hour=23, minute=59, second=59)
                        
                        # Обновляем данные с новыми фильтрами
                        update_data()
                        # Закрываем меню
                        date_menu.close()
                        # Обновляем текст кнопки фильтра
                        date_filter_btn.text = f'Date: {start} - {end}'
                
                # Функция для очистки фильтра дат
                def date_clear():
                    nonlocal start_date, end_date
                    start_date = None
                    end_date = None
                    date_input.value = None
                    date_filter_btn.text = 'Date Filter'
                    update_data()
                    date_menu.close()
            
            # Добавляем информацию о сортировке
            ui.label('Click on column headers to sort data').classes('text-caption text-grey-7 q-mt-sm')
    
    dialog.open()

# Функция для получения кнопки отчета по пользователям
def get_user_report_button():
    """Возвращает кнопку для отчета по статистике пользователей"""
    return ui.button('User Report', icon='people', on_click=show_user_rental_statistics).props('color=primary')

# Функция для получения кнопки отчета по типам оборудования
def get_equipment_report_button():
    """Возвращает кнопку для отчета по типам оборудования"""
    return ui.button('Equipment Report', icon='devices', on_click=show_equipment_type_statistics).props('color=primary')

# Функция для получения кнопки отчета по именам оборудования
def get_equipment_name_report_button():
    """Возвращает кнопку для отчета по именам оборудования"""
    return ui.button('Equipment Report by Name', icon='inventory_2', on_click=show_equipment_name_statistics)

# Функция для отображения полной истории аренды
def show_rental_history():
    """Показывает отчет с полной историей аренды оборудования"""
    with ui.dialog().classes('max-w-5xl') as dialog:
        with ui.card().style('width: 1000px; max-width: none'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Rental History').classes('text-h5')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            
            # Переменные для хранения выбранных дат
            start_date = None
            end_date = None
            
            # Создаем таблицу (ui.table)
            columns = [
                {'name': 'id', 'label': 'ID', 'field': 'id', 'sortable': True, 'align': 'left'},
                {'name': 'equipment', 'label': 'Equipment', 'field': 'equipment', 'sortable': True, 'align': 'left'},
                {'name': 'equipment_type', 'label': 'Type', 'field': 'equipment_type', 'sortable': True, 'align': 'left'},
                {'name': 'user', 'label': 'User', 'field': 'user', 'sortable': True, 'align': 'left'},
                {'name': 'department', 'label': 'Department', 'field': 'department', 'sortable': True, 'align': 'left'},
                {'name': 'rental_start', 'label': 'Rental Start', 'field': 'rental_start', 'sortable': True, 'align': 'left'},
                {'name': 'rental_end', 'label': 'Rental End', 'field': 'rental_end', 'sortable': True, 'align': 'left'},
                {'name': 'duration', 'label': 'Duration', 'field': 'duration', 'sortable': True, 'align': 'left'},
                {'name': 'comment', 'label': 'Comment', 'field': 'comment', 'sortable': True, 'align': 'left'},
            ]
            
            # Получаем полную историю аренды
            rental_history = []
            
            rentals = get_all_rentals(db)
            for rental in rentals:
                # Подготавливаем данные для отображения
                duration_str = "Активная аренда"
                if rental.rental_end:
                    # Рассчитываем продолжительность для завершенных аренд
                    duration = rental.rental_end - rental.rental_start
                    days = duration.days
                    hours = duration.seconds // 3600
                    minutes = (duration.seconds % 3600) // 60
                    duration_str = f"{days}:{hours:02}:{minutes:02}"
                
                rental_history.append({
                    'id': rental.id_re,
                    'equipment': rental.equipment.name,
                    'equipment_type': rental.equipment.etype.name if rental.equipment.etype else 'Unknown',
                    'user': rental.user.name,
                    'department': rental.user.department.name if rental.user.department else 'Unknown',
                    'rental_start': rental.rental_start.strftime('%Y-%m-%d %H:%M'),
                    'rental_end': rental.rental_end.strftime('%Y-%m-%d %H:%M') if rental.rental_end else 'Not returned',
                    'duration': duration_str,
                    'comment': rental.comment or ''
                })
            
            # Сохраняем оригинальные данные для фильтрации
            original_rental_history = rental_history.copy()
            
            # Создаем переменную для таблицы
            table = None
            
            # Функция для применения фильтра
            def apply_filter():
                search_text = search_input.value.lower() if search_input.value else ""
                
                # Добавляем уведомление о фильтрации
                ui.notify(f'Фильтрация по: "{search_text}"')
                
                if not search_text:
                    # Если поле поиска пустое, возвращаем все данные
                    table.rows = original_rental_history
                    return
                
                # Фильтруем данные по всем полям
                filtered_data = []
                for item in original_rental_history:
                    # Проверяем каждое поле на содержание строки поиска
                    item_matches = False
                    for field, value in item.items():
                        if str(value).lower().find(search_text) != -1:
                            item_matches = True
                            break
                    
                    if item_matches:
                        filtered_data.append(item)
                
                # Обновляем таблицу отфильтрованными данными
                table.rows = filtered_data
                
                # Выводим информацию о количестве найденных записей
                ui.notify(f'Найдено записей: {len(filtered_data)} из {len(original_rental_history)}')
            
            # Функция для сброса фильтра
            def reset_filter():
                search_input.value = ""
                table.rows = original_rental_history
                ui.notify('Фильтр сброшен')
            
            # Функция для обновления данных с учетом фильтров дат
            def update_data():
                nonlocal start_date, end_date
                
                # Фильтруем данные по датам
                filtered_data = original_rental_history.copy()
                
                if start_date and end_date:
                    filtered_data = []
                    for item in original_rental_history:
                        # Преобразуем строку даты в объект datetime
                        rental_start = datetime.datetime.strptime(item['rental_start'], '%Y-%m-%d %H:%M')
                        
                        # Проверяем, попадает ли дата в выбранный диапазон
                        if start_date <= rental_start <= end_date:
                            filtered_data.append(item)
                
                # Обновляем таблицу
                table.rows = filtered_data
                
                # Выводим информацию о количестве найденных записей
                ui.notify(f'Найдено записей: {len(filtered_data)} из {len(original_rental_history)}')
            
            # Функция для применения фильтра дат
            def date_apply():
                nonlocal start_date, end_date
                
                date_range = date_input.value
                if date_range and ' - ' in date_range:
                    start, end = date_range.split(' - ')
                    # Преобразуем строковые даты в объекты datetime
                    start_date = datetime.datetime.strptime(start, '%Y-%m-%d')
                    # Устанавливаем конец дня для конечной даты
                    end_date = datetime.datetime.strptime(end, '%Y-%m-%d')
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                    
                    # Обновляем данные с новыми фильтрами
                    update_data()
                    # Закрываем меню
                    date_menu.close()
                    # Обновляем текст кнопки фильтра
                    #date_filter_btn.text = f'Date: {start} - {end}'
            
            # Функция для очистки фильтра дат
            def date_clear():
                nonlocal start_date, end_date
                start_date = None
                end_date = None
                date_input.value = None
                #date_filter_btn.text = 'Date Filter'
                update_data()
                date_menu.close()
            
            with ui.row().classes('w-full items-center justify-between gap-4 py-4'):
                # Добавляем элементы фильтрации
                with ui.row().classes('items-center gap-2').style('width: 65%'):
                    search_input = ui.input(label='Search in all fields', placeholder='Type to search...').style('width: 100%')
                    ui.button('Apply Filter', icon='search', on_click=apply_filter).props('color=primary')
                    ui.button('Reset', icon='clear', on_click=reset_filter).props('flat')
                
                # Выпадающее меню для фильтра даты
                with ui.menu().props('auto-close').classes('ml-auto') as date_menu:
                    with ui.card():
                        ui.label('Select Date Range').classes('text-h6 q-pa-md')
                        
                        # Поле для отображения выбранного диапазона дат
                        date_input = ui.input('Date range').classes('w-full q-px-md')
                        
                        # Компонент выбора диапазона дат
                        date_picker = ui.date().props('range').bind_value(
                            date_input,
                            forward=lambda x: f'{x["from"]} - {x["to"]}' if x else None,
                            backward=lambda x: {
                                'from': x.split(' - ')[0],
                                'to': x.split(' - ')[1],
                            } if ' - ' in (x or '') else None,
                        )
                        
                        with ui.row().classes('q-pa-md justify-end'):
                            ui.button('Clear', on_click=lambda: date_clear()).props('flat')
                            ui.button('Apply', on_click=lambda: date_apply()).props('color=primary')
                
                # Кнопка для открытия меню с выбором даты
                #date_filter_btn = 
                ui.button('Date Filter', icon='event').props('outline').on_click(lambda: date_menu.open())
                
                # Кнопка экспорта с функциональностью
                ui.button('Export to CSV', icon='download', on_click=lambda: export_to_csv(
                    table.rows, f"rental_history_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )).props('outline')
            
            # Создаем таблицу с данными
            with ui.card().classes('w-full'):
                table = ui.table(
                    columns=columns,
                    rows=rental_history,
                    row_key='id',
                    title='Rental History',
                    pagination={'rowsPerPage': 15}
                ).classes('w-full')
            
            # Добавляем информацию о сортировке и фильтрации
            ui.label('Click on column headers to sort data • Enter search text and click Apply Filter').classes('text-caption text-grey-7 q-mt-sm')
    
    dialog.open()

# Функция для получения кнопки истории аренды
def get_rental_history_button():
    """Возвращает кнопку для просмотра истории аренды"""
    return ui.button('Rental History', icon='history', on_click=show_rental_history)

# Функция для отчета по отделам
def show_department_rental_statistics():
    """Показывает отчет со статистикой аренды по отделам"""
    with ui.dialog() as dialog:
        with ui.card().style('max-width: none; width: 1000px'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Department Rental Statistics').classes('text-h5')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            
            # Переменные для хранения выбранных дат
            start_date = None
            end_date = None
            
            # Создаем таблицу
            columns = [
                {'name': 'name', 'label': 'Department Name', 'field': 'name', 'sortable': True, 'align': 'left'},
                {'name': 'rental_count', 'label': 'Total Rentals', 'field': 'rental_count', 'sortable': True, 'align': 'right'},
                {'name': 'total_rental_time', 'label': 'Total Rental Time', 'field': 'total_rental_time', 'sortable': True, 'align': 'right'}
            ]
            
            # Функция для обновления данных с учетом фильтров
            def update_data():
                nonlocal start_date, end_date
                
                # Получаем данные из базы данных с фильтрацией
                dept_stats = get_department_rental_statistics(db, start_date, end_date)
                
                # Фильтруем записи с нулевым временем аренды
                dept_stats = [stat for stat in dept_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                # Обновляем таблицу
                table.rows = dept_stats
            
            with ui.row().classes('w-full items-center justify-center gap-4 py-4'):
                # Выпадающее меню для фильтра даты
                with ui.menu().props('auto-close').classes('ml-auto') as date_menu:
                    with ui.card():
                        ui.label('Select Date Range').classes('text-h6 q-pa-md')
                        
                        # Поле для отображения выбранного диапазона дат
                        date_input = ui.input('Date range').classes('w-full q-px-md')
                        
                        # Компонент выбора диапазона дат
                        date_picker = ui.date().props('range').bind_value(
                            date_input,
                            forward=lambda x: f'{x["from"]} - {x["to"]}' if x else None,
                            backward=lambda x: {
                                'from': x.split(' - ')[0],
                                'to': x.split(' - ')[1],
                            } if ' - ' in (x or '') else None,
                        )
                        
                        with ui.row().classes('q-pa-md justify-end'):
                            ui.button('Clear', on_click=lambda: date_clear()).props('flat')
                            ui.button('Apply', on_click=lambda: date_apply()).props('color=primary')
                
                # Кнопка для открытия меню с выбором даты
                date_filter_btn = ui.button('Date Filter', icon='event').props('outline').on_click(lambda: date_menu.open())
                
                # Кнопка экспорта с функциональностью
                ui.button('Export to CSV', icon='download', on_click=lambda: export_to_csv(
                    table.rows, f"department_rental_statistics_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )).props('outline')
            
            # Создаем таблицу с данными
            with ui.card().classes('w-full'):
                # Первоначальное получение данных без фильтров
                dept_stats = get_department_rental_statistics(db)
                
                # Фильтруем записи с нулевым временем аренды
                dept_stats = [stat for stat in dept_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
                
                table = ui.table(
                    columns=columns,
                    rows=dept_stats,
                    row_key='name',
                    title='Department Rental Statistics',
                    pagination={'sortBy': 'total_rental_time', 'descending': True}
                ).classes('w-full')
                
                # Функция для применения фильтра дат
                def date_apply():
                    nonlocal start_date, end_date
                    
                    date_range = date_input.value
                    if date_range and ' - ' in date_range:
                        start, end = date_range.split(' - ')
                        # Преобразуем строковые даты в объекты datetime
                        start_date = datetime.datetime.strptime(start, '%Y-%m-%d')
                        # Устанавливаем конец дня для конечной даты
                        end_date = datetime.datetime.strptime(end, '%Y-%m-%d')
                        end_date = end_date.replace(hour=23, minute=59, second=59)
                        
                        # Обновляем данные с новыми фильтрами
                        update_data()
                        # Закрываем меню
                        date_menu.close()
                        # Обновляем текст кнопки фильтра
                        date_filter_btn.text = f'Date: {start} - {end}'
                
                # Функция для очистки фильтра дат
                def date_clear():
                    nonlocal start_date, end_date
                    start_date = None
                    end_date = None
                    date_input.value = None
                    date_filter_btn.text = 'Date Filter'
                    update_data()
                    date_menu.close()
            
            # Добавляем информацию о сортировке
            ui.label('Click on column headers to sort data').classes('text-caption text-grey-7 q-mt-sm')
    
    dialog.open()

# Функция для получения кнопки отчета по отделам
def get_department_report_button():
    """Возвращает кнопку для отчета по статистике отделов"""
    return ui.button('Department Report', icon='business', on_click=show_department_rental_statistics)

# Если файл запущен напрямую, создаем тестовый интерфейс
if __name__ == '__main__':
    ui.label('Reports Test Page').classes('text-h4')
    with ui.row():
        get_user_report_button()
        get_equipment_report_button()
        get_equipment_name_report_button()
        get_department_report_button()
        get_rental_history_button()
    ui.run()

