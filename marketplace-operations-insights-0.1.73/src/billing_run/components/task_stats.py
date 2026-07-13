import html
import streamlit as st
import pandas as pd
from billing_run.components.constants import DEFAULT_STATUS_TYPES, DEFAULT_STATUS_COLORS, CATEGORY_CONFIGS

#     'tax_calculation': {
#         'display_name': 'Tax Calculations',
#         'status_colors': DEFAULT_STATUS_COLORS
#     }
# }

def render_status_metrics(df, status_types=None, container=None):
    """
    Renders metrics for each status type showing counts.
    
    Args:
        df (DataFrame): DataFrame containing task data
        status_types (list, optional): List of status types to render
        container: Streamlit container to render in (optional)
    
    Returns:
        dict: Dictionary of status counts
    """
    # Set defaults
    status_types = status_types or DEFAULT_STATUS_TYPES
    
    # Use provided container or default to st
    display = container if container is not None else st
    
    # Get status counts
    status_counts = df['status_clean'].value_counts().to_dict() if 'status_clean' in df.columns else df['status'].value_counts().to_dict()
    
    # Ensure all statuses have a count
    for status in status_types:
        if status not in status_counts:
            status_counts[status] = 0
    
    # Create columns for metrics
    total_tasks = len(df)
    if total_tasks > 0:
        cols = display.columns(len(status_types))
        for i, status in enumerate(status_types):
            with cols[i]:
                count = status_counts.get(status, 0)
                percentage = count / total_tasks if total_tasks > 0 else 0
                display.metric(
                    label=status.capitalize(),
                    value=count,
                    delta=f"{percentage:.1%}",
                    delta_color="off"
                )
    
        # Calculate average run duration for finished tasks if available
        if 'finished' in df['status'].values and 'run_duration' in df.columns:
            finished_tasks = df[df['status'] == 'finished']
            if len(finished_tasks) > 0:
                avg_duration = finished_tasks['run_duration'].mean()
                display.metric("Avg Duration (sec)", f"{avg_duration:.2f}", delta_color="off")
    
    return status_counts

def render_progress_bar(df, status_types=None, status_colors=None, container=None, category_name=None, category=None):
    """
    Renders a reusable stacked progress bar showing task status distribution.
    This function is primarily intended for internal use by render_task_stats.
    External modules should use render_task_stats instead for a more complete solution.
    
    Args:
        df (DataFrame): DataFrame containing task data
        status_types (list, optional): List of status types to render in order
        status_colors (dict, optional): Dictionary mapping status to color hex codes
        container: Streamlit container to render in (optional)
        category_name (str, optional): Display name for the category (deprecated, use category instead)
        category (str, optional): Category key for looking up configs
    
    Note:
        Any status mapping (e.g., 'waiting' → 'new') should be handled at the query level
        in the SQL, not in this component. Use status_clean column in your queries.
    
    Returns:
        dict: Dictionary of status counts
    """
    # Set defaults or use category-specific configuration
    if category and category in CATEGORY_CONFIGS:
        config = CATEGORY_CONFIGS[category]
        status_types = status_types or DEFAULT_STATUS_TYPES
        status_colors = status_colors or config.get('status_colors', DEFAULT_STATUS_COLORS)
        display_name = config.get('display_name', category_name)
    else:
        status_types = status_types or DEFAULT_STATUS_TYPES
        status_colors = status_colors or DEFAULT_STATUS_COLORS
        display_name = category_name
    
    total_tasks = len(df)
    
    # Use provided container or default to st
    display = container if container is not None else st
    
    if total_tasks > 0:
        # Get status counts - all mapping is now done at the query level
        status_counts = df['status_clean'].value_counts().to_dict() if 'status_clean' in df.columns else df['status'].value_counts().to_dict()
        
        # Ensure all main statuses have a count
        for status in status_types:
            if status not in status_counts:
                status_counts[status] = 0
        
        # Get the list of statuses that we'll use consistently
        statuses = status_types or DEFAULT_STATUS_TYPES
        
        # Calculate percentage for each status
        status_percentages = {
            status: (status_counts.get(status, 0) / total_tasks * 100 if total_tasks > 0 else 0)
            for status in statuses
        }
        
        # Show title with tooltip
        if display_name:
            help_text = None
            if category and category in CATEGORY_CONFIGS:
                config = CATEGORY_CONFIGS[category]
                help_text = config.get('description')
            
            display.subheader(display_name, help=help_text if help_text else None)

        # Build the progress bar segments dynamically
        progress_segments = [
            f'<div style="width:{status_percentages[status]}%; height:100%; background-color:{status_colors.get(status, "#6c757d")}; float:left;"></div>'
            for status in statuses
        ]

        # Create content with status boxes
        content_html = f"""
        <div style="width:100%; height:30px; margin-top:5px; margin-bottom:15px; border-radius:3px; overflow:hidden;">
            {''.join(progress_segments)}
        </div>
        <div style="display: flex; justify-content: space-between; gap: 8px; margin-bottom: 12px;">
            {' '.join([
                f'''<div style="flex: 1; background-color: {status_colors.get(status, "#6c757d")}; color: white; padding: 4px 6px; border-radius: 4px; text-align: center;">
                    <div style="font-weight: 500; font-size: 13px;">{html.escape(status.capitalize())}</div>
                    <div style="font-size: 16px; margin: 2px 0; font-weight: bold">{status_counts.get(status, 0):,}</div>
                    <div style="font-size: 11px; opacity: 0.9">{(status_counts.get(status, 0) / total_tasks * 100 if total_tasks > 0 else 0):.1f}%</div>
                </div>'''
                for status in statuses
            ])}
        </div>
        """
        display.markdown(content_html, unsafe_allow_html=True)
        
        # Create download dropdown
        status_options = [s for s in statuses if status_counts.get(s, 0) > 0]
        if status_options:
            cols = display.columns([3, 1])
            with cols[0]:
                selected_status = display.selectbox(
                    "Download tasks by status",
                    options=status_options,
                    format_func=lambda x: f"{x.capitalize()} ({status_counts.get(x, 0):,} tasks)",
                    key=f"status_select_{category}_{container}" if category else f"status_select_{container}"
                )
            with cols[1]:
                if selected_status:
                    status_df = df[df['status_clean' if 'status_clean' in df.columns else 'status'] == selected_status]
                    key = f"download_{category}_{selected_status}" if category else f"download_{selected_status}"
                    display.download_button(
                        "Download CSV",
                        data=status_df.to_csv(index=False),
                        file_name=f"{category}_{selected_status}_tasks.csv" if category else f"{selected_status}_tasks.csv",
                        mime="text/csv",
                        key=key,
                        help=f"Download {selected_status} tasks",
                        use_container_width=True
                )
        
        return status_counts
    else:
        display.info(f"No tasks found{' for ' + display_name if display_name else ''}.")
        return {}

def render_task_stats(df, category=None, show_metrics=True, show_table=False, container=None):
    """
    Composite function that renders task statistics including progress bar, metrics, and optionally a status table.
    
    Args:
        df (DataFrame): DataFrame containing task data
        category (str): Category key for looking up configs ('arrears_tasks', 'invoice_generation', etc.)
        show_metrics (bool, optional): Whether to show status count metrics. Defaults to True.
        show_table (bool, optional): Whether to show a status table by method/vendor. Defaults to False.
            Set to False if you plan to implement a custom status table with additional metrics
            by directly calling create_status_table elsewhere.
        container: Streamlit container to render in (optional)
    
    Returns:
        dict: Dictionary of status counts
    """
    # Use provided container or default to st
    display = container if container is not None else st
    
    # Set up display and configuration
    if category and category in CATEGORY_CONFIGS:
        config = CATEGORY_CONFIGS[category]
        status_types = DEFAULT_STATUS_TYPES
        display_name = config.get('display_name')
    else:
        status_types = DEFAULT_STATUS_TYPES
        display_name = None
    
    if len(df) == 0:
        display.info(f"No tasks found{' for ' + display_name if display_name else ''}.")
        return {}
    status_counts = {}

    if show_metrics:
        col1, col2 = display.columns(2)
        with col1:
            status_counts = render_progress_bar(df, category=category, container=display)
        with col2:
            render_status_metrics(df, status_types=status_types, container=display)
    else:
        # Render the progress bar
        status_counts = render_progress_bar(df, category=category, container=display)
    
    # Optionally render metrics
    # if show_metrics:
    #     display.divider()
    #     render_status_metrics(df, status_types=status_types, container=display)
    
    # Optionally render status table
    if show_table:
        from billing_run.components.status_utils import create_status_table
        
        display.divider()
        display.subheader(f"{display_name} Status by Method")
        
        # Determine the index column based on what's in the DataFrame
        index_col = 'method' if 'method' in df.columns else 'vendor'
        
        # Determine the rename function based on the index column
        if index_col == 'method':
            if df[index_col].str.contains('create').any():
                rename_func = lambda x: x.replace('create', '').replace('Invoice', '')
            elif df[index_col].str.contains('send').any():
                rename_func = lambda x: x.replace('send', '').replace('InvoiceFor', '')
            else:
                rename_func = None
        else:
            rename_func = None
        
        # Create status table
        status_table = create_status_table(
            df, 
            index_col=index_col,
            rename_index=rename_func
        )
        
        # Display table
        display.dataframe(status_table, use_container_width=True)
    
    return status_counts