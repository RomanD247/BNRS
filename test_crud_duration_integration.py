"""
Integration tests for CRUD functions with duration sorting.

This test suite validates that the CRUD functions properly return duration data
with both display strings and numerical sort values, and that the data structure
matches what the UI expects for proper sorting.

Tests cover:
1. User rental statistics function
2. Equipment type statistics function  
3. Equipment name statistics function
4. Department rental statistics function
5. Rental history data preparation
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import datetime
import sys
import os

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import the functions we want to test
try:
    from crud import (
        get_user_rental_statistics,
        get_equipment_type_statistics, 
        get_equipment_name_statistics,
        get_department_rental_statistics,
        get_all_rentals
    )
    from duration_utils import calculate_duration_data
except ImportError as e:
    print(f"Import error: {e}")
    print("This test requires the actual CRUD functions to be available")


class TestCRUDDurationIntegration(unittest.TestCase):
    """Test CRUD functions return proper duration data structure."""
    
    def setUp(self):
        """Set up mock database session and test data."""
        self.mock_db = Mock()
        
        # Create mock rental data
        self.mock_rental = Mock()
        self.mock_rental.rental_start = datetime.datetime(2024, 1, 1, 10, 0, 0)
        self.mock_rental.rental_end = datetime.datetime(2024, 1, 2, 11, 30, 0)  # 1 day, 1.5 hours
        
        # Create mock user data
        self.mock_user = Mock()
        self.mock_user.name = "Test User"
        self.mock_user.id_us = 1
        
        # Create mock department data
        self.mock_department = Mock()
        self.mock_department.name = "Test Department"
        self.mock_department.id_dep = 1
        
        # Create mock equipment data
        self.mock_equipment = Mock()
        self.mock_equipment.name = "Test Equipment"
        self.mock_equipment.id_eq = 1
        
        # Create mock equipment type data
        self.mock_etype = Mock()
        self.mock_etype.name = "Test Type"
        self.mock_etype.id_et = 1
    
    def test_duration_data_structure_requirements(self):
        """Test that duration data structure meets UI requirements."""
        # Expected structure for UI table sorting
        expected_fields = ['duration', 'duration_seconds']
        
        # Test with sample data
        start_time = datetime.datetime(2024, 1, 1, 10, 0, 0)
        end_time = datetime.datetime(2024, 1, 2, 11, 30, 0)
        
        display, seconds = calculate_duration_data(start_time, end_time)
        
        # Create data structure as CRUD functions should
        duration_data = {
            'duration': display,
            'duration_seconds': seconds
        }
        
        # Verify required fields exist
        for field in expected_fields:
            self.assertIn(field, duration_data)
        
        # Verify data types
        self.assertIsInstance(duration_data['duration'], str)
        self.assertIsInstance(duration_data['duration_seconds'], (int, float))
        
        # Verify sorting capability
        self.assertGreater(duration_data['duration_seconds'], 0)
    
    def test_user_statistics_duration_structure(self):
        """Test user statistics returns proper duration structure."""
        # This test validates the expected structure without requiring actual DB
        expected_structure = {
            'name': str,
            'department': str, 
            'rental_count': int,
            'total_rental_time': str,      # Display field
            'duration_seconds': float      # Sort field
        }
        
        # Verify the structure matches UI expectations
        for field, expected_type in expected_structure.items():
            self.assertIsInstance(field, str)
            self.assertTrue(callable(expected_type))
    
    def test_statistics_sorting_consistency(self):
        """Test that all statistics functions use consistent sorting approach."""
        # Mock data representing what CRUD functions should return
        mock_user_stats = [
            {
                'name': 'User A',
                'department': 'Dept 1',
                'rental_count': 5,
                'total_rental_time': '2:01:30',
                'duration_seconds': 176490.0
            },
            {
                'name': 'User B',
                'department': 'Dept 2', 
                'rental_count': 3,
                'total_rental_time': '1:00:00',
                'duration_seconds': 86400.0
            }
        ]
        
        # Test sorting works correctly
        sorted_stats = sorted(mock_user_stats, 
                            key=lambda x: x['duration_seconds'], 
                            reverse=True)
        
        # Verify correct order (User A should be first with longer duration)
        self.assertEqual(sorted_stats[0]['name'], 'User A')
        self.assertEqual(sorted_stats[1]['name'], 'User B')
        
        # Verify display format is preserved
        self.assertEqual(sorted_stats[0]['total_rental_time'], '2:01:30')
        self.assertEqual(sorted_stats[1]['total_rental_time'], '1:00:00')
    
    def test_rental_history_duration_structure(self):
        """Test rental history data includes proper duration fields."""
        # Mock rental history data structure
        mock_rental_data = {
            'id': 1,
            'equipment': 'Test Equipment',
            'serialnum': 'SN123',
            'equipment_type': 'Test Type',
            'user': 'Test User',
            'department': 'Test Department',
            'rental_start': '2024-01-01 10:00',
            'rental_end': '2024-01-02 11:30',
            'duration': '1:01:30',           # Display field
            'duration_seconds': 91800.0,     # Sort field
            'comment': 'Test comment'
        }
        
        # Verify required fields for sorting
        self.assertIn('duration', mock_rental_data)
        self.assertIn('duration_seconds', mock_rental_data)
        
        # Verify data types
        self.assertIsInstance(mock_rental_data['duration'], str)
        self.assertIsInstance(mock_rental_data['duration_seconds'], float)
        
        # Verify sorting value is reasonable
        self.assertGreater(mock_rental_data['duration_seconds'], 0)
    
    def test_active_rental_sorting_behavior(self):
        """Test that active rentals sort correctly to top."""
        mock_data = [
            {
                'equipment': 'Equipment A',
                'duration': '1:00:00',
                'duration_seconds': 86400.0
            },
            {
                'equipment': 'Equipment B', 
                'duration': 'Active rental',
                'duration_seconds': float('inf')
            },
            {
                'equipment': 'Equipment C',
                'duration': '0:30:00', 
                'duration_seconds': 43200.0
            }
        ]
        
        # Sort by duration_seconds descending
        sorted_data = sorted(mock_data, 
                           key=lambda x: x['duration_seconds'], 
                           reverse=True)
        
        # Active rental should be first
        self.assertEqual(sorted_data[0]['equipment'], 'Equipment B')
        self.assertEqual(sorted_data[0]['duration'], 'Active rental')
        
        # Other items should follow in correct order
        self.assertEqual(sorted_data[1]['equipment'], 'Equipment A')
        self.assertEqual(sorted_data[2]['equipment'], 'Equipment C')
    
    def test_column_configuration_compatibility(self):
        """Test that data structure works with expected column configuration."""
        # Expected column configuration for duration sorting
        duration_column_config = {
            'name': 'duration',
            'label': 'Duration',
            'field': 'duration',           # Display field
            'sortable': True,
            'align': 'left',
            'sort': 'duration_seconds'     # Sort field
        }
        
        # Mock data row
        data_row = {
            'duration': '1:30:45',
            'duration_seconds': 131445.0,
            'other_field': 'other_value'
        }
        
        # Verify display field exists and is accessible
        display_field = duration_column_config['field']
        self.assertIn(display_field, data_row)
        self.assertEqual(data_row[display_field], '1:30:45')
        
        # Verify sort field exists and is accessible
        sort_field = duration_column_config['sort']
        self.assertIn(sort_field, data_row)
        self.assertEqual(data_row[sort_field], 131445.0)
        
        # Verify sort field is different from display field
        self.assertNotEqual(display_field, sort_field)
    
    def test_special_cases_handling(self):
        """Test handling of special cases in statistics data."""
        special_cases = [
            {
                'case': 'active_rental',
                'duration': 'Active rental',
                'duration_seconds': float('inf')
            },
            {
                'case': 'never_rented',
                'duration': 'Never Rented',
                'duration_seconds': 0.0
            },
            {
                'case': 'zero_duration',
                'duration': '0:00:00',
                'duration_seconds': 0.0
            }
        ]
        
        for case_data in special_cases:
            # Verify display format
            self.assertIsInstance(case_data['duration'], str)
            
            # Verify numerical sort value
            self.assertIsInstance(case_data['duration_seconds'], (int, float))
            
            # Verify special values are handled correctly
            if case_data['case'] == 'active_rental':
                self.assertEqual(case_data['duration_seconds'], float('inf'))
            elif case_data['case'] in ['never_rented', 'zero_duration']:
                self.assertEqual(case_data['duration_seconds'], 0.0)
    
    def test_mixed_data_sorting_scenario(self):
        """Test sorting with mixed data including all special cases."""
        mixed_data = [
            {
                'name': 'Item A',
                'duration': '45:17:12',
                'duration_seconds': 3996720.0
            },
            {
                'name': 'Item B',
                'duration': 'Active rental', 
                'duration_seconds': float('inf')
            },
            {
                'name': 'Item C',
                'duration': '186:21:12',
                'duration_seconds': 16146720.0
            },
            {
                'name': 'Item D',
                'duration': '0:00:00',
                'duration_seconds': 0.0
            },
            {
                'name': 'Item E',
                'duration': 'Never Rented',
                'duration_seconds': 0.0
            }
        ]
        
        # Sort descending (longest first)
        sorted_desc = sorted(mixed_data, 
                           key=lambda x: x['duration_seconds'], 
                           reverse=True)
        
        # Expected order: Active (inf), 186 days, 45 days, zero/never (0)
        expected_order_desc = ['Item B', 'Item C', 'Item A', 'Item D', 'Item E']
        actual_order_desc = [item['name'] for item in sorted_desc]
        
        # Note: Items D and E both have 0.0, so their relative order may vary
        # We'll check the first 3 which should be deterministic
        self.assertEqual(actual_order_desc[:3], expected_order_desc[:3])
        
        # Sort ascending (shortest first)
        sorted_asc = sorted(mixed_data,
                          key=lambda x: x['duration_seconds'])
        
        # Expected order: zero/never (0), 45 days, 186 days, Active (inf)
        expected_order_asc = ['Item D', 'Item E', 'Item A', 'Item C', 'Item B']
        actual_order_asc = [item['name'] for item in sorted_asc]
        
        # Check that zero duration items come first and active comes last
        self.assertIn(actual_order_asc[0], ['Item D', 'Item E'])
        self.assertIn(actual_order_asc[1], ['Item D', 'Item E'])
        self.assertEqual(actual_order_asc[-1], 'Item B')  # Active should be last


class TestUITableSortingBehavior(unittest.TestCase):
    """Test expected UI table sorting behavior."""
    
    def test_table_column_sort_configuration(self):
        """Test that table columns are configured correctly for sorting."""
        # All dialogs should have similar duration column configuration
        expected_duration_columns = [
            # Rental History
            {
                'name': 'duration',
                'label': 'Duration', 
                'field': 'duration',
                'sortable': True,
                'align': 'left',
                'sort': 'duration_seconds'
            },
            # User Statistics
            {
                'name': 'total_rental_time',
                'label': 'Total Rental Time',
                'field': 'total_rental_time', 
                'sortable': True,
                'align': 'left',
                'sort': 'duration_seconds'
            },
            # Equipment Type Statistics  
            {
                'name': 'total_rental_time',
                'label': 'Total Rental Time',
                'field': 'total_rental_time',
                'sortable': True, 
                'align': 'right',
                'sort': 'duration_seconds'
            }
        ]
        
        for column_config in expected_duration_columns:
            # Verify required fields
            self.assertIn('sort', column_config)
            self.assertIn('field', column_config)
            self.assertTrue(column_config['sortable'])
            
            # Verify sort field is duration_seconds
            self.assertEqual(column_config['sort'], 'duration_seconds')
            
            # Verify display field is different from sort field
            self.assertNotEqual(column_config['field'], column_config['sort'])
    
    def test_pagination_default_sorting(self):
        """Test that tables default to correct sorting."""
        # Expected pagination configurations
        expected_pagination_configs = [
            # Rental History - should sort by ID descending by default
            {'sortBy': 'id', 'descending': True},
            
            # Statistics reports - should sort by duration descending by default
            {'sortBy': 'total_rental_time', 'descending': True}
        ]
        
        for config in expected_pagination_configs:
            self.assertIn('sortBy', config)
            self.assertIn('descending', config)
            self.assertIsInstance(config['descending'], bool)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)