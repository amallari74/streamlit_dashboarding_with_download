from utils import db_util
import streamlit as st

def fetch_invoice_count(invoice_month = None):
    """Fetch the invoice count KPI."""
    if invoice_month is None:
        invoice_count_date_clause = "DATE_TRUNC('MONTH', current_date)::DATE"
    else: 
        invoice_count_date_clause = f"DATE_TRUNC('MONTH', '{invoice_month}'::date)::DATE"
        
    query = f"""
    select
        'Invoice Count' as "Metric",
        sum(invoice_count_2_months_prior) as month_2,
        sum(invoice_count_1_month_prior) as month_1,
        sum(invoice_count_current_month) as month_0,
        sum(invoice_count_diff_current_month) as variance
    from mart_observability_and_automation.agg_invoice_region_type_month
    where invoice_date = {invoice_count_date_clause}
    """
    return db_util.query(query)


def fetch_invoice_balance(invoice_month = None):
    """Fetch invoice balance data."""
    if invoice_month is None:
        invoice_count_date_clause = "DATE_TRUNC('MONTH', current_date)::DATE"
    else: 
        invoice_count_date_clause = f"DATE_TRUNC('MONTH', '{invoice_month}'::date)::DATE"
        
    query = f"""
    select region,
        sum(balance_usd_2_months_prior) as month_2,
        sum(balance_usd_1_month_prior) as month_1,
        sum(balance_usd_current_month) as month_0,
        sum(balance_usd_diff_current_month) as variance
    from mart_observability_and_automation.agg_invoice_region_type_month
    where invoice_date = {invoice_count_date_clause}
    group by region
    order by month_0 desc
    """
    return db_util.query(query, params={})


def fetch_ledger_health(invoice_month = None):
    """Fetch ledger health KPI."""
    if invoice_month is None:
        ledger_health_start_date_clause = "DATE_TRUNC('MONTH', current_date)::DATE"
        ledger_health_1_month_prior_date_clause = "DATE_TRUNC('MONTH', DATEADD(month, -1, current_date))::DATE"
        ledger_health_end_date_clause = "DATE_TRUNC('MONTH', DATEADD(month, -2, current_date))::DATE"
    else: 
        ledger_health_start_date_clause = f"DATE_TRUNC('MONTH', '{invoice_month}'::date)::DATE"
        ledger_health_1_month_prior_date_clause = f"DATE_TRUNC('MONTH', DATEADD(month, -1, '{invoice_month}'::date))::DATE"
        ledger_health_end_date_clause = f"DATE_TRUNC('MONTH', DATEADD(month, -2, '{invoice_month}'::date))::DATE"
    query = f"""
    with health_view as (
    select
        'Ledger Health'::text as "Metric",
        sum(total_entities_healthy_ledger) as numerator,
        sum(total_entities) as denominator,
        (numerator::float / denominator) as ledger_health,
        transaction_month
    from mart_observability_and_automation.agg_ledger_health_region_month
    where transaction_month between {ledger_health_end_date_clause} and {ledger_health_start_date_clause}
    group by transaction_month
    order by transaction_month desc
    ),
    months as (
    select * from health_view
    pivot (
        max(ledger_health)
        for transaction_month in (
            {ledger_health_end_date_clause} as month_2,
            {ledger_health_1_month_prior_date_clause} as month_1,
            {ledger_health_start_date_clause} as month_0
        )
    ))
    select
        "Metric",
        max(month_2) as month_2,
        max(month_1) as month_1,
        max(month_0) as month_0,
        max(month_0) - max(month_1) as variance
    from months
    group by Metric
    """
    return db_util.query(query, params={})


def fetch_invoice_line_details(invoice_month = None):
    """Fetch invoice line details."""
    if invoice_month is None:
        invoice_line_details_date_clause = "DATE_TRUNC('MONTH', current_date)::DATE"
    else: 
        invoice_line_details_date_clause = f"DATE_TRUNC('MONTH', '{invoice_month}'::date)::DATE"
        
    query = f"""
    select * 
    from mart_observability_and_automation.agg_cira_region_type_month 
    where invoice_month = {invoice_line_details_date_clause}
    """
    return db_util.query(query, params={})


def fetch_credits_information(invoice_month = None):
    """Fetch credits information KPI."""
    if invoice_month is None:
        credits_information_start_date_clause = "DATE_TRUNC('MONTH', current_date)::DATE"
        credits_information_1_month_prior_date_clause = "DATE_TRUNC('MONTH', DATEADD(month, -1, current_date))::DATE"
        credits_information_end_date_clause = "DATE_TRUNC('MONTH', DATEADD(month, -2, current_date))::DATE"
    else: 
        credits_information_start_date_clause = f"DATE_TRUNC('MONTH', '{invoice_month}'::date)::DATE"
        credits_information_1_month_prior_date_clause = f"DATE_TRUNC('MONTH', DATEADD(month, -1, '{invoice_month}'::date))::DATE"
        credits_information_end_date_clause = f"DATE_TRUNC('MONTH', DATEADD(month, -2, '{invoice_month}'::date))::DATE"
    query = f"""
    select
        vendor,
        service_credit_usd_2_months_prior as month_2,
        service_credit_usd_1_month_prior as month_1,
        service_credit_usd_current_month as month_0,
        service_credit_usd_diff_current_month as variance
    from mart_observability_and_automation.agg_service_credit_vendor_month
    where transaction_month between {credits_information_end_date_clause} and {credits_information_start_date_clause}
    and current_month_service_credit_rank <= 5
    order by current_month_service_credit_rank
    """
    return db_util.query(query, params={})


def fetch_invoice_release_status(invoice_month = None):
    """Fetch invoice release status data."""
    if invoice_month is None:
        invoice_release_status_date_clause = "DATE_TRUNC('MONTH', current_date)::DATE"
    else: 
        invoice_release_status_date_clause = f"DATE_TRUNC('MONTH', '{invoice_month}'::date)::DATE"
        
    query = f"""
    select region, release_status, count(*) as value
    from mart_observability_and_automation.fact_invoice_nonvoid
    where invoice_date = {invoice_release_status_date_clause}
    group by region,release_status
    """
    return db_util.query(query, params={})

def fetch_invoice_health(invoice_month = None):
    """Fetch invoice health data."""
    if invoice_month is None:
        invoice_health_start_date_clause = "DATE_TRUNC('MONTH', current_date)::DATE"
        invoice_health_1_month_prior_date_clause = "DATE_TRUNC('MONTH', DATEADD(month, -1, current_date))::DATE"
        invoice_health_end_date_clause = "DATE_TRUNC('MONTH', DATEADD(month, -2, current_date))::DATE"
    else: 
        invoice_health_start_date_clause = f"DATE_TRUNC('MONTH', '{invoice_month}'::date)::DATE"
        invoice_health_1_month_prior_date_clause = f"DATE_TRUNC('MONTH', DATEADD(month, -1, '{invoice_month}'::date))::DATE"
        invoice_health_end_date_clause = f"DATE_TRUNC('MONTH', DATEADD(month, -2, '{invoice_month}'::date))::DATE"
    query = f"""
with health_view as (
    select
        'Invoice Health'::text as "Metric",
        sum(healthy_invoices) as numerator,
        sum(total_invoices) as denominator,
        (numerator::float / denominator) as invoice_health,
        invoice_month
    from mart_observability_and_automation.agg_invoice_health_region_month
    where invoice_month between {invoice_health_end_date_clause} and {invoice_health_start_date_clause}
    group by invoice_month
    order by invoice_month desc
    ),
    months as (
    select * from health_view
    pivot (
        max(invoice_health)
        for invoice_month in (
            {invoice_health_end_date_clause} as month_2,
            {invoice_health_1_month_prior_date_clause} as month_1,
            {invoice_health_start_date_clause} as month_0
        )
    ))
    select
        "Metric",
        max(month_2) as month_2,
        max(month_1) as month_1,
        max(month_0) as month_0,
        max(month_0) - max(month_1) as variance
    from months
    group by Metric    """
    return db_util.query(query, params={})

def fetch_invoice_row_details(schema="", database=None):
    """
    Fetch invoice row archive data for the last two months.
    
    Args:
        schema (str): Database schema prefix. Defaults to empty string.
        database (str): Database to query. Defaults to None, which will use postgresql if available, otherwise redshift.
        
    Returns:
        DataFrame: Pandas DataFrame containing invoice row archive data
    """       
    # Use database-specific date subtraction
    date_subtract = "dateadd('month', -1, current_date)" if database == "redshift" else "current_date - interval '1 month'"
    
    # Using subquery approach that works in both PostgreSQL and Redshift
    query = f"""
    WITH exchange_rates AS (
        SELECT 
            cira.id,
            cira.partner_id,
            cira.partner_name,
            cira.company_id,
            cira.invoice_id,
            cira.row_type,
            cira.term,
            cira.total,
            cira.total_after_tax,
            cira.cost_total,
            cira.cost_total_after_tax,
            cira.pax8_cost_total,
            cira.billed_by_pax8,
            cira.bills_in_arrears,
            cira.billing_fee,
            cira.billing_fee_after_tax,
            cira.currency_code,
            buc.unique_code as business_unit,
            CASE
                WHEN cira.currency_code = 'USD' THEN 1
                WHEN cira.currency_code = 'CAD' THEN 0.74
                WHEN cira.currency_code = 'GBP' THEN 1.24
                WHEN cira.currency_code = 'EUR' THEN 1.07
                WHEN cira.currency_code = 'NOK' THEN 0.091
                WHEN cira.currency_code = 'SEK' THEN 0.092
                WHEN cira.currency_code = 'DKK' THEN 0.14
                WHEN cira.currency_code = 'AUD' THEN 0.66
                WHEN cira.currency_code = 'NZD' THEN 0.61
                WHEN cira.currency_code = 'THB' THEN 0.029
                WHEN cira.currency_code = 'IDR' THEN 0.000067
                WHEN cira.currency_code = 'MYR' THEN 0.22
                WHEN cira.currency_code = 'SGD' THEN 0.74
                WHEN cira.currency_code = 'VND' THEN 0.000043
                WHEN cira.currency_code = 'PHP' THEN 0.018
                ELSE 1.00
            END AS exchange_rate_multiple,
            invoice_date,
            date_trunc('month', invoice_date) as invoice_month,
            pr.vendor
        FROM {schema}csv_invoice_row_archive cira
        JOIN {schema}partner p on p.id = cira.partner_id
        JOIN {schema}business_unit_cache buc on buc.uuid = p.business_unit_guid
        JOIN {schema}product pr on pr.id = cira.product_id
        WHERE invoice_date >= {date_subtract} and not is_voided
    )
    SELECT 
        id,
        partner_id,
        partner_name,
        company_id,
        invoice_id,
        row_type,
        term,
        total,
        total_after_tax,
        cost_total,
        cost_total_after_tax,
        pax8_cost_total,
        billed_by_pax8,
        bills_in_arrears,
        billing_fee,
        billing_fee_after_tax,
        currency_code,
        business_unit,
        exchange_rate_multiple,
        exchange_rate_multiple * total AS usd_total,
        exchange_rate_multiple * cost_total AS usd_cost_total,
        invoice_date,
        invoice_month,
        vendor
    FROM exchange_rates
    """
    
    return db_util.query(query, params={}, db=database)

def fetch_invoice_release_details(schema="", database=None):
    """
    Fetch invoice release status details with business unit breakdown for the current month.
    
    Args:
        schema (str): Database schema prefix. Defaults to empty string.
        database (str): Database to query. Defaults to None, which will use postgresql if available, otherwise redshift.
        
    Returns:
        DataFrame: Pandas DataFrame containing invoice release status details
    """      
    # Use database-specific date truncation
    date_trunc = "date_trunc('month', current_date)" if database == "redshift" else "date_trunc('month', current_date)"
    
    query = f"""
    SELECT 
        i.id,
        i.status,
        i.is_email_sent,
        i.approved,
        i.balance,
        cu.api_code as currency_code,
        i.business_unit_code,
        CASE
            WHEN i.partner_id IS NULL and i.company_id IS NOT NULL THEN 'Company Invoice'
            WHEN i.partner_id IS NOT NULL THEN 'Partner Invoice'
            ELSE 'Unknown'
        END AS invoice_audience,
        CASE WHEN i.partner_id IS NULL and i.company_id IS NOT NULL THEN p2.name ELSE p.name END AS partner_name,
        CASE WHEN i.partner_id IS NULL and i.company_id IS NOT NULL THEN p2.id ELSE p.id END AS partner_id,
        CASE
            WHEN i.is_email_sent AND i.approved THEN 'Released'
            WHEN NOT i.is_email_sent AND i.approved THEN 'Held - Approved'
            WHEN NOT i.is_email_sent AND NOT i.approved THEN 'Held - Needs Review'
            ELSE 'Unknown Status'
        END AS release_status
    FROM {schema}invoice i
    JOIN {schema}currency cu on i.currency_id = cu.id
    LEFT JOIN {schema}partner p on i.partner_id = p.id
    LEFT JOIN {schema}company c on i.company_id = c.id
    LEFT JOIN {schema}partner p2 on c.partner_id = p2.id
    WHERE invoice_date = {date_trunc}
    """
    
    return db_util.query(query, params={}, db=database)

def fetch_invoice_row_aggregated(schema="", database=None):
    """
    Fetch invoice row archive data for the last two months, pre-aggregated by row_type and term.
    This performs aggregation at the SQL level for better performance.
    
    Args:
        schema (str): Database schema prefix. Defaults to empty string.
        database (str): Database to query. Defaults to None, which will use postgresql if available, otherwise redshift.
        
    Returns:
        DataFrame: Pandas DataFrame containing aggregated invoice row data
    """  
    # Use database-specific date and string functions
    current_month_start = "date_trunc('month', current_date)" if database == "redshift" else "date_trunc('month', current_date)"
    prev_month_start = "dateadd('month', -1, date_trunc('month', current_date))" if database == "redshift" else "date_trunc('month', current_date) - interval '1 month'"
    month_format = "to_char(invoice_month, 'Month YYYY')" if database == "redshift" else "to_char(invoice_month, 'Month YYYY')"
    coalesce_term = "coalesce(term, 'No Term')" if database == "redshift" else "coalesce(term, 'No Term')"
    
    query = f"""
    WITH exchange_rates AS (
        SELECT 
            cira.id,
            cira.row_type,
            cira.term,
            cira.total,
            cira.cost_total,
            cira.currency_code,
            CASE
                WHEN cira.currency_code = 'USD' THEN 1
                WHEN cira.currency_code = 'CAD' THEN 0.74
                WHEN cira.currency_code = 'GBP' THEN 1.24
                WHEN cira.currency_code = 'EUR' THEN 1.07
                WHEN cira.currency_code = 'NOK' THEN 0.091
                WHEN cira.currency_code = 'SEK' THEN 0.092
                WHEN cira.currency_code = 'DKK' THEN 0.14
                WHEN cira.currency_code = 'AUD' THEN 0.66
                WHEN cira.currency_code = 'NZD' THEN 0.61
                WHEN cira.currency_code = 'THB' THEN 0.029
                WHEN cira.currency_code = 'IDR' THEN 0.000067
                WHEN cira.currency_code = 'MYR' THEN 0.22
                WHEN cira.currency_code = 'SGD' THEN 0.74
                WHEN cira.currency_code = 'VND' THEN 0.000043
                WHEN cira.currency_code = 'PHP' THEN 0.018
                ELSE 1.00
            END AS exchange_rate_multiple,
            date_trunc('month', invoice_date) as invoice_month,
            pr.vendor,
            buc.unique_code as business_unit
        FROM {schema}csv_invoice_row_archive cira
        JOIN {schema}partner p on p.id = cira.partner_id
        JOIN {schema}business_unit_cache buc on buc.uuid = p.business_unit_guid
        JOIN {schema}product pr on pr.id = cira.product_id
        WHERE date_trunc('month', invoice_date) >= {prev_month_start} 
          AND date_trunc('month', invoice_date) <= {current_month_start}
          AND NOT is_voided
    ),
    
    aggregated AS (
        SELECT 
            {coalesce_term} || ' - ' || row_type as row_type_term,
            {month_format} as month_name,
            business_unit,
            vendor,
            COUNT(*) as record_count,
            SUM(exchange_rate_multiple * total) as usd_total,
            SUM(exchange_rate_multiple * cost_total) as usd_cost_total,
            invoice_month
        FROM exchange_rates
        GROUP BY row_type, term, invoice_month, business_unit, vendor
    )
    
    SELECT * FROM aggregated
    ORDER BY invoice_month DESC, record_count DESC
    """
    
    return db_util.query(query, params={}, db=database)

def fetch_invoice_balance_by_business_unit(schema="", database=None):
    query = f"""
    WITH exchange_rates AS (SELECT i.id,
                                i.balance,
                                c.api_code,
                                i.status,
                                i.is_email_sent,
                                i.approved,
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
                                    END                           AS exchange_rate_multiple,
                                date_trunc('month', invoice_date) as invoice_month,
                                i.business_unit_code
                            FROM {schema}invoice i
                            JOIN {schema}currency c on i.currency_id = c.id
                            WHERE invoice_date = '2025-05-01'
                            AND status <> 'Void')
    SELECT *, exchange_rate_multiple * balance as balance_usd
    FROM exchange_rates
    """
    return db_util.query(query, params={}, db=database)

def fetch_current_month_invoice_counts():
    """Fetch counts of active non-voided invoices for the current and previous month.
    
    This function must use the Redshift database due to its dependency on the mart_observability_and_automation schema.
    
    Returns:
        dict | None: Dictionary containing invoice counts or None if the query fails
    """
    query = """
    WITH monthly_invoice_counts AS (
        SELECT 
            CASE 
                WHEN company_id IS NOT NULL AND partner_id IS NULL THEN 'company'
                WHEN partner_id IS NOT NULL THEN 'partner'
            END as invoice_type,
            COUNT(*) as count,
            invoice_date
        FROM mart_observability_and_automation.fact_invoice_nonvoid
        WHERE invoice_date >= dateadd('month', -1, date_trunc('month', current_date))
        AND invoice_date <= date_trunc('month', current_date)
        GROUP BY 
            CASE 
                WHEN company_id IS NOT NULL AND partner_id IS NULL THEN 'company'
                WHEN partner_id IS NOT NULL THEN 'partner'
            END,
            invoice_date
    )
    SELECT 
        SUM(CASE WHEN invoice_type = 'company' AND invoice_date = date_trunc('month', current_date) THEN count ELSE 0 END) as company_invoice_count,
        SUM(CASE WHEN invoice_type = 'partner' AND invoice_date = date_trunc('month', current_date) THEN count ELSE 0 END) as partner_invoice_count,
        SUM(CASE WHEN invoice_date = date_trunc('month', current_date) THEN count ELSE 0 END) as total_invoice_count,
        SUM(CASE WHEN invoice_type = 'company' AND invoice_date = dateadd('month', -1, date_trunc('month', current_date)) THEN count ELSE 0 END) as prev_company_invoice_count,
        SUM(CASE WHEN invoice_type = 'partner' AND invoice_date = dateadd('month', -1, date_trunc('month', current_date)) THEN count ELSE 0 END) as prev_partner_invoice_count,
        SUM(CASE WHEN invoice_date = dateadd('month', -1, date_trunc('month', current_date)) THEN count ELSE 0 END) as prev_total_invoice_count
    FROM monthly_invoice_counts
    """
    results = db_util.query(query, params={}, ttl=3600, db="redshift")
    if results is not None and len(results) > 0:
        return results.iloc[0].to_dict()  # Convert Series to dict for easier access
    return None

def fetch_missing_partner_invoices(schema="", database=None):
    """
    Fetch partners that should have an invoice for the current month but don't.
    This identifies partners who:
    1. Have ledger activity or invoice rows but no corresponding invoice
    2. Have auto_invoice_enabled set to true
    3. Are not test partners, root partners, or house accounts
    4. Are not deleted
    
    Args:
        schema (str): Database schema prefix. Defaults to empty string.
        database (str): Database to query. Defaults to None.
        
    Returns:
        DataFrame | None: Pandas DataFrame containing partner information and expected cost,
                        or None if the query fails
    """
    # Rewritten query to avoid correlated subqueries in COALESCE which Redshift can't handle
    query = f"""
    WITH invoice_row_costs AS (
        SELECT 
            cir.partner_id,
            sum(cir.cost_total) as row_cost
        FROM {schema}csv_invoice_row cir 
        WHERE cir.invoice_date = date_trunc('month', current_date)::date
        AND cir.partner_id IS NOT NULL
        GROUP BY cir.partner_id
    ),
    ledger_costs AS (
        SELECT 
            l.partner_id,
            sum(l.credit) - sum(l.debit) as ledger_cost
        FROM {schema}ledger l
        WHERE l.transaction_date >= date_trunc('month', current_date)::date
        AND l.transaction_date < dateadd('month', 1, date_trunc('month', current_date))::date
        GROUP BY l.partner_id
    ),
    existing_invoices AS (
        SELECT distinct i.partner_id 
        FROM {schema}invoice i 
        WHERE i.status <> 'Void' 
        AND i.invoice_date = date_trunc('month', current_date)::date
        AND i.partner_id IS NOT NULL
    )
    
    SELECT 
        p.id AS partner_id, 
        p.name AS partner_name,
        p.payment_day,
        p.is_invoice_dirty,
        date_trunc('month', current_date)::date AS invoice_date,
        p.currency_id,
        COALESCE(irc.row_cost, lc.ledger_cost, 0) AS cost 
    FROM {schema}partner p
    LEFT JOIN invoice_row_costs irc ON p.id = irc.partner_id
    LEFT JOIN ledger_costs lc ON p.id = lc.partner_id
    WHERE p.deleted = false 
    AND NOT p.test_partner 
    AND NOT p.is_root_partner
    AND p.auto_invoice_enabled = true
    AND p.id NOT IN (SELECT partner_id FROM existing_invoices)
    AND p.is_house_account = false
    AND (irc.row_cost IS NOT NULL OR lc.ledger_cost IS NOT NULL)
    AND COALESCE(irc.row_cost, lc.ledger_cost, 0) <> 0
    """
    
    return db_util.query(query, params={}, db=database)

def fetch_missing_company_invoices(schema="", database=None):
    """
    Fetch companies that should have an invoice for the current month but don't.
    This identifies companies who have ledger activity or invoice rows,
    but no corresponding invoice has been generated. Only includes companies
    that are set up for bill-on-behalf-of and are not telco companies.
    
    Args:
        schema (str): Database schema prefix. Defaults to empty string.
        database (str): Database to query. Defaults to None.
        
    Returns:
        DataFrame: Pandas DataFrame containing company information and expected cost
    """
    # Rewritten query to avoid correlated subqueries in COALESCE which Redshift can't handle
    query = f"""
    WITH invoice_row_costs AS (
        SELECT 
            cir.company_id,
            sum(cir.cost_total) as row_cost
        FROM {schema}csv_invoice_row cir 
        WHERE cir.invoice_date = date_trunc('month', current_date)::date
        AND cir.company_id IS NOT NULL
        GROUP BY cir.company_id
    ),
    ledger_costs AS (
        SELECT 
            l.company_id,
            sum(l.credit) - sum(l.debit) as ledger_cost
        FROM {schema}ledger l
        WHERE l.transaction_date >= date_trunc('month', current_date)::date
        AND l.transaction_date < dateadd('month', 1, date_trunc('month', current_date))::date
        GROUP BY l.company_id
    ),
    existing_invoices AS (
        SELECT distinct company_id 
        FROM {schema}invoice i 
        WHERE i.status <> 'Void' 
        AND i.invoice_date = date_trunc('month', current_date)::date
        AND i.company_id IS NOT NULL
    )
    
    SELECT 
        partner.id AS partner_id,
        partner.name AS partner_name,
        company.id AS company_id,
        company.name AS company_name,
        company.payment_day,
        company.is_invoice_dirty,
        company.currency_id,
        date_trunc('month', current_date)::date AS invoice_date,
        COALESCE(irc.row_cost, lc.ledger_cost, 0) AS cost
    FROM {schema}company company
    JOIN {schema}partner partner ON partner.id = company.partner_id
    LEFT JOIN invoice_row_costs irc ON company.id = irc.company_id
    LEFT JOIN ledger_costs lc ON company.id = lc.company_id
    WHERE company.status <> 'Deleted'
    AND company.bill_on_behalf_of_enabled
    AND (NOT company.is_telco OR company.is_telco IS NULL)
    AND company.id NOT IN (SELECT company_id FROM existing_invoices)
    AND (irc.row_cost IS NOT NULL OR lc.ledger_cost IS NOT NULL)
    AND COALESCE(irc.row_cost, lc.ledger_cost, 0) <> 0
    """
    return db_util.query(query, params={}, db=database)

def fetch_line_item_count(invoice_month = None):
    """Fetch invoice line details."""
    if invoice_month is None:
        invoice_line_count_end_date_clause = "DATE_TRUNC('MONTH', current_date)::DATE"
        invoice_line_count_start_date_clause = "DATE_TRUNC('MONTH', DATEADD(month, -6, current_date))"
    else:
        invoice_line_count_end_date_clause = f"DATE_TRUNC('MONTH', '{invoice_month}'::DATE)::DATE"
        invoice_line_count_start_date_clause = f"DATE_TRUNC('MONTH', DATEADD(month, -6, '{invoice_month}'::DATE))"

    query = f"""
    select * 
    from mart_observability_and_automation.agg_cira_region_type_month
    where invoice_month between {invoice_line_count_start_date_clause} and {invoice_line_count_end_date_clause}
    """
    return db_util.query(query, params={})