from utils import db_util


def fetch_tax_billing_tasks(invoice_month = None):
    """Fetch tax billing tasks data."""
    if invoice_month is None:
        tax_billing_tasks_date_clause = "DATE_TRUNC('MONTH', current_date)::DATE"
    else: 
        tax_billing_tasks_date_clause = f"DATE_TRUNC('MONTH', '{invoice_month}'::date)::DATE"
        
    query = f"""
    select
        method, current_status_clean as status, count(*)
    from
        mart_observability_and_automation.fact_billing_task_status_history
    where
        method_category = 'Calculate Tax'
        and run_on_month = {tax_billing_tasks_date_clause}
    group by method, status
    """
    return db_util.query(query, params={})


def fetch_task_status(selected_month):
    """Fetches the aggregated task status for billing tasks."""
    query = """
        WITH monthly_totals AS (
            SELECT 
                run_on_month,
                SUM(tasks_total) as month_total_tasks,
                SUM(finished_tasks_total) as month_total_finished,
                SUM(errored_tasks_total) as month_total_errors,
                SUM(reviewed_tasks_total) as month_total_reviewed
            FROM mart_observability_and_automation.agg_billing_task_region_method_month
            GROUP BY run_on_month
        ),
        prev_month_totals AS (
            SELECT 
                run_on_month,
                month_total_tasks,
                month_total_finished,
                month_total_errors,
                month_total_reviewed,
                LAG(month_total_tasks) OVER (ORDER BY run_on_month) as prev_tasks_total,
                LAG(month_total_finished) OVER (ORDER BY run_on_month) as prev_finished_total,
                LAG(month_total_errors) OVER (ORDER BY run_on_month) as prev_errored_total,
                LAG(month_total_reviewed) OVER (ORDER BY run_on_month) as prev_reviewed_total
            FROM monthly_totals
        )
        SELECT 
            a.*,
            COALESCE(p.prev_tasks_total, 0) as prev_tasks_total,
            COALESCE(p.prev_finished_total, 0) as prev_finished_total,
            COALESCE(p.prev_errored_total, 0) as prev_errored_total,
            COALESCE(p.prev_reviewed_total, 0) as prev_reviewed_total
        FROM mart_observability_and_automation.agg_billing_task_region_method_month a
        LEFT JOIN prev_month_totals p ON a.run_on_month = p.run_on_month
        WHERE a.run_on_month = :selected_month
    """
    params = {"selected_month": selected_month}
    return db_util.query(query, params=params)
