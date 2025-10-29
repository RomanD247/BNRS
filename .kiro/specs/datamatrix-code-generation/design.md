# Design Document

## Overview

Данный дизайн описывает реализацию двух функций в модуле NfcScan.py для генерации Data Matrix кодов для пользователей и оборудования. Функции будут использовать библиотеку pylibdmtx для создания Data Matrix кодов и PIL (Pillow) для работы с изображениями и добавления текста.

## Architecture

### Dependencies
- `pylibdmtx` - для генерации Data Matrix кодов
- `Pillow (PIL)` - для создания изображений, добавления текста и сохранения в PNG
- Существующие зависимости: `SQLAlchemy`, `models`, `database`

### Module Structure
- **NfcScan.py**: Содержит функции генерации кодов, использует сессию базы данных `db = SessionLocal()`
- **main.py**: Содержит GUI компоненты, кнопку в Admin Panel и диалоговое окно
- **Интеграция**: main.py импортирует функции из NfcScan.py для выполнения генерации

### GUI Architecture
- **Главное окно**: Существующий интерфейс с Admin Panel
- **Новая кнопка**: Добавляется в Admin Panel рядом с другими административными функциями
- **Диалоговое окно**: Модальное окно с двумя основными кнопками и прогресс-индикатором
- **Обработка событий**: Асинхронная обработка для предотвращения зависания интерфейса

## Components and Interfaces

### Existing Functions (NfcScan.py)

#### Function: generate_user_datamatrix

```python
def generate_user_datamatrix(user_id: int) -> PIL.Image.Image | None:
    """
    Генерирует Data Matrix код для пользователя
    
    Args:
        user_id: ID пользователя в базе данных
    
    Returns:
        PIL Image объект с Data Matrix кодом и текстом или None при ошибке
    """
```

#### Function: generate_equipment_datamatrix

```python
def generate_equipment_datamatrix(equipment_id: int) -> PIL.Image.Image | None:
    """
    Генерирует Data Matrix код для оборудования
    
    Args:
        equipment_id: ID оборудования в базе данных
    
    Returns:
        PIL Image объект с Data Matrix кодом и текстом или None при ошибке
    """
```

#### Helper Function: _create_datamatrix_image

```python
def _create_datamatrix_image(data: str, text_lines: list[str]) -> PIL.Image.Image | None:
    """
    Создает изображение с Data Matrix кодом и текстом
    
    Args:
        data: Данные для кодирования в Data Matrix
        text_lines: Список строк текста для добавления под кодом
    
    Returns:
        PIL Image объект или None при ошибке
    """
```

### New Functions (NfcScan.py)

#### Function: generate_all_users_codes

```python
def generate_all_users_codes(output_directory: str) -> tuple[int, int]:
    """
    Генерирует Data Matrix коды для всех пользователей и сохраняет в указанную папку
    
    Args:
        output_directory: Путь к папке для сохранения файлов
    
    Returns:
        Кортеж (количество созданных файлов, общее количество пользователей)
    """
```

#### Function: generate_all_equipment_codes

```python
def generate_all_equipment_codes(output_directory: str) -> tuple[int, int]:
    """
    Генерирует Data Matrix коды для всего оборудования и сохраняет в указанную папку
    
    Args:
        output_directory: Путь к папке для сохранения файлов
    
    Returns:
        Кортеж (количество созданных файлов, общее количество оборудования)
    """
```

### GUI Components (main.py)

#### Admin Panel Button

```python
# Добавление кнопки в Admin Panel
codes_button = tk.Button(admin_frame, text="Генерация кодов", 
                        command=open_codes_dialog, 
                        font=("Arial", 12))
```

#### Dialog Window Class

```python
class CodesGenerationDialog:
    """
    Диалоговое окно для управления генерацией Data Matrix кодов
    """
    
    def __init__(self, parent):
        """Инициализация диалогового окна"""
        
    def generate_users_codes(self):
        """Обработчик генерации кодов для всех пользователей"""
        
    def generate_equipment_codes(self):
        """Обработчик генерации кодов для всего оборудования"""
        
    def select_output_directory(self):
        """Выбор папки для сохранения файлов"""
```

## Data Models

### User Data Flow
1. Получение User_Entity по user_id из базы данных
2. Извлечение полей: `nfc`, `name`
3. Валидация наличия nfc поля
4. Генерация Data Matrix кода с nfc данными
5. Создание текстовой подписи с именем пользователя

### Equipment Data Flow
1. Получение Equipment_Entity по equipment_id из базы данных
2. Извлечение полей: `nfc`, `name`, `serialnum`
3. Валидация наличия nfc поля
4. Генерация Data Matrix кода с nfc данными
5. Создание текстовой подписи с именем и серийным номером

## Error Handling

### Database Errors
- Обработка случаев, когда пользователь/оборудование не найдены
- Логирование ошибок подключения к базе данных
- Возврат None и вывод сообщения об ошибке

### Data Validation Errors
- Проверка наличия nfc поля (не None и не пустая строка)
- Валидация корректности входных параметров
- Обработка некорректных ID

### Memory Management
- Эффективное использование памяти при создании изображений
- Освобождение ресурсов после генерации кода

### Image Generation Errors
- Обработка ошибок генерации Data Matrix кода
- Ошибки создания изображения или добавления текста
- Проблемы с кодировкой текста

## Implementation Details

### Image Specifications
- **Размер Data Matrix кода**: 200x200 пикселей
- **Размер итогового изображения**: 300x280 пикселей (с учетом текста)
- **Шрифт**: Arial или системный шрифт по умолчанию, размер 14
- **Цвета**: Черный код на белом фоне
- **Отступы**: 20 пикселей от краев, 10 пикселей между кодом и текстом

### File Naming Convention
- **Пользователи**: `user_{id}_{name}.png` (где name очищено от недопустимых символов)
- **Оборудование**: `equipment_{id}_{name}.png` (где name очищено от недопустимых символов)
- **Максимальная длина имени файла**: 100 символов

### Batch Generation Flow
1. Получение всех записей из соответствующей таблицы
2. Фильтрация записей с непустыми nfc полями
3. Генерация изображения для каждой записи
4. Сохранение в выбранную папку с прогресс-индикатором
5. Отчет о результатах (успешно/пропущено)

### GUI Layout
- **Диалоговое окно**: 400x300 пикселей, центрировано относительно главного окна
- **Кнопки**: Стандартный размер tkinter, отступы 10 пикселей
- **Прогресс-бар**: Отображается во время генерации
- **Текстовые метки**: Информация о процессе и результатах

### Return Value Format
- Существующие функции возвращают PIL Image объекты в памяти
- Новые batch функции возвращают кортеж (успешно, всего)
- При ошибке возвращается None или (0, 0)

## Testing Strategy

### Unit Tests
- Тестирование генерации кодов с валидными данными
- Тестирование обработки ошибок при отсутствующих nfc полях
- Тестирование создания файлов и директорий
- Тестирование валидации входных параметров

### Integration Tests
- Тестирование работы с реальной базой данных
- Проверка корректности создаваемых изображений
- Тестирование полного цикла: от ID до PNG файла

### Manual Testing
- Визуальная проверка качества генерируемых кодов
- Тестирование сканирования созданных Data Matrix кодов
- Проверка читаемости текстовых подписей

## Dependencies Update

Необходимо добавить в `requirements.txt`:
```
pylibdmtx==0.1.10
Pillow==10.1.0
```

## Security Considerations

- Валидация входных параметров (user_id, equipment_id должны быть положительными целыми числами)
- Ограничение размера генерируемых изображений в памяти
- Санитизация данных перед кодированием в Data Matrix