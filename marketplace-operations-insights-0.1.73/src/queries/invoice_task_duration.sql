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
ORDER BY invoice_date DESC, total_runtime_hours DESC;
