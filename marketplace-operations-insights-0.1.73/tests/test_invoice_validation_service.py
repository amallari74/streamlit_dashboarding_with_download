import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import json

# Add src directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.billing_run.invoice_validation_service import InvoiceValidationService

class TestInvoiceValidationService(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures, if any."""
        self.mock_repo = MagicMock()
        self.service = InvoiceValidationService(self.mock_repo)
        
        # Sample data for tests
        self.invoice_id = "test-invoice-123"
        self.invoice_date = "2024-01-15"
        
        # Mock invoice data
        self.mock_invoice_data = pd.DataFrame({
            'id': [self.invoice_id],
            'invoice_date': [self.invoice_date],
            'company_id': ['company-123'],
            'partner_id': ['partner-456'],
            'status': ['Active'],
            'total': [1000.00],
            'balance': [0.00],
            'is_current_invoice': [True]
        })
        
        # Mock line items data
        self.mock_line_items = pd.DataFrame({
            'line_item_id': ['line-1', 'line-2', 'line-3'],
            'invoice_id': [self.invoice_id, self.invoice_id, self.invoice_id],
            'sku': ['SKU-001', 'SKU-002', 'SKU-003'],
            'quantity': [5, 10, 2],
            'price': [10.00, 20.00, 150.00],
            'total': [50.00, 200.00, 300.00],
            'start_period': ['2024-01-01', '2024-01-01', '2024-01-01'],
            'end_period': ['2024-01-31', '2024-01-31', '2024-01-31'],
            'arrears_subscription_id': ['sub-001', 'sub-002', 'sub-003'],
            'completed_line_item_id': ['cli-001', 'cli-002', 'cli-003']
        })
        
        # Mock expected items from active subscriptions
        self.mock_expected_items = pd.DataFrame({
            'subscription_id': ['sub-001', 'sub-002', 'sub-003', 'sub-004'],
            'quantity': [5, 10, 2, 3],
            'status': ['Active', 'Active', 'Active', 'Active'],
            'billing_cycle_start': ['2024-01-01', '2024-01-01', '2024-01-01', '2024-01-01'],
            'billing_cycle_end': [None, None, None, None],
            'sku': ['SKU-001', 'SKU-002', 'SKU-003', 'SKU-004'],
            'product_name': ['Product 1', 'Product 2', 'Product 3', 'Product 4'],
            'price': [10.00, 20.00, 150.00, 75.00]
        })
        
        # Mock subscriptions data
        self.mock_subscriptions = pd.DataFrame({
            'id': ['sub-001', 'sub-002', 'sub-003', 'sub-004', 'sub-005'],
            'original_subscription_id': ['osub-001', 'osub-002', 'osub-003', 'osub-004', 'osub-005'],
            'completed_line_id': ['cli-001', 'cli-002', 'cli-003', 'cli-004', 'cli-005'],
            'status': ['Active', 'Active', 'Active', 'Active', 'Active'],
            'billing_cycle_start': ['2024-01-01', '2024-01-01', '2024-01-01', '2024-01-01', '2023-12-01'],
            'billing_cycle_end': [None, None, None, None, None],
            'sku': ['SKU-001', 'SKU-002', 'SKU-003', 'SKU-004', 'SKU-005']
        })
        
        # Mock transactions data
        self.mock_transactions = pd.DataFrame({
            'transaction_id': ['txn-001', 'txn-002', 'txn-003', 'txn-004', 'txn-005', 'txn-006'],
            'completed_line_item_id': ['cli-001', 'cli-002', 'cli-003', 'cli-004', 'cli-005', 'cli-006'],
            'subscription_id': ['sub-001', 'sub-002', 'sub-003', 'sub-004', 'sub-005', 'sub-006'],
            'sku': ['SKU-001', 'SKU-002', 'SKU-003', 'SKU-004', 'SKU-005', 'SKU-006'],
            'quantity': [5, 10, 2, 3, 1, 4],
            'price': [10.00, 20.00, 150.00, 75.00, 30.00, 45.00],
            'total': [50.00, 200.00, 300.00, 225.00, 30.00, 180.00]
        })
        
    
    def test_join_partner_data_by_completed_line_items(self):
        """Test joining partner subscriptions, transactions, and completed line items."""
        # Setup
        # Load mock data from JSON files
        mock_data_path = os.path.join(
            os.path.dirname(__file__),
            'fixtures/mock_invoice_datasets/invoice_1538618_partner_893537'
        )
        
        # Load the mock data
        with open(os.path.join(mock_data_path, 'subscriptions_attached_to_partner.json'), 'r') as f:
            partner_subs_data = json.load(f)
        with open(os.path.join(mock_data_path, 'transactions_attached_to_partner.json'), 'r') as f:
            partner_txns_data = json.load(f)
        with open(os.path.join(mock_data_path, 'completed_line_items_attached_to_partner.json'), 'r') as f:
            completed_line_items_data = json.load(f)
        
        # Convert to DataFrames
        partner_subs_df = pd.DataFrame(partner_subs_data)
        partner_txns_df = pd.DataFrame(partner_txns_data)
        completed_line_items_df = pd.DataFrame(completed_line_items_data)
        
        # Execute
        result_df = self.service.join_partner_data_by_completed_line_items(
            partner_subs_df,
            partner_txns_df,
            completed_line_items_df
        )
        
        # Assert
        self.assertFalse(result_df.empty, "Result DataFrame should not be empty")
        self.assertTrue('subscription_id' in result_df.columns, "Result should have subscription_id column")
        self.assertTrue('completed_line_item_id' in result_df.columns, "Result should have completed_line_item_id column")
        self.assertTrue('id' in result_df.columns, "Result should have id column from subscriptions")
        
        # Check that we have matching records
        self.assertGreater(len(result_df), 0, "Should have at least one matching record")
        
        # Verify the joins worked correctly by checking a sample record
        sample_record = result_df.iloc[0]
        self.assertEqual(
            sample_record['subscription_id'],
            sample_record['id'],
            "Subscription IDs should match"
        )
        
        # Check that all required columns are present
        required_columns = ['subscription_id', 'completed_line_item_id', 'id', 'status', 'sku']
        for col in required_columns:
            self.assertTrue(col in result_df.columns, f"Missing required column: {col}")

if __name__ == '__main__':
    unittest.main() 