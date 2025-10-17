# Implementation Plan

- [x] 1. Create duration utility functions





  - Create helper functions for duration calculation and formatting
  - Implement function to calculate both display string and numerical sort value
  - Add special case handling for active rentals and never-rented equipment
  - _Requirements: 1.3, 2.1, 2.2, 2.3_

- [x] 2. Update CRUD functions to include numerical duration data





  - [x] 2.1 Update get_user_rental_statistics function


    - Modify function to return both duration display string and duration_seconds
    - Ensure backward compatibility with existing data structure
    - _Requirements: 1.1, 1.2, 3.2_

  - [x] 2.2 Update get_equipment_type_statistics function


    - Add duration_seconds field to equipment type statistics data
    - Maintain existing duration display format
    - _Requirements: 1.1, 1.2, 3.3_

  - [x] 2.3 Update get_equipment_name_statistics function


    - Include numerical duration value in equipment name statistics
    - Handle special cases for never-rented equipment
    - _Requirements: 1.1, 1.2, 3.4_

  - [x] 2.4 Update get_department_rental_statistics function


    - Add duration_seconds to department statistics data structure
    - Ensure consistent duration calculation across all functions
    - _Requirements: 1.1, 1.2, 3.5_

- [x] 3. Update rental history duration data preparation










  - Modify show_rental_history function to include duration_seconds in data
  - Handle active rentals with appropriate sort values
  - Ensure special case handling for ongoing rentals
  - _Requirements: 1.1, 1.2, 1.5, 3.1_
-

- [x] 4. Update UI table column definitions for proper sorting






 

  - [x] 4.1 Update Rental History dialog table configuration


    - Modify duration column to use duration_seconds for sorting
    - Maintain duration field for display
    - _Requirements: 1.1, 1.2, 3.1_

  - [x] 4.2 Update User Rental Statistics dialog table configuration


    - Configure duration column to sort by numerical value
    - Preserve human-readable display format
    - _Requirements: 1.1, 1.2, 3.2_

  - [x] 4.3 Update Equipment Type Statistics dialog table configuration


    - Implement numerical sorting for duration column
    - Ensure consistent behavior with other dialogs
    - _Requirements: 1.1, 1.2, 3.3_

  - [x] 4.4 Update Equipment Name Statistics dialog table configuration


    - Add numerical sorting capability to duration column
    - Maintain display format consistency
    - _Requirements: 1.1, 1.2, 3.4_

  - [x] 4.5 Update Department Rental Statistics dialog table configuration


    - Configure duration column for proper numerical sorting
    - Ensure special case handling in UI
    - _Requirements: 1.1, 1.2, 3.5_

- [x] 5. Test and validate duration sorting functionality





  - [x] 5.1 Test sorting in Rental History dialog


    - Verify ascending and descending sort orders work correctly
    - Test with mixed data including active rentals
    - _Requirements: 1.1, 1.2, 1.5_

  - [x] 5.2 Test sorting in all statistics reports


    - Validate duration sorting in User, Equipment Type, Equipment Name, and Department reports
    - Ensure consistent sorting behavior across all dialogs
    - _Requirements: 1.1, 1.2, 3.2, 3.3, 3.4, 3.5_

  - [x] 5.3 Verify display format consistency


    - Confirm duration display format remains unchanged
    - Test special cases (active rentals, never rented, zero duration)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_