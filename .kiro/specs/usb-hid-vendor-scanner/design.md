# Design Document: USB HID Vendor Mode Scanner Integration

## Overview

This design document outlines the migration from keyboard-based scanner integration to USB HID Vendor Mode for improved stability and reliability. The current implementation uses keyboard emulation (HID keyboard mode) which has stability issues. The new system will communicate directly with the scanner via USB HID protocol using the `hidapi` library for Python.

The scanner integration is currently implemented in `NfcScan.py` with the `get_nfc_input()` function that waits for keyboard input. This will be replaced with a new USB HID-based implementation that reads raw data directly from the scanner device.

## Architecture

### Current Architecture
- Scanner operates in HID keyboard mode (emulates keyboard input)
- `get_nfc_input()` function displays a dialog with an invisible input field
- Scanner input is captured as keyboard events
- Data is processed as text input from the virtual keyboard

### New Architecture
- Scanner operates in USB HID Vendor Mode
- New `USBHIDScanner` class handles USB communication
- Configuration system manages VID/PID and mode settings
- Backward compatibility maintained through mode switching
- Same async interface preserved for seamless integration

### Component Layers

```
┌─────────────────────────────────────────┐
│     Application Layer (main.py)         │
│  - Rental workflows                     │
│  - UI dialogs                           │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   Scanner Interface (NfcScan.py)        │
│  - get_nfc_input() - async interface    │
│  - Mode detection and routing           │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼─────┐   ┌──────▼──────┐
│ USB HID    │   │  Keyboard   │
│ Scanner    │   │  Mode       │
│ (New)      │   │  (Legacy)   │
└────────────┘   └─────────────┘
       │
┌──────▼─────────────────────────────────┐
│  Configuration System                  │
│  - scanner_config.json                 │
│  - VID/PID settings                    │
│  - Mode selection                      │
└────────────────────────────────────────┘
```

## Components and Interfaces

### 1. USBHIDScanner Class

**Purpose**: Handles USB HID communication with the scanner device

**Location**: New file `usb_hid_scanner.py`

**Key Methods**:
```python
class USBHIDScanner:
    def __init__(self, vid: int, pid: int, timeout: int = 30):
        """Initialize scanner with VID/PID"""
        
    def connect(self) -> bool:
        """Connect to the scanner device"""
        
    def disconnect(self) -> None:
        """Disconnect from the scanner"""
        
    def read_scan(self, timeout: int = 30) -> Optional[str]:
        """Read scanned data from device"""
        
    def is_connected(self) -> bool:
        """Check if scanner is connected"""
        
    @staticmethod
    def list_devices() -> List[Dict]:
        """List all available HID devices"""
```

**Dependencies**:
- `hid` library (hidapi Python wrapper)
- Configuration system for VID/PID values

### 2. Scanner Configuration System

**Purpose**: Manage scanner settings including VID/PID and mode selection

**Location**: New file `scanner_config.py`

**Configuration Structure**:
```python
{
    "scanner_mode": "usb_vendor",  # or "keyboard"
    "usb_vendor": {
        "vid": 4602,  # 0x11FA
        "pid": 33282,  # 0x8202
        "timeout": 30,
        "read_size": 64,
        "encoding": "utf-8"
    },
    "keyboard": {
        "timeout": 30,
        "auto_focus": True
    }
}
```

**Key Functions**:
```python
def load_config() -> Dict:
    """Load configuration from file or return defaults"""
    
def save_config(config: Dict) -> bool:
    """Save configuration to file"""
    
def get_scanner_mode() -> str:
    """Get current scanner mode"""
    
def set_scanner_mode(mode: str) -> bool:
    """Set scanner mode (usb_vendor or keyboard)"""
    
def get_usb_config() -> Dict:
    """Get USB scanner configuration"""
    
def update_usb_config(vid: int = None, pid: int = None, **kwargs) -> bool:
    """Update USB scanner configuration"""
```

### 3. Modified get_nfc_input() Function

**Purpose**: Unified interface for scanner input with mode detection

**Location**: `NfcScan.py` (modified)

**Signature**:
```python
async def get_nfc_input(prompt_message: str) -> str:
    """
    Opens a dialog and waits for scanner input.
    Automatically routes to USB HID or keyboard mode based on configuration.
    
    Args:
        prompt_message: Message displayed in the dialog box
        
    Returns:
        Scanned data as lowercase string
    """
```

**Implementation Strategy**:
- Check scanner mode from configuration
- Route to appropriate implementation (USB HID or keyboard)
- Maintain same async interface for backward compatibility
- Handle errors gracefully with user-friendly messages

### 4. USB HID Input Dialog

**Purpose**: Display scanning status for USB HID mode

**Location**: New function `get_usb_hid_input()` in `NfcScan.py`

**Features**:
- Display connection status
- Show scanning progress
- Handle timeouts
- Provide cancel option
- Display scanned data preview

## Data Models

### Scanner Configuration Model
```python
@dataclass
class ScannerConfig:
    scanner_mode: str  # "usb_vendor" or "keyboard"
    usb_vid: int
    usb_pid: int
    usb_timeout: int
    usb_read_size: int
    usb_encoding: str
    keyboard_timeout: int
    keyboard_auto_focus: bool
```

### USB Device Info Model
```python
@dataclass
class USBDeviceInfo:
    vid: int
    pid: int
    manufacturer: str
    product: str
    serial_number: str
    path: bytes
```

### Scanner Read Result Model
```python
@dataclass
class ScanResult:
    success: bool
    data: Optional[str]
    error: Optional[str]
    timestamp: datetime
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property Reflection

After reviewing all testable properties from the prework analysis, I've identified the following consolidations to eliminate redundancy:

- Properties 3.1 and 3.2 (equipment code processing and user code processing) can be combined into a single property about behavioral equivalence for all code types
- Properties 7.2 and 7.3 (mode switching to keyboard and usb_vendor) can be combined into a single property about correct mode routing
- Properties 1.2 and 1.3 (HID report transmission and parsing) are sequential steps that can be combined into a single end-to-end property

The consolidated properties below provide unique validation value without redundancy.

### Correctness Properties

Property 1: USB device detection with valid credentials
*For any* valid VID and PID combination, attempting to connect to a USB HID device with those credentials should either succeed in establishing a connection or fail with a clear error message indicating the device is not found
**Validates: Requirements 1.1**

Property 2: HID report data extraction
*For any* valid HID report received from the scanner, the system should successfully parse the raw data and extract a non-empty scanned code
**Validates: Requirements 1.2, 1.3**

Property 3: Lowercase conversion consistency
*For any* extracted scanned code string, converting it to lowercase should produce a string where all alphabetic characters are lowercase
**Validates: Requirements 1.4**

Property 4: Configuration file loading
*For any* valid configuration file containing VID and PID values, loading the configuration should result in those exact VID and PID values being used by the scanner
**Validates: Requirements 2.2**

Property 5: Invalid configuration rejection
*For any* invalid VID or PID value (negative, zero, or exceeding valid USB ranges), the configuration system should reject the value and fall back to default values (VID=4602, PID=33282)
**Validates: Requirements 2.4**

Property 6: Runtime configuration persistence
*For any* valid VID and PID values set at runtime, those values should persist in the configuration and be used for subsequent scanner connections
**Validates: Requirements 2.5**

Property 7: Behavioral equivalence for code processing
*For any* valid equipment or user code, processing it through the USB HID scanner should produce the same result (finding the same equipment/user) as processing it through the keyboard-based scanner
**Validates: Requirements 3.1, 3.2**

Property 8: Equipment list update consistency
*For any* successful scan operation (rental or return), the equipment lists should be updated to reflect the new state (available/rented status changes)
**Validates: Requirements 3.4**

Property 9: Async interface compatibility
*For any* call to get_nfc_input(), the function should return an awaitable that resolves to a string, maintaining the same async interface as the previous implementation
**Validates: Requirements 3.5**

Property 10: Disconnection detection
*For any* USB HID scanner that becomes disconnected during operation, the system should detect the disconnection within one read attempt and notify the user
**Validates: Requirements 4.2**

Property 11: Corrupted data rejection
*For any* HID report containing invalid or corrupted data (malformed structure, invalid encoding), the system should reject it and not process it as a valid scan
**Validates: Requirements 4.3**

Property 12: Logging completeness
*For any* USB operation (connect, disconnect, read, error), the system should generate at least one log entry describing the operation and its outcome
**Validates: Requirements 6.3**

Property 13: Error handling coverage
*For any* USB operation that can fail (connect, read, disconnect), the system should catch exceptions and handle them gracefully without crashing
**Validates: Requirements 6.4**

Property 14: Mode routing correctness
*For any* scanner mode setting (usb_vendor or keyboard), calling get_nfc_input() should route to the correct implementation matching that mode
**Validates: Requirements 7.2, 7.3**

Property 15: Runtime mode switching
*For any* mode change operation, the new mode should take effect immediately for the next scan operation without requiring application restart
**Validates: Requirements 7.5**

## Error Handling

### Error Categories

1. **Connection Errors**
   - Device not found (VID/PID mismatch)
   - USB permissions insufficient
   - Device already in use by another process
   - USB subsystem not available

2. **Communication Errors**
   - Read timeout
   - Device disconnected during operation
   - Corrupted HID report data
   - Invalid data encoding

3. **Configuration Errors**
   - Invalid VID/PID values
   - Corrupted configuration file
   - Missing configuration file (handled by defaults)
   - Invalid mode setting

4. **Application Errors**
   - Scanner not initialized
   - Multiple simultaneous scan attempts
   - Cancelled by user

### Error Handling Strategy

**Connection Errors**:
- Display user-friendly error dialog with specific issue
- Provide troubleshooting steps (check USB connection, verify VID/PID, check permissions)
- Offer option to retry or switch to keyboard mode
- Log detailed error information for debugging

**Communication Errors**:
- Detect disconnection on next read attempt
- Display notification to user
- Automatically attempt reconnection
- Fall back to keyboard mode if USB fails repeatedly
- Log all communication errors with timestamps

**Configuration Errors**:
- Validate all configuration values on load
- Use default values for invalid entries
- Display warning for invalid configuration
- Save corrected configuration
- Log configuration issues

**Application Errors**:
- Handle cancellation gracefully (return empty string)
- Prevent concurrent scan operations with locks
- Provide clear feedback for each error type
- Log application-level errors

### Error Messages

All error messages should follow this format:
- **Title**: Brief description of the issue
- **Details**: Specific error information
- **Action**: What the user should do
- **Technical**: Log entry for debugging (not shown to user)

Example:
```
Title: "Scanner Not Found"
Details: "Could not connect to USB scanner (VID: 4602, PID: 33282)"
Action: "Please check that the scanner is connected and try again. You can also use keyboard mode as a fallback."
Technical: "USBHIDScanner.connect() failed: Device not found at VID=0x11FA, PID=0x8202. Error code: -4 (LIBUSB_ERROR_NO_DEVICE)"
```

## Testing Strategy

### Unit Testing

Unit tests will verify individual components in isolation:

**USBHIDScanner Class**:
- Test connection with valid/invalid VID/PID
- Test read operations with mock HID device
- Test disconnection detection
- Test error handling for various failure modes
- Test data parsing and lowercase conversion

**Scanner Configuration**:
- Test loading configuration from file
- Test saving configuration to file
- Test default value handling
- Test validation of VID/PID values
- Test mode switching

**Integration Points**:
- Test get_nfc_input() routing to correct implementation
- Test async interface compatibility
- Test error propagation through layers

### Property-Based Testing

Property-based tests will use the `Hypothesis` library for Python to verify universal properties across many randomly generated inputs.

**Configuration**:
- Each property test should run a minimum of 100 iterations
- Use appropriate strategies for generating test data (integers for VID/PID, strings for codes, etc.)
- Configure timeouts appropriately for async operations

**Test Tagging**:
- Each property-based test must include a comment with the format: `# Feature: usb-hid-vendor-scanner, Property N: <property description>`
- This links the test to the specific correctness property it validates

**Property Test Examples**:

```python
# Feature: usb-hid-vendor-scanner, Property 3: Lowercase conversion consistency
@given(st.text())
@settings(max_examples=100)
def test_lowercase_conversion(code: str):
    result = convert_to_lowercase(code)
    assert result == result.lower()
    assert all(c.islower() or not c.isalpha() for c in result)

# Feature: usb-hid-vendor-scanner, Property 5: Invalid configuration rejection
@given(st.integers(max_value=0) | st.integers(min_value=65536))
@settings(max_examples=100)
def test_invalid_vid_rejection(invalid_vid: int):
    config = ScannerConfig()
    config.set_vid(invalid_vid)
    assert config.get_vid() == 4602  # Default value
```

**Mock USB Devices**:
- Create mock HID device class for testing without physical hardware
- Simulate various device behaviors (successful reads, timeouts, disconnections)
- Generate random HID report data for parsing tests

**Async Testing**:
- Use pytest-asyncio for async test support
- Test timeout behavior with controlled delays
- Test cancellation handling

### Integration Testing

Integration tests will verify the complete workflow:

- Test end-to-end scanning workflow with mock USB device
- Test mode switching between USB and keyboard
- Test configuration persistence across application restarts
- Test error recovery scenarios
- Test backward compatibility with existing rental workflows

### Manual Testing Checklist

Before deployment, manually verify:
- [ ] Physical scanner connects successfully
- [ ] Scanning equipment codes works correctly
- [ ] Scanning user codes works correctly
- [ ] Error messages are clear and helpful
- [ ] Configuration utility works correctly
- [ ] Mode switching works without restart
- [ ] Keyboard mode still works as fallback
- [ ] All dialogs display correctly
- [ ] Timeout behavior is appropriate
- [ ] Disconnection is detected promptly

## Implementation Notes

### USB HID Library Selection

**Chosen Library**: `hidapi` (via `hid` Python package)

**Rationale**:
- Cross-platform support (Windows, Linux, macOS)
- Well-maintained and widely used
- Simple API for basic HID operations
- Good documentation and community support
- No complex dependencies

**Installation**:
```bash
pip install hidapi
```

### Data Format

**HID Report Structure**:
The scanner sends data in HID reports. The exact format depends on the scanner model, but typically:
- Report ID (1 byte)
- Data length (1 byte)
- Actual data (variable length, typically up to 62 bytes)
- Padding (if needed)

**Data Extraction**:
1. Read raw bytes from HID device
2. Extract data portion from report structure
3. Decode bytes to string using UTF-8
4. Strip whitespace and control characters
5. Convert to lowercase

### Configuration File Location

**Path**: `scanner_config.json` in the application root directory

**Format**: JSON for easy editing and parsing

**Permissions**: Read/write for application user

### Backward Compatibility

To ensure smooth transition:
1. Default to USB vendor mode but allow keyboard fallback
2. Preserve exact same async interface for get_nfc_input()
3. Maintain same dialog appearance and behavior
4. Keep same timeout values (30 seconds default)
5. Return data in same format (lowercase string)

### Performance Considerations

- USB read operations are blocking, so run in executor to avoid blocking async event loop
- Cache USB device connection to avoid repeated enumeration
- Implement connection pooling if multiple scanners needed in future
- Use appropriate read buffer size (64 bytes typical for HID)
- Minimize logging in hot path (only log errors and important events)

### Security Considerations

- Validate all data received from USB device
- Sanitize scanned codes before database queries
- Limit maximum data length to prevent buffer issues
- Use parameterized queries to prevent SQL injection
- Log all scanner access for audit trail
- Require appropriate USB permissions (may need udev rules on Linux)

## Dependencies

### New Dependencies
- `hidapi` (>= 0.14.0) - USB HID communication library

### Existing Dependencies
- `nicegui` - UI framework (already in use)
- `asyncio` - Async operations (Python standard library)
- `sqlalchemy` - Database ORM (already in use)
- `json` - Configuration file handling (Python standard library)

### Platform-Specific Requirements

**Windows**:
- No additional requirements (hidapi uses Windows HID API)

**Linux**:
- May require udev rules for USB device access
- Example udev rule for scanner:
  ```
  SUBSYSTEM=="usb", ATTRS{idVendor}=="11fa", ATTRS{idProduct}=="8202", MODE="0666"
  ```

**macOS**:
- No additional requirements (hidapi uses IOKit)

## Migration Path

### Phase 1: Implementation
1. Implement USBHIDScanner class
2. Implement configuration system
3. Add USB HID mode to get_nfc_input()
4. Implement error handling
5. Add logging

### Phase 2: Testing
1. Unit tests for all components
2. Property-based tests for correctness properties
3. Integration tests with mock devices
4. Manual testing with physical scanner

### Phase 3: Deployment
1. Deploy with keyboard mode as default initially
2. Test USB mode with physical scanner
3. Switch default to USB mode
4. Monitor for issues
5. Keep keyboard mode available as fallback

### Phase 4: Cleanup
1. Remove keyboard mode if USB mode is stable (optional)
2. Update documentation
3. Remove legacy code (optional)

## Future Enhancements

Potential future improvements:
- Support for multiple scanners simultaneously
- Scanner device auto-detection (enumerate and select)
- Configuration UI for VID/PID settings
- Scanner firmware version detection
- Advanced HID report parsing for different scanner models
- Barcode format detection and validation
- Scanner health monitoring and diagnostics
