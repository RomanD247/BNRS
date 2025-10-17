# Implementation Plan

- [x] 1. Extend State class to support name filtering





  - Add name_filter property to State class initialization
  - Create set_name_filter method to update the filter state
  - _Requirements: 1.1, 1.3_

- [x] 2. Implement equipment name filtering functions





  - [x] 2.1 Create filter_equipment_by_name function


    - Write function to filter equipment list by name containing filter text (case-insensitive)
    - Handle empty filter text by returning unfiltered list
    - _Requirements: 1.1, 1.3_
  
  - [x] 2.2 Create filter_rentals_by_equipment_name function


    - Write function to filter rental list by equipment name containing filter text
    - Access equipment name through rental.equipment.name relationship
    - _Requirements: 1.1, 1.2_
  
  - [x] 2.3 Create apply_combined_filters function


    - Implement logic to apply both type and name filters simultaneously
    - Get base equipment lists (all or filtered by type)
    - Apply name filter if active and update state
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Add name filter UI component to main interface





  - [x] 3.1 Add name filter input field to filter row


    - Position name filter input next to existing type filter
    - Set appropriate styling and placeholder text
    - Add proper labeling for accessibility
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [x] 3.2 Implement on_name_filter_change callback


    - Create callback function to handle name filter input changes
    - Update state and trigger combined filtering
    - Ensure real-time filtering as user types
    - _Requirements: 1.5, 2.2, 2.3_

- [x] 4. Integrate name filter with existing filter system





  - [x] 4.1 Modify filter_by_etype function


    - Update existing type filter function to work with combined filtering
    - Ensure name filter is preserved when type filter changes
    - _Requirements: 2.1, 2.2_
  
  - [x] 4.2 Update reset_filter function


    - Clear name filter when reset is triggered
    - Reset name filter input field visually
    - Ensure both filters are cleared together
    - _Requirements: 1.3, 2.4_
  

  - [x] 4.3 Modify equipment rental and return workflows

    - Ensure filters are maintained during rent/return operations
    - Update filter application after equipment status changes
    - _Requirements: 1.2, 2.2_

- [x] 5. Update equipment list refresh logic





  - [x] 5.1 Modify update_lists function


    - Ensure UI updates reflect current filter state
    - Maintain filter application when lists are refreshed
    - _Requirements: 1.1, 1.2_
  
  - [x] 5.2 Update full_refresh function


    - Apply active filters after full data refresh
    - Preserve filter state during refresh operations
    - _Requirements: 1.2, 2.4_