#!/usr/bin/env python
import streamlit as st
import pandas as pd
import datetime
from typing import Union, Dict, Any, List
from pathlib import Path
import sys
from billing_run.invoice_validation_service import InvoiceValidationService


# --- Helper Function ---
def find_row_as_dict(df: pd.DataFrame, column: str, value: Any) -> Dict[str, Any]:
    """Helper to find the first row matching a condition and return as dict, handling type conversions."""
    if df.empty or column not in df.columns:
        return {}
    try:
        col_dtype = df[column].dtype
        lookup_value = value
        
        # Convert lookup value and potentially column for reliable comparison
        if pd.api.types.is_numeric_dtype(col_dtype):
            lookup_value = pd.to_numeric(value, errors='coerce')
            if pd.isna(lookup_value): return {}
            # Ensure column is numeric for comparison, handling potential errors
            df_numeric = df.copy()
            df_numeric[column] = pd.to_numeric(df_numeric[column], errors='coerce')
            df_filtered = df_numeric[df_numeric[column] == lookup_value]
            
        elif pd.api.types.is_string_dtype(col_dtype) or col_dtype == 'object':
            lookup_value = str(value)
            df_str = df.copy()
            df_str[column] = df_str[column].astype(str)
            df_filtered = df_str[df_str[column] == lookup_value]
            
        else: # Attempt direct comparison for other types
            df_filtered = df[df[column] == value]
            
    except Exception as e:
        # st.warning(f"Lookup Warning: Error comparing value '{value}' in column '{column}': {e}")
        return {}
        
    if not df_filtered.empty:
        # Convert the first matching row to a dictionary, handling NaNs
        return df_filtered.iloc[0].where(pd.notna(df_filtered.iloc[0]), None).to_dict()
    return {}

# --- Styling Function ---
def style_rows(row):
    """Applies background color based on analysis results.
       Updated to only highlight rows present in the invoice.
    """
    style = '' # Default
    in_invoice = row.get('cli_in_invoice')
    # should_bill = row.get('cli_should_be_billable') # No longer used for styling
    
    # Only highlight green if the CLI is actually on the invoice
    if in_invoice is True:
        style = 'background-color: #90EE90' # LightGreen
    # Removed the elif condition for red highlighting
    # elif should_bill is True: # Implies in_invoice is False or None
    #     style = 'background-color: #FFCCCB' # LightCoral (Reddish)
        
    return [style] * len(row)

# --- Page Rendering ---
def render_new_invoice_validation_page():
    st.title("Invoice Validation (v2 - Consolidated View)")

    schema = "cc."
    database = "redshift"
    if "postgresql" in st.secrets["connections"]:
        schema = ""
        database = "postgresql"
    # Initialize service (consider making schema/db configurable later)
    service = InvoiceValidationService(schema=schema, database=database)

    # User Input
    invoice_id = st.number_input("Enter Invoice ID", min_value=1, value=1570272, key="invoice_id_v2")

    # Initialize state
    if 'analysis_df_v2' not in st.session_state:
        st.session_state.analysis_df_v2 = pd.DataFrame()

    if st.button("Analyze Invoice", key="analyze_btn_v2"):
        st.session_state.analysis_df_v2 = pd.DataFrame() # Clear previous results
        
        with st.spinner(f"Fetching and analyzing data for Invoice ID: {invoice_id}..."):
            # 1. Fetch Data
            fetched_data = service.fetch_full_invoice_data(invoice_id)
            if fetched_data.get('error'):
                st.error(f"Error fetching data: {fetched_data['error']}")
                st.stop()
            
            # Extract DataFrames
            partner_subscriptions_df = fetched_data.get('partner_subscriptions', pd.DataFrame())
            partner_clis_df = fetched_data.get('partner_completed_line_items', pd.DataFrame())
            invoice_line_items_df = fetched_data.get('invoice_line_items', pd.DataFrame())
            all_partner_transactions_df = fetched_data.get('partner_transactions', pd.DataFrame())
            invoice_df = fetched_data.get('invoice', pd.DataFrame())

            if invoice_df.empty:
                st.error("Invoice header data is missing.")
                st.stop()
            if partner_clis_df.empty:
                st.warning("Partner Completed Line Items data is missing or empty. Analysis may be incomplete.")
                # Allow proceeding, but analysis might yield empty results

            # Get Invoice Period
            try:
                invoice_date = pd.to_datetime(invoice_df.iloc[0]['invoice_date'])
                invoice_month = invoice_date.month
                invoice_year = invoice_date.year
                st.info(f"Analyzing for Invoice Period: {invoice_year}-{invoice_month:02d}")
            except Exception as e:
                st.error(f"Error determining invoice period: {e}")
                st.stop()

            # 2. Identify Potential CLIs
            potential_cli_ids = []
            if not partner_clis_df.empty and not partner_subscriptions_df.empty:
                potential_cli_ids = service.identify_potentially_billable_clis(
                    partner_subscriptions=partner_subscriptions_df,
                    partner_completed_line_items=partner_clis_df,
                    invoice_month=invoice_month,
                    invoice_year=invoice_year
                )
                st.write(f"Identified {len(potential_cli_ids)} potentially billable CLIs.")
            else:
                 st.warning("Skipping CLI identification due to missing partner subscription or CLI data.")

            # 3. Analyze each potential CLI and consolidate
            consolidated_results = []
            if potential_cli_ids:
                st.write("Analyzing individual CLIs and mapping data...")
                progress_bar = st.progress(0)
                total_clis = len(potential_cli_ids)
                
                # Pre-convert ID columns used for lookups/filtering for efficiency
                if 'id' in partner_clis_df.columns: partner_clis_df['id_num'] = pd.to_numeric(partner_clis_df['id'], errors='coerce')
                if 'completed_line_id' in partner_subscriptions_df.columns: partner_subscriptions_df['completed_line_id_num'] = pd.to_numeric(partner_subscriptions_df['completed_line_id'], errors='coerce')
                if 'completed_line_item_id' in all_partner_transactions_df.columns: all_partner_transactions_df['completed_line_item_id_num'] = pd.to_numeric(all_partner_transactions_df['completed_line_item_id'], errors='coerce')
                if 'completed_line_item_id' in invoice_line_items_df.columns: invoice_line_items_df['completed_line_item_id_num'] = pd.to_numeric(invoice_line_items_df['completed_line_item_id'], errors='coerce')

                for i, cli_id in enumerate(potential_cli_ids):
                    cli_id_num = cli_id # ID is already numeric from identify function

                    # Get Data for CLI
                    cli_record = find_row_as_dict(partner_clis_df, 'id_num', cli_id_num)
                    linked_sub = find_row_as_dict(partner_subscriptions_df, 'completed_line_id_num', cli_id_num)
                    
                    # Filter transactions
                    if 'completed_line_item_id_num' in all_partner_transactions_df.columns:
                         linked_txns = all_partner_transactions_df[all_partner_transactions_df['completed_line_item_id_num'] == cli_id_num].copy()
                    else:
                         linked_txns = pd.DataFrame()

                    # Find Invoice Row
                    if 'completed_line_item_id_num' in invoice_line_items_df.columns:
                        invoice_row = find_row_as_dict(invoice_line_items_df, 'completed_line_item_id_num', cli_id_num)
                    else:
                        invoice_row = {}

                    if not cli_record or not linked_sub:
                        # st.warning(f"Skipping CLI {cli_id}: Missing linked Sub or CLI record.")
                        continue # Skip if core data missing

                    # Run Single Analysis
                    analysis_dict = service.analyze_single_cli(
                        cli_record=cli_record,
                        linked_subscription=linked_sub,
                        linked_transactions=linked_txns,
                        invoice_line_items=invoice_line_items_df, # Pass full invoice lines for check inside function
                        invoice_month=invoice_month,
                        invoice_year=invoice_year
                    )

                    # Combine Data
                    output_row = {
                        # Analysis Results First
                        "cli_in_invoice": analysis_dict['cli_in_invoice'],
                        "cli_should_be_billable": analysis_dict['cli_should_be_billable'],
                        "has_transaction_for_period": analysis_dict['has_transaction_for_period'],
                        # Key Identifiers
                        "cli_id": cli_id_num,
                        "subscription_id": linked_sub.get('id'),
                        "original_subscription_id": linked_sub.get('original_subscription_id'),
                        "invoice_row_id": invoice_row.get('id'), # ID of the CIRA row if found
                        # Supporting Details (Examples)
                        "sub_status": linked_sub.get('status'),
                        "sub_quantity": linked_sub.get('quantity'),
                        "cli_term_in_months": cli_record.get('term_in_months'),
                        "invoice_row_total": invoice_row.get('total'),
                        "invoice_row_start_period": invoice_row.get('start_period'),
                        "invoice_row_end_period": invoice_row.get('end_period'),
                        "sub_commitment_end": linked_sub.get('commitment_term_end_date') # Added commit end date
                    }
                    consolidated_results.append(output_row)
                    progress_bar.progress((i + 1) / total_clis)
                progress_bar.empty()
            
            # 4. Create Final DataFrame and Store in State
            if consolidated_results:
                final_df = pd.DataFrame(consolidated_results)
                
                # --- Add URL columns for linking --- 
                base_url = "https://app.pax8.com/subscriptions/"
                # Handle potential errors during conversion/URL creation
                def create_sub_url(sub_id):
                    if pd.notna(sub_id):
                        try:
                            # Ensure it's treated as an integer for the URL
                            return f"{base_url}{int(sub_id)}"
                        except (ValueError, TypeError):
                            return None # Cannot form valid URL
                    return None
                    
                final_df['subscription_url'] = final_df['subscription_id'].apply(create_sub_url)
                # Assuming original_subscription_id might sometimes be non-numeric or different format
                final_df['original_subscription_url'] = final_df['original_subscription_id'].apply(
                    lambda x: f"{base_url}{x}" if pd.notna(x) else None
                )
                # --- End Add URL columns ---
                
                # Define column order
                cols_ordered = [
                    'cli_in_invoice', 'cli_should_be_billable', 'has_transaction_for_period',
                    'cli_id', 
                    'subscription_id', 'subscription_url', # Add URL col after ID
                    'original_subscription_id', 'original_subscription_url', # Add URL col after ID
                    'invoice_row_id',
                    'sub_status', 'sub_quantity', 'cli_term_in_months', 'sub_commitment_end',
                    'invoice_row_total', 'invoice_row_start_period', 'invoice_row_end_period'
                ]
                # Reindex to ensure order and include all expected columns, filling missing with NaN
                final_df = final_df.reindex(columns=cols_ordered) 
                st.session_state.analysis_df_v2 = final_df
                st.success(f"Analysis complete for {len(final_df)} potentially billable CLIs.")
            else:
                 st.session_state.analysis_df_v2 = pd.DataFrame() # Ensure empty df if no results
                 st.info("No potentially billable CLIs found or analyzed.")

    # --- Display Area --- (Ensure this block is outside the 'if st.button' block)
    st.divider()
    st.subheader("Consolidated CLI Analysis")
    
    final_display_df = st.session_state.analysis_df_v2

    if not final_display_df.empty:
        st.info("Highlighting: Green = In Invoice") # Updated info message
        
        # Apply styling
        styled_df = final_display_df.style.apply(style_rows, axis=1)
        
        # --- Define Column Configuration for Links --- 
        column_config = {
            "subscription_id": st.column_config.NumberColumn(
                "Subscription ID", 
                format="%d",
                help="The current Subscription ID."
            ), 
            "original_subscription_id": st.column_config.TextColumn(
                "Original Sub ID",     
                help="The original Subscription ID if different."
            ),
            "subscription_url": st.column_config.LinkColumn(
                "Link", # Column Header
                help="Opens the subscription in the Pax8 platform (new tab)",
                display_text="View", # Text displayed in the cell for the link
                width="small" # Make link column narrow
            ),
            "original_subscription_url": st.column_config.LinkColumn(
                "Orig Link", # Column Header
                help="Opens the original subscription in the Pax8 platform (new tab)",
                display_text="View", # Text displayed in the cell for the link
                width="small"
            ),
            "cli_id": st.column_config.NumberColumn(format="%d"),
            "invoice_row_id": st.column_config.NumberColumn(format="%d"),
            # Add formatting or hiding for other columns if desired
            "invoice_row_total": st.column_config.NumberColumn(format="%.2f"),
            "invoice_row_start_period": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "invoice_row_end_period": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "sub_commitment_end": st.column_config.DateColumn(format="YYYY-MM-DD"),
        }
        # --- End Column Configuration ---
        
        # Display the styled DataFrame
        st.dataframe(styled_df, column_config=column_config)
        
        # Optional: Add download button
        @st.cache_data # Cache conversion
        def convert_df(df):
           # Convert NaT explicitly to avoid issues
           df_copy = df.copy()
           for col in df_copy.select_dtypes(include=['<M8[ns]']).columns:
                df_copy[col] = df_copy[col].astype(str).replace('NaT', '')
           return df_copy.to_csv(index=False).encode('utf-8')

        csv = convert_df(final_display_df)
        st.download_button(
           label="Download analysis as CSV",
           data=csv,
           file_name=f'invoice_{st.session_state.get("invoice_id_v2", "unknown")}_cli_analysis_v2.csv',
           mime='text/csv',
        )
        
    else:
        st.info("Enter an Invoice ID and click 'Analyze Invoice' to see the consolidated analysis.")

# Entry point for Streamlit page execution
if __name__ == "__page__":
    render_new_invoice_validation_page() 