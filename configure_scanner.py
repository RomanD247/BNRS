#!/usr/bin/env python3
"""
Утилита командной строки для настройки клавиатурного сканера
Command-line utility for keyboard scanner configuration
"""

import argparse
import json
import sys
from pathlib import Path

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent))

from scanner_config import (
    get_effective_config, 
    set_config_value, 
    reset_config, 
    save_user_config,
    load_user_config,
    is_legacy_mode
)

def print_config(config=None):
    """Вывести текущую конфигурацию"""
    if config is None:
        config = get_effective_config()
    
    print("Current Scanner Configuration:")
    print("=" * 40)
    print(json.dumps(config, indent=2, ensure_ascii=False))

def print_status():
    """Вывести статус системы"""
    config = get_effective_config()
    
    print("Scanner System Status:")
    print("=" * 30)
    print(f"Mode: {config.get('scanner_mode', 'keyboard')}")
    print(f"Legacy Mode: {'Yes' if is_legacy_mode() else 'No'}")
    print(f"Input Timeout: {config.get('timeouts', {}).get('input_timeout', 30)} seconds")
    print(f"Auto Focus Restore: {'Yes' if config.get('behavior', {}).get('auto_focus_restore', True) else 'No'}")
    print(f"Performance Optimization: {'Yes' if config.get('performance', {}).get('enable_resource_optimization', True) else 'No'}")
    print(f"Platform: {config.get('platform', {}).get('focus_method', 'unknown')}")

def set_mode(mode):
    """Установить режим сканера"""
    if mode not in ['keyboard', 'legacy_nfc']:
        print(f"Error: Invalid mode '{mode}'. Use 'keyboard' or 'legacy_nfc'")
        return False
    
    if set_config_value('scanner_mode', mode):
        print(f"Scanner mode set to: {mode}")
        return True
    else:
        print("Error: Failed to set scanner mode")
        return False

def set_timeout(timeout):
    """Установить таймаут ввода"""
    try:
        timeout_value = float(timeout)
        if timeout_value < 5.0 or timeout_value > 300.0:
            print("Error: Timeout must be between 5 and 300 seconds")
            return False
        
        if set_config_value('timeouts.input_timeout', timeout_value):
            print(f"Input timeout set to: {timeout_value} seconds")
            return True
        else:
            print("Error: Failed to set timeout")
            return False
    except ValueError:
        print(f"Error: Invalid timeout value '{timeout}'. Must be a number.")
        return False

def toggle_auto_focus():
    """Переключить автоматическое восстановление фокуса"""
    config = get_effective_config()
    current_value = config.get('behavior', {}).get('auto_focus_restore', True)
    new_value = not current_value
    
    if set_config_value('behavior.auto_focus_restore', new_value):
        print(f"Auto focus restore: {'Enabled' if new_value else 'Disabled'}")
        return True
    else:
        print("Error: Failed to toggle auto focus")
        return False

def enable_performance_optimization():
    """Включить оптимизацию производительности"""
    updates = {
        'performance': {
            'enable_resource_optimization': True,
            'use_adaptive_intervals': True,
            'main_loop_interval': 0.2,
            'status_update_interval': 5.0,
        }
    }
    
    from scanner_config import update_config
    if update_config(updates):
        print("Performance optimization enabled")
        return True
    else:
        print("Error: Failed to enable performance optimization")
        return False

def disable_performance_optimization():
    """Отключить оптимизацию производительности"""
    updates = {
        'performance': {
            'enable_resource_optimization': False,
            'use_adaptive_intervals': False,
            'main_loop_interval': 0.1,
            'status_update_interval': 1.0,
        }
    }
    
    from scanner_config import update_config
    if update_config(updates):
        print("Performance optimization disabled")
        return True
    else:
        print("Error: Failed to disable performance optimization")
        return False

def export_config(filename):
    """Экспортировать конфигурацию в файл"""
    try:
        config = get_effective_config()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"Configuration exported to: {filename}")
        return True
    except Exception as e:
        print(f"Error exporting configuration: {e}")
        return False

def import_config(filename):
    """Импортировать конфигурацию из файла"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        from scanner_config import update_config
        if update_config(config):
            print(f"Configuration imported from: {filename}")
            return True
        else:
            print("Error: Failed to import configuration")
            return False
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file '{filename}': {e}")
        return False
    except Exception as e:
        print(f"Error importing configuration: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Configure keyboard scanner settings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --status                    # Show current status
  %(prog)s --config                    # Show full configuration
  %(prog)s --mode keyboard             # Set keyboard scanner mode
  %(prog)s --mode legacy_nfc           # Set legacy NFC mode
  %(prog)s --timeout 45                # Set input timeout to 45 seconds
  %(prog)s --toggle-focus              # Toggle auto focus restore
  %(prog)s --optimize                  # Enable performance optimization
  %(prog)s --reset                     # Reset to defaults
  %(prog)s --export config.json        # Export configuration
  %(prog)s --import config.json        # Import configuration
        """
    )
    
    parser.add_argument('--status', action='store_true',
                       help='Show scanner system status')
    parser.add_argument('--config', action='store_true',
                       help='Show full configuration')
    parser.add_argument('--mode', choices=['keyboard', 'legacy_nfc'],
                       help='Set scanner mode')
    parser.add_argument('--timeout', type=str,
                       help='Set input timeout in seconds (5-300)')
    parser.add_argument('--toggle-focus', action='store_true',
                       help='Toggle automatic focus restore')
    parser.add_argument('--optimize', action='store_true',
                       help='Enable performance optimization')
    parser.add_argument('--no-optimize', action='store_true',
                       help='Disable performance optimization')
    parser.add_argument('--reset', action='store_true',
                       help='Reset configuration to defaults')
    parser.add_argument('--export', type=str, metavar='FILE',
                       help='Export configuration to file')
    parser.add_argument('--import', type=str, metavar='FILE', dest='import_file',
                       help='Import configuration from file')
    
    args = parser.parse_args()
    
    # Если нет аргументов, показываем статус
    if len(sys.argv) == 1:
        print_status()
        return
    
    success = True
    
    if args.status:
        print_status()
    
    if args.config:
        print_config()
    
    if args.mode:
        success &= set_mode(args.mode)
    
    if args.timeout:
        success &= set_timeout(args.timeout)
    
    if args.toggle_focus:
        success &= toggle_auto_focus()
    
    if args.optimize:
        success &= enable_performance_optimization()
    
    if args.no_optimize:
        success &= disable_performance_optimization()
    
    if args.reset:
        if reset_config():
            print("Configuration reset to defaults")
        else:
            print("Error: Failed to reset configuration")
            success = False
    
    if args.export:
        success &= export_config(args.export)
    
    if args.import_file:
        success &= import_config(args.import_file)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()