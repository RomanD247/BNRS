# Requirements Document

## Introduction

This feature addresses the incorrect sorting behavior of the Duration column in various UI dialogs within the rental system. Currently, duration values like "185:45:12" (185 days, 45 hours, 12 minutes) are sorted lexicographically as strings, causing "45:41:12" to appear before "185:45:12" when sorting in descending order. The system needs to implement proper numerical sorting for duration values while maintaining human-readable display format.

## Glossary

- **Duration Column**: A table column displaying rental duration in the format "days:hours:minutes" (e.g., "185:45:12")
- **Rental History Dialog**: UI dialog showing complete rental history with sortable columns
- **Reports Dialogs**: UI dialogs showing various rental statistics (User Report, Equipment Type Report, Equipment Name Report, Department Report)
- **Lexicographic Sorting**: String-based sorting that compares characters position by position (causing "45" > "185")
- **Numerical Sorting**: Sorting based on actual numerical values (causing 185 > 45)
- **Duration Value**: Time span represented as total seconds or structured time components

## Requirements

### Requirement 1

**User Story:** As a system user, I want the Duration column to sort correctly by actual time duration, so that longer rental periods appear first when sorting in descending order.

#### Acceptance Criteria

1. WHEN the user clicks on the Duration column header to sort in descending order, THE system SHALL display rentals with longer actual durations first
2. WHEN the user clicks on the Duration column header to sort in ascending order, THE system SHALL display rentals with shorter actual durations first
3. WHILE maintaining the current display format "days:hours:minutes", THE system SHALL perform sorting based on numerical duration values
4. THE system SHALL apply correct duration sorting to all dialogs containing Duration columns
5. WHERE duration values are "Active rental" or "Never Rented", THE system SHALL handle these special cases appropriately in sorting

### Requirement 2

**User Story:** As a system user, I want duration display to remain human-readable and consistent, so that I can easily understand rental time periods.

#### Acceptance Criteria

1. THE system SHALL maintain the current "days:hours:minutes" display format for duration values
2. THE system SHALL display "Active rental" for ongoing rentals in the Duration column
3. THE system SHALL display appropriate text for equipment that has never been rented
4. THE system SHALL ensure duration display consistency across all reports and dialogs
5. WHEN duration is zero or very short, THE system SHALL display appropriate minimal duration representation

### Requirement 3

**User Story:** As a system user, I want the sorting fix to apply to all relevant dialogs, so that duration sorting works consistently throughout the application.

#### Acceptance Criteria

1. THE system SHALL implement correct duration sorting in the Rental History dialog
2. THE system SHALL implement correct duration sorting in the User Rental Statistics report
3. THE system SHALL implement correct duration sorting in the Equipment Type Statistics report  
4. THE system SHALL implement correct duration sorting in the Equipment Name Statistics report
5. THE system SHALL implement correct duration sorting in the Department Rental Statistics report