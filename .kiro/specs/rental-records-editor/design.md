# Design Document - Rental Records Editor

## Overview

Данный документ описывает проектирование функциональности редактирования записей аренды для Admin Panel системы WenglorMEL Rental System. Функция будет интегрирована в существующую архитектуру с использованием паттернов, применяемых в других модулях редактирования (gui_changeUser.py, gui_changeEquip.py).

## Architecture

### High-Level Architecture

Функциональность будет реализована по существующему архитектурному паттерну:

```
main.py (Admin Panel) 
    ↓ (кнопка "Edit Rentals")
gui/gui_changeRental.py (новый модуль)
    ↓ (использует)
crud.py (существующие + новая функция update_rental)
    ↓ (работает с)
models.py (существующая модель Rental)
    ↓ (сохраняет в)
rental.db (SQLite база данных)
```

### Integration Points

1. **Admin Panel Integration**: Добавление новой кнопки в main.py (строка ~400) рядом с существующими кнопками редактирования
2. **CRUD Layer**: Расширение crud.py новой функцией `update_rental()`
3. **GUI Module**: Создание нового модуля `gui/gui_changeRental.py` по аналогии с существующими модулями

## Components and Interfaces

### 1. Admin Panel Button (main.py)

**Компонент**: Новая кнопка в Admin Panel
**Расположение**: После кнопки "Edit device type" (строка ~401)

```python
with ui.button(on_click=edit_rentals_dialog).style('width: 100px; height: 100px;'):
    ui.icon('edit_note')  # или 'assignment'
    ui.label('Edit Rentals')
```

**Интерфейс**:
- Функция: `edit_rentals_dialog()` (импортируется из gui.gui_changeRental)
- Стиль: Соответствует существующим кнопкам (100x100 пикселей)
- Иконка: `edit_note` или `assignment` для обозначения редактирования записей

### 2. CRUD Function Extension (crud.py)

**Компонент**: Новая функция `update_rental()`

```python
def update_rental(db: Session, rental_id: int, user_id: int = None, 
                 equipment_id: int = None, rental_start: datetime = None, 
                 rental_end: datetime = None, comment: str = None) -> Optional[Rental]:
    """Update rental record"""
```

**Интерфейс**:
- Входные параметры: ID записи и опциональные поля для обновления
- Возвращает: Обновленный объект Rental или None при ошибке
- Валидация: Проверка существования пользователя и оборудования
- Обработка ошибок: Исключения при некорректных данных

### 3. GUI Module (gui/gui_changeRental.py)

**Компонент**: Новый модуль для редактирования записей аренды

#### 3.1 Main Dialog Function

```python
def edit_rentals_dialog():
    """Opens dialog for selecting and editing rental records"""
```

**Интерфейс**:
- Создает диалог с таблицей всех записей аренды
- Использует `crud.get_all_rentals()` для получения данных
- Размер диалога: 800x600 пикселей для размещения таблицы

#### 3.2 Rental List Display

**Компонент**: Таблица записей аренды

```python
# Структура отображения записей
columns = [
    {'name': 'id', 'label': 'ID', 'field': 'id_re'},
    {'name': 'user', 'label': 'User', 'field': 'user_name'},
    {'name': 'equipment', 'label': 'Equipment', 'field': 'equipment_name'},
    {'name': 'start', 'label': 'Start Date', 'field': 'rental_start'},
    {'name': 'end', 'label': 'End Date', 'field': 'rental_end'},
    {'name': 'comment', 'label': 'Comment', 'field': 'comment'}
]
```

**Интерфейс**:
- Использует `ui.table()` для отображения данных
- Обработчик клика на строку: открытие формы редактирования
- Форматирование дат: YYYY-MM-DD HH:MM:SS
- Обработка пустых значений: "Not returned" для rental_end

#### 3.3 Edit Form Function

```python
def show_edit_form_for_rental(rental, parent_dialog=None):
    """Creates and shows rental edit form"""
```

**Интерфейс**:
- Параметры: объект Rental и родительский диалог
- Форма содержит поля для всех редактируемых атрибутов
- Валидация данных перед сохранением
- Обработка отмены и сохранения

## Data Models

### Rental Record Structure

Используется существующая модель `Rental` из models.py:

```python
class Rental(Base):
    id_re = Column(Integer, primary_key=True)           # Только для чтения
    user_id = Column(Integer, ForeignKey("users.id_us")) # Редактируемое
    equipment_id = Column(Integer, ForeignKey("equipment.id_eq")) # Редактируемое
    rental_start = Column(DateTime, default=datetime.datetime.now) # Редактируемое
    rental_end = Column(DateTime, nullable=True)        # Редактируемое
    comment = Column(String, nullable=True)             # Редактируемое
```

### Form Data Structure

```python
form_data = {
    'rental_id': int,           # Неизменяемый ID
    'user_id': int,             # Выбор из списка активных пользователей
    'equipment_id': int,        # Выбор из списка активного оборудования
    'rental_start': datetime,   # Поле ввода даты/времени
    'rental_end': datetime,     # Поле ввода даты/времени (может быть None)
    'comment': str              # Текстовое поле
}
```

## Error Handling

### Validation Rules

1. **User Validation**: Проверка существования пользователя в базе данных
2. **Equipment Validation**: Проверка существования оборудования в базе данных
3. **Date Validation**: rental_start не должно быть позже rental_end
4. **Database Constraints**: Обработка ошибок целостности данных

### Error Messages

```python
error_messages = {
    'user_not_found': 'Selected user does not exist',
    'equipment_not_found': 'Selected equipment does not exist',
    'invalid_date_range': 'Start date cannot be later than end date',
    'database_error': 'Database error occurred while saving',
    'rental_not_found': 'Rental record not found'
}
```

### Exception Handling Strategy

1. **Database Exceptions**: Отлов SQLAlchemy исключений с пользовательскими сообщениями
2. **Validation Exceptions**: Проверка данных перед отправкой в базу
3. **UI Notifications**: Использование `ui.notify()` для отображения ошибок
4. **Graceful Degradation**: Сохранение состояния формы при ошибках

## Testing Strategy

### Unit Testing Approach

1. **CRUD Function Testing**:
   - Тестирование `update_rental()` с валидными данными
   - Тестирование обработки некорректных данных
   - Тестирование обновления отдельных полей

2. **Integration Testing**:
   - Тестирование полного цикла: выбор записи → редактирование → сохранение
   - Тестирование взаимодействия с базой данных
   - Тестирование валидации форм

3. **UI Testing**:
   - Тестирование открытия диалогов
   - Тестирование отображения данных в таблице
   - Тестирование обработки пользовательского ввода

### Test Data Requirements

```python
test_data = {
    'valid_rental': {
        'user_id': 1,
        'equipment_id': 1,
        'rental_start': datetime(2024, 1, 1, 10, 0),
        'rental_end': datetime(2024, 1, 2, 10, 0),
        'comment': 'Test rental'
    },
    'invalid_rental': {
        'user_id': 999,  # Несуществующий пользователь
        'equipment_id': 999,  # Несуществующее оборудование
        'rental_start': datetime(2024, 1, 2, 10, 0),
        'rental_end': datetime(2024, 1, 1, 10, 0)  # Неверный диапазон дат
    }
}
```

## Implementation Considerations

### Performance Considerations

1. **Database Queries**: Использование joinedload для загрузки связанных данных
2. **UI Responsiveness**: Асинхронная загрузка данных для больших таблиц
3. **Memory Management**: Правильное закрытие сессий базы данных

### Security Considerations

1. **Input Validation**: Валидация всех пользовательских данных
2. **SQL Injection Prevention**: Использование ORM параметризованных запросов
3. **Access Control**: Функция доступна только через Admin Panel с паролем

### Maintainability Considerations

1. **Code Consistency**: Следование существующим паттернам кодирования
2. **Error Logging**: Логирование ошибок для отладки
3. **Documentation**: Комментарии к сложным частям кода
4. **Modularity**: Разделение логики на отдельные функции

### Future Extensions

1. **Bulk Edit**: Возможность редактирования нескольких записей одновременно
2. **Filtering**: Фильтрация записей по пользователю, оборудованию или датам
3. **Export**: Экспорт отредактированных данных в CSV/Excel
4. **Audit Trail**: Логирование изменений записей аренды