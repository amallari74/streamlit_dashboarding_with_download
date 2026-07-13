import streamlit as st
import pandas as pd
from utils import db_util
from typing import List, Optional

@st.cache_data(ttl=600)
def fetch_arrears_tasks(schema: str = "", database: str = None):
    """
    Fetches arrears tasks data from the database for the current month.
    With status mapping applied at the query level.
    
    Args:
        schema (str): Database schema prefix. Defaults to empty string.
        database (str): Database to query. Defaults to None, which will use postgresql if available, otherwise redshift.
    
    Returns:
        DataFrame: Pandas DataFrame containing arrears tasks data with product info and mapped statuses
    """      
    query = f"""
    WITH
        arrears_tasks AS (
            SELECT
                id
                , subscription_id
                , product_id
                , status
                -- Map specific statuses to 'new' at the query level
                , CASE 
                    WHEN status = 'waiting' THEN 'new'
                    WHEN status = 'rap_running' THEN 'new'
                    WHEN status = 'usage_running' THEN 'new'
                    ELSE status
                  END AS status_clean
                , run_on
                , run_duration
                , error_message
                , error_count
                , created_dt
                , updated_dt
                , 'arrears_task' as table_name
            FROM {schema}arrears_task
            WHERE method = 'createArrearsBillsForSubscription'
            AND DATE_TRUNC('month', run_on) >= DATE_TRUNC('month', CURRENT_DATE)
            UNION ALL
            SELECT
                id
                , subscription_id
                , product_id
                , status
                -- Map specific statuses to 'new' at the query level
                , CASE 
                    WHEN status = 'waiting' THEN 'new'
                    WHEN status = 'rap_running' THEN 'new'
                    WHEN status = 'usage_running' THEN 'new'
                    ELSE status
                  END AS status_clean
                , run_on
                , run_duration
                , error_message
                , error_count
                , created_dt
                , updated_dt
                , 'arrears_task_2' as table_name
            FROM {schema}arrears_task_2
            WHERE method = 'createArrearsBillsForSubscription'
            AND DATE_TRUNC('month', run_on) >= DATE_TRUNC('month', CURRENT_DATE))
    SELECT art.*, s.original_subscription_id, p.name as product_name, p.vendor
    FROM arrears_tasks art
    JOIN {schema}subscription s ON s.id = art.subscription_id
    JOIN {schema}product p ON art.product_id = p.id
    """
    
    results = db_util.query(query, db=database, ttl=600)
    return results

@st.cache_data(ttl=600)
def fetch_billing_tasks(schema: str = "", methods: Optional[List[str]] = None, database: str = None) -> pd.DataFrame:
    """
    Fetches billing tasks data from multiple tables for the current month.
    Includes invoice generation, tax calculation, and invoice release tasks.
    
    Args:
        schema (str): Database schema prefix. Defaults to empty string.
        database (str): Database to query. Defaults to None, which will use postgresql if available, otherwise redshift.
        methods (Optional[List[str]]): List of methods to filter by. If None, defaults to the full set of billing methods.
    
    Returns:
        DataFrame: Pandas DataFrame containing billing tasks with extracted JSON payload data
    """
    # Set default methods if not provided
    if methods is None:
        methods = [
            'createPartnerInvoice',
            'createCompanyInvoice',
            'calculateAndStoreSalesTaxRatesForPartner',
            'calculateAndStoreSalesTaxRatesForCompany',
            'sendInvoiceForCompany',
            'sendInvoiceForPartner'
        ]
    methods_str = ", ".join(f"'{m}'" for m in methods)
    
    # Database-specific SQL functions
    is_valid_json = "IS_VALID_JSON(payload)" if database == "redshift" else "(payload::jsonb is not null)"
    json_extract = lambda path: f"JSON_EXTRACT_PATH_TEXT(payload, '{path}')" if database == "redshift" else f"payload::json->>'{path}'"
    
    query = f"""
    WITH billing_unioned AS (
        (
            SELECT
                "id",
                "service",
                "method",
                "payload",
                "status",
                "status" AS "status_clean", -- Add status_clean column for consistency
                "created_dt",
                "updated_dt",
                "error_count",
                "error_message",
                "run_on",
                "run_duration",
                "partner_id",
                "run_on_date_time",
                NULL as "guid",
                'billing_task' as "table_name"
            FROM {schema}billing_task
            WHERE method IN ({methods_str})
                AND run_on >= DATE_TRUNC('month', CURRENT_DATE)
        )

        UNION ALL

        (
            SELECT
                "id",
                "service",
                "method",
                "payload",
                "status",
                "status" AS "status_clean", -- Add status_clean column for consistency
                "created_dt",
                "updated_dt",
                "error_count",
                "error_message",
                "run_on",
                "run_duration",
                "partner_id",
                NULL as "run_on_date_time",
                "guid",
                'billing_task_2' as "table_name"
            FROM {schema}billing_task_2
            WHERE method IN ({methods_str})
                AND run_on >= DATE_TRUNC('month', CURRENT_DATE)
        )

        UNION ALL

        (
            SELECT
                "id",
                "service",
                "method",
                "payload",
                "status",
                "status" AS "status_clean", -- Add status_clean column for consistency
                "created_dt",
                "updated_dt",
                "error_count",
                "error_message",
                "run_on",
                "run_duration",
                NULL as "partner_id",
                NULL as "run_on_date_time",
                NULL as "guid",
                'mca_task' as "table_name"
            FROM {schema}mca_task
            WHERE method IN ({methods_str})
                AND run_on >= DATE_TRUNC('month', CURRENT_DATE)
        )

        UNION ALL

        (
            SELECT
                "id",
                "service",
                "method",
                "payload",
                "status",
                "status" AS "status_clean", -- Add status_clean column for consistency
                "created_dt",
                "updated_dt",
                "error_count",
                "error_message",
                "run_on",
                "run_duration",
                NULL as "partner_id",
                NULL as "run_on_date_time",
                NULL as "guid",
                'mca_task_2' as "table_name"
            FROM {schema}mca_task_2
            WHERE method IN ({methods_str})
                AND run_on >= DATE_TRUNC('month', CURRENT_DATE)
        )

        UNION ALL

        (
            SELECT
                "id",
                "service",
                "method",
                "payload",
                "status",
                "status" AS "status_clean", -- Add status_clean column for consistency
                "created_dt",
                "updated_dt",
                "error_count",
                "error_message",
                "run_on",
                "run_duration",
                NULL as "partner_id",
                NULL as "run_on_date_time",
                NULL as "guid",
                'mca_task_3' as "table_name"
            FROM {schema}mca_task_3
            WHERE method IN ({methods_str})
                AND run_on >= DATE_TRUNC('month', CURRENT_DATE)
        )

        UNION ALL

        (
            SELECT
                "id",
                "service",
                "method",
                "payload",
                "status",
                "status" AS "status_clean", -- Add status_clean column for consistency
                "created_dt",
                "updated_dt",
                "error_count",
                "error_message",
                "run_on",
                "run_duration",
                NULL as "partner_id",
                NULL as "run_on_date_time",
                NULL as "guid",
                'mca_task_4' as "table_name"
            FROM {schema}mca_task_4
            WHERE method IN ({methods_str})
                AND run_on >= DATE_TRUNC('month', CURRENT_DATE)
        )

        UNION ALL

        (
            SELECT
                "id",
                "service",
                "method",
                "payload",
                "status",
                "status" AS "status_clean", -- Add status_clean column for consistency
                "created_dt",
                "updated_dt",
                "error_count",
                "error_message",
                "run_on",
                "run_duration",
                NULL as "partner_id",
                NULL as "run_on_date_time",
                NULL as "guid",
                'mca_task_5' as "table_name"
            FROM {schema}mca_task_5
            WHERE method IN ({methods_str})
                AND run_on >= DATE_TRUNC('month', CURRENT_DATE)
        )

        UNION ALL

        (
            SELECT
                "id",
                "service",
                "method",
                "payload",
                "status",
                "status" AS "status_clean", -- Add status_clean column for consistency
                "created_dt",
                "updated_dt",
                "error_count",
                "error_message",
                "run_on",
                "run_duration",
                NULL as "partner_id",
                NULL as "run_on_date_time",
                NULL as "guid",
                'widget_task' as "table_name"
            FROM {schema}widget_task
            WHERE method IN ({methods_str})
                AND run_on >= DATE_TRUNC('month', CURRENT_DATE)
        )
        UNION ALL

        (
            SELECT
                "id",
                "service",
                "method",
                "payload",
                "status",
                "status" AS "status_clean", -- Add status_clean column for consistency
                "created_dt",
                "updated_dt",
                "error_count",
                "error_message",
                "run_on",
                "run_duration",
                NULL as "partner_id",
                NULL as "run_on_date_time",
                NULL as "guid",
                'report_task' as "table_name"
            FROM {schema}report_task
            WHERE method IN ({methods_str})
                AND run_on >= DATE_TRUNC('month', CURRENT_DATE)
        )
        UNION ALL

        (
            SELECT
                "id",
                "service",
                "method",
                "payload",
                "status",
                "status" AS "status_clean", -- Add status_clean column for consistency
                "created_dt",
                "updated_dt",
                "error_count",
                "error_message",
                "run_on",
                "run_duration",
                NULL as "partner_id",
                NULL as "run_on_date_time",
                NULL as "guid",
                'erp_task' as "table_name"
            FROM {schema}erp_task
            WHERE method IN ({methods_str})
                AND run_on >= DATE_TRUNC('month', CURRENT_DATE)
        )
    ),

    final AS (
        SELECT
            id,
            guid,
            partner_id,
            table_name,
            service,
            method,
            payload,
            CASE WHEN {is_valid_json} THEN NULLIF({json_extract('partnerId')}, '') END AS partner_id_parsed,
            CASE WHEN {is_valid_json} THEN NULLIF({json_extract('companyId')}, '') END AS company_id_parsed,
            status,
            TRIM(LOWER(status)) AS status_clean,
            error_message,
            error_count,
            run_duration,
            run_on,
            DATE_TRUNC('MONTH', run_on) AS run_on_month,
            created_dt,
            updated_dt
        FROM billing_unioned
    )

    SELECT * FROM final
    """
    
    results = db_util.query(query, db=database, ttl=600)
    return results

def get_task_category_dataframes(schema: str = "", database: str = None):
    """
    Fetches all task data and splits it into category-specific DataFrames.
    
    Args:
        schema (str): Database schema prefix. Defaults to empty string.
        database (str): Database to query. Defaults to None, which will use postgresql if available, otherwise redshift.
    
    Returns:
        dict: Dictionary with task category data frames
    """
    arrears_tasks_df = fetch_arrears_tasks(schema, database)
    
    # Create task category datasets by passing methods directly to fetch_billing_tasks
    invoice_generation_df = fetch_billing_tasks(schema, ['createPartnerInvoice', 'createCompanyInvoice'], database)
    invoice_release_df = fetch_billing_tasks(schema, ['sendInvoiceForCompany', 'sendInvoiceForPartner'], database)
    tax_calculation_df = fetch_billing_tasks(schema, ['calculateAndStoreSalesTaxRatesForPartner', 'calculateAndStoreSalesTaxRatesForCompany'], database)
    
    return {
        "Arrears Tasks": arrears_tasks_df,
        "Invoice Generation": invoice_generation_df,
        "Invoice Release": invoice_release_df,
        "Tax Calculations": tax_calculation_df
    } 

def fetch_arrears_usage_variance(schema: str = "", database: str = None):
    """
    Fetches arrears usage variance data for the last 6 months.
    
    Args:
        schema (str): Database schema prefix. Defaults to empty string.
        database (str): Database to query. Defaults to None, which will use postgresql if available, otherwise redshift.
    
    Returns:
        DataFrame: Pandas DataFrame containing arrears usage variance data
    """  
    # Define date subtraction function based on database
    if database == "redshift":
        month_interval = lambda n: f"INTERVAL '-{n} Month'"
    else:  # PostgreSQL
        month_interval = lambda n: f"interval '-{n} month'"
    
    query = f"""
    WITH arrears_variance AS (
        SELECT
            p.id AS partner_id,
            p.name,
            pr.vendor,
            pr.id AS product_id,
            s.status AS sub_status,
            s.start_date AS sub_start_date,
            s.end_date AS sub_end_date,
            cli.arrears_subscription_id,
            s.original_subscription_id,
            ROUND(SUM(CASE WHEN date_trunc('MONTH', cli.provision_start)::DATE = date_trunc('MONTH', current_date + {month_interval(6)})::DATE THEN cli.pax8_gross_revenue ELSE 0 END), 2) AS six_months_prior_gross_revenue,
            ROUND(SUM(CASE WHEN date_trunc('MONTH', cli.provision_start)::DATE = date_trunc('MONTH', current_date + {month_interval(5)})::DATE THEN cli.pax8_gross_revenue ELSE 0 END), 2) AS five_months_prior_gross_revenue,
            ROUND(SUM(CASE WHEN date_trunc('MONTH', cli.provision_start)::DATE = date_trunc('MONTH', current_date + {month_interval(4)})::DATE THEN cli.pax8_gross_revenue ELSE 0 END), 2) AS four_months_prior_gross_revenue,
            ROUND(SUM(CASE WHEN date_trunc('MONTH', cli.provision_start)::DATE = date_trunc('MONTH', current_date + {month_interval(3)})::DATE THEN cli.pax8_gross_revenue ELSE 0 END), 2) AS three_months_prior_gross_revenue,
            ROUND(SUM(CASE WHEN date_trunc('MONTH', cli.provision_start)::DATE = date_trunc('MONTH', current_date + {month_interval(2)})::DATE THEN cli.pax8_gross_revenue ELSE 0 END), 2) AS two_months_prior_gross_revenue,
            ROUND(SUM(CASE WHEN date_trunc('MONTH', cli.provision_start)::DATE = date_trunc('MONTH', current_date + {month_interval(1)})::DATE THEN cli.pax8_gross_revenue ELSE 0 END), 2) AS prior_month_gross_revenue,
            ROUND(SUM(CASE WHEN date_trunc('MONTH', cli.provision_start)::DATE = date_trunc('MONTH', current_date)::DATE THEN cli.pax8_gross_revenue ELSE 0 END), 2) AS current_month_gross_revenue,
            ROUND(SUM(CASE WHEN date_trunc('MONTH', cli.provision_start)::DATE = date_trunc('MONTH', current_date)::DATE THEN cli.quantity ELSE 0 END), 2) AS current_month_quantity,
            bu.unique_code AS business_unit,
            cli.currency_id,
            cli.type,
            (
                ROUND(SUM(CASE WHEN date_trunc('MONTH', cli.provision_start)::DATE = date_trunc('MONTH', current_date)::DATE THEN cli.pax8_gross_revenue ELSE 0 END), 2) -
                ROUND(SUM(CASE WHEN date_trunc('MONTH', cli.provision_start)::DATE = date_trunc('MONTH', current_date + {month_interval(1)})::DATE THEN cli.pax8_gross_revenue ELSE 0 END), 2)
            ) AS gross_revenue_difference
        FROM
            {schema}subscription s
            INNER JOIN {schema}completed_line_item cli ON s.id = cli.arrears_subscription_id
            INNER JOIN {schema}partner p ON s.partner_id = p.id
            INNER JOIN {schema}product pr ON s.product_id = pr.id
            INNER JOIN {schema}business_unit_cache bu ON p.business_unit_guid = bu.uuid
        WHERE
            cli.voided = 'f'
            AND cli.arrears_subscription_id IS NOT NULL
            AND cli.provision_start >= date_trunc('MONTH', current_date + {month_interval(6)})::DATE
        GROUP BY
            p.id, p.name, cli.arrears_subscription_id, s.status, s.start_date, s.end_date,
            pr.vendor, pr.id, s.original_subscription_id, bu.unique_code, cli.currency_id, cli.type
        ORDER BY
            gross_revenue_difference DESC
    ), arrears_variance_static_exchange AS (
        SELECT ar.*,
            CASE
                WHEN c.api_code = 'USD' THEN 1
                WHEN c.api_code = 'CAD' THEN 0.74
                WHEN c.api_code = 'GBP' THEN 1.24
                WHEN c.api_code = 'EUR' THEN 1.07
                WHEN c.api_code = 'NOK' THEN 0.091
                WHEN c.api_code = 'SEK' THEN 0.092
                WHEN c.api_code = 'DKK' THEN 0.14
                WHEN c.api_code = 'AUD' THEN 0.66
                WHEN c.api_code = 'NZD' THEN 0.61
                WHEN c.api_code = 'THB' THEN 0.029
                WHEN c.api_code = 'IDR' THEN 0.000067
                WHEN c.api_code = 'MYR' THEN 0.22
                WHEN c.api_code = 'SGD' THEN 0.74
                WHEN c.api_code = 'VND' THEN 0.000043
                WHEN c.api_code = 'PHP' THEN 0.018
                ELSE 1.00
            END AS exchange_rate_multiple
          FROM arrears_variance ar
        JOIN {schema}currency c ON ar.currency_id = c.id
    )
    SELECT
        ar.partner_id AS partner_id,
        ar.name AS partner_name,
        ar.vendor,
        ar.product_id,
        p.name AS subscription_product_name,
        ar.sub_status,
        ar.sub_start_date,
        ar.sub_end_date,
        ar.arrears_subscription_id,
        ar.original_subscription_id,
        ar.business_unit,
        ar.type,
        apuc.billing_day_of_month AS billing_task_run_day,
        ar.exchange_rate_multiple * ar.six_months_prior_gross_revenue AS usd_6_month_prior_revenue,
        ar.exchange_rate_multiple * ar.five_months_prior_gross_revenue AS usd_5_month_prior_revenue,
        ar.exchange_rate_multiple * ar.four_months_prior_gross_revenue AS usd_4_month_prior_revenue,
        ar.exchange_rate_multiple * ar.three_months_prior_gross_revenue AS usd_3_month_prior_revenue,
        ar.exchange_rate_multiple * ar.two_months_prior_gross_revenue AS usd_2_month_prior_revenue,
        ar.exchange_rate_multiple * ar.prior_month_gross_revenue AS usd_prior_month_revenue,
        ar.exchange_rate_multiple * ar.current_month_gross_revenue AS usd_current_month_gross_revenue,
        ar.exchange_rate_multiple * ar.gross_revenue_difference AS prior_vs_current_revenue_difference,
        (
            (ar.current_month_gross_revenue - ar.prior_month_gross_revenue) /
            NULLIF(ar.prior_month_gross_revenue, 0)
        ) * 100 AS percentage_change,
        (
            (ar.current_month_gross_revenue - ar.five_months_prior_gross_revenue) /
            NULLIF(ar.five_months_prior_gross_revenue, 0)
        ) * 100 AS percentage_change_5_months,
        ar.current_month_quantity,
        (
            (
                (
                    (ar.current_month_gross_revenue - ar.prior_month_gross_revenue) /
                    NULLIF(ar.prior_month_gross_revenue, 0)
                ) +
                (
                    (ar.prior_month_gross_revenue - ar.two_months_prior_gross_revenue) /
                    NULLIF(ar.two_months_prior_gross_revenue, 0)
                ) +
                (
                    (ar.two_months_prior_gross_revenue - ar.three_months_prior_gross_revenue) /
                    NULLIF(ar.three_months_prior_gross_revenue, 0)
                ) +
                (
                    (ar.three_months_prior_gross_revenue - ar.four_months_prior_gross_revenue) /
                    NULLIF(ar.four_months_prior_gross_revenue, 0)
                ) +
                (
                    (ar.four_months_prior_gross_revenue - ar.five_months_prior_gross_revenue) /
                    NULLIF(ar.five_months_prior_gross_revenue, 0)
                ) +
                (
                    (ar.five_months_prior_gross_revenue - ar.six_months_prior_gross_revenue) /
                    NULLIF(ar.six_months_prior_gross_revenue, 0)
                )
            ) / 6
        ) * 100 AS avg_6_month_percentage_variance
    FROM
        arrears_variance_static_exchange ar
        JOIN {schema}product p ON ar.product_id = p.id
        LEFT JOIN {schema}arrears_configuration_assignment aca ON ar.product_id = aca.product_id
        LEFT JOIN {schema}arrears_product_usage_configuration apuc ON aca.arrears_product_usage_configuration_id = apuc.id
    """
    
    results = db_util.query(query, db=database)
    return results 

def fetch_arrears_product_configurations(schema: str = "", database: str = None):
    """
    Fetches arrears product usage configuration data.
    
    Args:
        schema (str): Database schema prefix. Defaults to empty string.
        database (str): Database to query. Defaults to None, which will use postgresql if available, otherwise redshift.
    
    Returns:
        DataFrame: Pandas DataFrame containing arrears product usage configuration data
    """     
    query = f"""
    SELECT name, task_runner, billing_day_of_month 
    FROM {schema}arrears_product_usage_configuration
    """
    
    results = db_util.query(query, db=database)
    return results