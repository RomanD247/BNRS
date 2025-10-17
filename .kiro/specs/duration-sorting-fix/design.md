# Design Document

## Overview

The current duration sorting issue stems from treating duration values as strings rather than numerical values. The solution involves adding a numerical sort key alongside the human-readable duration display format. This approach maintains backward compatibility while enabling proper numerical sorting.

## Architecture

The fix will be implemented at two levels:

1. **Data Layer (crud.py)**: Modify functions that generate duration data to include both display string and numerical sort value
2. **UI Layer (gui_reports.py)**: Update table column definitions to use numerical sorting while displaying human-readable format

## Components and Interfaces

### 1. Duration Data Structure Enhancement

**Current Format:**
```python
{
    "duration": "185:45:12"  # String only
}
```

**Enhanced Format:**
```python
{
    "duration": "185:45:12",           # Human-readable display
    "duration_seconds": 16041912       # Numerical sort key (total seconds)
}
```

### 2. CRUD Functions Modification

The following functions need to be updated to include numerical duration values:

- `get_user_rental_statistics()` - User report duration data
- `get_equipment_type_statistics()` - Equipment type report duration data  
- `get_equipment_name_statistics()` - Equipment name report duration data
- `get_department_rental_statistics()` - Department report duration data
- `show_rental_history()` data preparation - Rental history duration data

### 3. UI Table Column Configuration

**Current Column Definition:**
```python
{'name': 'duration', 'label': 'Duration', 'field': 'duration', 'sortable': True, 'align': 'left'}
```

**Enhanced Column Definition:**
```python
{
    'name': 'duration', 
    'label': 'Duration', 
    'field': 'duration',           # Display field (human-readable)
    'sortable': True, 
    'align': 'left',
    'sort': 'duration_seconds'     # Sort field (numerical)
}
```

## Data Models

### Duration Calculation Logic

```python
def calculate_duration_data(start_time, end_time):
    """
    Calculate both display string and numerical value for duration
    
    Returns:
        tuple: (display_string, total_seconds)
    """
    if not end_time:
        return "Active rental", float('inf')  # Active rentals sort to top
    
    duration = end_time - start_time
    total_seconds = duration.total_seconds()
    
    days = duration.days
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    
    display_string = f"{days}:{hours:02}:{minutes:02}"
    
    return display_string, total_seconds
```

### Special Case Handling

1. **Active Rentals**: 
   - Display: "Active rental"
   - Sort value: `float('inf')` (always sorts to top in descending order)

2. **Never Rented Equipment**:
   - Display: "Never Rented" or "0:00:00"
   - Sort value: `0` (always sorts to bottom in descending order)

3. **Zero Duration Rentals**:
   - Display: "0:00:00"
   - Sort value: `0`

## Error Handling

### Data Validation
- Validate that start_time and end_time are proper datetime objects
- Handle None values gracefully
- Ensure total_seconds calculation doesn't result in negative values

### UI Error Handling
- Fallback to string sorting if numerical sort field is missing
- Display appropriate error messages if duration calculation fails
- Maintain table functionality even with malformed duration data

## Testing Strategy

### Unit Tests
1. **Duration Calculation Tests**
   - Test various duration ranges (minutes, hours, days, months)
   - Test edge cases (zero duration, very long durations)
   - Test special cases (active rentals, never rented)

2. **Data Generation Tests**
   - Verify CRUD functions return both display and sort values
   - Test date filtering with duration calculations
   - Validate data structure consistency

### Integration Tests
1. **UI Sorting Tests**
   - Test ascending and descending sort orders
   - Verify mixed data (active, completed, never rented) sorts correctly
   - Test sorting with filtered data

2. **Cross-Dialog Consistency Tests**
   - Ensure all dialogs with duration columns sort identically
   - Verify export functionality includes correct duration values

### Manual Testing Scenarios
1. Create test data with various duration ranges
2. Test sorting in each dialog (Rental History, User Report, etc.)
3. Verify display format remains unchanged
4. Test edge cases (all active rentals, all zero durations)

## Implementation Approach

### Phase 1: Core Duration Utilities
1. Create utility functions for duration calculation
2. Add helper functions for special case handling
3. Implement comprehensive unit tests

### Phase 2: CRUD Layer Updates
1. Update each statistics function to include duration_seconds
2. Modify rental history data preparation
3. Ensure backward compatibility

### Phase 3: UI Layer Updates
1. Update table column definitions in all dialogs
2. Test sorting functionality
3. Verify display format consistency

### Phase 4: Validation and Testing
1. Comprehensive testing across all dialogs
2. Performance validation with large datasets
3. User acceptance testing

## Performance Considerations

- Duration calculations are performed once during data retrieval
- Numerical sorting is more efficient than string sorting
- Memory overhead is minimal (one additional integer per row)
- No impact on database queries (calculations done in Python)

## Backward Compatibility

- Existing duration display format remains unchanged
- API contracts maintained (additional fields are additive)
- No breaking changes to existing functionality
- Graceful degradation if sort field is missing