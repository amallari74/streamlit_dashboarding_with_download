import streamlit as st
import pandas as pd
from typing import Union, List, Dict, Any, Optional
from datetime import date

def display_date_range_filter(
    df: pd.DataFrame,
    date_column: str,
    key: str,
    title: str = "Filter by Date Range"
) -> pd.DataFrame:
    """Display a date range filter for a dataframe and return filtered results"""
    if df.empty:
        return df
        
    df[date_column] = pd.to_datetime(df[date_column])
    min_date = df[date_column].min()
    max_date = df[date_column].max()
    
    date_range = st.date_input(
        title,
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key=key
    )
    
    if len(date_range) == 2:
        return df[
            (df[date_column].dt.date >= date_range[0]) &
            (df[date_column].dt.date <= date_range[1])
        ]
    return df

def display_dataframe_with_expander(
    df: pd.DataFrame,
    title: str,
    description: str,
    expanded: bool = True,
    empty_message: str = "No data found.",
    highlight_rows: Optional[List[int]] = None
) -> None:
    """Display a dataframe in an expander with empty state handling and optional row highlighting"""
    with st.expander(f"📋 {title}", expanded=expanded):
        st.markdown(f"### {description}")
        if not df.empty:
            if highlight_rows is not None:
                # Create a style function that highlights specific rows
                def highlight_matching_rows(row):
                    return ['background-color: #218f21' if row.name in highlight_rows else '' for _ in row]
                
                # Apply the styling
                styled_df = df.style.apply(highlight_matching_rows, axis=1)
                st.dataframe(styled_df)
            else:
                st.dataframe(df)
        else:
            st.info(empty_message)

def display_metrics_in_columns(
    metrics: Dict[str, Any],
    num_columns: int = 4
) -> None:
    """Display metrics in columns"""
    cols = st.columns(num_columns)
    for i, (label, value) in enumerate(metrics.items()):
        with cols[i % num_columns]:
            st.metric(label, value)

def display_analysis_documentation(
    title: str,
    steps: List[str],
    pseudo_code: str,
    key_points: List[str]
) -> None:
    """Display analysis documentation in an expander"""
    with st.expander("📊 Understanding Analysis"):
        st.markdown(f"""
        ### {title}
        {''.join(f'{i+1}. {step}\n' for i, step in enumerate(steps))}
        
        ### Pseudo Code:
        ```python
        {pseudo_code}
        ```
        
        ### Key data points we check:
        {''.join(f'- {point}\n' for point in key_points)}
        """)

def format_date_for_display(date_value: Union[date, pd.Timestamp]) -> str:
    """Format a date value for display"""
    if isinstance(date_value, (date, pd.Timestamp)):
        return date_value.strftime("%Y-%m-%d")
    return str(date_value)

def get_matching_row_indices(
    partner_df: pd.DataFrame,
    invoice_df: pd.DataFrame,
    match_column: str
) -> List[int]:
    """Get indices of rows in partner_df that match rows in invoice_df based on match_column"""
    if partner_df.empty or invoice_df.empty:
        return []
        
    # Convert match_column to string type for consistent comparison
    partner_df[match_column] = partner_df[match_column].astype(str)
    invoice_df[match_column] = invoice_df[match_column].astype(str)
    
    # Get matching rows
    matching_rows = partner_df[partner_df[match_column].isin(invoice_df[match_column])]
    return matching_rows.index.tolist()

def display_partner_and_invoice_data(
    partner_df: pd.DataFrame,
    invoice_df: pd.DataFrame,
    title: str,
    description: str,
    match_column: str,
    date_filter_column: Optional[str] = None,
    date_filter_key: Optional[str] = None,
    status_filter_key: Optional[str] = None,
    # Add new optional parameters for analysis columns
    analysis_in_invoice_col: Optional[str] = None,
    analysis_should_bill_col: Optional[str] = None,
    analysis_has_tx_col: Optional[str] = None # Optional for future use
) -> None:
    """Display partner and invoice data side by side with highlighting based on analysis columns if provided."""
    
    # --- Define Styling Function --- 
    def style_based_on_analysis(row, in_invoice_col, should_bill_col):
        style = '' # Default no style
        try:
            in_invoice = row.get(in_invoice_col) if in_invoice_col else None
            should_bill = row.get(should_bill_col) if should_bill_col else None

            # Check for boolean True explicitly, handle None/other types implicitly
            if in_invoice is True:
                style = 'background-color: #90EE90' # LightGreen
            elif should_bill is True: # Implies in_invoice is False or None due to previous check
                style = 'background-color: #FFCCCB' # LightCoral (Reddish)
            # Add more conditions here if needed
            # elif ... :
            #     style = 'background-color: #FFFFE0' # LightYellow for other cases? 
        except Exception as e:
            # st.error(f"Styling error: {e}") # Avoid breaking the UI on styling errors
            pass
        return [style] * len(row)

    # --- Display Logic --- 
    if not partner_df.empty:
        display_df = partner_df.copy() # Work on a copy
        
        # Apply date filter if specified
        if date_filter_column and date_filter_key:
            display_df = display_date_range_filter(
                display_df,
                date_filter_column,
                date_filter_key
            )
        
        # Apply status filter if specified
        if status_filter_key and 'status' in display_df.columns:
            status_options = sorted([str(s) for s in display_df['status'].unique()])
            status_filter = st.multiselect(
                "Filter by Status",
                options=status_options,
                default=status_options,
                key=status_filter_key
            )
            if status_filter:
                display_df = display_df[display_df['status'].astype(str).isin(status_filter)]
        
        # --- Styling Decision --- 
        styled_partner_df = None
        # Prioritize new styling if analysis columns are present
        if analysis_in_invoice_col and analysis_should_bill_col and \
           analysis_in_invoice_col in display_df.columns and analysis_should_bill_col in display_df.columns:
             st.caption("Highlighting based on CLI analysis flags.") # Inform user
             styled_partner_df = display_df.style.apply(
                 style_based_on_analysis, 
                 axis=1, 
                 in_invoice_col=analysis_in_invoice_col, 
                 should_bill_col=analysis_should_bill_col
             )
        else:
            # Fallback to old matching logic if analysis columns are not provided/present
            st.caption("Highlighting based on matching ID in invoice data.") # Inform user
            matching_indices = get_matching_row_indices(display_df, invoice_df, match_column)
            if matching_indices:
                def highlight_matching_rows(row):
                    return ['background-color: #90EE90' if row.name in matching_indices else '' for _ in row]
                styled_partner_df = display_df.style.apply(highlight_matching_rows, axis=1)
            # If no analysis cols and no matches, styled_partner_df remains None

        # Display partner data with or without styling
        display_dataframe_with_expander(
            styled_partner_df if styled_partner_df is not None else display_df, # Pass styled df or original
            f"Partner {title}",
            f"These are all {description.lower()} for this partner.",
            highlight_rows=None # Styling is now handled by df.style or not applied
        )
    
    # Display invoice data (no changes needed here)
    display_dataframe_with_expander(
        invoice_df,
        f"Invoice {title}",
        f"These are the {description.lower()} in the current invoice.",
        empty_message=f"No {description.lower()} found in this invoice."
    ) 