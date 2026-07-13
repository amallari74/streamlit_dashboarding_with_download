import streamlit as st
import pandas as pd
from utils import db_util, auth_util
from router.roles import BILLING_RUN_ROLES as ROLES
from billing_run.models.repositories import fetch_billing_tasks, fetch_invoice_release_details, fetch_invoice_balance_by_business_unit
from billing_run.components.task_stats import render_task_stats
from billing_run.components.refresh_status import show_multiple_refresh_status

def render_method_breakdown(df):
    """
    Renders a breakdown of tasks by method.
    
    Args:
        df (DataFrame): DataFrame containing task data
    """
    if len(df) > 0:
        # Count tasks by method
        method_counts = df['method'].value_counts().to_dict()
        
        # Create a bar chart for method counts
        st.subheader("Invoice Release Methods")
        
        # Create columns for the metrics
        cols = st.columns(len(method_counts))
        
        # Display metrics for each method
        for i, (method, count) in enumerate(method_counts.items()):
            # Format method name for display
            method_display = method.replace('send', '').replace('InvoiceFor', '')
            with cols[i]:
                st.metric(method_display, count)
        
        # Create a DataFrame for the chart
        method_df = pd.DataFrame({
            'Method': list(method_counts.keys()),
            'Count': list(method_counts.values())
        })
        
        # Display chart - REMOVED BAR CHART
    else:
        st.info("No invoice release tasks found for the current month.")

def render_invoice_release_status():
    """
    Renders a table showing invoice release status by business unit.
    """
    # Fetch invoice release data
    invoice_df = fetch_invoice_release_details()
    
    if len(invoice_df) > 0:
        st.subheader("Invoice Release Status")
        
        # Add business unit filter
        available_bus = sorted(invoice_df['business_unit_code'].unique())
        
        selected_bus = st.multiselect(
            "Filter by Business Unit:",
            options=available_bus,
            default=[],
            key="bu_filter_invoice_release",
            help="Select one or more business units to filter the invoices"
        )
        
        # Apply filter if business units are selected
        filtered_df = invoice_df
        if selected_bus:
            filtered_df = invoice_df[invoice_df['business_unit_code'].isin(selected_bus)]
            st.write(f"Showing {len(filtered_df)} of {len(invoice_df)} invoices")
        
        # Create a custom release_status field that prioritizes Void status
        filtered_df['release_status_with_void'] = filtered_df.apply(
            lambda row: 'Void' if row['status'] == 'Void' else row['release_status'], 
            axis=1
        )
        
        # Create pivot table of release status by business unit
        pivot_df = pd.crosstab(
            filtered_df['business_unit_code'], 
            filtered_df['release_status_with_void'], 
            margins=True, 
            margins_name='Total'
        )
        
        # Ensure all status categories exist in the table
        expected_statuses = ['Released', 'Held - Approved', 'Held - Needs Review', 'Void']
        for status in expected_statuses:
            if status not in pivot_df.columns:
                pivot_df[status] = 0
        
        # Add distinct partner count columns instead of percentages
        for status in expected_statuses:
            # For each business unit and status, count distinct partner_ids
            partner_counts = {}
            # Handle the "Total" row separately
            partner_counts['Total'] = filtered_df[filtered_df['release_status_with_void'] == status]['partner_id'].nunique()
            
            # Process each business unit
            for bu in filtered_df['business_unit_code'].unique():
                mask = (filtered_df['business_unit_code'] == bu) & (filtered_df['release_status_with_void'] == status)
                partner_counts[bu] = filtered_df[mask]['partner_id'].nunique()
            
            # Add the column to the pivot table
            pivot_df[f"{status} Partners"] = pivot_df.index.map(lambda x: partner_counts.get(x, 0))
        
        # Add distinct partner counts for any other unexpected statuses
        for status in pivot_df.columns:
            if status not in expected_statuses and status != 'Total' and not status.endswith(' Partners'):
                # Same as above for unexpected statuses
                partner_counts = {}
                partner_counts['Total'] = filtered_df[filtered_df['release_status_with_void'] == status]['partner_id'].nunique()
                
                for bu in filtered_df['business_unit_code'].unique():
                    mask = (filtered_df['business_unit_code'] == bu) & (filtered_df['release_status_with_void'] == status)
                    partner_counts[bu] = filtered_df[mask]['partner_id'].nunique()
                
                pivot_df[f"{status} Partners"] = pivot_df.index.map(lambda x: partner_counts.get(x, 0))
        
        # Create new columns list with expected statuses in specified order
        new_columns = []
        
        # Always add all expected statuses in our predefined order
        for status in expected_statuses:
            new_columns.append(status)
            new_columns.append(f"{status} Partners")
        
        # Add any other statuses that might exist but weren't in our expected list
        for status in pivot_df.columns:
            if status not in expected_statuses and status != 'Total' and not status.endswith(' Partners'):
                new_columns.append(status)
                new_columns.append(f"{status} Partners")
                
        new_columns.append('Total')
        
        # Apply column reordering
        pivot_df = pivot_df[new_columns]
        col1, col2, col3, col4 = st.columns(4)
        # Show overall statistics
        total_invoices = len(filtered_df)
        released = len(filtered_df[filtered_df['release_status_with_void'] == 'Released'])
        held_approved = len(filtered_df[filtered_df['release_status_with_void'] == 'Held - Approved'])
        needs_review = len(filtered_df[filtered_df['release_status_with_void'] == 'Held - Needs Review'])
        voided = len(filtered_df[filtered_df['release_status_with_void'] == 'Void'])
        with col1:
            st.metric("Released", f"{released} ({released/total_invoices:.1%})")
        
        with col2:
            st.metric("Held - Approved", f"{held_approved} ({held_approved/total_invoices:.1%})")
        
        with col3:
            st.metric("Held - Needs Review", f"{needs_review} ({needs_review/total_invoices:.1%})")
            
        with col4:
            st.metric("Void", f"{voided} ({voided/total_invoices:.1%})")
        # Display the table
        st.dataframe(pivot_df, use_container_width=True)
    else:
        st.info("No invoice data available for the current month.")

def render_invoice_balance_section():
    """
    Renders invoice balance by business unit with filters for status, approved, and is_email_sent,
    and shows top-level sum of balance and breakdown by business unit.
    """
    # Fetch invoice balance data
    balance_df = fetch_invoice_balance_by_business_unit()

    if len(balance_df) == 0:
        st.info("No invoice balance data available for the current month.")
        return

    st.subheader("Invoice Balance by Business Unit")

    # Filters for status, approved, and is_email_sent
    status_options = sorted(balance_df['status'].unique())
    selected_statuses = st.multiselect(
        "Filter by Status:",
        options=status_options,
        default=status_options,
        key="balance_status_filter"
    )
    filtered_df = balance_df[balance_df['status'].isin(selected_statuses)]

    approved_options = [True, False]
    selected_approved = st.multiselect(
        "Filter by Approved:",
        options=approved_options,
        default=approved_options,
        key="balance_approved_filter"
    )
    filtered_df = filtered_df[filtered_df['approved'].isin(selected_approved)]

    email_options = [True, False]
    selected_email = st.multiselect(
        "Filter by Email Sent:",
        options=email_options,
        default=email_options,
        key="balance_email_sent_filter"
    )
    filtered_df = filtered_df[filtered_df['is_email_sent'].isin(selected_email)]

    # Top-level sum of balance
    total_balance = filtered_df['balance_usd'].sum()
    st.metric("Total Balance", f"${total_balance:,.2f}")

    # Metrics for Email Sent and Approved flags
    col1, col2, col3, col4 = st.columns(4)
    # Sum balances where email was sent vs not
    balance_email_true = filtered_df[filtered_df['is_email_sent']]['balance_usd'].sum()
    balance_email_false = filtered_df[~filtered_df['is_email_sent']]['balance_usd'].sum()
    with col1:
        st.metric("Balance - Email Sent", f"${balance_email_true:,.2f}")
    with col2:
        st.metric("Balance - Not Email Sent", f"${balance_email_false:,.2f}")
    # Sum balances where approved vs not
    balance_approved_true = filtered_df[filtered_df['approved']]['balance_usd'].sum()
    balance_approved_false = filtered_df[~filtered_df['approved']]['balance_usd'].sum()
    with col3:
        st.metric("Balance - Approved", f"${balance_approved_true:,.2f}")
    with col4:
        st.metric("Balance - Not Approved", f"${balance_approved_false:,.2f}")

    # Breakdown by business unit
    bu_balance = filtered_df.groupby('business_unit_code')['balance_usd'].sum().reset_index()
    bu_balance = bu_balance.sort_values(by='balance_usd', ascending=False)
    st.dataframe(bu_balance, use_container_width=True, hide_index=True)

def init():
    auth_util.auth_for(ROLES)
    
    st.title("Invoice Release Monitoring")
    
    # Fetch data
    invoice_release_df = fetch_billing_tasks(methods=['sendInvoiceForCompany', 'sendInvoiceForPartner'])
    

    # Show task status overview with combined task stats rendering
    st.subheader("Task Status Overview")
    render_task_stats(
        df=invoice_release_df,
        category="invoice_release",
        show_metrics=True,
        show_table=True
    )
    
    # Show method breakdown
    render_method_breakdown(invoice_release_df)
    
    # Show invoice release status by business unit
    st.divider()
    render_invoice_release_status()

    # Show invoice balance section
    st.divider()
    render_invoice_balance_section()

if __name__ == "__page__":
    init() 