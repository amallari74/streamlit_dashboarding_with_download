import pandas as pd
from billing_run.components.constants import DEFAULT_STATUS_TYPES

def standardize_status_columns(df, status_types):
    """
    Ensures all status columns exist in a DataFrame and reorders them.
    
    Args:
        df (DataFrame): DataFrame containing status counts (typically from crosstab or pivot)
        status_types (list): List of status types that should be present
    
    Returns:
        DataFrame: DataFrame with all status columns present and ordered correctly
    """
    # Ensure all status columns exist
    for status in status_types:
        if status not in df.columns:
            df[status] = 0
    
    # Reorder columns to match status_types order
    # Get only the columns that exist in status_types (preserving other columns)
    status_columns = [col for col in status_types if col in df.columns]
    other_columns = [col for col in df.columns if col not in status_types]
    
    # Combine the columns
    all_columns = status_columns + other_columns
    
    # Return the reordered DataFrame
    return df[all_columns]

def create_status_table(df, index_col, status_col=None, rename_index=None, capitalize_columns=True, status_types=None):
    """
    Creates a complete status table with standardized columns, totals, and formatting.
    This function is used internally by render_task_stats when show_table=True, but can also
    be used directly when custom status tables with additional metrics are needed.
    
    Args:
        df (DataFrame): DataFrame containing task data
        index_col (str): Column to use as the index (e.g., 'method', 'vendor')
        status_col (str, optional): Column containing status values. Defaults to 'status_clean' if available, else 'status'.
        rename_index (callable, optional): Function to rename index values (e.g., lambda x: x.replace('create', ''))
        capitalize_columns (bool, optional): Whether to capitalize column names. Defaults to True.
        status_types (list, optional): List of status types to include. Defaults to DEFAULT_STATUS_TYPES.
    
    Returns:
        DataFrame: Formatted status table ready for display
    """
    # Set defaults
    status_types = status_types or DEFAULT_STATUS_TYPES
    
    # Determine status column
    if not status_col:
        status_col = 'status_clean' if 'status_clean' in df.columns else 'status'
    
    # Create the crosstab/pivot
    status_counts = pd.crosstab(df[index_col], df[status_col])
    
    # Standardize status columns
    status_counts = standardize_status_columns(status_counts, status_types)
    
    # Add a Total column
    status_counts['Total'] = status_counts.sum(axis=1)
    
    # Sort by total
    status_counts = status_counts.sort_values('Total', ascending=False)
    
    # Rename index if needed
    if rename_index:
        status_counts.index = status_counts.index.map(rename_index)
    
    # Capitalize column names if requested
    if capitalize_columns:
        status_counts.columns = [col.capitalize() for col in status_counts.columns]
        # Also capitalize the index name
        status_counts.index.name = index_col.capitalize()
    
    return status_counts 