import streamlit as st
import pandas as pd
from utils import db_util, auth_util
from streamlit_theme import st_theme
from router.roles import BILLING_RUN_ROLES as ROLES
from billing_run.models.repositories import fetch_arrears_tasks, fetch_billing_tasks, get_task_category_dataframes, fetch_latest_completed_tasks, fetch_open_tasks_count
from billing_run.components.constants import DEFAULT_STATUS_TYPES, CATEGORY_CONFIGS
from billing_run.components.task_stats import render_task_stats
from billing_run.components.refresh_status import show_multiple_refresh_status

# Initialize session state for timezone if not set
if 'timezone' not in st.session_state:
    st.session_state.timezone = 'America/New_York'  # Default to Eastern Time

# Add timezone selector
st.sidebar.selectbox(
    "Select Timezone",
    options=['America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles', 'Europe/London', 'Australia/Brisbane', 'UTC'],
    key='timezone',
    help="Select your timezone to see correct times"
)

def render_task_details_tab(df, category_name):
    total_tasks = len(df)
    if total_tasks > 0:
        # Add status filter
        status_column = 'status_clean' if 'status_clean' in df.columns else 'status'
        available_statuses = sorted(df[status_column].unique())
        default_statuses = ['error'] if 'error' in available_statuses else available_statuses[:1]
        
        selected_statuses = st.multiselect(
            "Filter by Status:",
            options=available_statuses,
            default=default_statuses,
            key=f"status_filter_{category_name}",
            help="Select one or more statuses to filter the tasks"
        )
        
        # Apply filter if statuses are selected
        filtered_df = df
        if selected_statuses:
            filtered_df = df[df[status_column].isin(selected_statuses)]
            st.write(f"Showing {len(filtered_df)} of {len(df)} tasks")
        else:
            filtered_df = df
        
        # Define common columns for display
        column_config = {
            "id": st.column_config.NumberColumn("Task ID", format="%d"),
            "status": st.column_config.TextColumn("Status"),
            "status_clean": st.column_config.TextColumn("Status Clean") if "status_clean" in df.columns else None,
            "method": st.column_config.TextColumn("Method") if "method" in df.columns else None,
            "run_on": st.column_config.DatetimeColumn(
                "Run Date",
                format="MMM D, YYYY, h:mm A",
                timezone="browser",
                help="Times are shown in your browser's timezone"
            ),
            "run_duration": st.column_config.NumberColumn("Duration (s)", format="%.2f"),
            "error_count": st.column_config.NumberColumn("Error Count", format="%d"),
            "created_dt": st.column_config.DatetimeColumn(
                "Created Date",
                format="MMM D, YYYY, h:mm A",
                timezone="browser",
                help="Times are shown in your browser's timezone"
            ),
            "updated_dt": st.column_config.DatetimeColumn(
                "Updated Date",
                format="MMM D, YYYY, h:mm A",
                timezone="browser",
                help="Times are shown in your browser's timezone"
            )
        }
        
        # Filter out None values
        column_config = {k: v for k, v in column_config.items() if v is not None}
        
        # Add specific columns for each task type
        if 'subscription_id' in df.columns:
            column_config["subscription_id"] = st.column_config.NumberColumn("Subscription ID", format="%d")
            column_config["original_subscription_id"] = "Original Subscription ID"
            column_config["product_id"] = st.column_config.NumberColumn("Product ID", format="%d")
            column_config["product_name"] = "Product Name"
            column_config["vendor"] = "Vendor"
        
        if 'partner_id' in df.columns:
            column_config["partner_id"] = st.column_config.NumberColumn("Partner ID", format="%d")
            column_config["partner_id_parsed"] = st.column_config.NumberColumn("Partner ID (Parsed)", format="%d")
            column_config["company_id_parsed"] = st.column_config.NumberColumn("Company ID (Parsed)", format="%d")
        
        st.dataframe(filtered_df, column_config=column_config, hide_index=True)
        
        # Error tasks details
        error_status = 'error'
        if 'status_clean' in df.columns:
            error_tasks = df[df['status_clean'] == error_status]
        else:
            error_tasks = df[df['status'] == error_status]
            
        if len(error_tasks) > 0:
            st.subheader(f"{category_name} with Errors")
            for _, task in error_tasks.iterrows():
                task_label = task.get('id', 'Unknown')
                task_type = task.get('method', 'Unknown Method')
                with st.expander(f"Task ID: {task_label} - {task_type}"):
                    st.write(f"**Error Message:**")
                    st.code(task.get('error_message', 'No error message'), language='java')
                    st.write(f"**Error Count:** {task.get('error_count', 0)}")
                    
                    # Format the timestamp with browser timezone
                    updated_dt = pd.to_datetime(task.get('updated_dt'))
                    if updated_dt is not None:
                        st.write("**Last Updated:**")
                        st.write(updated_dt.strftime("%B %d, %Y, %I:%M %p") + " (your timezone)")
    else:
        st.info(f"No {category_name} found.")

def init():
    auth_util.auth_for(ROLES)
    
    st.title("Task Manager Dashboard")
    
    # Add refresh status in the sidebar
    # show_multiple_refresh_status(
    #     ["fetch_arrears_tasks", "fetch_billing_tasks"],
    #     title="Data Last Refreshed"
    # )
    
    # Fetch categorized task dataframes
    task_dfs = get_task_category_dataframes()
    arrears_tasks_df = task_dfs["Arrears Tasks"]
    invoice_generation_df = task_dfs["Invoice Generation"]
    invoice_release_df = task_dfs["Invoice Release"]
    tax_calculation_df = task_dfs["Tax Calculations"]
    
    # Define task categories with their component category keys and descriptions
    # Get category configurations and add descriptions to them
    task_categories = []
    
    def add_category(category_key, df, description):
        config = CATEGORY_CONFIGS[category_key]
        # Add the description to the config
        config['description'] = description
        return {
            "name": config['display_name'],
            "df": df,
            "category": category_key
        }
    
    # Define all categories with their descriptions
    task_categories = [
        add_category('arrears_tasks', arrears_tasks_df,
            "Tasks that process billable usage data using createArrearsBillsForSubscription method. These run monthly to calculate usage-based charges."),
        
        add_category('tax_calculation', tax_calculation_df,
            "Tasks that calculate sales tax using calculateAndStoreSalesTaxRatesForPartner and calculateAndStoreSalesTaxRatesForCompany methods."),
        
        add_category('invoice_generation', invoice_generation_df,
            "Tasks that generate invoices using createPartnerInvoice and createCompanyInvoice methods."),
        
        add_category('invoice_release', invoice_release_df,
            "Tasks that send invoices using sendInvoiceForCompany and sendInvoiceForPartner methods.")
    ]
    
    # Show current month at the top
    st.markdown(f"""
        <h3 style='margin-bottom:1em;'>
            Task Status Overview &bull; <span style='opacity:0.7;'>{pd.Timestamp.now().strftime('%B %Y')}</span>
        </h3>
    """, unsafe_allow_html=True)
    
    # Display progress bars in pairs
    for i in range(0, len(task_categories), 2):
        # Create a row with two columns
        col1, col2 = st.columns(2)
        
        # First category in this row
        if i < len(task_categories):
            with col1:
                category = task_categories[i]
                render_task_stats(
                    df=category["df"], 
                    category=category["category"], 
                    show_metrics=False,  # Don't show metrics in the overview
                    show_table=False,    # Don't show tables in the overview
                    container=col1
                )
        
        # Second category in this row (if exists)
        if i + 1 < len(task_categories):
            with col2:
                category = task_categories[i + 1]
                render_task_stats(
                    df=category["df"], 
                    category=category["category"], 
                    show_metrics=False,  # Don't show metrics in the overview
                    show_table=False,    # Don't show tables in the overview
                    container=col2
                )
    
    st.divider()

    with st.expander("ℹ️ About Billing Tasks"):
        st.markdown("""
        ### Task Types and Methods

        | Category | Method | Description |
        |----------|---------|-------------|
        | **Billable Usage** | `createArrearsBillsForSubscription` | Generates billing records for usage-based subscriptions and processes actual usage data to create daily usage tasks. |
        | **Tax Calculation** | `calculateAndStoreSalesTaxRatesForPartner` | Uses Avalara API to calculate partner tax rates based on location and business rules. Supports additional taxable rows. |
        | **Tax Calculation** | `calculateAndStoreSalesTaxRatesForCompany` | Uses Avalara API to calculate company tax rates based on location and business rules. |
        | **Invoice Generation** | `createPartnerInvoice` | Generates partner-level invoices with CSV entries, including surcharges and sales tax. Creates PDF versions in S3 and supports auto-approval configuration. |
        | **Invoice Generation** | `createCompanyInvoice` | Generates company-level invoices with CSV entries and sales tax calculations. Creates PDF versions in S3 and supports bill-on-behalf-of scenarios. |
        | **Invoice Release** | `sendInvoiceForCompany` | Delivers approved company invoices based on company notification rules. |
        | **Invoice Release** | `sendInvoiceForPartner` | Delivers approved partner invoices based on partner notification rules. |

        #### Important Notes
        - **Date Requirements**: Invoice dates must be first day of month.
        - **Process Controls**:
          - Tasks prevent duplicate processing
          - PDF and CSV versions are stored in S3
        """)
    
    # Display open tasks count
    st.divider()
    
    st.subheader("Open Tasks")
    
    if "postgresql" in st.secrets["connections"]:
        try:
            open_tasks = fetch_open_tasks_count(database="postgresql")
            
            if not open_tasks.empty:
                    # Create a summary dataframe with totals and breakdowns
                    summary_data = []
                    
                    # Get unique table names
                    table_names = sorted(open_tasks['table_name'].unique())
                    
                    # Process each table
                    for table in table_names:
                        table_data = open_tasks[open_tasks['table_name'] == table]
                        total_count = table_data['open_count'].sum()
                        
                        # Create method breakdown string based on status
                        special_methods = ['table_not_found', 'error_querying', 'no_data', 'error']
                        
                        # Check if any special status methods exist for this table
                        special_status = False
                        for method in special_methods:
                            if method in table_data['method'].values:
                                special_status = True
                                break
                        
                        # Format the method breakdown
                        if special_status:
                            # Handle special status tables
                            if 'table_not_found' in table_data['method'].values:
                                method_breakdown = "Table not found in database"
                            elif 'error_querying' in table_data['method'].values:
                                method_breakdown = "Error querying table"
                            elif 'error' in table_data['method'].values:
                                method_breakdown = "Error processing table"
                            else:
                                method_breakdown = "No open tasks" 
                        elif total_count == 0:
                            # No open tasks
                            method_breakdown = "No open tasks"
                        else:
                            # Regular case with open tasks
                            # Only include methods with non-zero counts
                            valid_methods = []
                            for _, row in table_data.iterrows():
                                if row['open_count'] > 0 and row['method'] not in special_methods:
                                    valid_methods.append(f"{row['method']} ({row['open_count']})")
                            
                            if valid_methods:
                                method_breakdown = "; ".join(valid_methods)
                            else:
                                method_breakdown = "No open tasks"
                        
                        summary_data.append({
                            "table_name": table,
                            "total_count": total_count,
                            "method_breakdown": method_breakdown,
                            "hourly_completed": table_data['hourly_completed'].iloc[0] if 'hourly_completed' in table_data.columns else 0
                        })
                    
                    # Convert to DataFrame and sort by table name
                    summary_df = pd.DataFrame(summary_data)
                    summary_df = summary_df.sort_values('table_name')
                    
                    # Calculate estimated time to complete (in hours and minutes)
                    def calculate_eta(row):
                        if row['hourly_completed'] <= 0:  # Avoid division by zero
                            return "N/A"
                        
                        # Calculate time in hours (float)
                        hours_float = row['total_count'] / row['hourly_completed']
                        
                        # Convert to hours and minutes
                        hours = int(hours_float)
                        minutes = int((hours_float - hours) * 60)
                        
                        if hours == 0 and minutes == 0:
                            return "< 1 min"
                        elif hours == 0:
                            return f"{minutes} min"
                        elif minutes == 0:
                            return f"{hours} hr"
                        else:
                            return f"{hours} hr {minutes} min"
                    
                    # Apply the calculation to each row
                    summary_df['eta'] = summary_df.apply(calculate_eta, axis=1)
                    
                    # Display the summary table
                    st.dataframe(
                        summary_df,
                        column_config={
                            "table_name": st.column_config.TextColumn("Table", width="small"),
                            "total_count": st.column_config.NumberColumn("Total Open Tasks", format="%d", width="small"),
                            "hourly_completed": st.column_config.NumberColumn("Speed (Tasks Per Hour)", format="%d", width="small",
                                               help="Number of tasks completed in the last hour"),
                            "eta": st.column_config.TextColumn("Estimated Time to Complete", width="small",
                                  help="Estimated time until all open tasks are completed at current speed"),
                            "method_breakdown": st.column_config.TextColumn("Breakdown by Method", width="large")
                        },
                        hide_index=True,
                        column_order=["table_name", "total_count", "hourly_completed", "eta", "method_breakdown"],
                        use_container_width=True  # Make the table use full container width
                    )
            else:
                st.info("No open tasks data available")
        except Exception as e:
            import traceback
            st.error(f"Error fetching open tasks data: {str(e)}")
            st.code(traceback.format_exc())
            st.info("Check if the tunnel is properly set up using setup_tunnel.sh")
    else:
        st.info("PostgreSQL connection not configured")

    # Tab container for task categories
    # st.subheader("Tasks by Category")
    # tab_names = [category["name"] for category in task_categories]
    # tabs = st.tabs(tab_names)

    # Render each tab
    # for i, category in enumerate(task_categories):
    #     with tabs[i]:
    #         st.subheader(f"{category['name']} Summary")
    #         render_task_details_tab(category["df"], category["name"])

if __name__ == "__page__":
    init()
