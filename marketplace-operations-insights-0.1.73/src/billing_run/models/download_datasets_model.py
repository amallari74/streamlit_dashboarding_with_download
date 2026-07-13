import streamlit as st
import pandas as pd
from utils import db_util
from datetime import datetime, timedelta

@st.cache_data(ttl=3600)
def fetch_business_units(schema="", database=None):
    """Get all business units for dropdown filters"""   
    query = f"""
    SELECT DISTINCT unique_code 
    FROM {schema}business_unit_cache 
    ORDER BY unique_code
    """
    
    results = db_util.query(query, db=database)
    return results

@st.cache_data(ttl=3600)
def fetch_vendors(schema="", database=None):
    """Get all vendors for dropdown filters"""  
    query = f"""
    SELECT DISTINCT vendor 
    FROM {schema}product
    WHERE vendor IS NOT NULL
    ORDER BY vendor
    """
    
    results = db_util.query(query, db=database)
    return results

def fetch_invoice_row_details(business_unit=None, vendor=None, invoice_date=None, schema="", database=None):
    """Fetch invoice row details with filters"""
    # Convert invoice_date selection to actual date
    if invoice_date == "This Month":
        # First day of current month
        date_value = f"DATE_TRUNC('month', CURRENT_DATE)"
    else:  # Last Month
        # First day of previous month
        date_value = f"DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')"
    
    query = f"""
    SELECT cira.*, p.vendor, i.business_unit_code as business_unit
    FROM {schema}csv_invoice_row_archive cira
    JOIN {schema}product p ON p.id = cira.product_id
    JOIN {schema}invoice i ON cira.invoice_id = i.id
    WHERE 1=1 
    AND i.invoice_date = {date_value}
    AND cira.is_voided = false
    """
    
    # Add filters conditionally
    if business_unit:
        query += f" AND i.business_unit_code = '{business_unit}'"
    if vendor:
        query += f" AND p.vendor = '{vendor}'"
    
    results = db_util.query(query, db=database)
    return results

def fetch_invoices(business_unit=None, invoice_date=None, schema="", database=None):
    """Fetch invoices with filters""" 
    # Convert invoice_date selection to actual date
    if invoice_date == "This Month":
        # First day of current month
        date_value = f"DATE_TRUNC('month', CURRENT_DATE)"
    else:  # Last Month
        # First day of previous month
        date_value = f"DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')"
    
    query = f"""
    SELECT * 
    FROM {schema}invoice
    WHERE 1=1
    AND invoice_date = {date_value}
    """
    
    # Add business_unit filter conditionally
    if business_unit:
        query += f" AND business_unit_code = '{business_unit}'"
    
    results = db_util.query(query, db=database)
    return results

def fetch_filtered_arrears_tasks(status=None, vendor=None, schema="", database=None):
    """Fetch arrears tasks with filters"""
    query = f"""
    WITH arrears_tasks AS (
        SELECT
            id, subscription_id, product_id, status, run_on, 
            run_duration, error_message, error_count, created_dt, updated_dt
        FROM {schema}arrears_task
        WHERE method = 'createArrearsBillsForSubscription'
        AND DATE_TRUNC('month', run_on) >= DATE_TRUNC('month', CURRENT_DATE)
        UNION ALL
        SELECT
            id, subscription_id, product_id, status, run_on, 
            run_duration, error_message, error_count, created_dt, updated_dt
        FROM {schema}arrears_task_2
        WHERE method = 'createArrearsBillsForSubscription'
        AND DATE_TRUNC('month', run_on) >= DATE_TRUNC('month', CURRENT_DATE)
    )
    
    SELECT art.*, s.original_subscription_id, p.name as product_name, p.vendor
    FROM arrears_tasks art
    JOIN {schema}subscription s ON s.id = art.subscription_id
    JOIN {schema}product p ON art.product_id = p.id
    WHERE 1=1
    """
    
    # Add filters conditionally
    if status:
        query += f" AND art.status = '{status}'"
    if vendor:
        query += f" AND p.vendor = '{vendor}'"
    
    results = db_util.query(query, db=database)
    return results

def fetch_filtered_billing_tasks(status=None, method=None, schema="", database=None):
    """Fetch billing tasks with filters"""
    # Database-specific SQL functions
    is_valid_json = "IS_VALID_JSON(payload)" if database == "redshift" else "(payload::jsonb is not null)"
    json_extract = lambda path: f"JSON_EXTRACT_PATH_TEXT(payload, '{path}')" if database == "redshift" else f"payload::json->>'{path}'"
    
    methods = ["createPartnerInvoice", "createCompanyInvoice", "calculateAndStoreSalesTaxRatesForPartner", 
               "calculateAndStoreSalesTaxRatesForCompany", "sendInvoiceForCompany", "sendInvoiceForPartner"]
    
    if method:
        methods = [method]
    
    methods_str = "', '".join(methods)
    
    query = f"""
    WITH billing_unioned AS (
        SELECT
            "id", "service", "method", "payload", "status", "created_dt", "updated_dt",
            "error_count", "error_message", "run_on", "run_duration", "partner_id", 
            "run_on_date_time", NULL as "guid"
        FROM {schema}billing_task
        WHERE method IN ('{methods_str}')
        AND DATE_TRUNC('month', run_on) >= DATE_TRUNC('month', CURRENT_DATE)
        
        UNION ALL
        
        SELECT
            "id", "service", "method", "payload", "status", "created_dt", "updated_dt",
            "error_count", "error_message", "run_on", "run_duration", "partner_id", 
            NULL as "run_on_date_time", "guid"
        FROM {schema}billing_task_2
        WHERE method IN ('{methods_str}')
        AND DATE_TRUNC('month', run_on) >= DATE_TRUNC('month', CURRENT_DATE)
    )
    
    SELECT
        id, guid, partner_id, service, method, payload,
        CASE WHEN {is_valid_json} THEN NULLIF({json_extract('partnerId')}, '') END AS partner_id_parsed,
        CASE WHEN {is_valid_json} THEN NULLIF({json_extract('companyId')}, '') END AS company_id_parsed,
        status, error_message, error_count, run_duration, run_on,
        DATE_TRUNC('MONTH', run_on) AS run_on_month, created_dt, updated_dt
    FROM billing_unioned
    WHERE 1=1
    """
    
    # Add status filter conditionally
    if status:
        query += f" AND status = '{status}'"
    
    results = db_util.query(query, db=database)
    return results 

def fetch_invoice_report(business_unit=None, invoice_date=None, schema="", database=None):
    """Fetch invoice report with filters"""

    query = f"""
    SELECT i.alternate_id, i.balance, i.status, i.due_date, i.sales_tax as vat_tax_amount, i.business_unit_code,
    p.name as partner_name, i.partner_id, p.registration_number, p.tax_id as vat_id, c.iso_code as currency_code, i.invoice_date
    FROM {schema}invoice i
    INNER JOIN {schema}partner p on i.partner_id=p.id
    INNER JOIN {schema}currency c on i.currency_id=c.id
    WHERE i.status!='Void'
    """

    # Add business_unit and invoice_date filter conditionally
    if business_unit and invoice_date:
        query += f" AND business_unit_code = '{business_unit}' AND invoice_date >= '{invoice_date}'"

    results = db_util.query(query, db=database)
    return results

def fetch_credit_memo_report(business_unit=None, transaction_date=None, schema="", database=None):
    """Fetch credit memo report with filters"""

    query = f"""
    SELECT
    cm.alternate_id as credit_memo_id,
    cm.credit_sum as credit_memo_total,
    cm.created_date as credit_memo_created_dt,
    cm.send_date as credit_memo_send_dt,
    cm.business_unit_unique_code,
    p.id as partner_id,
    p.name as partner_name,
    p.registration_number,
    p.tax_id as vat_id,
    l.credit as credit_total,
    lest.amount_excluding_tax,
    lest.tax_amount,
    lest.rate as tax_rate,
    pa.name as product_name,
    pa.vendor as product_vendor,
    l.description,
    l.transaction_date
    FROM {schema}ledger l
    LEFT JOIN {schema}credit_memo cm on l.credit_memo_id=cm.id
    LEFT JOIN {schema}ledger_entry_sales_tax lest on l.id=lest.ledger_entry_id
    LEFT JOIN {schema}partner p on cm.partner_id=p.id
    LEFT JOIN {schema}product pa on l.product_id=pa.id
    """

    # Add business_unit filter conditionally
    if business_unit and transaction_date:
        query += f"WHERE business_unit_unique_code = '{business_unit}' AND transaction_date >= '{transaction_date}'"

    #if transaction_date:
    #   query += f" AND transaction_date = '{transaction_date}'"

    results = db_util.query(query, db=database)
    return results
