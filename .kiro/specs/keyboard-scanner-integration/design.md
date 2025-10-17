# Design Document

## Overview

Дизайн системы для интеграции клавиатурного сканера в существующую систему аренды оборудования. Система заменит текущую функцию NFC сканирования на решение, которое работает с физическими сканерами, эмулирующими клавиатуру.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Keyboard Scanner│───▶│ Background Input │───▶│ NFC Workflow    │
│ (Hardware)      │    │ Handler          │    │ (Existing)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │ Focus Manager    │
                       └──────────────────┘
```

### Component Integration

Новая система интегрируется с существующим кодом через:
- Замену функции `get_nfc_input()` в `NfcScan.py`
- Сохранение всех существующих интерфейсов и диалогов
- Использование той же асинхронной архитектуры

## Components and Interfaces

### 1. KeyboardInputHandler

**Назначение**: Основной компонент для перехвата и обработки клавиатурного ввода

**Интерфейс**:
```python
class KeyboardInputHandler:
    async def get_scanner_input(self, prompt_message: str) -> str
    def start_listening(self) -> None
    def stop_listening(self) -> None
    def _on_key_press(self, key) -> None
    def _on_key_release(self, key) -> None
```

**Ключевые особенности**:
- Использует библиотеку `pynput` для глобального перехвата клавиш
- Накапливает символы в внутреннем буфере
- Завершает ввод при получении символа новой строки
- Фильтрует специальные клавиши (Ctrl, Alt, Shift и т.д.)

### 2. FocusManager

**Назначение**: Управление фокусом окна приложения во время сканирования

**Интерфейс**:
```python
class FocusManager:
    def ensure_window_focus(self) -> bool
    def is_window_focused(self) -> bool
    def restore_focus(self) -> None
```

**Ключевые особенности**:
- Использует системные API для проверки и восстановления фокуса
- Кроссплатформенная совместимость (Windows/Linux/macOS)
- Интеграция с NiceGUI для получения информации о окне

### 3. ScannerDialog

**Назначение**: Пользовательский интерфейс для процесса сканирования

**Интерфейс**:
```python
class ScannerDialog:
    def show_scanning_dialog(self, message: str) -> ui.dialog
    def update_status(self, status: str) -> None
    def close_dialog(self) -> None
```

**Ключевые особенности**:
- Показывает диалог ожидания сканирования
- Предоставляет кнопку отмены
- Отображает статус процесса (ожидание, ошибка, успех)

## Data Models

### InputBuffer

```python
@dataclass
class InputBuffer:
    content: str = ""
    is_complete: bool = False
    timestamp: float = 0.0
    
    def add_character(self, char: str) -> None
    def clear(self) -> None
    def is_expired(self, timeout: float = 30.0) -> bool
```

### ScanResult

```python
@dataclass
class ScanResult:
    code: str
    success: bool
    error_message: Optional[str] = None
    scan_duration: float = 0.0
```

## Error Handling

### Error Categories

1. **Hardware Errors**:
   - Сканер не подключен или не работает
   - Неправильная конфигурация сканера

2. **Focus Errors**:
   - Потеря фокуса окна
   - Невозможность восстановить фокус

3. **Input Errors**:
   - Таймаут ожидания ввода
   - Некорректный формат данных
   - Пустой ввод

4. **System Errors**:
   - Ошибки библиотеки pynput
   - Проблемы с правами доступа

### Error Handling Strategy

```python
class ErrorHandler:
    def handle_timeout_error(self) -> ScanResult
    def handle_focus_error(self) -> ScanResult  
    def handle_input_error(self, error: Exception) -> ScanResult
    def handle_system_error(self, error: Exception) -> ScanResult
```

**Принципы обработки ошибок**:
- Graceful degradation: система продолжает работать при ошибках
- Понятные сообщения пользователю
- Логирование ошибок для диагностики
- Автоматическое восстановление где возможно

## Testing Strategy

### Unit Tests

1. **KeyboardInputHandler Tests**:
   - Тестирование накопления символов в буфере
   - Проверка обработки специальных клавиш
   - Тестирование завершения ввода по новой строке

2. **FocusManager Tests**:
   - Мокирование системных вызовов
   - Тестирование определения фокуса
   - Проверка восстановления фокуса

3. **ScannerDialog Tests**:
   - Тестирование создания и закрытия диалогов
   - Проверка обновления статуса
   - Тестирование отмены операции

### Integration Tests

1. **End-to-End Scanning**:
   - Симуляция полного процесса сканирования
   - Тестирование с различными типами кодов
   - Проверка интеграции с существующим NFC workflow

2. **Error Scenarios**:
   - Тестирование таймаутов
   - Проверка обработки потери фокуса
   - Тестирование некорректного ввода

### Manual Testing

1. **Hardware Testing**:
   - Тестирование с реальным клавиатурным сканером
   - Проверка различных типов штрих-кодов
   - Тестирование скорости сканирования

2. **User Experience Testing**:
   - Проверка интуитивности интерфейса
   - Тестирование в различных сценариях использования
   - Валидация сообщений об ошибках

## Implementation Details

### Dependencies

Новые зависимости для добавления в `requirements.txt`:
```
pynput>=1.7.6
psutil>=5.9.0  # для управления процессами и окнами
```

### Configuration

Настройки для клавиатурного сканера:
```python
SCANNER_CONFIG = {
    'input_timeout': 30.0,  # секунды ожидания ввода
    'focus_check_interval': 0.5,  # интервал проверки фокуса
    'buffer_clear_timeout': 60.0,  # очистка буфера при неактивности
    'allowed_characters': string.ascii_letters + string.digits + '-_',
    'termination_chars': ['\n', '\r'],  # символы завершения ввода
}
```

### File Structure Changes

```
NfcScan.py (modified)
├── KeyboardInputHandler (new class)
├── FocusManager (new class)  
├── ScannerDialog (new class)
├── get_scanner_input() (replaces get_nfc_input)
└── nfc_equipment_rental_workflow (minimal changes)

scanner_config.py (new file)
├── Configuration constants
└── Platform-specific settings
```

### Backward Compatibility

- Сохранение всех существующих функций и интерфейсов
- Переменные с префиксом `nfc_` остаются без изменений
- Существующие диалоги и workflow не изменяются
- Возможность переключения между старой и новой системой через конфигурацию

## Security Considerations

1. **Input Validation**:
   - Фильтрация вредоносных символов
   - Ограничение длины ввода
   - Валидация формата кодов

2. **System Access**:
   - Минимальные права для перехвата клавиатуры
   - Безопасное управление фокусом окна
   - Защита от injection атак через клавиатурный ввод

3. **Data Protection**:
   - Очистка буферов после использования
   - Отсутствие логирования чувствительных данных
   - Безопасное хранение временных данных

## Performance Considerations

1. **Resource Usage**:
   - Минимальное потребление CPU при ожидании ввода
   - Эффективная очистка ресурсов после завершения
   - Оптимизация частоты проверки фокуса

2. **Response Time**:
   - Мгновенная реакция на ввод символов
   - Быстрое определение завершения ввода
   - Минимальная задержка при восстановлении фокуса

3. **Memory Management**:
   - Ограничение размера буфера ввода
   - Автоматическая очистка при таймауте
   - Предотвращение утечек памяти в обработчиках событий