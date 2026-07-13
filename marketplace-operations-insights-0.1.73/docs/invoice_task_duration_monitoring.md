# Invoice Task Duration Monitoring

## Overview

The Invoice Task Duration Monitoring feature provides comprehensive performance analysis and alerting for `createPartnerInvoice` and `createCompanyInvoice` tasks across all billing task tables.

## Features

### 🚨 Automated Alerting
- **Critical Alerts**: Tasks with total runtime exceeding 24 hours
- **Warning Alerts**: Individual tasks exceeding 30 minutes
- Real-time alert summary with severity indicators

### 📊 Performance Analytics
- Task count and runtime aggregations by date, method, and table
- Percentile calculations (50th, 95th, 99th) for runtime distribution
- Efficiency metrics (tasks per hour, throughput analysis)

### 📈 Trend Visualization
- Daily runtime trends by method
- Performance comparison between `createPartnerInvoice` and `createCompanyInvoice`
- Task table performance analysis

### 🔍 Detailed Analysis
- Filterable data table with alert highlighting
- Downloadable CSV exports for further analysis
- Date range selection (default: last 30 days)

## Usage

### Accessing the Feature
1. Navigate to **Billing & Invoicing** section
2. Go to **Billing Analytics** > **Invoice Task Duration**

### Key Metrics Displayed
- **Total Tasks**: Number of finished invoice generation tasks
- **Total Runtime**: Cumulative execution time across all tasks
- **Average Runtime**: Weighted average task duration
- **95th Percentile**: Runtime threshold for slowest 5% of tasks
- **Max Runtime**: Longest single task execution time

### Alert Thresholds
- **24-hour threshold**: Triggers critical alert when total runtime for a task table/method/date combination exceeds 24 hours
- **30-minute threshold**: Triggers warning when any individual task takes longer than 30 minutes

## Technical Implementation

### Database Tables Queried
- `billing_task`
- `billing_task_2`
- `mca_task` through `mca_task_5`

### Key Query Features
```sql
-- Extract invoice date from JSON payload
(payload::json->'invoiceDate'->>'value')::date as invoice_date

-- Alert conditions
CASE WHEN SUM(run_duration) / 3600000.0 > 24 THEN true ELSE false END as alert_24hr_exceeded
CASE WHEN MAX(run_duration) / 1000.0 > 1800 THEN true ELSE false END as alert_30min_task_exceeded
```

### Files Structure
```
src/
├── queries/
│   ├── invoice_task_duration.sql          # Raw SQL query file
│   └── queries.py                         # Updated with new query
├── billing_run/
│   ├── models/
│   │   └── invoice_task_duration_model.py # Data access layer
│   └── pages/
│       └── invoice_task_duration_monitoring.py # Streamlit page
└── tests/
    └── test_invoice_task_duration.py      # Unit tests
```

## Customization

### Modifying Alert Thresholds
To change alert thresholds, update the constants in the SQL query:

```sql
-- Change 24-hour threshold to 12 hours
CASE WHEN SUM(run_duration) / 3600000.0 > 12 THEN true ELSE false END

-- Change 30-minute threshold to 60 minutes  
CASE WHEN MAX(run_duration) / 1000.0 > 3600 THEN true ELSE false END
```

### Adding New Task Methods
To monitor additional task methods, update the method filter in the query:

```sql
AND method IN ('createPartnerInvoice', 'createCompanyInvoice', 'newTaskMethod')
```

## Performance Considerations

- Query is cached for 5 minutes using `@st.cache_data(ttl=300)`
- Date range limited to prevent overly large result sets
- Recommended maximum date range: 1 year
- Default analysis period: last 30 days

## Troubleshooting

### Common Issues

1. **No data returned**: Verify date range includes periods with invoice generation activity
2. **Query timeout**: Reduce date range or check database performance
3. **Missing alerts**: Ensure task tables contain `run_duration` data
4. **Permission errors**: Verify user has `BILLING_RUN_ROLES` access

### Performance Tips

- Use smaller date ranges for faster loading
- Filter by specific task tables when investigating issues
- Export data for detailed offline analysis

## Future Enhancements

Potential improvements for future development:

1. **Historical trend analysis**: Compare current performance vs. historical baselines
2. **Predictive alerting**: Machine learning models to predict long-running tasks
3. **Integration with monitoring systems**: Push alerts to external monitoring tools
4. **Automated optimization suggestions**: Recommend actions based on performance patterns
5. **Real-time monitoring**: Live dashboard updates for active task execution
