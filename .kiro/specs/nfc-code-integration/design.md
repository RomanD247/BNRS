# Design Document

## Overview

Проект интегрирует функциональность обновления NFC кодов из существующего скрипта fill_nfc_fields.py в основное приложение через новый модуль MatrixCode.py. Система предоставит пользователям возможность обновлять NFC коды через кнопки в главном интерфейсе с отображением результатов операций.

## Architecture

### Модульная архитектура
```
main.py (UI Layer)
    ↓ imports & calls
MatrixCode.py (Business Logic Layer)
    ↓ uses
models.py (Data Model Layer)
    ↓ connects to
rental.db (Database Layer)
```

### Поток данных
1. Пользователь нажимает кнопку в main.py
2. main.py вызывает соответствующую функцию из MatrixCode.py
3. MatrixCode.py создает сессию базы данных
4. MatrixCode.py извлекает данные через модели SQLAlchemy
5. MatrixCode.py генерирует и обновляет NFC коды
6. MatrixCode.py возвращает результат операции
7. main.py отображает результат пользователю

## Components and Interfaces

### MatrixCode Module

#### Функция update_user_codes()
```python
def update_user_codes() -> dict:
    """
    Обновляет NFC коды для всех пользователей.
    
    Returns:
        dict: {
            'success': bool,
            'updated_count': int,
            'message': str,
            'error': str | None
        }
    """
```

**Алгоритм:**
1. Создание сессии базы данных
2. Получение всех пользователей из таблицы users
3. Для каждого пользователя:
   - Проверка наличия обязательных полей (name, id_dep)
   - Генерация NFC кода: f"{user.id_us}_{user.name}_{user.id_dep}".lower()
   - Обновление поля nfc
4. Сохранение изменений в базе данных
5. Возврат результата операции

#### Функция update_equipment_codes()
```python
def update_equipment_codes() -> dict:
    """
    Обновляет NFC коды для всего оборудования.
    
    Returns:
        dict: {
            'success': bool,
            'updated_count': int,
            'message': str,
            'error': str | None
        }
    """
```

**Алгоритм:**
1. Создание сессии базы данных
2. Получение всего оборудования из таблицы equipment
3. Для каждого оборудования:
   - Проверка наличия обязательных полей (name, serialnum)
   - Генерация NFC кода: f"{equipment.id_eq}_{equipment.name}_{equipment.serialnum}".lower()
   - Обновление поля nfc
4. Сохранение изменений в базе данных
5. Возврат результата операции

### Main Interface Integration

#### Обновление обработчиков кнопок
- Замена `self.update_user_codes.` на `self.handle_update_user_codes`
- Замена `self.update_equipment_codes` на `self.handle_update_equipment_codes`

#### Новые методы в main.py
```python
def handle_update_user_codes(self):
    """Обработчик кнопки обновления кодов пользователей."""
    
def handle_update_equipment_codes(self):
    """Обработчик кнопки обновления кодов оборудования."""
```

## Data Models

### Используемые модели

#### User Model
- **id_us**: Primary key (Integer)
- **name**: Имя пользователя (String, required)
- **id_dep**: ID отдела (Integer, ForeignKey, required)
- **nfc**: NFC код (String, nullable, unique)

#### Equipment Model
- **id_eq**: Primary key (Integer)
- **name**: Название оборудования (String, required)
- **serialnum**: Серийный номер (String, required)
- **nfc**: NFC код (String, nullable, unique)

### NFC Code Generation Rules

#### Для пользователей
- Формат: `{id_us}_{name}_{id_dep}`
- Преобразование в нижний регистр
- Пример: `1_john_doe_5` → `1_john_doe_5`

#### Для оборудования
- Формат: `{id_eq}_{name}_{serialnum}`
- Преобразование в нижний регистр
- Пример: `10_laptop_abc123` → `10_laptop_abc123`

## Error Handling

### Database Errors
- Перехват исключений SQLAlchemy
- Откат транзакции при ошибках
- Закрытие сессии в блоке finally
- Возврат информативных сообщений об ошибках

### Data Validation
- Проверка наличия обязательных полей перед генерацией NFC кода
- Пропуск записей с неполными данными
- Логирование пропущенных записей

### UI Error Display
- Отображение ошибок через status_label
- Различные стили для успешных и неуспешных операций
- Информативные сообщения о количестве обновленных записей

## Testing Strategy

### Unit Tests
- Тестирование функций update_user_codes() и update_equipment_codes()
- Мокирование базы данных для изолированного тестирования
- Проверка корректности генерации NFC кодов
- Тестирование обработки ошибок

### Integration Tests
- Тестирование взаимодействия с реальной базой данных
- Проверка корректности обновления записей
- Тестирование отката транзакций при ошибках

### UI Tests
- Тестирование обработчиков кнопок
- Проверка отображения результатов операций
- Тестирование пользовательского интерфейса

## Implementation Considerations

### Database Connection
- Использование существующей конфигурации подключения к базе данных
- Повторное использование настроек из DATABASE_URL
- Оптимизация сессий базы данных

### Performance
- Пакетное обновление записей для улучшения производительности
- Минимизация количества запросов к базе данных
- Эффективное использование сессий SQLAlchemy

### Code Reusability
- Создание общих утилит для работы с базой данных
- Возможность расширения функциональности в будущем
- Следование принципам DRY (Don't Repeat Yourself)

### User Experience
- Быстрое выполнение операций
- Информативная обратная связь
- Предотвращение случайных операций через подтверждения