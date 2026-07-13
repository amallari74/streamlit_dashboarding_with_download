import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from utils import db_util, auth_util
from router.roles import DIAGNOSTICS_ROLES as ROLES
from billing_run.models.billing_task_model import fetch_task_status

def calculate_change_percentage(current, previous):
    """Calculate percentage change between current and previous values"""
    if previous == 0:
        return 100 if current > 0 else 0
    return ((current - previous) / previous * 100)

def load_task_status_data(selected_month):
    """Load task status data for the specified month"""
    return fetch_task_status(selected_month)

def render_high_level_metrics(df):
    """Render high level task metrics"""
    st.subheader("High Level Metrics")
    
    # Data completeness indicators
    invoice_generation_complete = df['is_invoice_generation_complete'].all()
    
    # Calculate completion status for each method category
    tax_tasks = df[df['method'].str.contains('Tax', case=False, na=False)]
    tax_calculated_complete = (
        len(tax_tasks) > 0 and 
        tax_tasks['new_tasks_current'].sum() == 0 and 
        tax_tasks['errored_tasks_current'].sum() == 0
    )
    
    send_tasks = df[df['method'].str.contains('send', case=False, na=False)]
    invoice_sent_complete = (
        len(send_tasks) > 0 and 
        send_tasks['new_tasks_current'].sum() == 0 and 
        send_tasks['errored_tasks_current'].sum() == 0
    )
    
    # Status indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.caption("Tax Calculation Status")
        st.metric(
            "Tax Calculated",
            "Complete" if tax_calculated_complete else "Incomplete",
            delta_color="normal"
        )
        if not tax_calculated_complete and len(tax_tasks) > 0:
            with st.expander("View Tax Calculation Issues"):
                new_tasks = tax_tasks[tax_tasks['new_tasks_current'] > 0]
                error_tasks = tax_tasks[tax_tasks['errored_tasks_current'] > 0]
                for _, row in new_tasks.iterrows():
                    st.markdown(f"- **{row['method']}** ({row['partner_region']}): {row['new_tasks_current']} new tasks")
                for _, row in error_tasks.iterrows():
                    st.markdown(f"- **{row['method']}** ({row['partner_region']}): {row['errored_tasks_current']} errored tasks")
    
    with col2:
        st.caption("Invoice Generation Status")
        st.metric(
            "Invoice Generation",
            "Complete" if invoice_generation_complete else "Incomplete",
            delta_color="normal"
        )
        if not invoice_generation_complete:
            # Find methods with new tasks
            methods_with_new = df[
                (df['new_tasks_current'] > 0) & 
                (df['method'].str.contains('create', case=False, na=False))
            ].sort_values('new_tasks_current', ascending=False)
            if not methods_with_new.empty:
                with st.expander(f"View Generation Issues"):
                    for _, row in methods_with_new.iterrows():
                        st.markdown(f"- **{row['method']}** ({row['partner_region']}): {row['new_tasks_current']} new tasks")
    
    with col3:
        st.caption("Invoice Sending Status")
        st.metric(
            "Invoice Sent",
            "Complete" if invoice_sent_complete else "Incomplete",
            delta_color="normal"
        )
        if not invoice_sent_complete and len(send_tasks) > 0:
            with st.expander("View Sending Issues"):
                new_tasks = send_tasks[send_tasks['new_tasks_current'] > 0]
                error_tasks = send_tasks[send_tasks['errored_tasks_current'] > 0]
                for _, row in new_tasks.iterrows():
                    st.markdown(f"- **{row['method']}** ({row['partner_region']}): {row['new_tasks_current']} new tasks")
                for _, row in error_tasks.iterrows():
                    st.markdown(f"- **{row['method']}** ({row['partner_region']}): {row['errored_tasks_current']} errored tasks")
    
    st.caption("Task Counts and States")
    # Calculate totals for current month
    total_tasks = df['tasks_total'].sum()
    total_finished = df['finished_tasks_total'].sum()
    total_errors = df['errored_tasks_total'].sum()
    total_reviewed = df['reviewed_tasks_total'].sum()
    
    # Get previous month totals
    prev_total_tasks = df['prev_tasks_total'].iloc[0]
    prev_total_finished = df['prev_finished_total'].iloc[0]
    prev_total_errors = df['prev_errored_total'].iloc[0]
    prev_total_reviewed = df['prev_reviewed_total'].iloc[0]
    
    # Calculate change percentages
    tasks_change = calculate_change_percentage(total_tasks, prev_total_tasks)
    finished_change = calculate_change_percentage(total_finished, prev_total_finished)
    errors_change = calculate_change_percentage(total_errors, prev_total_errors)
    reviewed_change = calculate_change_percentage(total_reviewed, prev_total_reviewed)
    
    # Display historical metrics
    st.caption("Historical Task States (Tasks that were ever in this state for this month)")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Tasks",
            f"{total_tasks:,}",
            f"{tasks_change:+.1f}% ({prev_total_tasks:,})"
        )
    
    with col2:
        st.metric(
            "Total Finished",
            f"{total_finished:,}",
            f"{finished_change:+.1f}% ({prev_total_finished:,})"
        )
    
    with col3:
        st.metric(
            "Total Errored",
            f"{total_errors:,}",
            f"{errors_change:+.1f}% ({prev_total_errors:,})",
            delta_color="normal" if errors_change < 0 else "inverse"
        )
    
    with col4:
        st.metric(
            "Total Reviewed",
            f"{total_reviewed:,}",
            f"{reviewed_change:+.1f}% ({prev_total_reviewed:,})"
        )
    
    # Display current state metrics
    st.caption("Current Task States")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "New Tasks",
            f"{df['new_tasks_current'].sum():,}"
        )
    
    with col2:
        st.metric(
            "Currently Errored",
            f"{df['errored_tasks_current'].sum():,}"
        )
    
    with col3:
        st.metric(
            "Currently Reviewed",
            f"{df['reviewed_tasks_current'].sum():,}"
        )
    
    with col4:
        st.metric(
            "Currently Finished",
            f"{df['finished_tasks_current'].sum():,}"
        )
    
    with col5:
        st.metric(
            "Error Resolution",
            f"{df['errored_tasks_resolved'].sum():,}/{df['errored_tasks_total'].sum():,}",
            f"{df['errored_tasks_resolved'].sum() / df['errored_tasks_total'].sum() * 100:.1f}% Resolved"
        )

def render_region_breakdown(df):
    """Render region-based task breakdown"""
    st.subheader("Region Breakdown")
    
    # Group by region
    region_metrics = df.groupby('partner_region').agg({
        'tasks_total': 'sum',
        'finished_tasks_current': 'sum',
        'errored_tasks_current': 'sum',
        'reviewed_tasks_current': 'sum',
        'new_tasks_current': 'sum',
        'errored_tasks_total': 'sum',
        'errored_tasks_resolved': 'sum',
        'errored_tasks_unresolved': 'sum'
    }).reset_index()
    
    # Calculate error rates
    region_metrics['error_rate'] = (region_metrics['errored_tasks_total'] / region_metrics['tasks_total'] * 100).round(2)
    region_metrics['resolution_rate'] = (region_metrics['errored_tasks_resolved'] / region_metrics['errored_tasks_total'] * 100).fillna(0).round(2)
    
    # Create bar chart for current states
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Currently Finished',
        x=region_metrics['partner_region'],
        y=region_metrics['finished_tasks_current'],
        marker_color='green'
    ))
    
    fig.add_trace(go.Bar(
        name='Currently Errored',
        x=region_metrics['partner_region'],
        y=region_metrics['errored_tasks_current'],
        marker_color='red'
    ))
    
    fig.add_trace(go.Bar(
        name='Currently Reviewed',
        x=region_metrics['partner_region'],
        y=region_metrics['reviewed_tasks_current'],
        marker_color='yellow'
    ))
    
    fig.add_trace(go.Bar(
        name='Currently New',
        x=region_metrics['partner_region'],
        y=region_metrics['new_tasks_current'],
        marker_color='blue'
    ))
    
    fig.update_layout(
        barmode='group',
        title='Current Task Status by Region',
        xaxis_title='Region',
        yaxis_title='Number of Tasks'
    )
    
    st.plotly_chart(fig)
    
    # Show detailed metrics table
    st.caption("Current State Metrics")
    st.dataframe(
        region_metrics,
        column_config={
            'partner_region': 'Region',
            'tasks_total': st.column_config.NumberColumn('Total Tasks', format="%d"),
            'new_tasks_current': st.column_config.NumberColumn('Currently New', format="%d"),
            'finished_tasks_current': st.column_config.NumberColumn('Currently Finished', format="%d"),
            'errored_tasks_current': st.column_config.NumberColumn('Currently Errored', format="%d"),
            'reviewed_tasks_current': st.column_config.NumberColumn('Currently Reviewed', format="%d"),
            'errored_tasks_total': st.column_config.NumberColumn('Total Errors', format="%d"),
            'errored_tasks_resolved': st.column_config.NumberColumn('Errors Resolved', format="%d"),
            'errored_tasks_unresolved': st.column_config.NumberColumn('Errors Unresolved', format="%d"),
            'error_rate': st.column_config.NumberColumn('Error Rate', format="%.2f%%"),
            'resolution_rate': st.column_config.NumberColumn('Resolution Rate', format="%.2f%%")
        },
        hide_index=True
    )

def render_method_breakdown(df):
    """Render method-based task breakdown"""
    st.subheader("Method Breakdown")
    
    # Allow filtering by region
    selected_region = st.selectbox(
        "Filter by Region",
        options=['All'] + sorted(df['partner_region'].unique().tolist()),
        key="method_region_filter"
    )
    
    # Filter data if region is selected
    filtered_df = df if selected_region == 'All' else df[df['partner_region'] == selected_region]
    
    # Group by method
    method_metrics = filtered_df.groupby('method').agg({
        'tasks_total': 'sum',
        'finished_tasks_current': 'sum',
        'errored_tasks_current': 'sum',
        'reviewed_tasks_current': 'sum',
        'new_tasks_current': 'sum',
        'errored_tasks_total': 'sum',
        'errored_tasks_resolved': 'sum',
        'errored_tasks_unresolved': 'sum'
    }).reset_index()
    
    # Calculate rates
    method_metrics['error_rate'] = (method_metrics['errored_tasks_total'] / method_metrics['tasks_total'] * 100).round(2)
    method_metrics['resolution_rate'] = (method_metrics['errored_tasks_resolved'] / method_metrics['errored_tasks_total'] * 100).fillna(0).round(2)
    
    # Sort by current errors (descending) then total tasks (descending)
    method_metrics = method_metrics.sort_values(
        ['errored_tasks_current', 'tasks_total'], 
        ascending=[False, False]
    )
    
    # Create bar chart for current states
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Currently Finished',
        x=method_metrics['method'],
        y=method_metrics['finished_tasks_current'],
        marker_color='green'
    ))
    
    fig.add_trace(go.Bar(
        name='Currently Errored',
        x=method_metrics['method'],
        y=method_metrics['errored_tasks_current'],
        marker_color='red'
    ))
    
    fig.add_trace(go.Bar(
        name='Currently Reviewed',
        x=method_metrics['method'],
        y=method_metrics['reviewed_tasks_current'],
        marker_color='yellow'
    ))
    
    fig.add_trace(go.Bar(
        name='Currently New',
        x=method_metrics['method'],
        y=method_metrics['new_tasks_current'],
        marker_color='blue'
    ))
    
    fig.update_layout(
        barmode='group',
        title='Task Status by Method',
        xaxis_title='Method',
        yaxis_title='Number of Tasks',
        xaxis_tickangle=45,
        height=500
    )
    
    st.plotly_chart(fig)
    
    # Show detailed metrics table
    st.caption("Method Details")
    st.dataframe(
        method_metrics,
        column_config={
            'method': 'Method',
            'tasks_total': st.column_config.NumberColumn('Total Tasks', format="%d"),
            'new_tasks_current': st.column_config.NumberColumn('Currently New', format="%d"),
            'finished_tasks_current': st.column_config.NumberColumn('Currently Finished', format="%d"),
            'errored_tasks_current': st.column_config.NumberColumn('Currently Errored', format="%d"),
            'reviewed_tasks_current': st.column_config.NumberColumn('Currently Reviewed', format="%d"),
            'errored_tasks_total': st.column_config.NumberColumn('Total Errors', format="%d"),
            'errored_tasks_resolved': st.column_config.NumberColumn('Errors Resolved', format="%d"),
            'errored_tasks_unresolved': st.column_config.NumberColumn('Errors Unresolved', format="%d"),
            'error_rate': st.column_config.NumberColumn('Error Rate', format="%.2f%%"),
            'resolution_rate': st.column_config.NumberColumn('Resolution Rate', format="%.2f%%")
        },
        hide_index=True
    )

def show_billing_task_monitoring():
    """Main function to render the Billing Task Monitoring page"""
    auth_util.auth_for(ROLES)
    
    st.title("Billing Task Monitoring")
    
    # Get first day of current month
    current_month = date.today().replace(day=1)
    available_months = [
        (current_month.replace(year=current_month.year + ((current_month.month - i - 1) // 12),
                             month=((current_month.month - i - 1) % 12) + 1))
        for i in range(6)  # Show last 6 months
    ]

    selected_month = st.selectbox(
        "Select Month",
        options=available_months,
        format_func=lambda x: x.strftime("%B %Y"),
        index=0,
        key="month_selector"
    )
    
    # Format selected month for query
    selected_month_str = selected_month.strftime("%Y-%m-%d")
    
    try:
        # Load data
        with st.spinner("Loading task status data..."):
            task_status_df = load_task_status_data(selected_month_str)
        
        if len(task_status_df) == 0:
            st.info("No task data found for the selected month")
            return
            
        # Render high level metrics
        render_high_level_metrics(task_status_df)
        st.divider()
        
        # Create tabs for breakdowns
        tab1, tab2 = st.tabs(["Region Breakdown", "Method Breakdown"])
        
        with tab1:
            render_region_breakdown(task_status_df)
        
        with tab2:
            render_method_breakdown(task_status_df)
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")

if __name__ == "__page__":
    show_billing_task_monitoring() 