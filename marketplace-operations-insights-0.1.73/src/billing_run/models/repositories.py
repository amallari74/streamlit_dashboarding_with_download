from .db_service import DatabaseService
from typing import Dict, Any, List, Optional
import pandas as pd

# Import original functions with underscore prefix to avoid name conflicts
from .invoice_model import (
    fetch_invoice_row_details as _fetch_invoice_row_details,
    fetch_invoice_release_details as _fetch_invoice_release_details,
    fetch_invoice_row_aggregated as _fetch_invoice_row_aggregated,
    fetch_invoice_balance_by_business_unit as _fetch_invoice_balance_by_business_unit
)
from .task_manager import (
    fetch_arrears_tasks as _fetch_arrears_tasks,
    fetch_billing_tasks as _fetch_billing_tasks,
    get_task_category_dataframes as _get_task_category_dataframes,
    fetch_arrears_usage_variance as _fetch_arrears_usage_variance,
    fetch_arrears_product_configurations as _fetch_arrears_product_configurations
)
from .latest_tasks_model import (
    fetch_latest_completed_tasks as _fetch_latest_completed_tasks,
    fetch_open_tasks_count as _fetch_open_tasks_count
)
from .download_datasets_model import (
    fetch_business_units as _fetch_business_units,
    fetch_vendors as _fetch_vendors,
    fetch_invoice_row_details as _fetch_invoice_row_details_dataset,
    fetch_invoices as _fetch_invoices,
    fetch_filtered_arrears_tasks as _fetch_filtered_arrears_tasks,
    fetch_filtered_billing_tasks as _fetch_filtered_billing_tasks
)
from .invoice_validation_model import (
    fetch_invoice_by_id as _fetch_invoice_by_id,
    fetch_invoice_line_items as _fetch_invoice_line_items,
    fetch_invoice_subscriptions as _fetch_invoice_subscriptions,
    fetch_invoice_transactions as _fetch_invoice_transactions,
    fetch_all_partner_transactions as _fetch_all_partner_transactions,
    fetch_all_partner_subscriptions as _fetch_all_partner_subscriptions,
    fetch_all_partner_line_items as _fetch_all_partner_line_items,
    fetch_all_completed_line_items as _fetch_all_completed_line_items
)

from .arrears_task_model import (
    fetch_arrears_task_details as _fetch_arrears_task_details
)

# Initialize the database service
_db_service = DatabaseService()

# Invoice model wrappers
def fetch_invoice_row_details(**kwargs):
    """Wrapper for fetch_invoice_row_details that handles database selection"""
    return _db_service.execute_query(_fetch_invoice_row_details, **kwargs)

def fetch_invoice_release_details(**kwargs):
    """Wrapper for fetch_invoice_release_details that handles database selection"""
    return _db_service.execute_query(_fetch_invoice_release_details, **kwargs)

def fetch_invoice_row_aggregated(**kwargs):
    """Wrapper for fetch_invoice_row_aggregated that handles database selection"""
    return _db_service.execute_query(_fetch_invoice_row_aggregated, **kwargs)

# Task manager wrappers
def fetch_arrears_tasks(**kwargs):
    """Wrapper for fetch_arrears_tasks that handles database selection"""
    return _db_service.execute_query(_fetch_arrears_tasks, **kwargs)

def fetch_billing_tasks(**kwargs):
    """Wrapper for fetch_billing_tasks that handles database selection"""
    return _db_service.execute_query(_fetch_billing_tasks, **kwargs)

def get_task_category_dataframes(**kwargs):
    """Wrapper for get_task_category_dataframes that handles database selection"""
    return _db_service.execute_query(_get_task_category_dataframes, **kwargs)

def fetch_arrears_usage_variance(**kwargs):
    """Wrapper for fetch_arrears_usage_variance that handles database selection"""
    return _db_service.execute_query(_fetch_arrears_usage_variance, **kwargs)

def fetch_arrears_product_configurations(**kwargs):
    """Wrapper for fetch_arrears_product_configurations that handles database selection"""
    return _db_service.execute_query(_fetch_arrears_product_configurations, **kwargs)
    
def fetch_latest_completed_tasks(**kwargs):
    """Wrapper for fetch_latest_completed_tasks that handles database selection"""
    return _db_service.execute_query(_fetch_latest_completed_tasks, **kwargs)

def fetch_open_tasks_count(**kwargs):
    """Wrapper for fetch_open_tasks_count that handles database selection"""
    return _db_service.execute_query(_fetch_open_tasks_count, **kwargs)

# Download datasets model wrappers
def fetch_business_units(**kwargs):
    """Wrapper for fetch_business_units that handles database selection"""
    return _db_service.execute_query(_fetch_business_units, **kwargs)

def fetch_vendors(**kwargs):
    """Wrapper for fetch_vendors that handles database selection"""
    return _db_service.execute_query(_fetch_vendors, **kwargs)

def fetch_invoice_row_details_dataset(**kwargs):
    """Wrapper for dataset version of fetch_invoice_row_details that handles database selection"""
    return _db_service.execute_query(_fetch_invoice_row_details_dataset, **kwargs)

def fetch_invoices(**kwargs):
    """Wrapper for fetch_invoices that handles database selection"""
    return _db_service.execute_query(_fetch_invoices, **kwargs)

def fetch_filtered_arrears_tasks(**kwargs):
    """Wrapper for fetch_filtered_arrears_tasks that handles database selection"""
    return _db_service.execute_query(_fetch_filtered_arrears_tasks, **kwargs)

def fetch_filtered_billing_tasks(**kwargs):
    """Wrapper for fetch_filtered_billing_tasks that handles database selection"""
    return _db_service.execute_query(_fetch_filtered_billing_tasks, **kwargs)

# Helper function to get the formatted last refresh time
def get_last_refresh_formatted(func_name: str) -> str:
    """Get the formatted last refresh time for a function"""
    return _db_service.format_last_refresh(func_name)

def fetch_invoice_by_id(invoice_id):
    """Fetch basic invoice header information by ID using the database service"""
    return _db_service.execute_query(_fetch_invoice_by_id, invoice_id=invoice_id)

def fetch_invoice_line_items(invoice_id):
    """Fetch all line items for a specific invoice using the database service"""
    return _db_service.execute_query(_fetch_invoice_line_items, invoice_id=invoice_id)

def fetch_invoice_subscriptions(invoice_id):
    """Fetch active subscriptions for a partner that should be on the invoice using the database service"""
    return _db_service.execute_query(_fetch_invoice_subscriptions, invoice_id=invoice_id)

def fetch_invoice_transactions(invoice_id):
    """Fetch completed transactions that should be on the invoice using the database service"""
    return _db_service.execute_query(_fetch_invoice_transactions, invoice_id=invoice_id)

def fetch_all_partner_transactions(partner_id, invoice_date=None):
    """Fetch all transactions for a partner, optionally filtered by date using the database service"""
    return _db_service.execute_query(_fetch_all_partner_transactions, partner_id=partner_id, invoice_date=invoice_date)

def fetch_all_partner_subscriptions(partner_id, active_on_date=None):
    """Fetch all subscriptions for a partner, optionally filtered by active date using the database service"""
    return _db_service.execute_query(_fetch_all_partner_subscriptions, partner_id=partner_id, active_on_date=active_on_date)

def fetch_all_partner_line_items(partner_id, invoice_date=None):
    """Fetch all line items for a partner, optionally filtered by date using the database service"""
    return _db_service.execute_query(_fetch_all_partner_line_items, partner_id=partner_id, invoice_date=invoice_date)

def fetch_all_completed_line_items(partner_id, invoice_date=None):
    """Fetch all completed line items for a partner, optionally filtered by date using the database service"""
    return _db_service.execute_query(_fetch_all_completed_line_items, partner_id=partner_id, invoice_date=invoice_date)

def fetch_full_invoice_data(invoice_id):
    """
    Fetch all data related to an invoice in one function using the database service
    
    Args:
        invoice_id (int): Invoice ID to fetch data for
        
    Returns:
        dict: Dictionary containing all invoice data
    """
    # Fetch invoice header
    invoice_df = fetch_invoice_by_id(invoice_id)
    
    if invoice_df.empty:
        return {
            "sample_invoice": pd.DataFrame(),
            "line_items": pd.DataFrame(),
            "subscriptions": pd.DataFrame(),
            "transactions": pd.DataFrame(),
            "partner_id": None,
            "invoice_date": None
        }
    
    partner_id = invoice_df['partner_id'].iloc[0] if 'partner_id' in invoice_df.columns else None
    invoice_date = invoice_df['invoice_date'].iloc[0] if 'invoice_date' in invoice_df.columns else None
    
    # Fetch invoice line items, subscriptions, transactions
    line_items_df = fetch_invoice_line_items(invoice_id)
    subscriptions_df = fetch_invoice_subscriptions(invoice_id)
    transactions_df = fetch_invoice_transactions(invoice_id)
    
    # Fetch partner-level data for the invoice month
    partner_line_items_df = fetch_all_partner_line_items(partner_id, invoice_date)
    partner_transactions_df = fetch_all_partner_transactions(partner_id, invoice_date)
    partner_subscriptions_df = fetch_all_partner_subscriptions(partner_id, invoice_date)
    completed_line_items_df = fetch_all_completed_line_items(partner_id, invoice_date)
    
    return {
        "sample_invoice": invoice_df,
        "line_items": line_items_df,
        "subscriptions": subscriptions_df,
        "transactions": transactions_df,
        "line_items_attached_to_partner": partner_line_items_df,
        "transactions_attached_to_partner": partner_transactions_df,
        "subscriptions_attached_to_partner": partner_subscriptions_df,
        "completed_line_items_attached_to_partner": completed_line_items_df,
        "partner_id": partner_id,
        "invoice_date": invoice_date
    } 

def fetch_invoice_balance_by_business_unit(**kwargs):
    """Wrapper for fetch_invoice_balance_by_business_unit that handles database selection"""
    return _db_service.execute_query(_fetch_invoice_balance_by_business_unit, **kwargs)

def fetch_arrears_task_details(**kwargs):
    """Wrapper for fetch_arrears_task_details that handles database selection"""
    return _db_service.execute_query(_fetch_arrears_task_details, **kwargs)