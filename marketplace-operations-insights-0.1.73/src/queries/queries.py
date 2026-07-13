class Queries:
    INVOICE_BALANCE = """
    select region,
        sum(balance_usd_2_months_prior) as month_2,
        sum(balance_usd_1_month_prior) as month_1,
        sum(balance_usd_current_month) as month_0,
        sum(balance_usd_diff_current_month) as variance
    from mart_observability_and_automation.agg_invoice_region_type_month
    where invoice_date = DATE_TRUNC('MONTH', current_date)::DATE
    group by region
    order by month_0 desc
    """

    OVERVIEW_INVOICE_COUNT = """
    select
        'Invoice Count' as "Metric",
        sum(invoice_count_2_months_prior) as month_2,
        sum(invoice_count_1_month_prior) as month_1,
        sum(invoice_count_current_month) as month_0,
        sum(invoice_count_diff_current_month) as variance
    from mart_observability_and_automation.agg_invoice_region_type_month
    where invoice_date = date_trunc('MONTH', current_date)
    """

    KEY_INVOICE_HEALTH = """
    with health_view as (
    select
        'Invoice Health'::text as "Metric",
        sum(healthy_invoices) as numerator,
        sum(total_invoices) as denominator,
        (numerator::float / denominator) as invoice_health,
        invoice_month
    from mart_observability_and_automation.agg_invoice_health_region_month
    where invoice_month >= dateadd(month, -2, date_trunc('MONTH', current_date))
    group by invoice_month
    order by invoice_month desc
    ),
    months as (
    select * from health_view
    pivot (
        max(invoice_health)
        for invoice_month in (
            dateadd(month, -2, date_trunc('MONTH', current_date)) as month_2,
            dateadd(month, -1, date_trunc('MONTH', current_date)) as month_1,
            date_trunc('MONTH', current_date) as month_0
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

    KEY_LEDGER_HEALTH = """
    with health_view as (
    select
        'Ledger Health'::text as "Metric",
        sum(total_entities_healthy_ledger) as numerator,
        sum(total_entities) as denominator,
        (numerator::float / denominator) as ledger_health,
        transaction_month
    from mart_observability_and_automation.agg_ledger_health_region_month
    where transaction_month >= dateadd(month, -2, date_trunc('MONTH', current_date))
    group by transaction_month
    order by transaction_month desc
    ),
    months as (
    select * from health_view
    pivot (
        max(ledger_health)
        for transaction_month in (
            dateadd(month, -2, date_trunc('MONTH', current_date)) as month_2,
            dateadd(month, -1, date_trunc('MONTH', current_date)) as month_1,
            date_trunc('MONTH', current_date) as month_0
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

    MANUAL_ARREARS = """
    select vendor,
        manual_arrears_revenue_usd_2_months_prior as month_2,
        manual_arrears_revenue_usd_1_month_prior as month_1,
        manual_arrears_revenue_usd_current_month as month_0,
        manual_arrears_revenue_usd_diff_current_month as variance
    from mart_observability_and_automation.agg_arrears_vendor_month
    where provision_start_month = DATE_TRUNC('MONTH', current_date)::DATE
    and current_month_manual_arrears_rank <= 5
    order by current_month_manual_arrears_rank
    """

    CREDITS_INFORMATION = """
    select
        vendor,
        service_credit_usd_2_months_prior as month_2,
        service_credit_usd_1_month_prior as month_1,
        service_credit_usd_current_month as month_0,
        service_credit_usd_diff_current_month as variance
    from mart_observability_and_automation.agg_service_credit_vendor_month
    where transaction_month = date_trunc('month', current_date)
    and current_month_service_credit_rank <= 5
    order by current_month_service_credit_rank
    """


    TAX_BILLING_TASKS = """
    select
        method, current_status_clean as status, count(*)
    from
        mart_observability_and_automation.fact_billing_task_status_history
    where
        method_category = 'Calculate Tax'
        and run_on_month = date_trunc('MONTH', current_date)::DATE
    group by method, status
    """

    ARREARS_TASKS = """
    SELECT
        run_on, current_status_clean as status, count(*)
    FROM
        mart_observability_and_automation.fact_arrears_task_status_history
    WHERE
        run_on_month = date_trunc('MONTH', current_date)::DATE
    GROUP BY run_on, status
    ORDER BY run_on, status
    """

    INVOICES_RELEASED = """
    select region, release_status, count(*) as value
    from mart_observability_and_automation.fact_invoice_nonvoid
    where invoice_date = date_trunc('month', current_date)
    group by region,release_status
    """

    AGG_INVOICE_LINE_DETAILS = """
    select * 
    from mart_observability_and_automation.agg_cira_region_type_month 
    where invoice_month = date_trunc('month', current_date)
    """

    ARREARS_ERROR_TOTALS = """
    SELECT
        sum(errored_tasks_unresolved) as errored_tasks_unresolved,
        sum(errored_tasks_resolved) as errored_tasks_resolved,
        sum(errored_tasks_total) as errored_tasks_total
    FROM mart_observability_and_automation.agg_arrears_task_region_vendor_month
    WHERE run_on_month = date_trunc('MONTH', current_date)::DATE
    """

    ARREARS_ERROR_CATEGORY = """
    SELECT
        vendor,
        error_category,
        errored_tasks_unresolved,
        errored_tasks_resolved,
        errored_tasks_total
    FROM mart_observability_and_automation.agg_arrears_error_category_vendor_month
    WHERE run_on_month = date_trunc('MONTH', current_date)::DATE
    """


    UNIQUE_VENDORS_SUBSCRIPTION = """
    SELECT DISTINCT vendor
    FROM mart_observability_and_automation.agg_subscription_history
    """

    SUBSCRIPTIONS_BY_INVOICE = """
    WITH subscriptions AS (
        SELECT DISTINCT
            s.id,
            s.status AS sub_status,
            cira.invoice_date,
            CASE
                WHEN cira.arrears_subscription_id IS NOT NULL THEN TRUE
                ELSE FALSE
            END AS has_arrears,
            s.start_date,
            s.end_date,
            cira.partner_name,
            cira.company_name,
            s.product_name,
            cira.product_id,
            cira.row_type,
            SUM(cira.quantity) AS quantity,
            cli.term_in_months,
            SUM(ROUND(cira.cost_total, 2)) AS partner_total,
            SUM(ROUND(cira.total, 2)) AS customer_total,
            ROUND(customer_total - partner_total,2) as partner_profit, 
            CASE 
                WHEN customer_total = 0 THEN NULL
                ELSE ROUND(partner_profit / customer_total, 2) * 100
            END AS partner_margin, 
            cira.billed_by_pax8 as bill_on_behalf_indicator, 
            cli.type AS completed_line_item_type,
            rp.id AS rate_plan_id,
            rp.start_date AS rate_plan_start_date,
            rp.end_date AS rate_plan_end_date,
            au.first_name || ' ' || au.last_name AS rate_plan_creator
        FROM mart_observability_and_automation.int_subscription_joined s
        JOIN mart_observability_and_automation.stg__cc_csv_invoice_row_archive cira 
            ON s.id = cira.arrears_subscription_id
        JOIN mart_observability_and_automation.stg__cc_completed_line_item cli 
            ON cira.completed_line_item_id = cli.id
        JOIN cc.invoice i 
            ON cira.invoice_id = i.id
        JOIN mart_observability_and_automation.stg__cc_rate_plan rp 
            ON cli.rate_plan_id = rp.id
        JOIN cc.app_user au 
            ON rp.user_id = au.id
        WHERE {condition}
          AND cira.is_voided = FALSE
          AND cira.arrears_subscription_id IS NOT NULL
        GROUP BY
            s.id,
            s.status,
            cira.invoice_date,
            cira.arrears_subscription_id,
            s.start_date,
            s.end_date,
            cira.partner_name,
            cira.company_name,
            s.product_name,
            cira.product_id,
            cira.row_type,
            cli.term_in_months,
            cira.billed_by_pax8, 
            cli.type,
            rp.id,
            rp.start_date,
            rp.end_date,
            au.first_name,
            au.last_name
        UNION ALL
        SELECT DISTINCT
            s.id,
            s.status AS sub_status,
            cira.invoice_date,
            FALSE AS has_arrears,
            s.start_date,
            s.end_date,
            cira.partner_name,
            cira.company_name,
            s.product_name,
            cira.product_id,
            cira.row_type,
            cira.quantity AS quantity,
            cli.term_in_months,
            ROUND(cira.cost_total, 2) AS partner_total,
            ROUND(cira.total, 2) AS customer_total,
            customer_total - partner_total as partner_profit, 
            CASE 
                WHEN customer_total = 0 THEN NULL
                ELSE ROUND(partner_profit / customer_total, 2) * 100
            END AS partner_margin, 
            cira.billed_by_pax8 as bill_on_behalf_indicator, 
            cli.type AS completed_line_item_type,
            rp.id AS rate_plan_id,
            rp.start_date AS rate_plan_start_date,
            rp.end_date AS rate_plan_end_date,
            au.first_name || ' ' || au.last_name AS rate_plan_creator
        FROM mart_observability_and_automation.int_subscription_joined s
        JOIN mart_observability_and_automation.stg__cc_completed_line_item cli 
            ON s.completed_line_id = cli.id
        JOIN mart_observability_and_automation.stg__cc_csv_invoice_row_archive cira 
            ON cli.id = cira.completed_line_item_id
        JOIN cc.invoice i 
            ON cira.invoice_id = i.id
        JOIN mart_observability_and_automation.stg__cc_rate_plan rp 
            ON cli.rate_plan_id = rp.id
        JOIN cc.app_user au 
            ON rp.user_id = au.id
        WHERE {condition}
          AND cira.is_voided = FALSE
    )
    SELECT *
    FROM subscriptions
    ORDER BY
        has_arrears DESC,
        CASE
            WHEN end_date IS NULL THEN 0
            WHEN end_date > GETDATE() THEN 0
            ELSE 1
        END,
        start_date DESC,
        partner_total DESC;
    """

    RELATED_SUBSCRIPTIONS = """
    with coterm as (
    select
         s.id as subscription_id,
         s.original_subscription_id,
         s.commitment_term_end_date as current_commitment_end,
         pt.id as provision_task,
         pt.status as task_status,
         pt.additional_params,
         json_extract_path_text(additional_params, 'commitmentTerm') AS commitment_term,
         json_extract_path_text(additional_params, 'billingTerm') AS billing_term,
         json_extract_path_text(additional_params, 'coTermDate') AS co_term_date
    from cc.subscription s
    join cc.provision_task pt on pt.subscription_id = s.id
    join cc.completed_line_item cli on cli.id = s.completed_line_id
    join cc.rate_plan rp on rp.id = cli.rate_plan_id
    where pt.id in (select max(id) from cc.provision_task where type = 'ScheduledInstruction' and subscription_id = s.id)),

    subscription_data as (
    SELECT
        s.id,
        s.original_subscription_id,
        s.status,
        s.quantity,
        s.start_date,
        s.end_date,
        s.commitment_term_end_date,
        ct.term_in_months as commitment_term_in_months,
        p.name as product_name,
        au.first_name || ' ' || au.last_name as modified_by,
        au.email as modified_by_email,
        cli.type,
        cli.partner_buy_rate,
        cli.actual_retail_price,
        cli.pax8_gross_revenue,
        cli.term_in_months,
        cli.pax8_gross_revenue/NULLIF(cli.term_in_months, 0) as monthly_revenue
    FROM mart_observability_and_automation.stg__cc_subscription s
    LEFT JOIN mart_observability_and_automation.stg__cc_completed_line_item cli ON s.completed_line_id = cli.id
    LEFT JOIN mart_observability_and_automation.stg__cc_product p on s.product_id=p.id
    LEFT JOIN mart_observability_and_automation.stg__cc_commitment_term ct on s.commitment_term_id=ct.id
    LEFT JOIN cc.app_user au on cli.approving_user_id=au.id
        ORDER BY s.created_dt DESC)

    select
        sd.*,
        ct.co_term_date
    from subscription_data sd
    left join coterm ct on sd.original_subscription_id=ct.original_subscription_id and sd.id>=ct.subscription_id
    where sd.original_subscription_id=:original_subscription_id order by sd.id desc;
    """

    SUBSCRIPTION_METRICS = """
    SELECT DISTINCT
        s.id,
        s.status,
        s.original_subscription_id,
        s.partner_name,
        s.company_name,
        s.product_name,
        s.quantity,
        s.start_date,
        s.end_date,
        s.billing_cycle_start,
        s.billing_cycle_end,
        s.billing_start,
        s.commitment_term_end_date,
        s.partner_business_unit_guid,
        s.vendor,
        DATEDIFF(day, s.start_date, GETDATE()) as days_active,
        cli.pax8_gross_revenue,
        cli.term_in_months,
        cli.pax8_gross_revenue/NULLIF(cli.term_in_months, 0) as monthly_revenue
    FROM mart_observability_and_automation.int_subscription_joined s
    LEFT JOIN cc.completed_line_item cli ON s.completed_line_id = cli.id
    WHERE s.id = :subscription_id
    """

    SUBSCRIPTION_ARREARS_TASKS = """
    with arrears_task_info as (
        select
            at.subscription_id,
            at.run_on,
            at.status_clean as status,
            at.method,
            at.service,
            at.error_message,
            SPLIT_PART(at._dbt_source_relation, '.', 3) AS table_source
        from mart_observability_and_automation.stg__cc_arrears_task_unioned at order by at.run_on desc),
    
    subscription_info as (
        select
            s.id as subscription_id,
            s.original_subscription_id,
            s.company_id,
            c.name as company_name
        from mart_observability_and_automation.stg__cc_subscription s
        inner join mart_observability_and_automation.stg__cc_company c on s.company_id=c.id)
    
        select
            si.subscription_id,
            si.original_subscription_id,
            si.company_id || ' ' || si.company_name as company_info,
            ati.run_on,
            ati.method,
            ati.service,
            ati.status,
            ati.error_message,
            ati.table_source
        from arrears_task_info ati
        inner join subscription_info si on ati.subscription_id=si.subscription_id
        where ati.subscription_id= :subscription_id
        order by ati.run_on desc
    """

    SUBSCRIPTION_ARREARS_ERRORS = """
    WITH task_errors AS (
        SELECT 
            at.subscription_id,
            aec.run_on,
            aec.error_message,
            aec.error_category,
            aec.current_status_clean
        FROM mart_observability_and_automation.fact_arrears_task_status_history at
        JOIN mart_observability_and_automation.fact_arrears_error_categorization aec 
            ON at.unique_task_id = aec.unique_task_id
        WHERE at.subscription_id = :subscription_id
    )
    SELECT 
        run_on,
        error_message,
        error_category,
        current_status_clean as status,
        COUNT(*) as occurrence_count
    FROM task_errors
    GROUP BY run_on, error_message, error_category, current_status_clean
    ORDER BY run_on DESC, occurrence_count DESC
    LIMIT 100
    """

    REVENUE_VARIANCE = """
    WITH monthly_revenue AS (
        SELECT 
            cira.invoice_month,
            SUM(cira.total) as total_revenue,
            SUM(cira.quantity) as total_quantity
        FROM mart_observability_and_automation.stg__cc_csv_invoice_row_archive cira
        WHERE cira.arrears_subscription_id = :subscription_id 
            OR cira.completed_line_item_id IN (
                SELECT completed_line_id 
                FROM mart_observability_and_automation.int_subscription_joined 
                WHERE id = :subscription_id
            )
            AND cira.is_voided = false
        GROUP BY cira.invoice_month
        ORDER BY cira.invoice_month DESC
        LIMIT 6
    )
    SELECT 
        invoice_month,
        CASE 
            WHEN LAG(total_revenue) OVER (ORDER BY invoice_month) = 0 THEN NULL
            ELSE ((total_revenue - LAG(total_revenue) OVER (ORDER BY invoice_month)) 
                / LAG(total_revenue) OVER (ORDER BY invoice_month)) * 100 
        END as revenue_variance_pct,
        CASE 
            WHEN LAG(total_quantity) OVER (ORDER BY invoice_month) = 0 THEN NULL
            ELSE ((total_quantity - LAG(total_quantity) OVER (ORDER BY invoice_month)) 
                / LAG(total_quantity) OVER (ORDER BY invoice_month)) * 100 
        END as quantity_variance_pct,
        CASE 
            WHEN LAG(total_revenue/total_quantity) OVER (ORDER BY invoice_month) = 0 THEN NULL
            ELSE ((total_revenue/total_quantity - LAG(total_revenue/total_quantity) OVER (ORDER BY invoice_month)) 
                / LAG(total_revenue/total_quantity) OVER (ORDER BY invoice_month)) * 100 
        END as revenue_to_quantity_ratio_variance_pct,
        total_revenue,
        total_quantity,
        LAG(total_revenue) OVER (ORDER BY invoice_month) as prev_revenue,
        LAG(total_quantity) OVER (ORDER BY invoice_month) as prev_quantity,
        total_revenue/total_quantity as revenue_to_quantity_ratio,
        LAG(total_revenue/total_quantity) OVER (ORDER BY invoice_month) as prev_revenue_to_quantity_ratio
    FROM monthly_revenue
    """

    @staticmethod
    def load_subscription_overview_data(billing_period=None, vendor=None):
        if vendor == 'All':
            return """
            SELECT
                partner_count,
                company_count,
                active_subscription_count,
                cancelled_subscription_count,
                net_new_subscription_count,
                total_product_changes,
                total_renewals,
                total_modifications,
                total_quantity_change,
                total_partner_buy_rate_changes
            FROM mart_observability_and_automation.agg_subscription_monthly_summary
                WHERE transaction_month = CAST(:billing_period AS VARCHAR)
            """
        else: 
            return """
            SELECT
                partner_count,
                company_count,
                active_subscription_count,
                cancelled_subscription_count,
                net_new_subscription_count,
                total_product_changes,
                total_renewals,
                total_modifications,
                total_quantity_change,
                total_partner_buy_rate_changes
            FROM mart_observability_and_automation.agg_subscription_monthly_vendor_summary
                WHERE transaction_month = CAST(:billing_period AS VARCHAR)
                AND vendor = CAST(:vendor AS VARCHAR)
            """
    @staticmethod
    def load_subscription_overview_trends(billing_period=None, vendor=None):
         if vendor == 'All':
            return """
            WITH last_6_months AS (
                SELECT DISTINCT transaction_month
                FROM mart_observability_and_automation.agg_subscription_history
                WHERE transaction_month <= CAST(:billing_period AS DATE)
                    AND transaction_month > DATEADD(month, -6, CAST(:billing_period AS DATE))
            )
            SELECT
                m.transaction_month,
                s.partner_count,
                s.company_count,
                s.active_subscription_count,
                s.cancelled_subscription_count,
                s.net_new_subscription_count,
                s.total_product_changes,
                s.total_renewals, 
                s.total_modifications,
                s.total_quantity_change, 
                s.total_partner_buy_rate_changes
            FROM last_6_months m
            LEFT JOIN mart_observability_and_automation.agg_subscription_monthly_summary s
                ON m.transaction_month = s.transaction_month
            ORDER BY m.transaction_month
            """
         else: 
            return """
            WITH last_6_months AS (
                SELECT DISTINCT transaction_month
                FROM mart_observability_and_automation.agg_subscription_history
                WHERE transaction_month <= CAST(:billing_period AS DATE)
                    AND transaction_month > DATEADD(month, -6, CAST(:billing_period AS DATE))
            )
            SELECT
                m.transaction_month,
                s.partner_count,
                s.company_count,
                s.active_subscription_count,
                s.cancelled_subscription_count,
                s.net_new_subscription_count,
                s.total_product_changes,
                s.total_renewals, 
                s.total_modifications,
                s.total_quantity_change, 
                s.total_partner_buy_rate_changes
            FROM last_6_months m
            LEFT JOIN mart_observability_and_automation.agg_subscription_monthly_vendor_summary s
                ON m.transaction_month = s.transaction_month
                AND s.vendor = CAST(:vendor AS VARCHAR)
            ORDER BY m.transaction_month
            """
         
    @staticmethod
    def load_subscription_overview_history(vendor=None):
        if vendor == 'All':
            return """
            SELECT
                transaction_month,
                partner_count,
                company_count,
                active_subscription_count,
                cancelled_subscription_count,
                net_new_subscription_count,
                total_product_changes,
                total_renewals,
                total_modifications,
                total_quantity_change,
                total_partner_buy_rate_changes
            FROM mart_observability_and_automation.agg_subscription_monthly_summary
                order by transaction_month asc
            """
        else: 
            return """
            SELECT
                transaction_month,
                partner_count,
                company_count,
                active_subscription_count,
                cancelled_subscription_count,
                net_new_subscription_count,
                total_product_changes,
                total_renewals,
                total_modifications,
                total_quantity_change,
                total_partner_buy_rate_changes
            FROM mart_observability_and_automation.agg_subscription_monthly_vendor_summary
                WHERE vendor = CAST(:vendor AS VARCHAR)
                order by transaction_month asc
            """
    @staticmethod
    def load_subscriptions_by_invoice(invoice_id=None, subscription_id=None):
        conditions = []
        if invoice_id is not None:
            if isinstance(invoice_id, str):
                conditions.append("i.alternate_id = :invoice_id")
            elif isinstance(invoice_id, int):
                conditions.append("i.id = :invoice_id")
            else:
                raise ValueError("invoice_id must be a string or an integer.")
        if subscription_id is not None:
            if isinstance(subscription_id, int):
                conditions.append("s.id = :subscription_id")
            else:
                raise ValueError("subscription_id must be an integer.")
        if not conditions:
            raise ValueError("At least one of invoice_id or subscription_id must be provided.")

        condition = " AND ".join(conditions)
        return Queries.SUBSCRIPTIONS_BY_INVOICE.format(condition=condition)

    @staticmethod
    def load_related_subscriptions(original_subscription_id):
        return Queries.RELATED_SUBSCRIPTIONS

    @staticmethod
    def load_subscription_metrics(subscription_id):
        return Queries.SUBSCRIPTION_METRICS

    @staticmethod
    def load_subscription_arrears_tasks(subscription_id):
        return Queries.SUBSCRIPTION_ARREARS_TASKS

    @staticmethod
    def load_subscription_arrears_errors(subscription_id):
        return Queries.SUBSCRIPTION_ARREARS_ERRORS

    @staticmethod
    def calculate_revenue_variance(subscription_id):
        return Queries.REVENUE_VARIANCE

    INVOICE_TASK_DURATION_ANALYSIS = """
    -- Invoice Task Duration Analysis Query
    -- Analyzes run durations for createPartnerInvoice and createCompanyInvoice tasks
    -- across all task tables with date range filtering and alerting thresholds

    WITH invoice_tasks AS (
        -- billing_task table
        SELECT 
            'billing_task' as task_table,
            method,
            (payload::json->'invoiceDate'->>'value')::date as invoice_date,
            run_duration,
            created_dt,
            updated_dt,
            id,
            status,
            error_message
        FROM billing_task 
        WHERE status = 'finished'
            AND method IN ('createPartnerInvoice', 'createCompanyInvoice')
            AND (payload::json->'invoiceDate'->>'value')::date >= :start_date
            AND (payload::json->'invoiceDate'->>'value')::date <= :end_date
            AND run_duration IS NOT NULL

        UNION ALL

        -- billing_task_2 table
        SELECT 
            'billing_task_2' as task_table,
            method,
            (payload::json->'invoiceDate'->>'value')::date as invoice_date,
            run_duration,
            created_dt,
            updated_dt,
            id,
            status,
            error_message
        FROM billing_task_2 
        WHERE status = 'finished'
            AND method IN ('createPartnerInvoice', 'createCompanyInvoice')
            AND (payload::json->'invoiceDate'->>'value')::date >= :start_date
            AND (payload::json->'invoiceDate'->>'value')::date <= :end_date
            AND run_duration IS NOT NULL

        UNION ALL

        -- mca_task table  
        SELECT 
            'mca_task' as task_table,
            method,
            (payload::json->'invoiceDate'->>'value')::date as invoice_date,
            run_duration,
            created_dt,
            updated_dt,
            id,
            status,
            error_message
        FROM mca_task 
        WHERE status = 'finished'
            AND method IN ('createPartnerInvoice', 'createCompanyInvoice')
            AND (payload::json->'invoiceDate'->>'value')::date >= :start_date
            AND (payload::json->'invoiceDate'->>'value')::date <= :end_date
            AND run_duration IS NOT NULL

        UNION ALL

        -- mca_task_2 table
        SELECT 
            'mca_task_2' as task_table,
            method,
            (payload::json->'invoiceDate'->>'value')::date as invoice_date,
            run_duration,
            created_dt,
            updated_dt,
            id,
            status,
            error_message
        FROM mca_task_2 
        WHERE status = 'finished'
            AND method IN ('createPartnerInvoice', 'createCompanyInvoice')
            AND (payload::json->'invoiceDate'->>'value')::date >= :start_date
            AND (payload::json->'invoiceDate'->>'value')::date <= :end_date
            AND run_duration IS NOT NULL

        UNION ALL

        -- mca_task_3 table
        SELECT 
            'mca_task_3' as task_table,
            method,
            (payload::json->'invoiceDate'->>'value')::date as invoice_date,
            run_duration,
            created_dt,
            updated_dt,
            id,
            status,
            error_message
        FROM mca_task_3 
        WHERE status = 'finished'
            AND method IN ('createPartnerInvoice', 'createCompanyInvoice')
            AND (payload::json->'invoiceDate'->>'value')::date >= :start_date
            AND (payload::json->'invoiceDate'->>'value')::date <= :end_date
            AND run_duration IS NOT NULL

        UNION ALL

        -- mca_task_4 table
        SELECT 
            'mca_task_4' as task_table,
            method,
            (payload::json->'invoiceDate'->>'value')::date as invoice_date,
            run_duration,
            created_dt,
            updated_dt,
            id,
            status,
            error_message
        FROM mca_task_4 
        WHERE status = 'finished'
            AND method IN ('createPartnerInvoice', 'createCompanyInvoice')
            AND (payload::json->'invoiceDate'->>'value')::date >= :start_date
            AND (payload::json->'invoiceDate'->>'value')::date <= :end_date
            AND run_duration IS NOT NULL

        UNION ALL

        -- mca_task_5 table
        SELECT 
            'mca_task_5' as task_table,
            method,
            (payload::json->'invoiceDate'->>'value')::date as invoice_date,
            run_duration,
            created_dt,
            updated_dt,
            id,
            status,
            error_message
        FROM mca_task_5 
        WHERE status = 'finished'
            AND method IN ('createPartnerInvoice', 'createCompanyInvoice')
            AND (payload::json->'invoiceDate'->>'value')::date >= :start_date
            AND (payload::json->'invoiceDate'->>'value')::date <= :end_date
            AND run_duration IS NOT NULL
    ),

    duration_aggregates AS (
        SELECT 
            task_table,
            invoice_date,
            method,
            COUNT(*) as total_tasks,
            MIN(run_duration) as min_runtime_ms,
            MAX(run_duration) as max_runtime_ms,
            ROUND(AVG(run_duration), 2) as avg_runtime_ms,
            SUM(run_duration) as total_runtime_ms,
            -- Convert to seconds for easier reading
            ROUND(MIN(run_duration) / 1000.0, 2) as min_runtime_sec,
            ROUND(MAX(run_duration) / 1000.0, 2) as max_runtime_sec,
            ROUND(AVG(run_duration) / 1000.0, 2) as avg_runtime_sec,
            ROUND(SUM(run_duration) / 1000.0, 2) as total_runtime_sec,
            -- Convert to minutes and hours for very long tasks
            ROUND(SUM(run_duration) / 60000.0, 2) as total_runtime_min,
            ROUND(SUM(run_duration) / 3600000.0, 2) as total_runtime_hours,
            -- Add percentile calculations
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY run_duration) as p50_runtime_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY run_duration) as p95_runtime_ms,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY run_duration) as p99_runtime_ms,
            -- Alert flags
            CASE WHEN SUM(run_duration) / 3600000.0 > 24 THEN true ELSE false END as alert_24hr_exceeded,
            CASE WHEN MAX(run_duration) / 1000.0 > 1800 THEN true ELSE false END as alert_30min_task_exceeded
        FROM invoice_tasks
        WHERE invoice_date IS NOT NULL
        GROUP BY task_table, invoice_date, method
    )

    SELECT 
        task_table,
        invoice_date,
        method,
        total_tasks,
        min_runtime_ms,
        max_runtime_ms,
        avg_runtime_ms,
        total_runtime_ms,
        min_runtime_sec,
        max_runtime_sec,
        avg_runtime_sec,
        total_runtime_sec,
        total_runtime_min,
        total_runtime_hours,
        ROUND(p50_runtime_ms / 1000.0, 2) as p50_runtime_sec,
        ROUND(p95_runtime_ms / 1000.0, 2) as p95_runtime_sec,
        ROUND(p99_runtime_ms / 1000.0, 2) as p99_runtime_sec,
        alert_24hr_exceeded,
        alert_30min_task_exceeded,
        -- Alert messages
        CASE 
            WHEN alert_24hr_exceeded THEN 'ALERT: Total runtime exceeds 24 hours (' || total_runtime_hours || 'h)'
            WHEN alert_30min_task_exceeded THEN 'WARNING: Individual task exceeds 30 minutes (' || max_runtime_sec || 's)'
            ELSE null 
        END as alert_message
    FROM duration_aggregates
    ORDER BY invoice_date DESC, total_runtime_hours DESC
    """

    @staticmethod
    def get_invoice_task_duration_analysis(start_date, end_date):
        """
        Get invoice task duration analysis with alerting for specified date range.
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            
        Returns:
            str: SQL query for invoice task duration analysis
        """
        return Queries.INVOICE_TASK_DURATION_ANALYSIS