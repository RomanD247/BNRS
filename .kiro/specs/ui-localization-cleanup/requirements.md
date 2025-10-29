# Requirements Document

## Introduction

This feature addresses UI improvements for the Data Matrix codes generation dialog by removing redundant status text under buttons and translating all Russian text to English for better internationalization.

## Glossary

- **CodesGenerationDialog**: The dialog window class that manages Data Matrix code operations in the main application
- **Status Label**: The UI label element that displays operation status text under the action buttons
- **UI Notify**: The notification system that shows temporary messages to users
- **MatrixCode Module**: The backend module containing update_user_codes() and update_equipment_codes() functions

## Requirements

### Requirement 1

**User Story:** As a user, I want cleaner UI without redundant status text under buttons, so that the interface is less cluttered and more professional.

#### Acceptance Criteria

1. WHEN user clicks "Update Users Codes" button, THE CodesGenerationDialog SHALL display notifications only through ui.notify
2. WHEN user clicks "Update Equipments Codes" button, THE CodesGenerationDialog SHALL display notifications only through ui.notify  
3. THE CodesGenerationDialog SHALL NOT display status text in the status label under the buttons after code update operations
4. THE CodesGenerationDialog SHALL maintain all existing functionality for code generation and updates

### Requirement 2

**User Story:** As a user, I want all interface text in English, so that the application is accessible to English-speaking users.

#### Acceptance Criteria

1. THE CodesGenerationDialog SHALL display all button labels in English
2. THE CodesGenerationDialog SHALL display all notification messages in English
3. THE CodesGenerationDialog SHALL display all status messages in English
4. THE MatrixCode Module SHALL return success and error messages in English
5. THE CodesGenerationDialog SHALL display all instructional text in English