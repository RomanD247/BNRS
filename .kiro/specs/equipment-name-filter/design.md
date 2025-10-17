# Equipment Name Filter Design

## Overview

This design implements a text-based equipment name filter that works alongside the existing equipment type filter. The solution extends the current filtering system in `main.py` by adding a text input field and modifying the filtering logic to support both type and name-based filtering simultaneously.

## Architecture

The implementation follows the existing pattern in the application:
- **State Management**: Extend the existing `State` class to include name filter state
- **UI Components**: Add text input field to the existing filter row
- **Filtering Logic**: Create new filtering functions that support both type and name filtering
- **Data Flow**: Maintain the current pattern of updating state and then refreshing UI

## Components and Interfaces

### 1. State Class Extensions

```python
class State:
    # Existing properties...
    def __init__(self):
        # Existing initialization...
        self.name_filter = ""  # New property for name filter text
    
    def set_name_filter(self, filter_text: str):
        """Set the name filter and update equipment lists"""
        self.name_filter = filter_text.lower().strip()
```

### 2. New Filtering Functions

```python
def filter_equipment_by_name(equipment_list, name_filter):
    """Filter equipment list by name containing the filter text"""
    if not name_filter:
        return equipment_list
    return [eq for eq in equipment_list if name_filter in eq.name.lower()]

def apply_combined_filters():
    """Apply both type and name filters to equipment lists"""
    # Get base equipment lists (all or filtered by type)
    if state.selected_etype_id is not None:
        available = get_available_equipment_by_type(db, state.selected_etype_id)
        rented = get_active_rentals_by_equipment_type(db, state.selected_etype_id)
    else:
        available = get_available_equipment(db)
        rented = get_active_rentals(db)
    
    # Apply name filter if active
    if state.name_filter:
        available = filter_equipment_by_name(available, state.name_filter)
        rented = filter_rentals_by_equipment_name(rented, state.name_filter)
    
    # Update state
    state.available_equipment = available
    state.rented_equipment = rented
```

### 3. UI Component Integration

The name filter input will be added to the existing filter row:

```python
# In main() function, modify the filter row:
with ui.row().classes('items-center'):
    ui.label('Filter by Equipment Type:').classes('text-h6')
    # Existing type filter...
    
    ui.label('Filter by Name:').classes('text-h6').style('margin-left: 20px')
    name_filter_input = ui.input(
        label='Equipment Name',
        placeholder='Type equipment name...',
        on_change=on_name_filter_change
    ).style('width: 200px; margin-right: 10px')
```

## Data Models

No changes to existing data models are required. The filtering operates on the existing Equipment and Rental models.

## Error Handling

- **Empty Filter**: When name filter is empty, show all equipment (respecting type filter)
- **No Matches**: When no equipment matches the filter criteria, display empty lists with appropriate messaging
- **Invalid Input**: Handle special characters gracefully by treating them as literal search text

## Testing Strategy

### Unit Tests
- Test `filter_equipment_by_name()` with various input scenarios
- Test `apply_combined_filters()` with different filter combinations
- Test case-insensitive matching

### Integration Tests
- Test UI updates when filters change
- Test filter persistence during equipment rental/return operations
- Test filter reset functionality

### User Acceptance Tests
- Verify real-time filtering as user types
- Verify combined type + name filtering works correctly
- Verify filter clearing restores appropriate equipment lists

## Implementation Details

### Filter Update Flow
1. User types in name filter input
2. `on_name_filter_change()` is triggered
3. State is updated with new filter text
4. `apply_combined_filters()` is called
5. Equipment lists are filtered and state is updated
6. `update_lists()` refreshes the UI containers

### Performance Considerations
- Filtering is performed on already-loaded data (no additional database queries)
- Text matching uses simple string containment (case-insensitive)
- Real-time filtering may trigger on every keystroke - consider debouncing if performance issues arise

### Backward Compatibility
- Existing type filter functionality remains unchanged
- All existing functions continue to work as before
- New functionality is additive only

## User Experience

### Visual Design
- Name filter input positioned next to type filter for logical grouping
- Consistent styling with existing UI elements
- Clear placeholder text to indicate purpose
- Optional: Add clear button (X) when text is entered

### Interaction Flow
1. User can use either filter independently
2. User can combine both filters for precise searching
3. Filters persist during normal operations (rent/return)
4. Filters are cleared by the existing "reset_filter()" function or manually by user

### Accessibility
- Proper labels for screen readers
- Keyboard navigation support
- Clear visual indication of active filters