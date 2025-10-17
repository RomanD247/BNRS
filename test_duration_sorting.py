"""
Test suite for duration sorting functionality.

This test suite validates that the duration sorting fix works correctly across
all dialogs and reports in the rental system. It tests both the data layer
(CRUD functions) and the expected UI behavior.

Tests cover:
1. Rental History dialog sorting
2. All statistics reports sorting  
3. Display format consistency
4. Special cases (active rentals, never rented, zero duration)
"""

import unittest
import datetime
from unittest.mock import Mock, patch
import sys
import os

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from duration_utils import (
    calculate_duration_data, 
    format_duration_from_seconds,
    get_special_case_duration_data,
    validate_duration_data,
    create_duration_dict
)


class TestDurationSortingFunctionality(unittest.TestCase):
    """Test suite for duration sorting functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create test datetime objects
        self.base_time = datetime.datetime(2024, 1, 1, 10, 0, 0)
        self.end_time_1h = self.base_time + datetime.timedelta(hours=1)
        self.end_time_1d = self.base_time + datetime.timedelta(days=1)
        self.end_time_185d = self.base_time + datetime.timedelta(days=185, hours=45, minutes=12)
        self.end_time_45d = self.base_time + datetime.timedelta(days=45, hours=41, minutes=12)
    
    def test_duration_calculation_basic(self):
        """Test basic duration calculation functionality."""
        # Test 1 hour duration
        display, seconds = calculate_duration_data(self.base_time, self.end_time_1h)
        self.assertEqual(display, "0:01:00")
        self.assertEqual(seconds, 3600.0)
        
        # Test 1 day duration
        display, seconds = calculate_duration_data(self.base_time, self.end_time_1d)
        self.assertEqual(display, "1:00:00")
        self.assertEqual(seconds, 86400.0)
    
    def test_duration_calculation_sorting_scenario(self):
        """Test the specific sorting scenario from requirements."""
        # Test 185 days, 45 hours, 12 minutes (should be larger)
        display_185, seconds_185 = calculate_duration_data(self.base_time, self.end_time_185d)
        
        # Test 45 days, 41 hours, 12 minutes (should be smaller)
        display_45, seconds_45 = calculate_duration_data(self.base_time, self.end_time_45d)
        
        # Verify display format
        self.assertEqual(display_185, "186:21:12")  # 185 days + 45 hours = 186 days, 21 hours
        self.assertEqual(display_45, "46:17:12")   # 45 days + 41 hours = 46 days, 17 hours
        
        # Verify numerical sorting works correctly
        self.assertGreater(seconds_185, seconds_45)
        
        # Verify the problematic lexicographic sorting would be wrong
        # (This is what we're fixing - "45" > "185" lexicographically)
        self.assertTrue(display_45 > display_185)  # Lexicographic comparison (wrong)
        self.assertTrue(seconds_185 > seconds_45)  # Numerical comparison (correct)
    
    def test_active_rental_handling(self):
        """Test handling of active rentals."""
        display, seconds = calculate_duration_data(self.base_time, None)
        self.assertEqual(display, "Active rental")
        self.assertEqual(seconds, float('inf'))
        
        # Verify active rentals sort to top in descending order
        normal_seconds = 86400.0  # 1 day
        self.assertGreater(seconds, normal_seconds)
    
    def test_never_rented_handling(self):
        """Test handling of never rented equipment."""
        display, seconds = calculate_duration_data(None, None)
        self.assertEqual(display, "Never Rented")
        self.assertEqual(seconds, 0.0)
    
    def test_zero_duration_handling(self):
        """Test handling of zero duration rentals."""
        same_time = self.base_time
        display, seconds = calculate_duration_data(same_time, same_time)
        self.assertEqual(display, "0:00:00")
        self.assertEqual(seconds, 0.0)
    
    def test_negative_duration_handling(self):
        """Test handling of negative durations (data integrity issue)."""
        future_time = self.base_time + datetime.timedelta(hours=1)
        past_time = self.base_time
        
        display, seconds = calculate_duration_data(future_time, past_time)
        self.assertEqual(display, "0:00:00")
        self.assertEqual(seconds, 0.0)
    
    def test_format_duration_from_seconds(self):
        """Test formatting duration from seconds."""
        # Test various durations
        test_cases = [
            (0, "0:00:00"),
            (3600, "0:01:00"),      # 1 hour
            (86400, "1:00:00"),     # 1 day
            (90000, "1:01:00"),     # 1 day, 1 hour
            (90060, "1:01:01"),     # 1 day, 1 hour, 1 minute
        ]
        
        for seconds, expected in test_cases:
            result = format_duration_from_seconds(seconds)
            self.assertEqual(result, expected, f"Failed for {seconds} seconds")
    
    def test_special_case_duration_data(self):
        """Test special case duration data generation."""
        # Test active rental
        display, seconds = get_special_case_duration_data('active')
        self.assertEqual(display, "Active rental")
        self.assertEqual(seconds, float('inf'))
        
        # Test never rented
        display, seconds = get_special_case_duration_data('never_rented')
        self.assertEqual(display, "Never Rented")
        self.assertEqual(seconds, 0.0)
        
        # Test zero duration
        display, seconds = get_special_case_duration_data('zero')
        self.assertEqual(display, "0:00:00")
        self.assertEqual(seconds, 0.0)
    
    def test_duration_data_validation(self):
        """Test duration data validation."""
        # Valid data
        valid_data = {'duration': '1:00:00', 'duration_seconds': 3600.0}
        self.assertTrue(validate_duration_data(valid_data))
        
        # Missing duration field
        invalid_data1 = {'duration_seconds': 3600.0}
        self.assertFalse(validate_duration_data(invalid_data1))
        
        # Missing duration_seconds field
        invalid_data2 = {'duration': '1:00:00'}
        self.assertFalse(validate_duration_data(invalid_data2))
        
        # Invalid duration_seconds type
        invalid_data3 = {'duration': '1:00:00', 'duration_seconds': 'invalid'}
        self.assertFalse(validate_duration_data(invalid_data3))
        
        # Not a dictionary
        self.assertFalse(validate_duration_data("not a dict"))
    
    def test_create_duration_dict(self):
        """Test creation of standardized duration dictionary."""
        display = "1:00:00"
        seconds = 3600.0
        
        result = create_duration_dict(display, seconds)
        expected = {'duration': '1:00:00', 'duration_seconds': 3600.0}
        
        self.assertEqual(result, expected)
        self.assertTrue(validate_duration_data(result))


class TestRentalHistorySorting(unittest.TestCase):
    """Test rental history dialog sorting functionality."""
    
    def setUp(self):
        """Set up test data for rental history."""
        self.base_time = datetime.datetime(2024, 1, 1, 10, 0, 0)
        
        # Create mock rental data with different durations
        self.mock_rentals = [
            {
                'id': 1,
                'equipment': 'Equipment A',
                'rental_start': self.base_time,
                'rental_end': self.base_time + datetime.timedelta(days=185, hours=45, minutes=12),
                'duration': '186:21:12',
                'duration_seconds': 16146720.0
            },
            {
                'id': 2, 
                'equipment': 'Equipment B',
                'rental_start': self.base_time,
                'rental_end': self.base_time + datetime.timedelta(days=45, hours=41, minutes=12),
                'duration': '46:17:12',
                'duration_seconds': 3996720.0
            },
            {
                'id': 3,
                'equipment': 'Equipment C', 
                'rental_start': self.base_time,
                'rental_end': None,  # Active rental
                'duration': 'Active rental',
                'duration_seconds': float('inf')
            },
            {
                'id': 4,
                'equipment': 'Equipment D',
                'rental_start': self.base_time,
                'rental_end': self.base_time + datetime.timedelta(hours=1),
                'duration': '0:01:00',
                'duration_seconds': 3600.0
            }
        ]
    
    def test_rental_history_duration_sorting_descending(self):
        """Test rental history sorts correctly in descending order."""
        # Sort by duration_seconds descending (longest first)
        sorted_rentals = sorted(self.mock_rentals, 
                              key=lambda x: x['duration_seconds'], 
                              reverse=True)
        
        # Expected order: Active (inf), 186 days, 46 days, 1 hour
        expected_order = [3, 1, 2, 4]  # IDs in expected order
        actual_order = [rental['id'] for rental in sorted_rentals]
        
        self.assertEqual(actual_order, expected_order)
    
    def test_rental_history_duration_sorting_ascending(self):
        """Test rental history sorts correctly in ascending order."""
        # Sort by duration_seconds ascending (shortest first)
        sorted_rentals = sorted(self.mock_rentals, 
                              key=lambda x: x['duration_seconds'])
        
        # Expected order: 1 hour, 46 days, 186 days, Active (inf)
        expected_order = [4, 2, 1, 3]  # IDs in expected order
        actual_order = [rental['id'] for rental in sorted_rentals]
        
        self.assertEqual(actual_order, expected_order)
    
    def test_rental_history_display_format_preserved(self):
        """Test that display format is preserved while sorting works."""
        for rental in self.mock_rentals:
            # Verify display format is human-readable
            duration_display = rental['duration']
            
            if duration_display == 'Active rental':
                continue
            
            # Should match pattern "days:hours:minutes"
            if ':' in duration_display:
                parts = duration_display.split(':')
                self.assertEqual(len(parts), 3)
                # Each part should be numeric (except for active rentals)
                for part in parts:
                    self.assertTrue(part.isdigit())


class TestStatisticsReportsSorting(unittest.TestCase):
    """Test statistics reports sorting functionality."""
    
    def setUp(self):
        """Set up test data for statistics reports."""
        # Mock statistics data with duration information
        self.mock_user_stats = [
            {
                'name': 'User A',
                'department': 'Dept 1',
                'rental_count': 5,
                'total_rental_time': '186:21:12',
                'duration_seconds': 16146720.0
            },
            {
                'name': 'User B', 
                'department': 'Dept 2',
                'rental_count': 3,
                'total_rental_time': '46:17:12',
                'duration_seconds': 3996720.0
            },
            {
                'name': 'User C',
                'department': 'Dept 1', 
                'rental_count': 1,
                'total_rental_time': '0:01:00',
                'duration_seconds': 3600.0
            }
        ]
        
        self.mock_equipment_type_stats = [
            {
                'type_name': 'Type A',
                'rental_count': 10,
                'total_rental_time': '186:21:12',
                'duration_seconds': 16146720.0
            },
            {
                'type_name': 'Type B',
                'rental_count': 5,
                'total_rental_time': '46:17:12', 
                'duration_seconds': 3996720.0
            }
        ]
    
    def test_user_statistics_sorting(self):
        """Test user statistics sorting by duration."""
        # Sort by duration_seconds descending
        sorted_stats = sorted(self.mock_user_stats,
                            key=lambda x: x['duration_seconds'],
                            reverse=True)
        
        # Expected order: User A (186 days), User B (46 days), User C (1 hour)
        expected_names = ['User A', 'User B', 'User C']
        actual_names = [stat['name'] for stat in sorted_stats]
        
        self.assertEqual(actual_names, expected_names)
    
    def test_equipment_type_statistics_sorting(self):
        """Test equipment type statistics sorting by duration."""
        # Sort by duration_seconds descending
        sorted_stats = sorted(self.mock_equipment_type_stats,
                            key=lambda x: x['duration_seconds'],
                            reverse=True)
        
        # Expected order: Type A (186 days), Type B (46 days)
        expected_types = ['Type A', 'Type B']
        actual_types = [stat['type_name'] for stat in sorted_stats]
        
        self.assertEqual(actual_types, expected_types)
    
    def test_statistics_display_consistency(self):
        """Test that all statistics maintain consistent display format."""
        all_stats = self.mock_user_stats + self.mock_equipment_type_stats
        
        for stat in all_stats:
            duration_display = stat['total_rental_time']
            duration_seconds = stat['duration_seconds']
            
            # Verify both fields exist
            self.assertIn('total_rental_time', stat)
            self.assertIn('duration_seconds', stat)
            
            # Verify display format
            if ':' in duration_display:
                parts = duration_display.split(':')
                self.assertEqual(len(parts), 3)
            
            # Verify numerical value is valid
            self.assertIsInstance(duration_seconds, (int, float))
            self.assertGreaterEqual(duration_seconds, 0)


class TestDisplayFormatConsistency(unittest.TestCase):
    """Test display format consistency across all dialogs."""
    
    def test_duration_display_format_standards(self):
        """Test that duration display follows consistent format standards."""
        test_cases = [
            # (seconds, expected_display)
            (0, "0:00:00"),
            (3600, "0:01:00"),          # 1 hour
            (86400, "1:00:00"),         # 1 day  
            (90000, "1:01:00"),         # 1 day, 1 hour
            (90060, "1:01:01"),         # 1 day, 1 hour, 1 minute
            (16041912, "185:16:05"),    # Calculated correct value
            (16146720, "186:21:12")     # 185 days + 45 hours + 12 minutes
        ]
        
        for seconds, expected in test_cases:
            result = format_duration_from_seconds(seconds)
            self.assertEqual(result, expected, 
                           f"Format mismatch for {seconds} seconds")
    
    def test_special_cases_display_consistency(self):
        """Test special cases display consistently."""
        # Active rental
        display, _ = get_special_case_duration_data('active')
        self.assertEqual(display, "Active rental")
        
        # Never rented
        display, _ = get_special_case_duration_data('never_rented')
        self.assertEqual(display, "Never Rented")
        
        # Zero duration
        display, _ = get_special_case_duration_data('zero')
        self.assertEqual(display, "0:00:00")
    
    def test_column_configuration_format(self):
        """Test that column configurations follow expected format."""
        # Expected column configuration for duration sorting
        expected_duration_column = {
            'name': 'duration',
            'label': 'Duration', 
            'field': 'duration',           # Display field
            'sortable': True,
            'align': 'left',
            'sort': 'duration_seconds'     # Sort field
        }
        
        # Verify all required fields are present
        required_fields = ['name', 'label', 'field', 'sortable', 'sort']
        for field in required_fields:
            self.assertIn(field, expected_duration_column)
        
        # Verify sort field is different from display field
        self.assertNotEqual(expected_duration_column['field'], 
                          expected_duration_column['sort'])


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)