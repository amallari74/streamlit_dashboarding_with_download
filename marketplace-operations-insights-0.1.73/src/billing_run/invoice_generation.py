from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from billing_run.components.refresh_status import show_multiple_refresh_status
from billing_run.components.task_stats import render_task_stats
from billing_run.models.invoice_model import (
    fetch_current_month_invoice_counts,
    fetch_missing_partner_invoices,
    fetch_missing_company_invoices
)
from billing_run.models.repositories import (
    fetch_billing_tasks,
    fetch_invoice_row_details,
    fetch_invoice_row_aggregated
)
from router.roles import BILLING_RUN_ROLES as ROLES
from utils import auth_util, db_util

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
        st.subheader("Invoice Generation Methods")
        
        # Create columns for the metrics
        cols = st.columns(len(method_counts))
        
        # Display metrics for each method
        for i, (method, count) in enumerate(method_counts.items()):
            # Format method name for display
            method_display = method.replace('create', '').replace('Invoice', '')
            with cols[i]:
                st.metric(method_display, count)
        
        # Create a DataFrame for the chart
        method_df = pd.DataFrame({
            'Method': list(method_counts.keys()),
            'Count': list(method_counts.values())
        })
        
        # Display chart
        st.bar_chart(method_df.set_index('Method'))
    else:
        st.info("No invoice generation tasks found for the current month.")

def render_invoice_row_data():
    """
    Renders aggregated invoice row data grouped by row_type and term.
    Uses pre-aggregated data from SQL query for improved performance.
    """
    # Fetch pre-aggregated invoice row data
    invoice_row_df = fetch_invoice_row_aggregated()
    
    if len(invoice_row_df) > 0:
        # Add section header
        st.subheader("Invoice Row Type Analysis")
        
        # Add collapsible help text
        with st.expander("About this data"):
            st.write(
                """
                This table shows invoice data summarized by type (one-time, subscription, etc.) 
                and billing period (monthly, annual, etc.).
                
                The data is pulled from the csv_invoice_row_archive table and grouped by row type, term, business unit, and vendor.
                
                Numbers are aggregated by month, with currency values converted using static exchange rates.
                
                You can filter by Business Unit(s) and Vendor using the dropdowns below.
                
                Records = Number of invoice line items

                Customer Total USD = Amount charged to customers (converted to USD)
                
                Partner Total USD = Amount paid to partners (converted to USD)
                """
            )
        
        # Add filters for business_unit and vendor
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            # Get unique business units and add "All" option
            business_units = sorted(invoice_row_df['business_unit'].unique().tolist())
            selected_bus = st.multiselect("Business Unit(s)", business_units, default=[])
        
        with filter_col2:
            # Get unique vendors and add "All" option
            vendors = ["All"] + sorted(invoice_row_df['vendor'].unique().tolist())
            selected_vendor = st.selectbox("Vendor", vendors)
        
        # Apply filters
        filtered_df = invoice_row_df.copy()
        if selected_bus:
            filtered_df = filtered_df[filtered_df['business_unit'].isin(selected_bus)]
        if selected_vendor != "All":
            filtered_df = filtered_df[filtered_df['vendor'] == selected_vendor]
        
        # Get unique month names and row_type_terms from filtered data
        # Sort months in descending order to ensure current month is first
        months = sorted(filtered_df['month_name'].unique(), reverse=True)
        row_types = filtered_df['row_type_term'].unique()
        
        # Create a pivot table structure
        pivot_data = {}
        
        # Initialize the pivot data structure with empty dictionaries for each row type
        for row_type in row_types:
            pivot_data[row_type] = {}
        
        # Populate the pivot data from the aggregated results
        # Group by row_type_term and month_name to properly sum up values
        for (row_type, month), group in filtered_df.groupby(['row_type_term', 'month_name']):
            record_count = group['record_count'].sum()
            usd_total = group['usd_total'].sum()
            usd_cost_total = group['usd_cost_total'].sum()
            
            # Initialize if not exists
            if row_type not in pivot_data:
                pivot_data[row_type] = {}
                
            pivot_data[row_type][f"{month} - Records"] = record_count
            pivot_data[row_type][f"{month} - Customer Total USD"] = "${:,.2f}".format(usd_total)
            pivot_data[row_type][f"{month} - Partner Total USD"] = "${:,.2f}".format(usd_cost_total)
        
        # Convert the dictionary to a DataFrame
        pivot_df = pd.DataFrame.from_dict(pivot_data, orient='index')
        
        # Sort columns to ensure current month comes first
        # Get all columns
        all_columns = list(pivot_df.columns)
        
        # Sort columns by putting current month first for each metric
        if len(months) > 0:
            current_month = months[0]  # First month should be the current month
            
            # Order columns to put current month first for each metric type
            ordered_columns = []
            for metric in ['Records', 'Customer Total USD', 'Partner Total USD']:
                for month in months:
                    col_name = f"{month} - {metric}"
                    if col_name in all_columns:
                        ordered_columns.append(col_name)
            
            # Apply the column ordering if we have columns to order
            if ordered_columns:
                pivot_df = pivot_df[ordered_columns]
        
        # Sort by record count in the current month
        if len(months) > 0:
            current_month = months[0]  # The first month should be the current month
            count_col = f"{current_month} - record_count"
            if count_col in pivot_df.columns:
                pivot_df = pivot_df.sort_values(count_col, ascending=False)
        
        # Display the table
        st.dataframe(pivot_df,
                     height=35 * len(pivot_df) + 38, 
                      use_container_width=True)
    else:
        st.info("No invoice row data available for the selected period.")

def init():
    auth_util.auth_for(ROLES)
    
    st.title("Invoice Generation Monitoring")
    
    # Fetch data
    invoice_generation_df = fetch_billing_tasks(methods=['createPartnerInvoice', 'createCompanyInvoice'])
    
    # Show invoice count comparison and task stats side by side
    stats_col, invoice_col = st.columns([40, 60])  # 40:60 split for better balance
    
    # Task stats in the narrower left column
    with stats_col:
        render_task_stats(
            df=invoice_generation_df,
            category="invoice_generation",
            show_metrics=False,
            show_table=True,
            container=stats_col
        )

    # Invoice counts in the wider right column
    with invoice_col:
        st.markdown("### Invoice Count Comparison")
        
        try:
            # Fetch invoice counts for current and previous month
            invoice_counts = fetch_current_month_invoice_counts()
            if invoice_counts is None:
                st.warning("⚠️ No invoice counts found for the current month. The visualizations below will show zeros. Please try again later.")
            
            # Default all counts to 0 if we couldn't get data
            current_company = 0
            current_partner = 0
            current_total = 0
            prev_company = 0
            prev_partner = 0
            prev_total = 0
            
            if invoice_counts is not None:
                # Get current and previous counts
                current_company = int(invoice_counts.get('company_invoice_count', 0))
                current_partner = int(invoice_counts.get('partner_invoice_count', 0))
                current_total = int(invoice_counts.get('total_invoice_count', 0))
                
                prev_company = int(invoice_counts.get('prev_company_invoice_count', 0))
                prev_partner = int(invoice_counts.get('prev_partner_invoice_count', 0))
                prev_total = int(invoice_counts.get('prev_total_invoice_count', 0))
                

                
                # Show bar chart for invoice comparison
                invoice_types = ['Company', 'Partner', 'Total']
                current_counts = [current_company, current_partner, current_total]
                previous_counts = [prev_company, prev_partner, prev_total]
                
                fig = go.Figure(data=[
                    go.Bar(name='Previous Month', x=invoice_types, y=previous_counts,
                          text=previous_counts, textposition='inside',
                          marker_color='rgb(141, 161, 179)'),
                    go.Bar(name='Current Month', x=invoice_types, y=current_counts,
                          text=current_counts, textposition='inside',
                          marker_color='rgb(55, 83, 109)')
                ])
                
                fig.update_layout(
                    barmode='group',
                    height=600,  # Further reduced height for better fit
                    xaxis=dict(title=None),
                    yaxis=dict(title='Number of Invoices',
                              gridcolor='rgba(0,0,0,0.1)',
                              zerolinecolor='rgba(0,0,0,0.2)'),
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    margin=dict(l=50, r=50, t=20, b=50),  # Adjusted top margin since we removed the title
                    plot_bgcolor='white'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No invoice count data available for the current month.")
        except Exception as e:
            st.error(f"Error fetching invoice counts: {str(e)}")
            st.exception(e)  # This will show the full traceback
    
    # No need for additional task stats section since we moved it above
    
    # Missing Partner Invoices section
    st.subheader("Missing Partner Invoices")
    st.info("Partners with ledger transactions or invoice line items this month but no generated invoice (excluding test, root, house, and manually invoiced accounts)")
    missing_partners = fetch_missing_partner_invoices("cc.", "redshift")
    if missing_partners is not None and len(missing_partners) > 0:
        # Format the DataFrame for display
        display_partners = missing_partners[['partner_id', 'partner_name', 'payment_day', 'cost']].copy()
        display_partners['cost'] = display_partners['cost'].apply(lambda x: f"${x:,.2f}")
        st.dataframe(
            display_partners,
            column_config={
                "partner_id": st.column_config.NumberColumn(
                    "Partner ID", 
                    format="%d",
                    help="Partner identifier"
                ),
                "partner_name": "Partner Name",
                "payment_day": "Payment Day",
                "cost": "Expected Cost"
            },
            use_container_width=True
        )
    else:
        st.info("No missing partner invoices found.")
    
    # Add some vertical spacing
    st.markdown("---")
    
    # Missing Company Invoices section
    st.subheader("Missing Company Invoices")
    st.info("Bill-on-behalf-of enabled companies with ledger transactions or invoice line items this month but no generated invoice (excluding telco companies)")
    missing_companies = fetch_missing_company_invoices("cc.", "redshift")
    if missing_companies is not None and len(missing_companies) > 0:
        # Format the DataFrame for display
        display_companies = missing_companies[['company_id', 'company_name', 'partner_id', 'partner_name', 'payment_day', 'cost']].copy()
        display_companies['cost'] = display_companies['cost'].apply(lambda x: f"${x:,.2f}")
        st.dataframe(
            display_companies,
            column_config={
                "company_id": st.column_config.NumberColumn(
                    "Company ID",
                    format="%d",
                    help="Company identifier"
                ),
                "company_name": "Company Name",
                "partner_id": st.column_config.NumberColumn(
                    "Partner ID",
                    format="%d", 
                    help="Associated partner identifier"
                ),
                "partner_name": "Partner Name",
                "payment_day": "Payment Day",
                "cost": "Expected Cost"
            },
            use_container_width=True
        )
    else:
        st.info("No missing company invoices found.")
    
    # Show invoice row data
    render_invoice_row_data()

if __name__ == "__page__":
    init()