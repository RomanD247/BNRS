# Implementation Plan

- [x] 1. Set up USB HID infrastructure
  - Install hidapi library and verify it works on the target platform
  - Create basic project structure for new scanner modules
  - _Requirements: 6.1_

- [x] 1.1 Install and verify hidapi library
  - Add hidapi to requirements.txt
  - Test basic HID device enumeration
  - _Requirements: 6.1_

- [x] 1.2 Create scanner module structure
  - Create usb_hid_scanner.py file
  - Create scanner_config.py file
  - Set up module imports
  - _Requirements: 6.2_

- [x] 2. Implement scanner configuration system
  - Create configuration data structures
  - Implement configuration file loading and saving
  - Implement validation for VID/PID values
  - Add default configuration values
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 2.1 Create configuration data structures
  - Define ScannerConfig dataclass
  - Define configuration JSON schema
  - _Requirements: 2.1_

- [x] 2.2 Implement configuration file operations
  - Implement load_config() function
  - Implement save_config() function
  - Handle missing configuration file with defaults
  - _Requirements: 2.2, 2.3_

- [ ]* 2.3 Write property test for configuration file loading
  - **Property 4: Configuration file loading**
  - **Validates: Requirements 2.2**

- [x] 2.4 Implement VID/PID validation
  - Validate VID/PID ranges (1-65535)
  - Reject invalid values and use defaults
  - _Requirements: 2.4_

- [ ]* 2.5 Write property test for invalid configuration rejection
  - **Property 5: Invalid configuration rejection**
  - **Validates: Requirements 2.4**

- [x] 2.6 Implement runtime configuration updates
  - Implement get_scanner_mode() function
  - Implement set_scanner_mode() function
  - Implement update_usb_config() function
  - _Requirements: 2.5_

- [ ]* 2.7 Write property test for runtime configuration persistence
  - **Property 6: Runtime configuration persistence**
  - **Validates: Requirements 2.5**

- [x] 3. Implement USBHIDScanner class
  - Create USBHIDScanner class with initialization
  - Implement device connection and disconnection
  - Implement data reading from HID device
  - Implement data parsing and conversion
  - Add error handling for USB operations
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.1, 4.2, 4.3, 6.4_

- [x] 3.1 Create USBHIDScanner class structure
  - Define __init__ method with VID/PID parameters
  - Add instance variables for device handle and state
  - _Requirements: 1.1_

- [x] 3.2 Implement device connection
  - Implement connect() method using hidapi
  - Handle device not found errors
  - Implement is_connected() method
  - _Requirements: 1.1, 4.1_

- [ ]* 3.3 Write property test for USB device detection
  - **Property 1: USB device detection with valid credentials**
  - **Validates: Requirements 1.1**

- [x] 3.4 Implement device disconnection
  - Implement disconnect() method
  - Clean up device resources properly
  - _Requirements: 1.1_

- [x] 3.5 Implement data reading
  - Implement read_scan() method with timeout
  - Handle read timeouts appropriately
  - Detect device disconnection during read
  - _Requirements: 1.2, 4.2, 4.4_

- [ ]* 3.6 Write property test for disconnection detection
  - **Property 10: Disconnection detection**
  - **Validates: Requirements 4.2**

- [x] 3.7 Implement HID report parsing
  - Parse HID report structure
  - Extract data from report
  - Decode bytes to string using UTF-8
  - Handle corrupted or invalid data
  - _Requirements: 1.3, 4.3_

- [ ]* 3.8 Write property test for HID report data extraction
  - **Property 2: HID report data extraction**
  - **Validates: Requirements 1.2, 1.3**

- [ ]* 3.9 Write property test for corrupted data rejection
  - **Property 11: Corrupted data rejection**
  - **Validates: Requirements 4.3**

- [x] 3.10 Implement lowercase conversion
  - Convert extracted code to lowercase
  - Strip whitespace and control characters
  - _Requirements: 1.4_

- [ ]* 3.11 Write property test for lowercase conversion
  - **Property 3: Lowercase conversion consistency**
  - **Validates: Requirements 1.4**

- [x] 3.12 Add error handling for USB operations
  - Wrap all USB operations in try-except blocks
  - Handle specific USB error codes
  - Provide meaningful error messages
  - _Requirements: 4.1, 4.2, 4.3, 4.5, 6.4_

- [ ]* 3.13 Write property test for error handling coverage
  - **Property 13: Error handling coverage**
  - **Validates: Requirements 6.4**

- [x] 3.14 Implement device enumeration utility
  - Implement list_devices() static method
  - Return list of available HID devices
  - _Requirements: 1.1_

- [x] 4. Implement logging system
  - Add logging for all USB operations
  - Log connection/disconnection events
  - Log read operations and errors
  - Log configuration changes
  - _Requirements: 6.3_

- [x] 4.1 Set up logging configuration
  - Configure Python logging module
  - Set appropriate log levels
  - Define log format
  - _Requirements: 6.3_

- [x] 4.2 Add logging to USBHIDScanner
  - Log connect/disconnect operations
  - Log read operations
  - Log all errors with details
  - _Requirements: 6.3_

- [ ]* 4.3 Write property test for logging completeness
  - **Property 12: Logging completeness**
  - **Validates: Requirements 6.3**

- [x] 4.4 Add logging to configuration system
  - Log configuration loads and saves
  - Log validation failures
  - Log mode changes
  - _Requirements: 6.3_

- [x] 5. Modify get_nfc_input() for USB HID support
  - Add mode detection logic
  - Implement USB HID input dialog
  - Route to appropriate implementation based on mode
  - Maintain async interface compatibility
  - _Requirements: 3.5, 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 5.1 Create get_usb_hid_input() function
  - Create new async function for USB HID input
  - Display dialog with connection status
  - Show scanning progress
  - Handle timeouts and cancellation
  - _Requirements: 1.1, 1.2, 5.2, 5.3, 5.4, 5.5_

- [x] 5.2 Modify get_nfc_input() for mode routing
  - Load scanner mode from configuration
  - Route to USB HID or keyboard implementation
  - Maintain same function signature
  - Preserve async interface
  - _Requirements: 3.5, 7.2, 7.3_

- [x] 5.3 Write property test for async interface compatibility
  - **Property 9: Async interface compatibility**
  - **Validates: Requirements 3.5**

- [x] 5.4 Write property test for mode routing correctness
  - **Property 14: Mode routing correctness**
  - **Validates: Requirements 7.2, 7.3**

- [x] 5.5 Write property test for runtime mode switching
  - **Property 15: Runtime mode switching**
  - **Validates: Requirements 7.5**

- [x] 6. Implement error dialogs and user feedback
  - Create error dialog for connection failures
  - Create error dialog for read failures
  - Add troubleshooting information to dialogs
  - Implement user-friendly error messages
  - _Requirements: 1.5, 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 6.1 Create connection error dialog
  - Display device not found errors
  - Show VID/PID information
  - Provide troubleshooting steps
  - Offer retry and fallback options
  - _Requirements: 1.5, 4.1_

- [x] 6.2 Create communication error dialogs
  - Handle timeout errors
  - Handle disconnection errors
  - Handle corrupted data errors
  - Provide clear user feedback
  - _Requirements: 4.2, 4.3, 4.4_

- [x] 6.3 Create permission error dialog
  - Detect permission issues
  - Provide platform-specific instructions
  - _Requirements: 4.5_

- [x] 7. Integrate USB scanner with rental workflows
  - Test integration with nfc_equipment_rental_workflow
  - Verify equipment code scanning works
  - Verify user code scanning works
  - Ensure equipment lists update correctly
  - _Requirements: 3.1, 3.2, 3.4_

- [x] 7.1 Test equipment code scanning
  - Scan equipment codes using USB HID scanner
  - Verify equipment is found correctly
  - Compare results with keyboard mode
  - _Requirements: 3.1_

- [x] 7.2 Test user code scanning
  - Scan user codes using USB HID scanner
  - Verify users are found correctly
  - Compare results with keyboard mode
  - _Requirements: 3.2_

- [ ]* 7.3 Write property test for behavioral equivalence
  - **Property 7: Behavioral equivalence for code processing**
  - **Validates: Requirements 3.1, 3.2**

- [x] 7.4 Test equipment list updates
  - Verify available equipment list updates after rental
  - Verify rented equipment list updates after rental
  - Verify lists update after return
  - _Requirements: 3.4_

- [ ]* 7.5 Write property test for equipment list updates
  - **Property 8: Equipment list update consistency**
  - **Validates: Requirements 3.4**

- [x] 8. Create configuration utility
  - Create command-line utility for configuration
  - Add commands for viewing current configuration
  - Add commands for changing VID/PID
  - Add commands for switching modes
  - _Requirements: 2.5, 7.1, 7.2, 7.3_

- [x] 8.1 Create configuration utility script
  - Create configure_scanner.py file
  - Add argument parsing
  - Implement status display command
  - _Requirements: 2.5_

- [x] 8.2 Implement configuration commands
  - Add command to set VID/PID
  - Add command to set scanner mode
  - Add command to reset to defaults
  - _Requirements: 2.5, 7.1_

- [x] 8.3 Add configuration export/import
  - Implement configuration export to file
  - Implement configuration import from file
  - _Requirements: 2.5_

- [ ] 9. Update documentation
  - Update README with USB scanner setup instructions
  - Document VID/PID configuration
  - Document mode switching
  - Add troubleshooting guide
  - _Requirements: All_

- [ ] 9.1 Create USB scanner setup guide
  - Document hidapi installation
  - Document VID/PID configuration
  - Document platform-specific requirements
  - _Requirements: 1.1, 2.1, 2.2_

- [ ] 9.2 Create troubleshooting guide
  - Document common connection issues
  - Document permission issues
  - Document fallback to keyboard mode
  - _Requirements: 4.1, 4.2, 4.5_

- [ ] 9.3 Update user documentation
  - Document scanning workflow
  - Document error messages
  - Document configuration utility usage
  - _Requirements: All_

- [ ] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
