import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from utils import db_util, auth_util
from router.roles import DIAGNOSTICS_ROLES as ROLES
from billing_run.models.arrears_task_model import (
    fetch_task_status, 
    fetch_error_categories, 
    fetch_arrears_vendor_list
)
from billing_run.models.repositories import (
    fetch_arrears_task_details
)
from utils.jira_service import JiraService
from utils.jira_debug import debug_jira_connection, try_create_jira_ticket

def calculate_change_percentage(current, previous):
    """Calculate percentage change between current and previous values"""
    if previous == 0:
        return 100 if current > 0 else 0
    return ((current - previous) / previous * 100)

def load_task_status_data(selected_month):
    """Load task status data for the specified month"""
    return fetch_task_status(selected_month)

def load_error_category_data(selected_month):
    """Load error category data for the specified month"""
    return fetch_error_categories(selected_month)

def show_warning_message(new_tasks_count):
    st.warning(f"There are {new_tasks_count} error tasks. Please wait for the tasks to finish before creating a ticket")

def render_high_level_metrics(df):
    """Render high level task metrics"""
    st.subheader("High Level Metrics")
    
    # Data completeness indicators
    data_collection = df['is_data_collection_complete'].all()
    data_validation = df['is_data_validation_complete'].all()
    
    # Status indicators
    st.caption("Data Collection Status")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Data Collection",
            "Complete" if data_collection else "Incomplete",
            delta_color="normal"
        )
        
        if not data_collection:
            # Find vendors with new tasks
            vendors_with_new = df[df['new_tasks_current'] > 0].sort_values('new_tasks_current', ascending=False)
            if not vendors_with_new.empty:
                with st.expander(f"View {len(vendors_with_new)} Vendors with Pending Collection"):
                    for _, row in vendors_with_new.iterrows():
                        st.markdown(f"- **{row['vendor']}** ({row['partner_region']}): {row['new_tasks_current']} new tasks")
    
    with col2:
        st.metric(
            "Data Validation",
            "Complete" if data_validation else "Incomplete",
            delta_color="normal"
        )
        
        if not data_validation:
            # Create a summary of incomplete tasks by vendor
            validation_summary = []
            for _, row in df.iterrows():
                if row['new_tasks_current'] > 0 or row['errored_tasks_current'] > 0:
                    validation_summary.append({
                        'vendor': row['vendor'],
                        'region': row['partner_region'],
                        'new_tasks': row['new_tasks_current'],
                        'error_tasks': row['errored_tasks_current'],
                        'total_incomplete': row['new_tasks_current'] + row['errored_tasks_current']
                    })
            
            # Convert to DataFrame for easier handling
            validation_df = pd.DataFrame(validation_summary)
            if not validation_df.empty:
                # Group by vendor to combine regions
                vendor_summary = validation_df.groupby('vendor').agg({
                    'new_tasks': 'sum',
                    'error_tasks': 'sum',
                    'total_incomplete': 'sum',
                    'region': lambda x: ', '.join(sorted(set(x)))
                }).sort_values('total_incomplete', ascending=False)
                
                with st.expander(f"View {len(vendor_summary)} Vendors Needing Validation"):
                    for vendor, row in vendor_summary.iterrows():
                        details = []
                        if row['new_tasks'] > 0:
                            details.append(f"{row['new_tasks']} new")
                        if row['error_tasks'] > 0:
                            details.append(f"{row['error_tasks']} errored")
                        st.markdown(f"- **{vendor}** ({row['region']}): {', '.join(details)}")
    
    st.caption("Task Counts and States")
    # Calculate totals for current month
    total_tasks = df['tasks_total'].sum()
    total_finished = df['finished_tasks_total'].sum()
    total_errors = df['errored_tasks_total'].sum()
    total_reviewed = df['reviewed_tasks_total'].sum()
    
    # Get previous month totals (these will be the same for all rows since we used cross join)
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

def render_vendor_breakdown(df):
    """Render vendor-based task breakdown"""
    st.subheader("Vendor Breakdown")
    
    # Allow filtering by region
    selected_region = st.selectbox(
        "Filter by Region",
        options=['All'] + sorted(df['partner_region'].unique().tolist())
    )
    
    # Filter data if region is selected
    filtered_df = df if selected_region == 'All' else df[df['partner_region'] == selected_region]
    
    # Group by vendor
    vendor_metrics = filtered_df.groupby('vendor').agg({
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
    vendor_metrics['error_rate'] = (vendor_metrics['errored_tasks_total'] / vendor_metrics['tasks_total'] * 100).round(2)
    vendor_metrics['resolution_rate'] = (vendor_metrics['errored_tasks_resolved'] / vendor_metrics['errored_tasks_total'] * 100).fillna(0).round(2)
    
    # Sort by current errors (descending) then total tasks (descending)
    vendor_metrics = vendor_metrics.sort_values(
        ['errored_tasks_current', 'tasks_total'], 
        ascending=[False, False]
    )
    
    # Show top vendors with current errors
    top_error_vendors = vendor_metrics[vendor_metrics['errored_tasks_current'] > 0].head(10)
    
    # Create bar chart for current states
    if not top_error_vendors.empty:
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Currently Finished',
            x=top_error_vendors['vendor'],
            y=top_error_vendors['finished_tasks_current'],
            marker_color='green'
        ))
        
        fig.add_trace(go.Bar(
            name='Currently Errored',
            x=top_error_vendors['vendor'],
            y=top_error_vendors['errored_tasks_current'],
            marker_color='red'
        ))
        
        fig.add_trace(go.Bar(
            name='Currently Reviewed',
            x=top_error_vendors['vendor'],
            y=top_error_vendors['reviewed_tasks_current'],
            marker_color='yellow'
        ))
        
        fig.add_trace(go.Bar(
            name='Currently New',
            x=top_error_vendors['vendor'],
            y=top_error_vendors['new_tasks_current'],
            marker_color='blue'
        ))
        
        fig.update_layout(
            barmode='group',
            title='Top 10 Vendors by Current Errors',
            xaxis_title='Vendor',
            yaxis_title='Number of Tasks',
            xaxis_tickangle=45
        )
        
        st.plotly_chart(fig)
    
    # Show detailed metrics table
    st.caption("All Vendor Details")
    st.dataframe(
        vendor_metrics,
        column_config={
            'vendor': 'Vendor',
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

def render_error_categorization(df):
    """Render error categorization breakdown"""
    st.subheader("Error Categorization")
    
    # Allow filtering by vendor
    selected_vendor = st.selectbox(
        "Filter by Vendor",
        options=['All'] + sorted(df['vendor'].unique().tolist())
    )
    # Filter data if vendor is selected
    filtered_df = df if selected_vendor == 'All' else df[df['vendor'] == selected_vendor]
    
    # Group by error category
    category_metrics = filtered_df.groupby('error_category').agg({
        'errors_total': 'sum',
        'errors_resolved': 'sum',
        'errors_unresolved': 'sum',
        'vendor': 'nunique'  # Count unique vendors
    }).reset_index()
    
    # Calculate resolution rate
    category_metrics['resolution_rate'] = (category_metrics['errors_resolved'] / category_metrics['errors_total'] * 100).round(2)
    
    # Sort by total errors descending
    category_metrics = category_metrics.sort_values('errors_total', ascending=False)
    
    # Create stacked bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Resolved',
        x=category_metrics['error_category'],
        y=category_metrics['errors_resolved'],
        marker_color='green'
    ))
    
    fig.add_trace(go.Bar(
        name='Unresolved',
        x=category_metrics['error_category'],
        y=category_metrics['errors_unresolved'],
        marker_color='red'
    ))
    
    fig.update_layout(
        barmode='stack',
        title='Error Categories by Resolution Status',
        xaxis_title='Error Category',
        yaxis_title='Number of Errors',
        xaxis_tickangle=45,
        height=500  # Make the chart a bit taller for better readability
    )
    
    st.plotly_chart(fig)
    
    # Create two columns for the table and vendor details
    col1, col2 = st.columns([2, 1])
    def on_select_error_category():
        if (st.session_state.error_category_table and 
            "selection" in st.session_state.error_category_table and 
            "rows" in st.session_state.error_category_table["selection"] and 
            len(st.session_state.error_category_table["selection"]["rows"]) > 0):
            
            selected_row = category_metrics.iloc[st.session_state.error_category_table["selection"]["rows"][0]]
            st.session_state.selected_error_category = selected_row['error_category']

    with col1:
        # Show detailed metrics table with selection
        st.caption("Error Category Details")
        
        # Initialize session state for selection if it doesn't exist
        if 'selected_error_category' not in st.session_state:
            st.session_state.selected_error_category = None
        
        # Create selectable dataframe
        st.dataframe(
            category_metrics,
            column_config={
                'error_category': st.column_config.TextColumn('Error Category'),
                'errors_total': st.column_config.NumberColumn('Total Errors', format="%d"),
                'errors_resolved': st.column_config.NumberColumn('Resolved', format="%d"),
                'errors_unresolved': st.column_config.NumberColumn('Unresolved', format="%d"),
                'resolution_rate': st.column_config.NumberColumn('Resolution Rate', format="%.2f%%"),
                'vendor': st.column_config.NumberColumn('Vendor Count', format="%d")
            },
            hide_index=True,
            selection_mode="single-row",
            key="error_category_table",
            on_select=on_select_error_category,
            use_container_width=True,
            column_order=['error_category', 'errors_total', 'errors_resolved', 'errors_unresolved', 'resolution_rate', 'vendor']
        )

    with col2:
        # Show vendor details for selected category
        if st.session_state.selected_error_category:
            st.caption(f"Vendors with {st.session_state.selected_error_category}")
            
            # Get vendors for selected category
            vendor_details = df[df['error_category'] == st.session_state.selected_error_category].groupby('vendor').agg({
                'errors_total': 'sum',
                'errors_resolved': 'sum',
                'errors_unresolved': 'sum'
            }).reset_index()
            
            vendor_details['resolution_rate'] = (vendor_details['errors_resolved'] / vendor_details['errors_total'] * 100).round(2)
            vendor_details = vendor_details.sort_values('errors_total', ascending=False)
            
            st.dataframe(
                vendor_details,
                column_config={
                    'vendor': 'Vendor',
                    'errors_total': st.column_config.NumberColumn('Total', format="%d"),
                    'errors_resolved': st.column_config.NumberColumn('Resolved', format="%d"),
                    'errors_unresolved': st.column_config.NumberColumn('Unresolved', format="%d"),
                    'resolution_rate': st.column_config.NumberColumn('Resolution Rate', format="%.2f%%")
                },
                hide_index=True,
                use_container_width=True
            )

def render_details_and_jira_ticket_creation(df):
    """Render details and Jira ticket creation"""
    st.subheader("Details and Jira Ticket Creation")

    # Initialize Jira Service
    jira_service = JiraService()
    
    # Style button CSS (keep existing CSS)
    st.markdown(
        """
        <style>
        /* Base button styling */
        .stButton > button {
            width: 100%;
        }
        
        /* Target all Streamlit buttons and style them */
        button[kind="secondary"] {
            background-color: #0099ff !important;
            color: white !important;
            border: none !important;
        }
        
        /* Hover effect for all buttons */
        button[kind="secondary"]:hover {
            background-color: #007acc !important;
            color: white !important;
        }
        
        /* More specific targeting for our buttons */
        .stButton button {
            background-color: #0099ff !important;
            color: white !important;
            border: none !important;
        }
        
        /* Another selector attempt */
        div[data-testid="stButton"] button {
            background-color: #0099ff !important;
            color: white !important;
            border: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Create columns for filters
    col1, col2, col3, col4 = st.columns(4)
    col5, col6, col7, col8 = st.columns(4)

    with col1:
        selected_date = st.date_input(
            "Select Date",
            value=datetime.now(),
            format="YYYY-MM-DD"
        )

    with col2:
        selected_method = st.selectbox(
            "Select Method",
            options=[
                "createArrearsBillsForSubscription",
                "createUsageRecordsForSubscription"
            ]
        )

    with col3:
        try:
            vendor_df = fetch_arrears_vendor_list()
            vendors = ['Select Vendor'] + vendor_df['vendor'].tolist() if not vendor_df.empty else ['Select Vendor']
            
            selected_vendor = st.selectbox(
                "Select Vendor",
                options=vendors
            )
        except Exception as e:
            st.error(f"Error loading vendors: {str(e)}")
            selected_vendor = None

    with col4:
        status_options = ["error", "All", "followup", "finished", "new", "reviewed"]
        selected_status = st.selectbox(
            "Select Status",
            options=status_options,
            index=0
        )

    # Fetch task details BEFORE the button click handler
    task_details = None
    if (selected_date and selected_method and 
        selected_vendor and selected_vendor != 'Select Vendor'):
        try:
            if "postgresql" in st.secrets["connections"]:
                database = "postgresql"
                schema = ""
            else: 
                database = "redshift"
                schema = "cc."
        except Exception as e: 
            st.error(f"Error fetching task details: {str(e)}")
            return
        
        try:
            date_str = selected_date.strftime("%Y-%m-%d")
            full_vendor_task_details = fetch_arrears_task_details(
                run_on=date_str,
                vendor=selected_vendor,
                method=selected_method, 
                schema=schema,
                database=database
            )
            
            
            if not full_vendor_task_details.empty:
                
                st.markdown(
                    """
                    <div style="background-color: #ffdddd; padding: 10px; border-radius: 5px; margin-bottom: 15px; border: 1px solid #ffcccc;">
                    <p style="color: #333; margin: 0;">
                    <strong>⚠️ Important:</strong> Please assure that the tasks for the vendor you're monitoring are all finished before creating a ticket. 
                    If they are still running or not synced into the datawarehouse then subscriptions could be missing.
                    </p>
                    <p style="margin-top: 8px; margin-bottom: 0;">
                    <a href="https://app.pax8.com/product-admin/arrears-dashboard" target="_blank">Link to the arrears dashboard</a>
                    </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                columns_to_display = ['error_message', 'partner_info', 'product_info', 'subscription_id', 'original_subscription_id','partner_region']
                task_details_filtered = full_vendor_task_details[columns_to_display]

                st.subheader("Task Details")
                if selected_status != "All":
                    filtered_vendor_task_details = full_vendor_task_details[full_vendor_task_details['status'] == selected_status]
                else:
                    filtered_vendor_task_details = full_vendor_task_details

                st.dataframe(
                    filtered_vendor_task_details,
                    column_config={
                        'error_message': 'Error Message',
                        'subscription_id': st.column_config.NumberColumn('Subscription ID', format="%d"),
                        'original_subscription_id': st.column_config.NumberColumn('Original Subscription ID', format="%d"),
                        'partner_region': 'Region',
                        'partner_info': 'Partner Info',
                        'product_info': 'Product Info'
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # Create a JIRA table manually for the description
                table = "||Notes||Error Message||Subscription ID||Original Subscription ID||Partner Region||Partner Info||Product Info||\n"
                
                for _, row in filtered_vendor_task_details.iterrows():
                    error_msg = str(row['error_message']).strip()
                    if len(error_msg) > 500:
                        error_msg = error_msg[:497] + "..."
                    if "{" in error_msg and "}" in error_msg:
                        error_msg = error_msg.replace("{", "\\{").replace("}", "\\}")
                    
                    table += f"|| ||{error_msg}||{row['subscription_id']}||{row['original_subscription_id']}||{row['partner_region']}||{row['partner_info']}||{row['product_info']}||\n"
                
                description = f"""
                                * Date: {selected_date}
                                * Method: {selected_method}
                                * Vendor: {selected_vendor}
                                * Status: {selected_status}
                                * Partners Impacted: {filtered_vendor_task_details['partner_info'].nunique()}
                                * Subscriptions Impacted: {filtered_vendor_task_details['subscription_id'].nunique()}
                                * Region: {filtered_vendor_task_details['partner_region'].unique()}

                                h2. Task Summary
                                {table}
                            """

                # Set up the ticket parameters
                ticket_params = {
                    "project_key": "BRUN",
                    "summary": f"Arrears Error - {selected_vendor} - {selected_date}",
                    "description": description,
                    "issue_type": "Story",
                    "labels": ["arrears", "automated_jira_ticket"],
                    "customfield_10371": [selected_vendor.replace(" ", "") if selected_vendor else ""],  # Vendor field
                    "customfield_10372": task_details_filtered['partner_info'].nunique()  # Partners Impacted
                }

                # Create a button to create the Jira ticket
                with col5:
                    create_ticket = st.button("Create Jira Ticket", key="create_ticket_button", use_container_width=True)
                    new_tasks_count = len(full_vendor_task_details[full_vendor_task_details['status'] == 'new'])
                    if create_ticket and new_tasks_count > 0:
                        show_warning_message(new_tasks_count)

                    if create_ticket and new_tasks_count == 0:
                        try:
                            ticket_url = jira_service.create_ticket(
                                project_key="BRUN",
                                summary=f"Arrears Error - {selected_vendor} - {selected_date}",
                                description=description,
                                issue_type="Story",
                                labels=["arrears", "automated_jira_ticket"],
                                customfield_10371=[selected_vendor.replace(" ", "") if selected_vendor else ""],  # Vendor field
                                customfield_10372=task_details_filtered['partner_info'].nunique()  # Partners Impacted
                            )
                            if ticket_url:
                                st.success(f"✨ JIRA ticket created successfully! [View ticket]({ticket_url})")
                            else:
                                st.error("❌ Failed to get ticket URL after creation")
                        except Exception as e:
                            st.error(f"❌ Failed to create JIRA ticket: {str(e)}")
                    

                with col6:
                    debug_button = st.button("Debug Jira Connection", key="debug_button", use_container_width=True)
                
                if debug_button:
                    with st.expander("JIRA Connection Debug Info", expanded=True):
                        debug_jira_connection(
                            project_key="BRUN", 
                            issue_type="Story", 
                            custom_field_ids=["customfield_10371", "customfield_10372"],
                            jira_service=jira_service
                        )
        except Exception as e:
            st.error(f"Error creating Jira ticket: {str(e)}")

def show_arrears_monitoring():
    """Main function to render the Arrears Task Monitoring page"""
    auth_util.auth_for(ROLES)
    
    st.title("Arrears Task Monitoring")
    
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
        index=0
    )
    
    # Format selected month for query
    selected_month_str = selected_month.strftime("%Y-%m-%d")
    
    try:
        # Load data
        with st.spinner("Loading task status data..."):
            task_status_df = load_task_status_data(selected_month_str)
            error_category_df = load_error_category_data(selected_month_str)
        
        if len(task_status_df) == 0:
            st.info("No task data found for the selected month")
            return
            
        # Render high level metrics
        render_high_level_metrics(task_status_df)
        st.divider()
        
        # Create tabs for breakdowns
        tab1, tab2, tab3, tab4 = st.tabs(["Region Breakdown", "Vendor Breakdown", "Error Categories", "Details and Jira Ticket Creation"])
        
        with tab1:
            render_region_breakdown(task_status_df)
        
        with tab2:
            render_vendor_breakdown(task_status_df)
            
        with tab3:
            render_error_categorization(error_category_df)
        
        with tab4:
            render_details_and_jira_ticket_creation(task_status_df)
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")

if __name__ == "__page__":
    show_arrears_monitoring() 