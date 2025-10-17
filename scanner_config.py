"""
Конфигурация для клавиатурного сканера
Configuration for keyboard scanner integration
"""

import string
import platform
import time
from dataclasses import dataclass
from typing import Optional

# Основные настройки сканера / Main scanner settings
SCANNER_CONFIG = {
    # Таймаут ожидания ввода в секундах / Input timeout in seconds
    'input_timeout': 30.0,
    
    # Интервал проверки фокуса окна в секундах / Window focus check interval in seconds
    'focus_check_interval': 1.0,  # Увеличен с 0.5 до 1.0 для снижения нагрузки
    
    # Таймаут очистки буфера при неактивности в секундах / Buffer clear timeout on inactivity in seconds
    'buffer_clear_timeout': 60.0,
    
    # Разрешенные символы для ввода / Allowed input characters
    'allowed_characters': string.ascii_letters + string.digits + '-_',
    
    # Символы завершения ввода / Input termination characters
    'termination_chars': ['\n', '\r'],
    
    # Максимальная длина кода / Maximum code length
    'max_code_length': 50,
    
    # Минимальная длина кода / Minimum code length
    'min_code_length': 1,
    
    # Настройки производительности / Performance settings
    'performance': {
        # Интервал основного цикла ожидания в секундах / Main wait loop interval in seconds
        'main_loop_interval': 0.2,  # Увеличен с 0.1 до 0.2
        
        # Интервал обновления статуса в секундах / Status update interval in seconds
        'status_update_interval': 5.0,
        
        # Максимальное количество попыток восстановления фокуса / Max focus restore attempts
        'max_focus_restore_attempts': 3,
        
        # Интервал проверки истечения буфера в секундах / Buffer expiration check interval
        'buffer_expiration_check_interval': 10.0,
        
        # Включить оптимизацию ресурсов / Enable resource optimization
        'enable_resource_optimization': True,
        
        # Использовать адаптивные интервалы / Use adaptive intervals
        'use_adaptive_intervals': True,
    }
}

# Платформо-специфичные настройки / Platform-specific settings
PLATFORM_CONFIG = {
    'Windows': {
        'focus_method': 'win32',
        'window_title_pattern': 'WenglorMEL Rental System',
    },
    'Linux': {
        'focus_method': 'x11',
        'window_title_pattern': 'WenglorMEL Rental System',
    },
    'Darwin': {  # macOS
        'focus_method': 'cocoa',
        'window_title_pattern': 'WenglorMEL Rental System',
    }
}

# Получение текущей платформы / Get current platform
CURRENT_PLATFORM = platform.system()

# Настройки для текущей платформы / Settings for current platform
CURRENT_PLATFORM_CONFIG = PLATFORM_CONFIG.get(CURRENT_PLATFORM, PLATFORM_CONFIG['Windows'])

# Настройки отладки / Debug settings
DEBUG_CONFIG = {
    'log_key_events': False,  # Логировать события клавиатуры / Log keyboard events
    'log_focus_changes': False,  # Логировать изменения фокуса / Log focus changes
    'verbose_errors': True,  # Подробные сообщения об ошибках / Verbose error messages
}

# Сообщения пользователю / User messages
USER_MESSAGES = {
    'ru': {
        'scanning_prompt': 'Отсканируйте код...',
        'scanning_timeout': 'Время ожидания сканирования истекло',
        'scanning_cancelled': 'Сканирование отменено',
        'scanning_error': 'Ошибка при сканировании',
        'focus_lost': 'Окно потеряло фокус. Восстанавливаем...',
        'focus_restored': 'Фокус восстановлен',
        'invalid_code': 'Получен некорректный код',
        'empty_code': 'Получен пустой код',
    },
    'en': {
        'scanning_prompt': 'Scan code...',
        'scanning_timeout': 'Scanning timeout expired',
        'scanning_cancelled': 'Scanning cancelled',
        'scanning_error': 'Error during scanning',
        'focus_lost': 'Window lost focus. Restoring...',
        'focus_restored': 'Focus restored',
        'invalid_code': 'Invalid code received',
        'empty_code': 'Empty code received',
    }
}

# Язык по умолчанию / Default language
DEFAULT_LANGUAGE = 'ru'

def get_message(key: str, language: str = DEFAULT_LANGUAGE) -> str:
    """
    Получить сообщение на указанном языке
    Get message in specified language
    
    Args:
        key: Ключ сообщения / Message key
        language: Язык ('ru' или 'en') / Language ('ru' or 'en')
    
    Returns:
        str: Сообщение / Message
    """
    messages = USER_MESSAGES.get(language, USER_MESSAGES[DEFAULT_LANGUAGE])
    return messages.get(key, f"Message not found: {key}")

@dataclass
class InputBuffer:
    """
    Буфер для накопления символов от клавиатурного сканера
    Buffer for accumulating characters from keyboard scanner
    """
    content: str = ""
    is_complete: bool = False
    timestamp: float = 0.0
    
    def __post_init__(self):
        """Инициализация временной метки при создании буфера"""
        if self.timestamp == 0.0:
            self.timestamp = time.time()
    
    def add_character(self, char: str) -> bool:
        """
        Добавить символ в буфер с валидацией
        Add character to buffer with validation
        
        Args:
            char: Символ для добавления / Character to add
            
        Returns:
            bool: True если символ был добавлен / True if character was added
        """
        # Быстрая проверка на пустой символ
        if not char:
            return False
            
        # Проверка на символы завершения ввода
        # Check for input termination characters
        if char in SCANNER_CONFIG['termination_chars']:
            # Символ завершения ввода
            if len(self.content) >= SCANNER_CONFIG['min_code_length']:
                self.is_complete = True
            return True
        
        # Быстрая проверка максимальной длины перед валидацией
        # Quick max length check before validation
        if len(self.content) >= SCANNER_CONFIG['max_code_length']:
            return False
        
        # Валидация символа (оптимизированная)
        # Character validation (optimized)
        if not self._is_character_valid_fast(char):
            return False
        
        # Добавляем символ
        # Add character
        self.content += char
        self.timestamp = time.time()  # Обновляем временную метку
        return True
    
    def _is_character_valid(self, char: str) -> bool:
        """
        Проверить валидность символа
        Check character validity
        
        Args:
            char: Символ для проверки / Character to check
            
        Returns:
            bool: True если символ валиден / True if character is valid
        """
        if not char:
            return False
        
        # Проверка на разрешенные символы
        # Check for allowed characters
        if char not in SCANNER_CONFIG['allowed_characters']:
            return False
        
        # Дополнительная проверка на опасные символы
        # Additional check for dangerous characters
        dangerous_chars = {'<', '>', '"', "'", '&', ';', '|', '`', '$', '(', ')', '[', ']', '{', '}', '\\', '/', '*', '?'}
        if char in dangerous_chars:
            return False
        
        return True
    
    def _is_character_valid_fast(self, char: str) -> bool:
        """
        Быстрая проверка валидности символа (оптимизированная версия)
        Fast character validity check (optimized version)
        
        Args:
            char: Символ для проверки / Character to check
            
        Returns:
            bool: True если символ валиден / True if character is valid
        """
        # Кэшированные множества для быстрой проверки
        if not hasattr(self, '_allowed_chars_set'):
            self._allowed_chars_set = set(SCANNER_CONFIG['allowed_characters'])
            self._dangerous_chars_set = {'<', '>', '"', "'", '&', ';', '|', '`', '\n', '(', ')', '[', ']', '{', '}', '\\', '/', '*', '?'}
        
        # Быстрая проверка через множества (O(1) вместо O(n))
        return (char in self._allowed_chars_set and 
                char not in self._dangerous_chars_set)
    
    def clear(self) -> None:
        """
        Очистить буфер
        Clear buffer
        """
        self.content = ""
        self.is_complete = False
        self.timestamp = time.time()
    
    def is_expired(self, timeout: Optional[float] = None) -> bool:
        """
        Проверить, истек ли таймаут буфера
        Check if buffer timeout has expired
        
        Args:
            timeout: Таймаут в секундах (по умолчанию из конфигурации)
                    Timeout in seconds (default from configuration)
        
        Returns:
            bool: True если таймаут истек / True if timeout expired
        """
        if timeout is None:
            timeout = SCANNER_CONFIG['buffer_clear_timeout']
        
        return (time.time() - self.timestamp) > timeout
    
    def get_code(self) -> str:
        """
        Получить код из буфера (только если ввод завершен)
        Get code from buffer (only if input is complete)
        
        Returns:
            str: Код или пустая строка / Code or empty string
        """
        if self.is_complete and self.content:
            return self.content.strip()
        return ""
    
    def is_valid(self) -> bool:
        """
        Проверить, содержит ли буфер валидный код
        Check if buffer contains valid code
        
        Returns:
            bool: True если код валиден / True if code is valid
        """
        return (self.is_complete and 
                SCANNER_CONFIG['min_code_length'] <= len(self.content) <= SCANNER_CONFIG['max_code_length'] and
                all(c in SCANNER_CONFIG['allowed_characters'] for c in self.content))


@dataclass
class ScanResult:
    """
    Результат сканирования кода
    Scan result data structure
    """
    code: str
    success: bool
    error_message: Optional[str] = None
    scan_duration: float = 0.0
    
    @classmethod
    def success_result(cls, code: str, scan_duration: float = 0.0) -> 'ScanResult':
        """
        Создать успешный результат сканирования
        Create successful scan result
        
        Args:
            code: Отсканированный код / Scanned code
            scan_duration: Длительность сканирования в секундах / Scan duration in seconds
        
        Returns:
            ScanResult: Успешный результат / Successful result
        """
        return cls(
            code=code,
            success=True,
            error_message=None,
            scan_duration=scan_duration
        )
    
    @classmethod
    def error_result(cls, error_message: str, code: str = "", scan_duration: float = 0.0) -> 'ScanResult':
        """
        Создать результат с ошибкой
        Create error result
        
        Args:
            error_message: Сообщение об ошибке / Error message
            code: Частично отсканированный код (если есть) / Partially scanned code (if any)
            scan_duration: Длительность попытки сканирования / Scan attempt duration
        
        Returns:
            ScanResult: Результат с ошибкой / Error result
        """
        return cls(
            code=code,
            success=False,
            error_message=error_message,
            scan_duration=scan_duration
        )
    
    @classmethod
    def timeout_result(cls, scan_duration: float = 0.0) -> 'ScanResult':
        """
        Создать результат с таймаутом
        Create timeout result
        
        Args:
            scan_duration: Длительность ожидания / Wait duration
        
        Returns:
            ScanResult: Результат с таймаутом / Timeout result
        """
        return cls.error_result(
            error_message=get_message('scanning_timeout'),
            scan_duration=scan_duration
        )
    
    @classmethod
    def cancelled_result(cls, scan_duration: float = 0.0) -> 'ScanResult':
        """
        Создать результат отмены сканирования
        Create cancelled scan result
        
        Args:
            scan_duration: Длительность до отмены / Duration until cancellation
        
        Returns:
            ScanResult: Результат отмены / Cancelled result
        """
        return cls.error_result(
            error_message=get_message('scanning_cancelled'),
            scan_duration=scan_duration
        )
    
    @classmethod
    def invalid_code_result(cls, code: str, scan_duration: float = 0.0) -> 'ScanResult':
        """
        Создать результат с некорректным кодом
        Create invalid code result
        
        Args:
            code: Некорректный код / Invalid code
            scan_duration: Длительность сканирования / Scan duration
        
        Returns:
            ScanResult: Результат с некорректным кодом / Invalid code result
        """
        return cls.error_result(
            error_message=get_message('invalid_code'),
            code=code,
            scan_duration=scan_duration
        )
    
    @classmethod
    def empty_code_result(cls, scan_duration: float = 0.0) -> 'ScanResult':
        """
        Создать результат с пустым кодом
        Create empty code result
        
        Args:
            scan_duration: Длительность сканирования / Scan duration
        
        Returns:
            ScanResult: Результат с пустым кодом / Empty code result
        """
        return cls.error_result(
            error_message=get_message('empty_code'),
            scan_duration=scan_duration
        )
    
    def is_valid_code(self) -> bool:
        """
        Проверить, содержит ли результат валидный код
        Check if result contains valid code
        
        Returns:
            bool: True если код валиден / True if code is valid
        """
        return (self.success and 
                self.code and 
                SCANNER_CONFIG['min_code_length'] <= len(self.code) <= SCANNER_CONFIG['max_code_length'])


# Расширенные настройки конфигурации / Advanced configuration settings
ADVANCED_CONFIG = {
    # Режим работы сканера / Scanner operation mode
    'scanner_mode': 'keyboard',  # 'keyboard' или 'legacy_nfc' / 'keyboard' or 'legacy_nfc'
    
    # Настройки таймаутов / Timeout settings
    'timeouts': {
        'input_timeout': 30.0,  # Основной таймаут ввода / Main input timeout
        'focus_restore_timeout': 5.0,  # Таймаут восстановления фокуса / Focus restore timeout
        'dialog_auto_close_timeout': 2.0,  # Автозакрытие диалога после успеха / Auto-close dialog after success
        'error_display_timeout': 5.0,  # Время показа ошибки / Error display time
    },
    
    # Настройки поведения / Behavior settings
    'behavior': {
        'auto_focus_restore': True,  # Автоматическое восстановление фокуса / Automatic focus restore
        'show_manual_input': True,  # Показывать поле ручного ввода / Show manual input field
        'confirm_on_enter': True,  # Подтверждение по Enter / Confirm on Enter
        'clear_on_error': True,  # Очищать буфер при ошибке / Clear buffer on error
        'beep_on_scan': False,  # Звуковой сигнал при сканировании / Beep on scan
        'vibrate_on_error': False,  # Вибрация при ошибке (если поддерживается) / Vibrate on error
    },
    
    # Настройки валидации / Validation settings
    'validation': {
        'strict_mode': False,  # Строгий режим валидации / Strict validation mode
        'allow_special_chars': False,  # Разрешить специальные символы / Allow special characters
        'case_sensitive': False,  # Чувствительность к регистру / Case sensitivity
        'trim_whitespace': True,  # Обрезать пробелы / Trim whitespace
        'normalize_input': True,  # Нормализовать ввод / Normalize input
    },
    
    # Настройки интерфейса / UI settings
    'ui': {
        'theme': 'auto',  # 'light', 'dark', 'auto' / Theme setting
        'show_progress': True,  # Показывать прогресс / Show progress
        'show_remaining_time': True,  # Показывать оставшееся время / Show remaining time
        'dialog_position': 'center',  # 'center', 'top', 'bottom' / Dialog position
        'auto_focus_input': True,  # Автофокус на поле ввода / Auto-focus input field
    },
    
    # Настройки логирования / Logging settings
    'logging': {
        'log_level': 'INFO',  # 'DEBUG', 'INFO', 'WARNING', 'ERROR' / Log level
        'log_scan_events': False,  # Логировать события сканирования / Log scan events
        'log_performance': False,  # Логировать производительность / Log performance
        'log_to_file': False,  # Логировать в файл / Log to file
        'log_file_path': 'scanner.log',  # Путь к файлу лога / Log file path
    },
    
    # Настройки совместимости / Compatibility settings
    'compatibility': {
        'legacy_nfc_fallback': True,  # Откат к старой системе NFC / Fallback to legacy NFC
        'preserve_nfc_variables': True,  # Сохранять переменные NFC / Preserve NFC variables
        'emulate_nfc_behavior': True,  # Эмулировать поведение NFC / Emulate NFC behavior
    }
}

# Пользовательские настройки (могут быть переопределены) / User settings (can be overridden)
USER_CONFIG = {}

def load_user_config(config_path: str = None) -> dict:
    """
    Загрузить пользовательские настройки из файла
    Load user settings from file
    
    Args:
        config_path: Путь к файлу конфигурации / Path to configuration file
        
    Returns:
        dict: Пользовательские настройки / User settings
    """
    import json
    import os
    
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), 'user_scanner_config.json')
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load user config from {config_path}: {e}")
    
    return {}

def save_user_config(config: dict, config_path: str = None) -> bool:
    """
    Сохранить пользовательские настройки в файл
    Save user settings to file
    
    Args:
        config: Настройки для сохранения / Settings to save
        config_path: Путь к файлу конфигурации / Path to configuration file
        
    Returns:
        bool: True если сохранение успешно / True if save successful
    """
    import json
    import os
    
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), 'user_scanner_config.json')
    
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error: Could not save user config to {config_path}: {e}")
        return False

def merge_configs(*configs) -> dict:
    """
    Объединить несколько конфигураций с приоритетом
    Merge multiple configurations with priority
    
    Args:
        *configs: Конфигурации для объединения / Configurations to merge
        
    Returns:
        dict: Объединенная конфигурация / Merged configuration
    """
    result = {}
    
    for config in configs:
        if isinstance(config, dict):
            for key, value in config.items():
                if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                    result[key] = merge_configs(result[key], value)
                else:
                    result[key] = value
    
    return result

def get_effective_config() -> dict:
    """
    Получить эффективную конфигурацию с учетом всех настроек
    Get effective configuration considering all settings
    
    Returns:
        dict: Эффективная конфигурация / Effective configuration
    """
    global USER_CONFIG
    
    # Загружаем пользовательские настройки если они еще не загружены
    if not USER_CONFIG:
        USER_CONFIG = load_user_config()
    
    # Объединяем конфигурации в порядке приоритета
    return merge_configs(
        SCANNER_CONFIG,
        ADVANCED_CONFIG,
        {'platform': CURRENT_PLATFORM_CONFIG},
        {'debug': DEBUG_CONFIG},
        {'language': DEFAULT_LANGUAGE},
        USER_CONFIG
    )

def update_config(updates: dict, save_to_file: bool = True) -> bool:
    """
    Обновить конфигурацию
    Update configuration
    
    Args:
        updates: Обновления конфигурации / Configuration updates
        save_to_file: Сохранить в файл / Save to file
        
    Returns:
        bool: True если обновление успешно / True if update successful
    """
    global USER_CONFIG
    
    USER_CONFIG = merge_configs(USER_CONFIG, updates)
    
    if save_to_file:
        return save_user_config(USER_CONFIG)
    
    return True

def reset_config() -> bool:
    """
    Сбросить конфигурацию к значениям по умолчанию
    Reset configuration to default values
    
    Returns:
        bool: True если сброс успешен / True if reset successful
    """
    global USER_CONFIG
    USER_CONFIG = {}
    return save_user_config(USER_CONFIG)

def get_config_value(key_path: str, default=None):
    """
    Получить значение конфигурации по пути
    Get configuration value by path
    
    Args:
        key_path: Путь к ключу (например, 'timeouts.input_timeout') / Key path (e.g., 'timeouts.input_timeout')
        default: Значение по умолчанию / Default value
        
    Returns:
        Значение конфигурации / Configuration value
    """
    config = get_effective_config()
    keys = key_path.split('.')
    
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current

def set_config_value(key_path: str, value, save_to_file: bool = True) -> bool:
    """
    Установить значение конфигурации по пути
    Set configuration value by path
    
    Args:
        key_path: Путь к ключу / Key path
        value: Новое значение / New value
        save_to_file: Сохранить в файл / Save to file
        
    Returns:
        bool: True если установка успешна / True if set successful
    """
    keys = key_path.split('.')
    updates = {}
    current = updates
    
    for i, key in enumerate(keys):
        if i == len(keys) - 1:
            current[key] = value
        else:
            current[key] = {}
            current = current[key]
    
    return update_config(updates, save_to_file)

def is_legacy_mode() -> bool:
    """
    Проверить, включен ли режим совместимости с NFC
    Check if legacy NFC compatibility mode is enabled
    
    Returns:
        bool: True если включен режим совместимости / True if legacy mode enabled
    """
    return get_config_value('scanner_mode', 'keyboard') == 'legacy_nfc'

def get_scanner_config() -> dict:
    """
    Получить полную конфигурацию сканера
    Get complete scanner configuration
    
    Returns:
        dict: Конфигурация сканера / Scanner configuration
    """
    return get_effective_config()