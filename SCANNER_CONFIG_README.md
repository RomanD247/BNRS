# Keyboard Scanner Configuration Guide

## Overview

The keyboard scanner system provides extensive configuration options to customize behavior, performance, and compatibility settings.

## Configuration Files

### 1. Default Configuration
- Located in `scanner_config.py`
- Contains base settings and platform-specific configurations
- Should not be modified directly

### 2. User Configuration
- File: `user_scanner_config.json` (created automatically)
- Contains user-specific overrides
- Can be edited manually or through configuration tools

### 3. Configuration Template
- File: `user_scanner_config_template.json`
- Example configuration with all available options
- Copy and modify as needed

## Configuration Options

### Scanner Mode
```json
{
  "scanner_mode": "keyboard"  // "keyboard" or "legacy_nfc"
}
```

### Timeouts
```json
{
  "timeouts": {
    "input_timeout": 30.0,              // Main input timeout (seconds)
    "focus_restore_timeout": 5.0,       // Focus restore timeout
    "dialog_auto_close_timeout": 2.0,   // Auto-close dialog after success
    "error_display_timeout": 5.0        // Error display time
  }
}
```

### Behavior Settings
```json
{
  "behavior": {
    "auto_focus_restore": true,    // Automatically restore window focus
    "show_manual_input": true,     // Show manual input field in dialog
    "confirm_on_enter": true,      // Confirm input on Enter key
    "clear_on_error": true,        // Clear buffer on validation error
    "beep_on_scan": false,         // Audio beep on successful scan
    "vibrate_on_error": false      // Vibration on error (if supported)
  }
}
```

### Performance Settings
```json
{
  "performance": {
    "main_loop_interval": 0.2,                    // Main wait loop interval (seconds)
    "status_update_interval": 5.0,                // Status update frequency
    "max_focus_restore_attempts": 3,              // Max focus restore attempts
    "buffer_expiration_check_interval": 10.0,     // Buffer cleanup frequency
    "enable_resource_optimization": true,         // Enable performance optimizations
    "use_adaptive_intervals": true                // Use adaptive timing
  }
}
```

### Validation Settings
```json
{
  "validation": {
    "strict_mode": false,          // Strict validation mode
    "allow_special_chars": false,  // Allow special characters
    "case_sensitive": false,       // Case-sensitive validation
    "trim_whitespace": true,       // Trim whitespace from input
    "normalize_input": true        // Normalize input format
  }
}
```

### UI Settings
```json
{
  "ui": {
    "theme": "auto",                // "light", "dark", "auto"
    "show_progress": true,          // Show scanning progress
    "show_remaining_time": true,    // Show remaining timeout
    "dialog_position": "center",    // "center", "top", "bottom"
    "auto_focus_input": true        // Auto-focus manual input field
  }
}
```

### Compatibility Settings
```json
{
  "compatibility": {
    "legacy_nfc_fallback": true,      // Enable fallback to legacy NFC
    "preserve_nfc_variables": true,   // Preserve NFC variable names
    "emulate_nfc_behavior": true      // Emulate original NFC behavior
  }
}
```

## Configuration Methods

### 1. Command Line Tool
```bash
# Show current status
python configure_scanner.py --status

# Set scanner mode
python configure_scanner.py --mode keyboard
python configure_scanner.py --mode legacy_nfc

# Set timeout
python configure_scanner.py --timeout 45

# Toggle auto focus
python configure_scanner.py --toggle-focus

# Enable performance optimization
python configure_scanner.py --optimize

# Reset to defaults
python configure_scanner.py --reset

# Export/import configuration
python configure_scanner.py --export my_config.json
python configure_scanner.py --import my_config.json
```

### 2. Programmatic Configuration
```python
from scanner_config import set_config_value, get_config_value

# Set individual values
set_config_value('scanner_mode', 'keyboard')
set_config_value('timeouts.input_timeout', 45.0)
set_config_value('behavior.auto_focus_restore', False)

# Get values
mode = get_config_value('scanner_mode', 'keyboard')
timeout = get_config_value('timeouts.input_timeout', 30.0)
```

### 3. GUI Configuration
```python
from NfcScan import configure_scanner_settings

# Open configuration dialog
configure_scanner_settings()
```

### 4. Direct File Editing
Edit `user_scanner_config.json` directly with any text editor.

## Performance Optimization

### Recommended Settings for High Performance
```json
{
  "performance": {
    "main_loop_interval": 0.2,
    "status_update_interval": 10.0,
    "enable_resource_optimization": true,
    "use_adaptive_intervals": true
  },
  "behavior": {
    "auto_focus_restore": true
  }
}
```

### Recommended Settings for Low Resource Usage
```json
{
  "performance": {
    "main_loop_interval": 0.5,
    "status_update_interval": 15.0,
    "buffer_expiration_check_interval": 30.0,
    "enable_resource_optimization": true,
    "use_adaptive_intervals": true
  }
}
```

## Switching Between Keyboard and Legacy NFC

### Enable Keyboard Scanner (Default)
```bash
python configure_scanner.py --mode keyboard
```

### Enable Legacy NFC Mode
```bash
python configure_scanner.py --mode legacy_nfc
```

### Check Current Mode
```bash
python configure_scanner.py --status
```

## Troubleshooting

### Configuration Not Loading
1. Check if `user_scanner_config.json` exists and is valid JSON
2. Reset configuration: `python configure_scanner.py --reset`
3. Check file permissions

### Performance Issues
1. Enable performance optimization: `python configure_scanner.py --optimize`
2. Increase intervals in performance settings
3. Disable unnecessary features (beep, vibration, etc.)

### Focus Issues
1. Enable auto focus restore: `python configure_scanner.py --toggle-focus`
2. Adjust `focus_restore_timeout` in timeouts settings
3. Check platform-specific focus method compatibility

## Examples

### Basic Setup for Production
```bash
python configure_scanner.py --mode keyboard --timeout 30 --optimize
```

### Development/Testing Setup
```bash
python configure_scanner.py --mode keyboard --timeout 60 --no-optimize
```

### Legacy Compatibility
```bash
python configure_scanner.py --mode legacy_nfc
```

## Configuration Priority

1. User configuration file (`user_scanner_config.json`)
2. Advanced configuration (`ADVANCED_CONFIG` in `scanner_config.py`)
3. Base configuration (`SCANNER_CONFIG` in `scanner_config.py`)
4. Platform-specific configuration
5. Default values

Higher priority settings override lower priority ones.