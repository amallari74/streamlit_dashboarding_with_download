"""
Invoice Task Duration Monitoring Page

Provides comprehensive monitoring and alerting for createPartnerInvoice and createCompanyInvoice task durations.
Includes performance analytics, trend analysis, and automated alerting for tasks exceeding thresholds.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from typing import Optional

from utils import auth_util, db_util
from router.roles import BILLING_RUN_ROLES as ROLES
from billing_run.models.invoice_task_duration_model import (
    fetch_invoice_task_duration_analysis,
    get_alert_summary,
    get_performance_summary,
    get_default_date_range,
    format_runtime_display
)


def render_alert_summary(alert_summary: dict):
    """Render the alert summary section with critical and warning alerts."""
    st.subheader("🚨 Alert Summary")
    
    # Show alert metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Alerts",
            alert_summary["total_alerts"],
            delta_color="inverse" if alert_summary["total_alerts"] > 0 else "normal"
        )
    
    with col2:
        st.metric(
            "Critical (>24h)",
            alert_summary["critical_alerts"],
            delta_color="inverse" if alert_summary["critical_alerts"] > 0 else "normal"
        )
    
    with col3:
        st.metric(
            "Warnings (>30m)",
            alert_summary["warning_alerts"],
            delta_color="inverse" if alert_summary["warning_alerts"] > 0 else "normal"
        )
    
    with col4:
        st.metric(
            "Max Runtime",
            f"{alert_summary['max_runtime_hours']:.1f}h",
            delta_color="inverse" if alert_summary["max_runtime_hours"] > 24 else "normal"
        )
    
    # Show alert details if any exist
    if alert_summary["alert_details"]:
        st.subheader("Alert Details")
        
        alert_df = pd.DataFrame(alert_summary["alert_details"])
        
        # Style the dataframe based on severity
        def color_severity(val):
            if val == "CRITICAL":
                return "background-color: #ffebee; color: #c62828"
            elif val == "WARNING":
                return "background-color: #fff3e0; color: #ef6c00"
            return ""
        
        styled_df = alert_df.style.map(color_severity, subset=['severity'])
        
        st.dataframe(
            styled_df,
            column_config={
                "severity": st.column_config.TextColumn("Severity", width="small"),
                "date": st.column_config.DateColumn("Invoice Date", width="medium"),
                "table": st.column_config.TextColumn("Task Table", width="medium"),
                "method": st.column_config.TextColumn("Method", width="medium"),
                "runtime_hours": st.column_config.NumberColumn("Runtime (Hours)", format="%.2f", width="small"),
                "max_runtime_sec": st.column_config.NumberColumn("Max Runtime (Sec)", format="%.1f", width="small"),
                "total_tasks": st.column_config.NumberColumn("Total Tasks", format="%d", width="small"),
                "message": st.column_config.TextColumn("Alert Message", width="large")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✅ No alerts found for the selected date range.")


def render_performance_summary(perf_summary: dict):
    """Render the performance summary section."""
    st.subheader("📊 Performance Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Tasks Analyzed", f"{perf_summary['total_tasks']:,}")
        st.metric("Date Range", f"{perf_summary['date_range_days']} days")
    
    with col2:
        st.metric("Total Runtime", f"{perf_summary['total_runtime_hours']:.1f}h")
        st.metric("Avg Task Runtime", format_runtime_display(perf_summary['avg_runtime_sec']))
    
    with col3:
        st.metric("95th Percentile", format_runtime_display(perf_summary['p95_runtime_sec']))
        st.metric("Slowest Task Table", perf_summary['slowest_task_table'])


def render_duration_trends(df: pd.DataFrame, database: str):
    """Render duration trend visualizations with dynamic date filtering."""
    st.subheader("📈 Performance Trends")
    
    # Add chart-specific date range filtering that re-queries data
    st.write("**Select Date Range for Charts:**")
    chart_col1, chart_col2, chart_col3 = st.columns([2, 2, 3])
    
    # Set up flexible date range (not constrained by current data)
    today = date.today()
    default_start = today - timedelta(days=7)  # Last week
    default_end = today
    
    with chart_col1:
        chart_start_date = st.date_input(
            "Chart Start Date",
            value=default_start,
            key="chart_start_date",
            help="Charts will show data from this date forward"
        )
    
    with chart_col2:
        chart_end_date = st.date_input(
            "Chart End Date", 
            value=default_end,
            key="chart_end_date",
            help="Charts will show data up to this date"
        )
    
    with chart_col3:
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 Refresh Charts", help="Re-fetch data for selected date range"):
                st.rerun()
        with col_b:
            if st.button("🔍 Check Available Dates", help="See what invoice dates exist in database"):
                # Quick query to see what dates exist
                with st.spinner("Checking available dates..."):
                    try:
                        # Simple query to find available invoice dates
                        if database == "redshift":
                            date_query = """
                            SELECT DISTINCT 
                                CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL 
                                END as invoice_date,
                                method,
                                'cc.billing_task' as source_table
                            FROM cc.billing_task 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                                AND status = 'finished'
                                AND run_duration IS NOT NULL
                                AND IS_VALID_JSON(payload)
                            ORDER BY invoice_date DESC
                            LIMIT 20
                            """
                        else:
                            date_query = """
                            SELECT DISTINCT 
                                (payload::json->'invoiceDate'->>'value')::date as invoice_date,
                                method,
                                'billing_task' as source_table
                            FROM billing_task 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                                AND status = 'finished'
                                AND run_duration IS NOT NULL
                            ORDER BY invoice_date DESC
                            LIMIT 20
                            """
                        
                        available_dates_df = db_util.query(date_query, db=database)
                        if not available_dates_df.empty:
                            st.write("📅 **Available Invoice Dates in Database:**")
                            st.dataframe(available_dates_df)
                        else:
                            st.warning("No invoice dates found in database")
                            
                    except Exception as e:
                        st.error(f"Error checking available dates: {e}")
                        st.exception(e)
    
    # Re-fetch data for the chart date range
    chart_start_str = chart_start_date.strftime('%Y-%m-%d')
    chart_end_str = chart_end_date.strftime('%Y-%m-%d')
    
    with st.spinner(f"Loading chart data for {chart_start_str} to {chart_end_str}..."):
        try:
            chart_df = fetch_invoice_task_duration_analysis(
                start_date=chart_start_str,
                end_date=chart_end_str,
                database=database
            )
            
            # Debug: Show what we got back
            st.write(f"🔍 **Debug Info for {chart_start_str} to {chart_end_str}:**")
            st.write(f"- Rows returned: {len(chart_df)}")
            if not chart_df.empty:
                st.write(f"- Unique invoice dates found: {chart_df['invoice_date'].nunique()}")
                st.write(f"- Date range in results: {chart_df['invoice_date'].min()} to {chart_df['invoice_date'].max()}")
                st.write(f"- Methods found: {chart_df['method'].unique().tolist()}")
                st.write(f"- Task tables found: {chart_df['task_table'].unique().tolist()}")
            else:
                st.write("- No data returned from query")
                
        except Exception as e:
            st.error(f"Error loading chart data: {e}")
            st.exception(e)
            return
    
    if chart_df.empty:
        st.warning(f"No data available for the selected date range ({chart_start_str} to {chart_end_str})")
        st.info("💡 Try selecting a different date range or check if data exists for those dates")
        return
    
    # Prepare data for visualization
    df_viz = chart_df.copy()
    df_viz['invoice_date'] = pd.to_datetime(df_viz['invoice_date'])
    
    st.success(f"📊 **Found {len(df_viz)} records from {chart_start_str} to {chart_end_str}**")
    
    # Tab for different views
    tab1, tab2, tab3 = st.tabs(["Daily Performance", "Method Comparison", "Table Performance"])
    
    with tab1:
        st.write("**Runtime Performance by Invoice Date**")
        
        # Group by date and method for trend line
        daily_trends = df_viz.groupby(['invoice_date', 'method']).agg({
            'total_runtime_hours': 'sum',
            'total_tasks': 'sum',
            'avg_runtime_sec': 'mean'
        }).reset_index()
        
        # Check if we have multiple dates or just one
        unique_dates = daily_trends['invoice_date'].nunique()
        
        if unique_dates == 1:
            # Single date - show bar charts instead of line charts
            st.info("📊 Showing single-date analysis (bar charts used instead of trends)")
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig1 = px.bar(
                    daily_trends,
                    x='method',
                    y='total_runtime_hours',
                    color='method',
                    title=f'Total Runtime by Method ({daily_trends.iloc[0]["invoice_date"].strftime("%Y-%m-%d")})',
                    labels={
                        'method': 'Task Method',
                        'total_runtime_hours': 'Total Runtime (Hours)'
                    }
                )
                
                # Add 24-hour threshold line
                fig1.add_hline(y=24, line_dash="dash", line_color="red", 
                              annotation_text="24h Alert Threshold")
                
                fig1.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                fig2 = px.bar(
                    daily_trends,
                    x='method',
                    y='total_tasks',
                    color='method',
                    title=f'Task Count by Method ({daily_trends.iloc[0]["invoice_date"].strftime("%Y-%m-%d")})',
                    labels={
                        'method': 'Task Method',
                        'total_tasks': 'Number of Tasks'
                    }
                )
                
                fig2.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)
            
            # Show average runtime comparison
            st.write("**Average Task Runtime Comparison**")
            fig3 = px.bar(
                daily_trends,
                x='method',
                y='avg_runtime_sec',
                color='method',
                title=f'Average Runtime per Task ({daily_trends.iloc[0]["invoice_date"].strftime("%Y-%m-%d")})',
                labels={
                    'method': 'Task Method',
                    'avg_runtime_sec': 'Average Runtime (Seconds)'
                }
            )
            
            # Add 30-minute (1800 sec) threshold line
            fig3.add_hline(y=1800, line_dash="dash", line_color="orange", 
                          annotation_text="30min Warning Threshold")
            
            fig3.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)
            
        else:
            # Multiple dates - show line trends
            col1, col2 = st.columns(2)
            
            with col1:
                fig1 = px.line(
                    daily_trends,
                    x='invoice_date',
                    y='total_runtime_hours',
                    color='method',
                    title='Total Runtime Trends',
                    labels={
                        'invoice_date': 'Invoice Date',
                        'total_runtime_hours': 'Total Runtime (Hours)',
                        'method': 'Task Method'
                    }
                )
                
                # Add 24-hour threshold line
                fig1.add_hline(y=24, line_dash="dash", line_color="red", 
                              annotation_text="24h Alert Threshold")
                
                fig1.update_layout(height=350, showlegend=True)
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                fig2 = px.line(
                    daily_trends,
                    x='invoice_date',
                    y='total_tasks',
                    color='method',
                    title='Task Count Trends',
                    labels={
                        'invoice_date': 'Invoice Date',
                        'total_tasks': 'Number of Tasks',
                        'method': 'Task Method'
                    }
                )
                
                fig2.update_layout(height=350, showlegend=True)
                st.plotly_chart(fig2, use_container_width=True)
            
            # Show average runtime trend
            st.write("**Average Task Runtime Trends**")
            fig3 = px.line(
                daily_trends,
                x='invoice_date',
                y='avg_runtime_sec',
                color='method',
                title='Average Runtime Trends',
                labels={
                    'invoice_date': 'Invoice Date',
                    'avg_runtime_sec': 'Average Runtime (Seconds)',
                    'method': 'Task Method'
                }
            )
            
            # Add 30-minute (1800 sec) threshold line
            fig3.add_hline(y=1800, line_dash="dash", line_color="orange", 
                          annotation_text="30min Warning Threshold")
            
            fig3.update_layout(height=300)
            st.plotly_chart(fig3, use_container_width=True)
    
    with tab2:
        st.write("**Performance Comparison by Method**")
        
        # Compare methods
        method_comparison = df_viz.groupby('method').agg({
            'total_tasks': 'sum',
            'total_runtime_hours': 'sum',
            'avg_runtime_sec': 'mean',
            'p95_runtime_sec': 'mean'
        }).reset_index()
        
        # Calculate tasks per hour
        method_comparison['tasks_per_hour'] = method_comparison['total_tasks'] / method_comparison['total_runtime_hours']
        method_comparison['tasks_per_hour'] = method_comparison['tasks_per_hour'].fillna(0)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.bar(
                method_comparison,
                x='method',
                y='total_runtime_hours',
                title='Total Runtime by Method',
                labels={'total_runtime_hours': 'Total Runtime (Hours)'}
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            fig2 = px.bar(
                method_comparison,
                x='method',
                y='tasks_per_hour',
                title='Throughput (Tasks per Hour)',
                labels={'tasks_per_hour': 'Tasks per Hour'}
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    with tab3:
        st.write("**Performance by Task Table**")
        
        # Compare task tables
        table_comparison = df_viz.groupby('task_table').agg({
            'total_tasks': 'sum',
            'total_runtime_hours': 'sum',
            'avg_runtime_sec': 'mean'
        }).reset_index()
        
        # Calculate efficiency metrics
        table_comparison['avg_tasks_per_day'] = table_comparison['total_tasks'] / df_viz['invoice_date'].nunique()
        
        fig = px.scatter(
            table_comparison,
            x='total_tasks',
            y='total_runtime_hours',
            size='avg_runtime_sec',
            color='task_table',
            title='Task Volume vs Runtime by Table',
            labels={
                'total_tasks': 'Total Tasks',
                'total_runtime_hours': 'Total Runtime (Hours)',
                'avg_runtime_sec': 'Avg Runtime (Sec)'
            }
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show table data
        st.dataframe(
            table_comparison,
            column_config={
                "task_table": "Task Table",
                "total_tasks": st.column_config.NumberColumn("Total Tasks", format="%d"),
                "total_runtime_hours": st.column_config.NumberColumn("Total Runtime (Hours)", format="%.2f"),
                "avg_runtime_sec": st.column_config.NumberColumn("Avg Runtime (Sec)", format="%.1f"),
                "avg_tasks_per_day": st.column_config.NumberColumn("Avg Tasks/Day", format="%.1f")
            },
            use_container_width=True,
            hide_index=True
        )


def render_comprehensive_invoice_analysis(database: str):
    """Render comprehensive invoice analysis based on the createPartnerInvoice performance analysis query."""
    st.subheader("🔍 Comprehensive Invoice Analysis")
    st.markdown("""
    Deep-dive analysis for a specific invoice date showing overall performance, task distribution, 
    and throughput metrics across all task tables.
    """)
    
    # Date input for analysis
    analysis_date = st.date_input(
        "Select Invoice Date for Analysis",
        value=date.today() - timedelta(days=1),
        key="comprehensive_analysis_date",
        help="Analyze all createPartnerInvoice and createCompanyInvoice tasks for this specific invoice date"
    )
    
    if st.button("🚀 Run Analysis", help="Execute comprehensive analysis for selected date"):
            analysis_date_str = analysis_date.strftime('%Y-%m-%d')
            
            with st.spinner(f"Running comprehensive analysis for {analysis_date_str}..."):
                try:
                    # Build the comprehensive analysis queries based on your SQL file
                    if database == "redshift":
                        # Part 1: Overall Performance Summary
                        overall_query = """
                        WITH all_tasks AS (
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM cc.billing_task 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM cc.billing_task_2
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM cc.mca_task
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM cc.mca_task_2
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM cc.mca_task_3
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM cc.mca_task_4
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM cc.mca_task_5
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM cc.report_task
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM cc.erp_task
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                        )
                        
                        SELECT 
                            'OVERALL_PERFORMANCE' as metric_category,
                            COUNT(*) as total_tasks,
                            COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_tasks,
                            COUNT(CASE WHEN status = 'new' THEN 1 END) as new_tasks,
                            COUNT(CASE WHEN status = 'error' THEN 1 END) as error_tasks,
                            MIN(created_dt) as first_task_queued,
                            MAX(CASE WHEN status = 'finished' AND updated_dt IS NOT NULL 
                                 THEN updated_dt END) as last_task_completed,
                            ROUND(
                                DATEDIFF(hour, MIN(created_dt), MAX(CASE WHEN status = 'finished' AND updated_dt IS NOT NULL THEN updated_dt END)), 2
                            ) as total_runtime_hours,
                            ROUND(
                                (COUNT(CASE WHEN status = 'finished' THEN 1 END)::numeric / 
                                 NULLIF(COUNT(*)::numeric, 0)) * 100, 2
                            ) as completion_rate_percent,
                            ROUND(
                                AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                     THEN run_duration END) / 1000.0, 2
                            ) as avg_task_runtime_seconds
                        FROM all_tasks
                        """
                        
                        # PostgreSQL version
                    else:
                        overall_query = """
                        WITH all_tasks AS (
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM billing_task 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM billing_task_2
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM mca_task
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM mca_task_2
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM mca_task_3
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM mca_task_4
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM mca_task_5
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM report_task
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            
                            UNION ALL
                            
                            SELECT 
                                created_dt, 
                                updated_dt, 
                                status,
                                method,
                                run_duration
                            FROM erp_task
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                        )
                        
                        SELECT 
                            'OVERALL_PERFORMANCE' as metric_category,
                            COUNT(*) as total_tasks,
                            COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_tasks,
                            COUNT(CASE WHEN status = 'new' THEN 1 END) as new_tasks,
                            COUNT(CASE WHEN status = 'error' THEN 1 END) as error_tasks,
                            MIN(created_dt) as first_task_queued,
                            MAX(CASE WHEN status = 'finished' AND updated_dt IS NOT NULL 
                                 THEN updated_dt END) as last_task_completed,
                            ROUND(
                                EXTRACT(EPOCH FROM (
                                    MAX(CASE WHEN status = 'finished' AND updated_dt IS NOT NULL THEN updated_dt END) - 
                                    MIN(created_dt)
                                )) / 3600.0, 2
                            ) as total_runtime_hours,
                            ROUND(
                                (COUNT(CASE WHEN status = 'finished' THEN 1 END)::numeric / 
                                 NULLIF(COUNT(*)::numeric, 0)) * 100, 2
                            ) as completion_rate_percent,
                            ROUND(
                                AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                     THEN run_duration END) / 1000.0, 2
                            ) as avg_task_runtime_seconds
                        FROM all_tasks
                        """
                    
                    # Execute overall performance query
                    # Replace all %s with the actual date parameter for Redshift/PostgreSQL
                    formatted_query = overall_query
                    for i in range(9):  # Replace all 9 %s instances (now includes report_task and erp_task)
                        formatted_query = formatted_query.replace('%s', f"'{analysis_date_str}'", 1)
                    
                    overall_df = db_util.query(formatted_query, db=database)
                    
                    if overall_df.empty:
                        st.warning(f"No data found for invoice date {analysis_date_str}")
                        return
                    
                    # Display Overall Performance
                    st.write("### 📊 Overall Performance Summary")
                    overall_row = overall_df.iloc[0]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Tasks", f"{overall_row['total_tasks']:,}")
                        st.metric("Completed Tasks", f"{overall_row['completed_tasks']:,}")
                    
                    with col2:
                        st.metric("New Tasks", f"{overall_row['new_tasks']:,}")
                        st.metric("Error Tasks", f"{overall_row['error_tasks']:,}")
                    
                    with col3:
                        st.metric("Total Runtime", f"{overall_row['total_runtime_hours']:.2f}h")
                        st.metric("Completion Rate", f"{overall_row['completion_rate_percent']:.1f}%")
                    
                    with col4:
                        st.metric("Avg Task Runtime", f"{overall_row['avg_task_runtime_seconds']:.1f}s")
                        if overall_row['first_task_queued'] and overall_row['last_task_completed']:
                            st.metric("Duration", f"{overall_row['first_task_queued'].strftime('%H:%M')} - {overall_row['last_task_completed'].strftime('%H:%M')}")
                    
                    # Task Distribution Query (Part 2 from your SQL)
                    if database == "redshift":
                        distribution_query = """
                        WITH task_distribution AS (
                            SELECT 
                                'cc.billing_task' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM cc.billing_task 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'cc.billing_task_2' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM cc.billing_task_2 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'cc.mca_task' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM cc.mca_task 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'cc.mca_task_2' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM cc.mca_task_2 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'cc.mca_task_3' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM cc.mca_task_3 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'cc.mca_task_4' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM cc.mca_task_4 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'cc.mca_task_5' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM cc.mca_task_5 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'cc.report_task' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM cc.report_task 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'cc.erp_task' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM cc.erp_task 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND CASE WHEN IS_VALID_JSON(payload) 
                                     THEN JSON_EXTRACT_PATH_TEXT(payload, 'invoiceDate', 'value')::date 
                                     ELSE NULL END = %s
                            GROUP BY method
                        )
                        
                        SELECT 
                            task_table,
                            method,
                            task_count,
                            completed_count,
                            new_count,
                            error_count,
                            ROUND((completed_count::numeric / NULLIF(task_count::numeric, 0)) * 100, 2) as completion_rate,
                            avg_runtime_seconds
                        FROM task_distribution
                        WHERE task_count > 0
                        ORDER BY task_table, method
                        """
                    else:
                        distribution_query = """
                        WITH task_distribution AS (
                            SELECT 
                                'billing_task' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM billing_task 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'billing_task_2' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM billing_task_2 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'mca_task' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM mca_task 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'mca_task_2' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM mca_task_2 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'mca_task_3' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM mca_task_3 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'mca_task_4' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM mca_task_4 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'mca_task_5' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM mca_task_5 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'report_task' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM report_task 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            GROUP BY method
                            
                            UNION ALL
                            
                            SELECT 
                                'erp_task' as task_table,
                                method,
                                COUNT(*) as task_count,
                                COUNT(CASE WHEN status = 'finished' THEN 1 END) as completed_count,
                                COUNT(CASE WHEN status = 'new' THEN 1 END) as new_count,
                                COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count,
                                ROUND(AVG(CASE WHEN status = 'finished' AND run_duration IS NOT NULL 
                                               THEN run_duration END) / 1000.0, 2) as avg_runtime_seconds
                            FROM erp_task 
                            WHERE method IN ('createPartnerInvoice', 'createCompanyInvoice')
                            AND (payload::json->'invoiceDate'->>'value')::date = %s
                            GROUP BY method
                        )
                        
                        SELECT 
                            task_table,
                            method,
                            task_count,
                            completed_count,
                            new_count,
                            error_count,
                            ROUND((completed_count::numeric / NULLIF(task_count::numeric, 0)) * 100, 2) as completion_rate,
                            avg_runtime_seconds
                        FROM task_distribution
                        WHERE task_count > 0
                        ORDER BY task_table, method
                        """
                    
                    # Execute distribution query
                    # Replace all %s with the actual date parameter for Redshift/PostgreSQL
                    formatted_dist_query = distribution_query
                    for i in range(9):  # Replace all 9 %s instances (now includes all task tables)
                        formatted_dist_query = formatted_dist_query.replace('%s', f"'{analysis_date_str}'", 1)
                    
                    distribution_df = db_util.query(formatted_dist_query, db=database)
                    
                    if not distribution_df.empty:
                        st.write("### 📋 Task Distribution by Table and Method")
                        
                        # Create visualization
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            fig1 = px.bar(
                                distribution_df,
                                x='task_table',
                                y='task_count',
                                color='method',
                                title='Task Count by Table and Method',
                                labels={'task_count': 'Number of Tasks', 'task_table': 'Task Table'}
                            )
                            st.plotly_chart(fig1, use_container_width=True)
                        
                        with col2:
                            fig2 = px.bar(
                                distribution_df,
                                x='task_table',
                                y='avg_runtime_seconds',
                                color='method',
                                title='Average Runtime by Table and Method',
                                labels={'avg_runtime_seconds': 'Avg Runtime (Seconds)', 'task_table': 'Task Table'}
                            )
                            st.plotly_chart(fig2, use_container_width=True)
                        
                        # Show detailed table
                        st.dataframe(
                            distribution_df,
                            column_config={
                                "task_table": "Task Table",
                                "method": "Method",
                                "task_count": st.column_config.NumberColumn("Tasks", format="%d"),
                                "completed_count": st.column_config.NumberColumn("Completed", format="%d"),
                                "new_count": st.column_config.NumberColumn("New", format="%d"),
                                "error_count": st.column_config.NumberColumn("Errors", format="%d"),
                                "completion_rate": st.column_config.NumberColumn("Completion %", format="%.1f"),
                                "avg_runtime_seconds": st.column_config.NumberColumn("Avg Runtime (s)", format="%.1f")
                            },
                            use_container_width=True,
                            hide_index=True
                        )
                        
                except Exception as e:
                    st.error(f"Error running comprehensive analysis: {e}")
                    st.exception(e)


def render_detailed_data(df: pd.DataFrame):
    """Render the detailed data table with filtering and download options."""
    if df.empty:
        st.info("No detailed data available.")
        return
    
    st.subheader("📋 Detailed Analysis Data")
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        method_filter = st.selectbox(
            "Filter by Method",
            options=["All"] + sorted(df['method'].unique().tolist()),
            key="detail_method_filter"
        )
    
    with col2:
        table_filter = st.selectbox(
            "Filter by Task Table",
            options=["All"] + sorted(df['task_table'].unique().tolist()),
            key="detail_table_filter"
        )
    
    with col3:
        alert_filter = st.selectbox(
            "Show Only",
            options=["All Records", "With Alerts", "Critical Only (>24h)", "Warnings Only (>30m)"],
            key="detail_alert_filter"
        )
    
    # Apply filters
    filtered_df = df.copy()
    
    if method_filter != "All":
        filtered_df = filtered_df[filtered_df['method'] == method_filter]
    
    if table_filter != "All":
        filtered_df = filtered_df[filtered_df['task_table'] == table_filter]
    
    if alert_filter != "All Records":
        if alert_filter == "With Alerts":
            filtered_df = filtered_df[filtered_df['alert_message'].notna()]
        elif alert_filter == "Critical Only (>24h)":
            if 'alert_24hr_exceeded' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['alert_24hr_exceeded'] == True]
            else:
                filtered_df = filtered_df.iloc[0:0]  # Empty DataFrame
        elif alert_filter == "Warnings Only (>30m)":
            if 'alert_30min_task_exceeded' in filtered_df.columns and 'alert_24hr_exceeded' in filtered_df.columns:
                filtered_df = filtered_df[(filtered_df['alert_30min_task_exceeded'] == True) & 
                                        (filtered_df['alert_24hr_exceeded'] != True)]
            else:
                filtered_df = filtered_df.iloc[0:0]  # Empty DataFrame
    
    # Show filtered data count
    st.write(f"Showing {len(filtered_df):,} of {len(df):,} records")
    
    # Style rows with alerts
    def highlight_alerts(row):
        try:
            if 'alert_24hr_exceeded' in row.index and row['alert_24hr_exceeded']:
                return ['background-color: #ffebee'] * len(row)
            elif 'alert_30min_task_exceeded' in row.index and row['alert_30min_task_exceeded']:
                return ['background-color: #fff3e0'] * len(row)
        except (KeyError, AttributeError):
            pass
        return [''] * len(row)
    
    # Display columns for the table
    display_columns = [
        'invoice_date', 'task_table', 'method', 'total_tasks',
        'total_runtime_hours', 'avg_runtime_sec', 'max_runtime_sec',
        'p95_runtime_sec', 'alert_message'
    ]
    
    # Filter to only existing columns
    available_columns = [col for col in display_columns if col in filtered_df.columns]
    display_df = filtered_df[available_columns]
    
    if not display_df.empty:
        styled_df = display_df.style.apply(highlight_alerts, axis=1)
        
        st.dataframe(
            styled_df,
            column_config={
                "invoice_date": st.column_config.DateColumn("Invoice Date"),
                "task_table": "Task Table",
                "method": "Method", 
                "total_tasks": st.column_config.NumberColumn("Total Tasks", format="%d"),
                "total_runtime_hours": st.column_config.NumberColumn("Runtime (Hours)", format="%.2f"),
                "avg_runtime_sec": st.column_config.NumberColumn("Avg Runtime (Sec)", format="%.1f"),
                "max_runtime_sec": st.column_config.NumberColumn("Max Runtime (Sec)", format="%.1f"),
                "p95_runtime_sec": st.column_config.NumberColumn("95th %ile (Sec)", format="%.1f"),
                "alert_message": st.column_config.TextColumn("Alert Message", width="large")
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Download button
        csv_data = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv_data,
            file_name=f"invoice_task_duration_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No data matches the selected filters.")


def show_invoice_task_duration_monitoring():
    """Main function to render the Invoice Task Duration Monitoring page."""
    
    auth_util.auth_for(ROLES)
    
    st.title("🕐 Invoice Task Duration Monitoring")
    st.markdown("""
    Monitor and analyze runtime performance for `createPartnerInvoice` and `createCompanyInvoice` tasks.
    Automated alerting for tasks exceeding performance thresholds.
    """)
    
    # Date range selection
    st.subheader("📅 Analysis Period")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    default_start, default_end = get_default_date_range()
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.strptime(default_start, '%Y-%m-%d').date(),
            key="duration_start_date"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.strptime(default_end, '%Y-%m-%d').date(),
            key="duration_end_date"
        )
    
    with col3:
        # Check if PostgreSQL is available and set default accordingly
        available_dbs = []
        default_index = 0
        
        # PostgreSQL (read replica) preferred when available
        if "postgresql" in st.secrets.get("connections", {}):
            available_dbs.append("postgresql")
        
        # Redshift always available as fallback
        available_dbs.append("redshift")
        
        # Default to PostgreSQL if available, otherwise Redshift
        if "postgresql" in available_dbs:
            default_index = 0  # PostgreSQL
        else:
            default_index = 0  # Redshift (only option)
        
        database = st.selectbox(
            "Database",
            options=available_dbs,
            index=default_index,
            key="duration_database",
            help="PostgreSQL (read replica) is preferred for better performance"
        )
    
    # Validate date range
    if start_date > end_date:
        st.error("Start date must be before end date.")
        return
    
    if (end_date - start_date).days > 365:
        st.warning("Date range is longer than 1 year. This may result in slower query performance.")
    
    # Convert dates to strings
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    try:
        # Fetch data
        with st.spinner("Loading duration analysis data..."):
            duration_df = fetch_invoice_task_duration_analysis(
                start_date=start_date_str,
                end_date=end_date_str,
                database=database
            )
        
        if duration_df.empty:
            st.info(f"No invoice task data found for the period {start_date_str} to {end_date_str}.")
            return
        
        # Generate summaries
        alert_summary = get_alert_summary(duration_df)
        perf_summary = get_performance_summary(duration_df)
        
        # Render sections
        render_alert_summary(alert_summary)
        st.divider()
        
        render_performance_summary(perf_summary)
        st.divider()
        
        render_duration_trends(duration_df, database)
        st.divider()
        
        render_detailed_data(duration_df)
        st.divider()
        
        render_comprehensive_invoice_analysis(database)
        
        # Add refresh timestamp
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        st.error(f"Error loading duration analysis data: {str(e)}")
        st.exception(e)


if __name__ == "__page__":
    show_invoice_task_duration_monitoring()
