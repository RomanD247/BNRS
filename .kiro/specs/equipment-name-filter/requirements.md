# Equipment Name Filter Requirements

## Introduction

This feature adds text-based filtering capability to the main equipment rental interface, allowing users to search for equipment by name in addition to the existing equipment type filter.

## Glossary

- **Equipment_Name_Filter**: A text input field that filters equipment by name containing the entered text
- **Main_Interface**: The primary equipment rental interface showing available and rented equipment lists
- **Filter_System**: The combined filtering mechanism including both equipment type and name filters

## Requirements

### Requirement 1

**User Story:** As a user, I want to filter equipment by name so that I can quickly find specific equipment without scrolling through long lists

#### Acceptance Criteria

1. WHEN the user types text in the equipment name filter field, THE Main_Interface SHALL display only equipment whose names contain the entered text (case-insensitive)
2. WHILE the name filter is active, THE Main_Interface SHALL update both available and rented equipment lists to show only matching equipment
3. WHEN the user clears the name filter field, THE Main_Interface SHALL restore the full equipment lists (respecting any active type filter)
4. WHERE both name and type filters are active, THE Main_Interface SHALL show equipment that matches both criteria
5. WHEN the user types in the name filter, THE Main_Interface SHALL update the lists in real-time without requiring a button press

### Requirement 2

**User Story:** As a user, I want the name filter to work together with the existing type filter so that I can use both filtering methods simultaneously

#### Acceptance Criteria

1. WHEN both name and type filters are applied, THE Filter_System SHALL show equipment that matches both the selected type AND contains the name text
2. WHEN the user changes the type filter while name filter is active, THE Main_Interface SHALL maintain the name filter and apply both filters
3. WHEN the user changes the name filter while type filter is active, THE Main_Interface SHALL maintain the type filter and apply both filters
4. WHEN either filter is cleared, THE Main_Interface SHALL continue applying the remaining active filter

### Requirement 3

**User Story:** As a user, I want the name filter to be visually integrated with the existing filter controls so that the interface remains intuitive

#### Acceptance Criteria

1. THE Equipment_Name_Filter SHALL be positioned near the existing equipment type filter
2. THE Equipment_Name_Filter SHALL have a clear label indicating its purpose
3. THE Equipment_Name_Filter SHALL provide visual feedback when active (e.g., highlighting, clear button)
4. THE Equipment_Name_Filter SHALL maintain consistent styling with the existing interface elements