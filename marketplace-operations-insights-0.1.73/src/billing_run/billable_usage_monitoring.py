import streamlit as st
import pandas as pd
from utils import db_util, auth_util
from router.roles import BILLING_RUN_ROLES as ROLES
from billing_run.models.repositories import fetch_arrears_tasks, fetch_arrears_usage_variance, fetch_arrears_product_configurations
from billing_run.components.task_stats import render_task_stats
from billing_run.components.status_utils import create_status_table
from billing_run.components.refresh_status import show_multiple_refresh_status

def render_vendor_status_table(df):
    """
    Renders a table showing task status counts aggregated by vendor.
    
    Args:
        df (DataFrame): DataFrame containing task data
    """
    if len(df) > 0:
        # Create vendor status table using the utility function
        vendor_status_counts = create_status_table(df, index_col='vendor')
        
        # Rename index to capitalize first letter
        vendor_status_counts.index.name = 'Vendor'
        
        # Calculate distinct subscription count by vendor
        subscription_counts = df.groupby('vendor')['subscription_id'].nunique().to_frame('Subscriptions')
        
        # Fetch usage variance data
        usage_variance_df = fetch_arrears_usage_variance()
        
        # Aggregate usage variance data by vendor
        vendor_usage_variance = usage_variance_df.groupby('vendor').agg({
            'usd_current_month_gross_revenue': 'sum',
            'usd_prior_month_revenue': 'sum'
        }).round(2)
        
        # Calculate percentage change after aggregation
        vendor_usage_variance['percentage_change'] = ((vendor_usage_variance['usd_current_month_gross_revenue'] - 
                                                      vendor_usage_variance['usd_prior_month_revenue']) / 
                                                     vendor_usage_variance['usd_prior_month_revenue'].replace(0, float('nan'))) * 100
        
        # Calculate revenue difference
        vendor_usage_variance['revenue_difference'] = vendor_usage_variance['revenue_difference'] = (vendor_usage_variance['usd_current_month_gross_revenue'].fillna(0) - 
+                                              vendor_usage_variance['usd_prior_month_revenue'].fillna(0))

        # Replace inf values (from division by zero) with 0
        vendor_usage_variance['percentage_change'] = vendor_usage_variance['percentage_change'].replace([float('inf'), float('-inf')], 0)
        
        # Rename columns for clarity
        vendor_usage_variance.columns = [
            'Current Month Revenue (USD)',
            'Prior Month Revenue (USD)',
            'Revenue Change (%)', 
            'Revenue Difference (USD)'
        ]
        
        # Join all the dataframes
        final_df = vendor_status_counts.join([subscription_counts, vendor_usage_variance], how='left')
        
        # Fill NaN values with 0
        final_df = final_df.fillna(0)
        
        # Format currency columns with commas and dollar signs
        final_df['Current Month Revenue (USD)'] = final_df['Current Month Revenue (USD)'].apply(lambda x: "${:,.2f}".format(x))
        final_df['Prior Month Revenue (USD)'] = final_df['Prior Month Revenue (USD)'].apply(lambda x: "${:,.2f}".format(x))
        final_df['Revenue Difference (USD)'] = final_df['Revenue Difference (USD)'].apply(lambda x: "${:,.2f}".format(x))
        
        
        # Display the table
        st.subheader("Task Status and Usage by Vendor")
        st.dataframe(
            final_df,
            use_container_width=True,
            column_config={
                "Revenue Change (%)": st.column_config.NumberColumn(
                    format="%.2f%%",
                    help="Percentage change in revenue"
                )
            }
        )
    
    else:
        st.info("No tasks found for the current month.")

def render_vendor_billing_day_groups():
    """
    Renders vendor details grouped by billing day of month in a three-column layout.
    """
    # Add a header for the section
    st.header("Vendors by Billing Day")
    
    # Fetch product configuration data - no need to specify schema or database
    config_df = fetch_arrears_product_configurations()
    
    # Trim whitespace from name column
    config_df['name'] = config_df['name'].str.strip()
    
    # Group vendors by billing day
    day_1_vendors = config_df[config_df['billing_day_of_month'] == 1]
    day_2_vendors = config_df[config_df['billing_day_of_month'] == 2]
    day_3_vendors = config_df[config_df['billing_day_of_month'] == 3]
    
    # Create three columns
    col1, col2, col3 = st.columns(3)
    
    # Display Day 1
    with col1:
        with st.expander("Billing Day 1", expanded=False):
            if len(day_1_vendors) > 0:
                for _, row in day_1_vendors.iterrows():
                    st.markdown(f"**{row['name']}** - {row['task_runner']}")
            else:
                st.info("No vendors for Day 1")
    
    # Display Day 2
    with col2:
        with st.expander("Billing Day 2", expanded=False):
            if len(day_2_vendors) > 0:
                for _, row in day_2_vendors.iterrows():
                    st.markdown(f"**{row['name']}** - {row['task_runner']}")
            else:
                st.info("No vendors for Day 2")
    
    # Display Day 3
    with col3:
        with st.expander("Billing Day 3", expanded=False):
            if len(day_3_vendors) > 0:
                for _, row in day_3_vendors.iterrows():
                    st.markdown(f"**{row['name']}** - {row['task_runner']}")
            else:
                st.info("No vendors for Day 3")

def init():
    auth_util.auth_for(ROLES)
    
    st.title("Billable Usage Monitoring")
    
    # Add refresh status in the sidebar
    # show_multiple_refresh_status([
    #     "fetch_arrears_tasks", 
    #     "fetch_arrears_usage_variance", 
    #     "fetch_arrears_product_configurations"
    # ], title="Data Last Refreshed")
    
    # Fetch data
    arrears_tasks_df = fetch_arrears_tasks()
    
    # Show task status overview with combined task stats rendering
    st.subheader("Task Status Overview")
    # We use show_table=False here because we have a custom vendor status table implementation below
    # that provides additional metrics like revenue data and subscription counts
    render_task_stats(
        df=arrears_tasks_df,
        category="arrears_tasks",
        show_metrics=True,
        show_table=False  # We have a custom vendor table instead
    )

    st.divider()
    
    # Show vendor billing day groups
    render_vendor_billing_day_groups()
    
    # Show vendor status table (custom implementation with additional metrics)
    render_vendor_status_table(arrears_tasks_df)

if __name__ == "__page__":
    init() 