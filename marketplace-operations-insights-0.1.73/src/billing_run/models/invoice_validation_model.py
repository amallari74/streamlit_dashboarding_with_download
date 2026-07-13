from utils import db_util
import pandas as pd
from datetime import datetime
import os
import numpy as np
from typing import Dict, Any, List, Optional

def fetch_invoice_by_id(invoice_id: int, schema: str = "", database: str = None) -> pd.DataFrame:
    """Fetch basic invoice header information by ID"""
    query = f"""
    WITH sample_invoice AS (
        SELECT
            id,
            invoice_date,
            company_id,
            partner_id,
            status,
            total,
            balance,
            created_dt,
            updated_dt,
            is_email_sent,
            approved,
            business_unit_code,
            currency_id,
            carried_balance,
            sales_tax,
            alternate_id,
            guid,
            billing_id,
            billing_number,
            archive_rows_match
        FROM {schema}invoice
        WHERE id = :invoice_id
    )
    SELECT * FROM sample_invoice
    ORDER BY id
    """
    try:
        return db_util.query(query, params={"invoice_id": invoice_id}, db=database)
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        return pd.DataFrame()

def fetch_invoice_line_items(invoice_id: int, schema: str = "", database: str = None) -> pd.DataFrame:
    """Fetch all invoice line items (CIRA) for a specific invoice"""
    query = f"""
    WITH invoice_line_items AS (
        SELECT
            cira.id as line_item_id,
            cira.invoice_id,
            cira.sku,
            cira.quantity,
            cira.price,
            cira.total,
            cira.pax8_cost,
            cira.cost_total,
            cira.pax8_cost_total,
            cira.start_period,
            cira.end_period,
            cira.arrears_subscription_id,
            cira.completed_line_item_id,
            cira.product_id,
            cira.product_name,
            cira.company_id,
            cira.company_name,
            cira.partner_id,
            cira.partner_name,
            pr.anniversary_billing
        FROM {schema}csv_invoice_row_archive cira
        JOIN {schema}product pr ON cira.product_id = pr.id
        WHERE cira.invoice_id = :invoice_id
        AND pr.anniversary_billing = true
    )
    SELECT * FROM invoice_line_items
    ORDER BY line_item_id DESC
    """
    try:
        return db_util.query(query, params={"invoice_id": invoice_id}, db=database)
    except Exception as e:
        print(f"Error fetching invoice line items: {str(e)}")
        return pd.DataFrame()

def fetch_invoice_subscriptions(invoice_id: int, schema: str = "", database: str = None) -> pd.DataFrame:
    """Fetch active subscriptions for a partner that should be on the invoice"""
    query = f"""
    WITH line_items AS (
        SELECT completed_line_item_id
        FROM {schema}csv_invoice_row_archive cira
        JOIN {schema}product pr ON cira.product_id = pr.id
        WHERE cira.invoice_id = :invoice_id
        AND pr.anniversary_billing = true
    ),
    subscriptions AS (
        SELECT
            s.id,
            s.original_subscription_id,
            s.completed_line_id,
            s.status,
            s.billing_cycle_start,
            s.billing_cycle_end,
            s.quantity,
            p.sku,
            p.name as product_name,
            p.vendor,
            s.partner_id,
            s.company_id,
            s.commitment_term_end_date,
            s.end_date,
            s.start_date,
            p.anniversary_billing
        FROM {schema}subscription s
        JOIN line_items li ON s.completed_line_id = li.completed_line_item_id
        LEFT JOIN {schema}product p ON s.product_id = p.id
        WHERE p.anniversary_billing = true
    )
    SELECT * FROM subscriptions
    ORDER BY id DESC
    """
    try:
        return db_util.query(query, params={"invoice_id": invoice_id}, db=database)
    except Exception as e:
        print(f"Error fetching subscriptions: {str(e)}")
        return pd.DataFrame()

def fetch_invoice_transactions(invoice_id: int, schema: str = "", database: str = None) -> pd.DataFrame:
    """Fetch completed transactions that should be on the invoice"""
    query = f"""
    WITH line_items AS (
        SELECT completed_line_item_id
        FROM {schema}csv_invoice_row_archive cira
        JOIN {schema}product pr ON cira.product_id = pr.id
        WHERE cira.invoice_id = :invoice_id
        AND pr.anniversary_billing = true
    ),
    transactions AS (
        SELECT
            t.guid as transaction_id,
            t.completed_line_item_id,
            t.subscription_id,
            t.sku,
            t.quantity,
            t.price,
            t.total,
            t.start_period,
            t.end_period,
            t.partner_id,
            t.company_id,
            t.product_name,
            t.product_vendor_id,
            t.pax8_cost,
            t.pax8_cost_total,
            t.cost_total,
            t.invoice_date,
            t.company_name,
            t.term,
            t.type,
            t.rate_plan_type,
            t.rate_type,
            t.service_start,
            t.charge_type,
            t.order_date,
            p.anniversary_billing
        FROM {schema}order_manager_transaction t
        JOIN {schema}completed_line_item cli ON t.completed_line_item_id = cli.guid
        JOIN line_items li ON cli.id = li.completed_line_item_id
        JOIN {schema}product p ON t.product_uuid = p.uuid
    )
    SELECT * FROM transactions
    ORDER BY transaction_id DESC
    """
    try:
        return db_util.query(query, params={"invoice_id": invoice_id}, db=database)
    except Exception as e:
        print(f"Error fetching transactions: {str(e)}")
        return pd.DataFrame()

def fetch_invoice_completed_line_items(invoice_id: int, schema: str = "", database: str = None) -> pd.DataFrame:
    """Fetch completed line items for a specific invoice"""
    query = f"""
    WITH line_items AS (
        SELECT completed_line_item_id
        FROM {schema}csv_invoice_row_archive cira
        JOIN {schema}product pr ON cira.product_id = pr.id
        WHERE cira.invoice_id = :invoice_id
        AND pr.anniversary_billing = true
    ),
    completed_line_items AS (
        SELECT
            cli.id,
            cli.guid,
            cli.partner_buy_rate,
            cli.actual_retail_price,
            cli.partner_gross_revenue,
            cli.partner_net_revenue,
            cli.partner_net_revenue_delta,
            cli.partner_gross_revenue_delta,
            cli.vendor_gross_revenue,
            cli.vendor_prorate_gross,
            cli.pax8_net_revenue,
            cli.pax8_gross_revenue,
            cli.pax8_gross_revenue_delta,
            cli.pax8_margin_in_dollars,
            cli.pax8_net_revenue_delta,
            cli.pax8_prorate_gross,
            cli.pax8_prorate_net,
            cli.wholesale_buy_rate,
            cli.quantity,
            cli.updated_dt,
            cli.created_dt,
            cli.term,
            cli.type,
            cli.sku,
            cli.rate_plan_type,
            cli.rate_plan_uuid,
            cli.term_in_months,
            cli.line_number,
            cli.completed_order_id,
            cli.total,
            cli.prorate_waived,
            cli.recurring_total,
            pr.anniversary_billing
        FROM {schema}completed_line_item cli
        JOIN line_items li ON cli.id = li.completed_line_item_id
        JOIN {schema}product pr ON cli.product_id = pr.id
        WHERE pr.anniversary_billing = true
    )
    SELECT * FROM completed_line_items
    ORDER BY id DESC
    """
    
    try:
        return db_util.query(query, params={"invoice_id": invoice_id}, db=database)
    except Exception as e:
        print(f"Error fetching completed line items: {str(e)}")
        return pd.DataFrame() 


def fetch_all_partner_transactions(partner_id: int, schema: str = "", database: str = None) -> pd.DataFrame:
    """Fetch all transactions for a partner"""
    query = f"""
    WITH transactions AS (
        SELECT
            t.guid as transaction_id,
            t.completed_line_item_id,
            t.subscription_id,
            t.sku,
            t.quantity,
            t.price,
            t.total,
            t.start_period,
            t.end_period,
            t.partner_id,
            t.company_id,
            t.product_name,
            t.product_vendor_id,
            t.pax8_cost,
            t.pax8_cost_total,
            t.cost_total,
            t.invoice_date,
            t.company_name,
            t.term,
            t.type,
            t.rate_plan_type,
            t.rate_type,
            t.service_start,
            t.charge_type,
            t.order_date,
            pr.anniversary_billing
        FROM {schema}order_manager_transaction t
        JOIN {schema}partner p on p.guid = t.partner_id
        JOIN {schema}product pr ON t.product_uuid = pr.uuid
        WHERE p.id = :partner_id
        AND pr.anniversary_billing = true
        AND t.order_date >= '2024-01-01'
    )
    SELECT * FROM transactions
    ORDER BY transaction_id DESC
    """
    
    try:
        return db_util.query(query, params={"partner_id": partner_id}, db=database)
    except Exception as e:
        print(f"Error fetching partner transactions: {str(e)}")
        return pd.DataFrame()

def fetch_all_partner_subscriptions(partner_id: int, schema: str = "", database: str = None) -> pd.DataFrame:
    """Fetch all subscriptions for a partner"""
    query = f"""
    WITH subscriptions AS (
        SELECT
            s.id,
            s.original_subscription_id,
            s.completed_line_id,
            s.status,
            s.billing_cycle_start,
            s.billing_cycle_end,
            s.quantity,
            pr.sku,
            pr.name as product_name,
            pr.vendor,
            s.partner_id,
            s.company_id,
            s.commitment_term_end_date,
            s.end_date,
            s.start_date,
            pr.anniversary_billing
        FROM {schema}subscription s
        JOIN {schema}partner p ON s.partner_id = p.id
        LEFT JOIN {schema}product pr ON s.product_id = pr.id
        WHERE p.id = :partner_id
        AND pr.anniversary_billing = true
        AND s.created_dt >= '2024-01-01'
    )
    SELECT * FROM subscriptions
    ORDER BY id DESC
    """
    
    try:
        return db_util.query(query, params={"partner_id": partner_id}, db=database)
    except Exception as e:
        print(f"Error fetching partner subscriptions: {str(e)}")
        return pd.DataFrame()

def fetch_all_partner_line_items(partner_id: int, schema: str = "", database: str = None) -> pd.DataFrame:
    """Fetch all line items for a partner"""
    query = f"""
    WITH line_items AS (
        SELECT
            cira.id as line_item_id,
            cira.invoice_id,
            cira.sku,
            cira.quantity,
            cira.price,
            cira.total,
            cira.pax8_cost,
            cira.cost_total,
            cira.pax8_cost_total,
            cira.start_period,
            cira.end_period,
            cira.arrears_subscription_id,
            cira.completed_line_item_id,
            cira.product_id,
            cira.product_name,
            cira.company_id,
            cira.company_name,
            cira.partner_id,
            cira.partner_name,
            pr.anniversary_billing
        FROM {schema}csv_invoice_row_archive cira
        JOIN {schema}invoice i on i.partner_id = cira.partner_id
        JOIN {schema}product pr ON cira.product_id = pr.id
        WHERE i.partner_id = :partner_id
        AND pr.anniversary_billing = true
        AND cira.created_dt >= '2024-01-01'
    )
    SELECT * FROM line_items
    ORDER BY line_item_id DESC
    """
    
    try:
        return db_util.query(query, params={"partner_id": partner_id}, db=database)
    except Exception as e:
        print(f"Error fetching partner line items: {str(e)}")
        return pd.DataFrame()

def fetch_all_completed_line_items(partner_id: int, schema: str = "", database: str = None) -> pd.DataFrame:
    """Fetch all completed line items for a partner"""
    query = f"""
    WITH completed_line_items AS (
        SELECT
            cli.id,
            cli.guid,
            cli.partner_buy_rate,
            cli.partner_gross_revenue,
            cli.partner_net_revenue,
            cli.partner_net_revenue_delta,
            cli.partner_gross_revenue_delta,
            cli.vendor_gross_revenue,
            cli.vendor_prorate_gross,
            cli.pax8_net_revenue,
            cli.pax8_gross_revenue,
            cli.pax8_gross_revenue_delta,
            cli.pax8_margin_in_dollars,
            cli.pax8_net_revenue_delta,
            cli.pax8_prorate_gross,
            cli.pax8_prorate_net,
            cli.wholesale_buy_rate,
            cli.actual_retail_price,
            cli.quantity,
            cli.updated_dt,
            cli.created_dt,
            cli.term,
            cli.type,
            cli.sku,
            cli.rate_plan_type,
            cli.rate_plan_uuid,
            cli.term_in_months,
            cli.line_number,
            cli.completed_order_id,
            cli.total,
            cli.prorate_waived,
            cli.recurring_total,
            pr.anniversary_billing
        FROM {schema}completed_line_item cli
        JOIN {schema}completed_order co on cli.completed_order_id = co.id
        JOIN {schema}partner p on p.id = co.partner_id
        JOIN {schema}product pr ON cli.product_id = pr.id
        WHERE p.id = :partner_id
        AND pr.anniversary_billing = true
        AND cli.created_dt >= '2024-01-01'
    )
    SELECT * FROM completed_line_items
    ORDER BY id DESC
    """
    
    try:
        return db_util.query(query, params={"partner_id": partner_id}, db=database)
    except Exception as e:
        print(f"Error fetching completed line items: {str(e)}")
        return pd.DataFrame()

