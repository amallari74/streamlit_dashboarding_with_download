from utils import db_util
import pandas as pd
from typing import Dict, Any, List, Optional


def fetch_task_status(selected_month):
    """Fetches the aggregated task status for arrears tasks."""
    query = """
        WITH monthly_totals AS (
            SELECT 
                run_on_month,
                SUM(tasks_total) AS month_total_tasks,
                SUM(finished_tasks_total) AS month_total_finished,
                SUM(errored_tasks_total) AS month_total_errors,
                SUM(reviewed_tasks_total) AS month_total_reviewed
            FROM mart_observability_and_automation.agg_arrears_task_region_vendor_month
            GROUP BY run_on_month
        ),
        prev_month_totals AS (
            SELECT 
                run_on_month,
                month_total_tasks,
                month_total_finished,
                month_total_errors,
                month_total_reviewed,
                LAG(month_total_tasks) OVER (ORDER BY run_on_month) AS prev_tasks_total,
                LAG(month_total_finished) OVER (ORDER BY run_on_month) AS prev_finished_total,
                LAG(month_total_errors) OVER (ORDER BY run_on_month) AS prev_errored_total,
                LAG(month_total_reviewed) OVER (ORDER BY run_on_month) AS prev_reviewed_total
            FROM monthly_totals
        )
        SELECT 
            a.*,
            COALESCE(p.prev_tasks_total, 0) AS prev_tasks_total,
            COALESCE(p.prev_finished_total, 0) AS prev_finished_total,
            COALESCE(p.prev_errored_total, 0) AS prev_errored_total,
            COALESCE(p.prev_reviewed_total, 0) AS prev_reviewed_total
        FROM mart_observability_and_automation.agg_arrears_task_region_vendor_month a
        LEFT JOIN prev_month_totals p ON a.run_on_month = p.run_on_month
        WHERE a.run_on_month = :selected_month
    """
    params = {"selected_month": selected_month}
    return db_util.query(query, params=params)


def fetch_arrears_tasks(invoice_month = None):
    if invoice_month is None:
        arrears_tasks_date_clause = "DATE_TRUNC('MONTH', current_date)::DATE"
    else: 
        arrears_tasks_date_clause = f"DATE_TRUNC('MONTH', '{invoice_month}'::date)::DATE"
        
    query = f"""
    SELECT
        run_on, current_status_clean as status, count(*)
    FROM
        mart_observability_and_automation.fact_arrears_task_status_history
    WHERE
        run_on_month = {arrears_tasks_date_clause}
    GROUP BY run_on, status
    ORDER BY run_on, status    """
    return db_util.query(query, params={})

def fetch_error_categories(selected_month):
    """Fetches error categorization for arrears tasks."""
    query = """
        SELECT 
            run_on_month, 
            vendor, 
            error_category, 
            errors_total, 
            errors_resolved, 
            errors_unresolved 
        FROM mart_observability_and_automation.agg_arrears_error_category_vendor_month
        WHERE run_on_month = :selected_month
    """
    params = {"selected_month": selected_month}
    return db_util.query(query, params=params)


def fetch_arrears_vendor_list():
    """Fetches list of vendors for arrears tasks"""
    query = """
        SELECT
            DISTINCT sub.vendor AS vendor
        FROM mart_observability_and_automation.stg__cc_arrears_task_unioned AS at
        LEFT JOIN mart_observability_and_automation.int_subscription_joined AS sub on at.subscription_id=sub.id
        WHERE sub.vendor IS NOT NULL
        ORDER BY sub.vendor desc
    """
    return db_util.query(query)

def fetch_arrears_task_details(run_on, vendor: str, method: str, schema: str, database: str) -> pd.DataFrame:
    """Fetches details for arrears tasks info used for Jira ticket creation and prevent SQL injection based on Qobo PR feedback"""
    allowed_schemas = ['', 'cc.']
    if schema not in allowed_schemas:
        raise ValueError(f"Invalid schema: {schema}")

    query = f"""
    WITH combined_arrears_task AS (
        SELECT
            REPLACE(LEFT(at.error_message,300),'|', '-') AS error_message,
            sub.partner_id || ' - ' || p.name AS partner_info,
            pa.name AS product_info,
            at.subscription_id,
            sub.original_subscription_id,
            at.method,
            at.status,
            bu.unique_code AS partner_region,
            pa.vendor,
            at.run_on::date as run_on
        FROM {schema}arrears_task AS at
            LEFT JOIN {schema}subscription sub ON at.subscription_id = sub.id
            LEFT JOIN {schema}partner AS p ON sub.partner_id = p.id
            LEFT JOIN {schema}product AS pa ON sub.product_id = pa.id
            LEFT JOIN {schema}business_unit_cache AS bu ON p.business_unit_guid = bu.uuid
        UNION ALL
        SELECT
            REPLACE(LEFT(at2.error_message,300),'|', '-') AS error_message,
            sub.partner_id || ' - ' || p.name AS partner_info,
            pa.name AS product_info,
            at2.subscription_id,
            sub.original_subscription_id,
            at2.method,
            at2.status,
            bu.unique_code AS partner_region,
            pa.vendor,
            at2.run_on::date as run_on
        FROM {schema}arrears_task_2 AS at2
            LEFT JOIN {schema}subscription sub ON at2.subscription_id = sub.id
            LEFT JOIN {schema}partner AS p ON sub.partner_id = p.id
            LEFT JOIN {schema}product AS pa ON sub.product_id = pa.id
            LEFT JOIN {schema}business_unit_cache AS bu ON p.business_unit_guid = bu.uuid
    )
    SELECT * 
    FROM combined_arrears_task
    WHERE vendor = :vendor
        AND run_on = :run_on
        AND method = :method
    """
    try:
        params = {"vendor": vendor, "run_on": run_on, "method": method}
        return db_util.query(query, params=params, db=database)
    except Exception as e:
        print(f"Error fetching arrears task details: {str(e)}")
        return pd.DataFrame()


def fetch_manual_arrears_tasks(invoice_month = None):
    """Fetch manual arrears tasks data."""
    if invoice_month is None:
        manual_arrears_tasks_date_clause = "DATE_TRUNC('MONTH', current_date)::DATE"
    else: 
        manual_arrears_tasks_date_clause = f"DATE_TRUNC('MONTH', '{invoice_month}'::date)::DATE"
        
    query = f"""
    select vendor,
        manual_arrears_revenue_usd_2_months_prior as month_2,
        manual_arrears_revenue_usd_1_month_prior as month_1,
        manual_arrears_revenue_usd_current_month as month_0,
        manual_arrears_revenue_usd_diff_current_month as variance
    from mart_observability_and_automation.agg_arrears_vendor_month
    where provision_start_month = {manual_arrears_tasks_date_clause}
    and current_month_manual_arrears_rank <= 5
    order by current_month_manual_arrears_rank
    """
    return db_util.query(query, params={})

def fetch_arrears_error_totals(invoice_month = None):
    """Fetch arrears error totals data."""
    if invoice_month is None:
        arrears_error_totals_date_clause = "DATE_TRUNC('MONTH', current_date)::DATE"
    else: 
        arrears_error_totals_date_clause = f"DATE_TRUNC('MONTH', '{invoice_month}'::date)::DATE"
        
    query = f"""
    SELECT
        sum(errored_tasks_unresolved) as errored_tasks_unresolved,
        sum(errored_tasks_resolved) as errored_tasks_resolved,
        sum(errored_tasks_total) as errored_tasks_total
    FROM mart_observability_and_automation.agg_arrears_task_region_vendor_month
    WHERE run_on_month = {arrears_error_totals_date_clause}
    """
    return db_util.query(query, params={})

