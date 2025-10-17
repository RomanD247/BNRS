"""
Duration utility functions for the rental system.

This module provides helper functions for duration calculation and formatting
to support proper numerical sorting while maintaining human-readable display format.

The main purpose is to fix the duration column sorting issue where duration values
like "185:45:12" were being sorted lexicographically as strings, causing incorrect
sort order. These utilities provide both human-readable display strings and 
numerical sort values.

Example usage:
    from duration_utils import calculate_duration_data
    
    # For completed rentals
    display, seconds = calculate_duration_data(start_time, end_time)
    
    # For active rentals  
    display, seconds = calculate_duration_data(start_time, None)
    # Returns: ("Active rental", float('inf'))
    
    # Create standardized duration data
    duration_data = create_duration_dict(display, seconds)
    # Returns: {'duration': '2:15:30', 'duration_seconds': 95730.0}
"""

import datetime
from typing import Tuple, Optional


def calculate_duration_data(start_time: Optional[datetime.datetime], 
                          end_time: Optional[datetime.datetime]) -> Tuple[str, float]:
    """
    Calculate both display string and numerical value for duration.
    
    Args:
        start_time: Rental start datetime
        end_time: Rental end datetime (None for active rentals)
    
    Returns:
        tuple: (display_string, total_seconds)
            - display_string: Human-readable format "days:hours:minutes"
            - total_seconds: Numerical value for sorting (float('inf') for active rentals)
    """
    # Handle never rented (no start time)
    if not start_time:
        return "Never Rented", 0.0
    
    # Handle active rentals (no end time but has start time)
    if not end_time:
        return "Active rental", float('inf')
    
    # Calculate duration
    duration = end_time - start_time
    total_seconds = duration.total_seconds()
    
    # Handle negative durations (data integrity issue)
    if total_seconds < 0:
        return "0:00:00", 0.0
    
    # Format display string using existing pattern
    days = duration.days
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    
    display_string = f"{days}:{hours:02}:{minutes:02}"
    
    return display_string, total_seconds


def calculate_current_rental_duration_data(start_time: datetime.datetime) -> Tuple[str, float]:
    """
    Calculate duration data for currently active rentals.
    
    Args:
        start_time: Rental start datetime
    
    Returns:
        tuple: (display_string, total_seconds)
            - display_string: Current duration in "days:hours:minutes" format
            - total_seconds: Current duration in seconds
    """
    if not start_time:
        return "0:00:00", 0.0
    
    # Calculate current duration
    current_time = datetime.datetime.now()
    duration = current_time - start_time
    total_seconds = duration.total_seconds()
    
    # Handle negative durations (clock issues)
    if total_seconds < 0:
        return "0:00:00", 0.0
    
    # Format display string using existing pattern
    days = duration.days
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    
    display_string = f"{days}:{hours:02}:{minutes:02}"
    
    return display_string, total_seconds


def format_duration_from_seconds(total_seconds: float) -> str:
    """
    Format duration from total seconds to human-readable string.
    
    Args:
        total_seconds: Duration in seconds
    
    Returns:
        str: Formatted duration string "days:hours:minutes"
    """
    if total_seconds <= 0:
        return "0:00:00"
    
    # Convert to integer seconds for calculation
    seconds = int(total_seconds)
    
    # Calculate components
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    
    return f"{days}:{hours:02}:{minutes:02}"


def get_special_case_duration_data(case_type: str) -> Tuple[str, float]:
    """
    Get duration data for special cases.
    
    Args:
        case_type: Type of special case ('active', 'never_rented', 'zero')
    
    Returns:
        tuple: (display_string, sort_value)
    """
    special_cases = {
        'active': ("Active rental", float('inf')),
        'never_rented': ("Never Rented", 0.0),
        'zero': ("0:00:00", 0.0)
    }
    
    return special_cases.get(case_type, ("0:00:00", 0.0))


def validate_duration_data(duration_data: dict) -> bool:
    """
    Validate that duration data contains required fields.
    
    Args:
        duration_data: Dictionary containing duration information
    
    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = ['duration', 'duration_seconds']
    
    if not isinstance(duration_data, dict):
        return False
    
    for field in required_fields:
        if field not in duration_data:
            return False
    
    # Validate duration_seconds is a number
    try:
        float(duration_data['duration_seconds'])
    except (ValueError, TypeError):
        return False
    
    return True


def create_duration_dict(display_string: str, total_seconds: float) -> dict:
    """
    Create a standardized duration dictionary with both display and sort values.
    
    Args:
        display_string: Human-readable duration string
        total_seconds: Numerical duration value for sorting
    
    Returns:
        dict: Dictionary with 'duration' and 'duration_seconds' keys
    """
    return {
        'duration': display_string,
        'duration_seconds': total_seconds
    }


def get_duration_sort_value(duration_data: dict) -> float:
    """
    Extract the numerical sort value from duration data.
    
    Args:
        duration_data: Dictionary containing duration information
    
    Returns:
        float: Numerical sort value, defaults to 0.0 if invalid
    """
    if not validate_duration_data(duration_data):
        return 0.0
    
    try:
        return float(duration_data['duration_seconds'])
    except (ValueError, TypeError):
        return 0.0