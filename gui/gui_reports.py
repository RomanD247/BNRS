from nicegui import ui
from sqlalchemy.orm import Session
import sys
import os
import csv
import tempfile
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crud import get_user_rental_statistics, get_equipment_type_statistics
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
            
            # Получаем данные из базы данных
            user_stats = get_user_rental_statistics(db)
            
            # Фильтруем записи с нулевым временем аренды
            user_stats = [stat for stat in user_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
            
            # Создаем таблицу (ui.table)
            columns = [
                {'name': 'name', 'label': 'User Name', 'field': 'name', 'sortable': True, 'align': 'left'},
                {'name': 'department', 'label': 'Department', 'field': 'department', 'sortable': True, 'align': 'left'},
                {'name': 'total_rental_time', 'label': 'Total Rental Time', 'field': 'total_rental_time', 'sortable': True, 'align': 'left'}
            ]
            
            with ui.row().classes('w-full items-center justify-center gap-4 py-4'):
                # Фильтр по отделу
                departments = list(set(stat['department'] for stat in user_stats))
                departments.sort()
                departments.insert(0, 'All Departments')
                dep_filter = ui.select(departments, value='All Departments', label='Filter by Department')
                
                # Кнопка экспорта с функциональностью
                ui.button('Export to CSV', icon='download', on_click=lambda: export_to_csv(
                    table.rows, f"user_rental_statistics_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )).props('outline')
            
            # Создаем таблицу с данными
            with ui.card().classes('w-full'):
                table = ui.table(
                    columns=columns,
                    rows=user_stats,
                    row_key='name',
                    title='User Rental Statistics',
                    pagination={'sortBy': 'total_rental_time', 'descending': True}
                ).classes('w-full')
                
                # Добавляем фильтрацию данных по отделу
                def filter_data():
                    selected_dep = dep_filter.value
                    if selected_dep == 'All Departments':
                        table.rows = user_stats
                    else:
                        table.rows = [stat for stat in user_stats if stat['department'] == selected_dep]
                
                dep_filter.on('update:model-value', lambda: filter_data())
            
            # Добавляем информацию о сортировке
            ui.label('Click on column headers to sort data').classes('text-caption text-grey-7 q-mt-sm')
    
    dialog.open()

# Функция отчета по типам оборудования
def show_equipment_type_statistics():
    """Показывает отчет со статистикой по типам оборудования"""
    with ui.dialog() as dialog:
        with ui.card().style('max-width: none; width: 1000px'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Equipment Type Statistics').classes('text-h5')
                ui.button(icon='close', on_click=dialog.close).props('flat round')
            
            # Получаем данные из базы данных
            type_stats = get_equipment_type_statistics(db)
            
            # Фильтруем записи с нулевым временем аренды
            type_stats = [stat for stat in type_stats if str(stat['total_rental_time']).strip() != '0' and str(stat['total_rental_time']).strip() != '']
            
            # Создаем таблицу
            columns = [
                {'name': 'type_name', 'label': 'Equipment Type', 'field': 'type_name', 'sortable': True, 'align': 'left'},
                {'name': 'total_equipment', 'label': 'Total', 'field': 'total_equipment', 'sortable': True, 'align': 'right'},
                {'name': 'available_equipment', 'label': 'Available', 'field': 'available_equipment', 'sortable': True, 'align': 'right'},
                {'name': 'rented_equipment', 'label': 'Rented', 'field': 'rented_equipment', 'sortable': True, 'align': 'right'},
                {'name': 'availability_percentage', 'label': 'Availability', 'field': 'availability_percentage', 'sortable': True, 'align': 'right'},
                {'name': 'total_rental_time', 'label': 'Total Rental Time', 'field': 'total_rental_time', 'sortable': True, 'align': 'right'}
            ]
            
            with ui.row().classes('w-full items-center justify-center gap-4 py-4'):
                # Кнопка экспорта с функциональностью
                ui.button('Export to CSV', icon='download', on_click=lambda: export_to_csv(
                    type_stats, f"equipment_type_statistics_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )).props('outline')
            
            # Создаем таблицу с данными
            with ui.card().classes('w-full'):
                table = ui.table(
                    columns=columns,
                    rows=type_stats,
                    row_key='type_name',
                    title='Equipment Type Statistics',
                    pagination={'sortBy': 'total_rental_time', 'descending': True}
                ).classes('w-full')
            
            # Добавляем сводку
            with ui.card().classes('w-full q-mt-md'):
                ui.label('Summary').classes('text-h6')
                
                # Расчет суммарных значений
                total_all = sum(stat['total_equipment'] for stat in type_stats)
                total_rented = sum(stat['rented_equipment'] for stat in type_stats)
                total_available = total_all - total_rented
                
                if total_all > 0:
                    total_availability = (total_available / total_all) * 100
                else:
                    total_availability = 100
                
                # Отображение сводки
                with ui.row().classes('w-full justify-around'):
                    ui.label(f"Total Equipment: {total_all}").classes('text-body1')
                    ui.label(f"Available: {total_available}").classes('text-body1')
                    ui.label(f"Rented: {total_rented}").classes('text-body1')
                    ui.label(f"Overall Availability: {total_availability:.1f}%").classes('text-body1')
            
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

# Если файл запущен напрямую, создаем тестовый интерфейс
if __name__ == '__main__':
    ui.label('Reports Test Page').classes('text-h4')
    with ui.row():
        get_user_report_button()
        get_equipment_report_button()
    ui.run()

