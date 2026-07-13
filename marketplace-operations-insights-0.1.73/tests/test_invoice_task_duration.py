"""
Test module for invoice task duration analysis functionality.
"""

import pytest
import pandas as pd
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch

# Import the modules we want to test
from billing_run.models.invoice_task_duration_model import (
    get_alert_summary,
    get_performance_summary,
    get_default_date_range,
    format_runtime_display
)
from queries.queries import Queries


class TestInvoiceTaskDurationModel:
    """Test cases for the invoice task duration model functions."""
    
    def test_get_alert_summary_empty_dataframe(self):
        """Test alert summary with empty DataFrame."""
        df = pd.DataFrame()
        result = get_alert_summary(df)
        
        assert result["total_alerts"] == 0
        assert result["critical_alerts"] == 0
        assert result["warning_alerts"] == 0
        assert result["alert_details"] == []
        assert result["max_runtime_hours"] == 0
        assert result["affected_dates"] == []
    
    def test_get_alert_summary_with_alerts(self):
        """Test alert summary with alert data."""
        # Create sample data with alerts
        df = pd.DataFrame({
            'invoice_date': ['2024-01-01', '2024-01-02'],
            'task_table': ['billing_task', 'mca_task'],
            'method': ['createPartnerInvoice', 'createCompanyInvoice'],
            'total_runtime_hours': [25.5, 15.0],
            'max_runtime_sec': [1200, 2000],
            'total_tasks': [100, 50],
            'alert_24hr_exceeded': [True, False],
            'alert_30min_task_exceeded': [False, True],
            'alert_message': ['ALERT: Total runtime exceeds 24 hours (25.5h)', 'WARNING: Individual task exceeds 30 minutes (2000s)']
        })
        
        result = get_alert_summary(df)
        
        assert result["total_alerts"] == 2
        assert result["critical_alerts"] == 1
        assert result["warning_alerts"] == 1
        assert len(result["alert_details"]) == 2
        assert result["max_runtime_hours"] == 25.5
        assert len(result["affected_dates"]) == 2
    
    def test_get_performance_summary_empty_dataframe(self):
        """Test performance summary with empty DataFrame."""
        df = pd.DataFrame()
        result = get_performance_summary(df)
        
        assert result["total_tasks"] == 0
        assert result["total_runtime_hours"] == 0
        assert result["avg_runtime_sec"] == 0
        assert result["p95_runtime_sec"] == 0
        assert result["slowest_task_table"] == "N/A"
        assert result["date_range_days"] == 0
    
    def test_get_performance_summary_with_data(self):
        """Test performance summary with sample data."""
        df = pd.DataFrame({
            'invoice_date': ['2024-01-01', '2024-01-02'],
            'task_table': ['billing_task', 'mca_task'],
            'total_tasks': [100, 50],
            'total_runtime_hours': [10.5, 5.5],
            'avg_runtime_sec': [30.0, 45.0],
            'p95_runtime_sec': [120.0, 180.0]
        })
        
        result = get_performance_summary(df)
        
        assert result["total_tasks"] == 150
        assert result["total_runtime_hours"] == 16.0
        assert result["avg_runtime_sec"] == 35.0  # Weighted average
        assert result["p95_runtime_sec"] == 180.0
        assert result["slowest_task_table"] == "billing_task"
        assert result["date_range_days"] == 2
    
    def test_get_default_date_range(self):
        """Test default date range generation."""
        start_date, end_date = get_default_date_range()
        
        # Should return strings in YYYY-MM-DD format
        assert isinstance(start_date, str)
        assert isinstance(end_date, str)
        assert len(start_date) == 10
        assert len(end_date) == 10
        
        # Start date should be 30 days before end date
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        assert (end_dt - start_dt).days == 30
    
    def test_format_runtime_display(self):
        """Test runtime formatting function."""
        # Test seconds
        assert format_runtime_display(30.5) == "30.5s"
        
        # Test minutes
        assert format_runtime_display(120.0) == "2.0m"
        assert format_runtime_display(90.0) == "1.5m"
        
        # Test hours
        assert format_runtime_display(3600.0) == "1.0h"
        assert format_runtime_display(7200.0) == "2.0h"
        assert format_runtime_display(5400.0) == "1.5h"


class TestQueriesClass:
    """Test cases for the Queries class functionality."""
    
    def test_get_invoice_task_duration_analysis(self):
        """Test that the query method returns the expected query string."""
        start_date = "2024-01-01"
        end_date = "2024-01-31"
        
        query = Queries.get_invoice_task_duration_analysis(start_date, end_date)
        
        # Should return the query string
        assert isinstance(query, str)
        assert "createPartnerInvoice" in query
        assert "createCompanyInvoice" in query
        assert ":start_date" in query
        assert ":end_date" in query
        assert "alert_24hr_exceeded" in query
        assert "alert_30min_task_exceeded" in query
    
    def test_invoice_task_duration_analysis_query_structure(self):
        """Test that the query has the expected structure."""
        query = Queries.INVOICE_TASK_DURATION_ANALYSIS
        
        # Check for main components
        assert "WITH invoice_tasks AS" in query
        assert "duration_aggregates AS" in query
        assert "UNION ALL" in query
        assert "billing_task" in query
        assert "mca_task" in query
        assert "PERCENTILE_CONT" in query
        assert "ORDER BY invoice_date DESC" in query


class TestDatabaseIntegration:
    """Test cases for database integration (mocked)."""
    
    @patch('billing_run.models.invoice_task_duration_model.db_util.query')
    def test_fetch_invoice_task_duration_analysis_mock(self, mock_query):
        """Test the fetch function with mocked database."""
        # Mock the database query response
        mock_df = pd.DataFrame({
            'task_table': ['billing_task'],
            'invoice_date': ['2024-01-01'],
            'method': ['createPartnerInvoice'],
            'total_tasks': [50],
            'total_runtime_hours': [12.5],
            'alert_24hr_exceeded': [False],
            'alert_30min_task_exceeded': [False]
        })
        mock_query.return_value = mock_df
        
        # Import here to avoid Streamlit dependency issues in tests
        from billing_run.models.invoice_task_duration_model import fetch_invoice_task_duration_analysis
        
        # Call the function
        result = fetch_invoice_task_duration_analysis("2024-01-01", "2024-01-31", "postgresql")
        
        # Verify the mock was called with correct parameters
        mock_query.assert_called_once()
        call_args = mock_query.call_args
        assert call_args[1]['params']['start_date'] == "2024-01-01"
        assert call_args[1]['params']['end_date'] == "2024-01-31"
        assert call_args[1]['db'] == "postgresql"
        
        # Verify the result
        assert len(result) == 1
        assert result.iloc[0]['task_table'] == 'billing_task'


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
