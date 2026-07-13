import streamlit as st
import pandas as pd
import datetime
from typing import Union, Dict, Any, List
from billing_run.invoice_validation_service import InvoiceValidationService
from billing_run.models.invoice_validation_model import fetch_invoice_by_id
from billing_run.components.invoice_validation_components import (
    display_date_range_filter,
    display_dataframe_with_expander,
    display_metrics_in_columns,
    display_analysis_documentation,
    format_date_for_display,
    display_partner_and_invoice_data
)

def find_row_as_dict(df: pd.DataFrame, column: str, value: Any) -> Dict[str, Any]:
    """Helper to find the first row matching a condition and return as dict."""
    # Ensure correct type comparison if necessary (e.g., numeric)
    try:
        if column not in df.columns:
             # st.warning(f"Helper Warning: Column '{column}' not found in DataFrame for lookup.")
             return {}
             
        # Handle potential type mismatches before comparison
        col_dtype = df[column].dtype
        lookup_value = value
        
        if pd.api.types.is_numeric_dtype(col_dtype):
            lookup_value = pd.to_numeric(value, errors='coerce')
            if pd.isna(lookup_value):
                 # st.warning(f"Helper Warning: Could not convert value '{value}' to numeric for column '{column}'. Skipping lookup.")
                 return {}
            # Ensure the DataFrame column is also numeric for comparison
            df_numeric = df.copy()
            df_numeric[column] = pd.to_numeric(df_numeric[column], errors='coerce')
            df_filtered = df_numeric[df_numeric[column] == lookup_value]
        elif pd.api.types.is_string_dtype(col_dtype) or col_dtype == 'object':
             lookup_value = str(value)
             # Ensure the DataFrame column is also string for comparison
             df_str = df.copy()
             df_str[column] = df_str[column].astype(str)
             df_filtered = df_str[df_str[column] == lookup_value]
        else:
             # Attempt direct comparison for other types (dates, bools, etc.)
             df_filtered = df[df[column] == lookup_value]
             
    except KeyError:
        # st.warning(f"Helper Warning: Column '{column}' not found in DataFrame during lookup.")
        return {} # Column doesn't exist
    except Exception as e:
        # st.warning(f"Helper Warning: Unexpected error during lookup for value '{value}' in column '{column}': {e}")
        return {}
        
    if not df_filtered.empty:
        # Convert the first matching row to a dictionary, handling NaNs properly
        return df_filtered.iloc[0].where(pd.notna(df_filtered.iloc[0]), None).to_dict()
    return {}

def analyze_invoice_data(data: dict) -> dict:
    """Analyze invoice data and related records"""
    results = {
        "missing_subscriptions": 0,
        "missing_transactions": 0,
        "invoice_info": {},
        "records_associated": {},
        "partner_records": {},
        "billing_period": {},
        "subscription_analysis": {},
        "transaction_analysis": {},
        "line_item_analysis": {}
    }
    
    # Get invoice information
    invoice = data["invoice"].iloc[0] if not data["invoice"].empty else None
    if invoice is not None:
        invoice_date = pd.to_datetime(invoice.get('invoice_date'))
        invoice_month = invoice_date.month if invoice_date else None
        invoice_year = invoice_date.year if invoice_date else None
        
        results["invoice_info"] = {
            "id": invoice.get('id'),
            "invoice_date": invoice.get('invoice_date'),
            "partner_id": invoice.get('partner_id'),
            "company_id": invoice.get('company_id'),
            "status": invoice.get('status'),
            "total": invoice.get('total'),
            "month": invoice_month,
            "year": invoice_year
        }
        
        # Get billing period from line items
        if not data["invoice_line_items"].empty:
            line_items = data["invoice_line_items"]
            if 'start_period' in line_items.columns:
                line_items['start_period'] = pd.to_datetime(line_items['start_period'])
            if 'end_period' in line_items.columns:
                line_items['end_period'] = pd.to_datetime(line_items['end_period'])
            min_start = line_items['start_period'].min() if 'start_period' in line_items.columns else None
            max_end = line_items['end_period'].max() if 'end_period' in line_items.columns else None
            
            results["billing_period"] = {
                "start": min_start,
                "end": max_end
            }
        
        # Records associated with invoice
        results["records_associated"] = {
            "invoice_line_items": len(data["invoice_line_items"]),
            "subscriptions": len(data["subscriptions"]),
            "transactions": len(data["transactions"])
        }
        
        # Partner records
        results["partner_records"] = {
            "partner_transactions": len(data["partner_transactions"]),
            "partner_subscriptions": len(data["partner_subscriptions"]),
            "partner_line_items": len(data["partner_line_items"]),
            "completed_line_items": len(data["completed_line_items"])
        }
        
        # Subscription analysis
        if not data["partner_subscriptions"].empty:
            subs_df = data["partner_subscriptions"]
            
            # Filter active subscriptions
            if 'status' in subs_df.columns:
                active_subs = subs_df[subs_df['status'].str.lower() == 'active']
                
                # Check billing cycles
                if 'billing_cycle_start' in active_subs.columns:
                    active_subs['billing_cycle_start'] = pd.to_datetime(active_subs['billing_cycle_start'])
                    active_subs['billing_cycle_month'] = active_subs['billing_cycle_start'].dt.month
                    active_subs['billing_cycle_year'] = active_subs['billing_cycle_start'].dt.year
                    
                    should_be_in_invoice = active_subs[
                        (active_subs['billing_cycle_month'] == invoice_month) & 
                        (active_subs['billing_cycle_year'] == invoice_year)
                    ]
                    
                    # Check which are in the invoice
                    if not data["subscriptions"].empty and 'completed_line_id' in active_subs.columns:
                        invoice_subs = data["subscriptions"]
                        
                        if 'completed_line_id' in invoice_subs.columns:
                            invoice_completed_line_ids = set(invoice_subs['completed_line_id'].dropna())
                            should_be_in_cli_ids = set(should_be_in_invoice['completed_line_id'].dropna())
                            missing_subs = should_be_in_cli_ids - invoice_completed_line_ids
                            results["missing_subscriptions"] = len(missing_subs)
                            
                            # Add detailed subscription analysis
                            results["subscription_analysis"] = {
                                "active_subscriptions": len(active_subs),
                                "should_be_in_invoice": len(should_be_in_invoice),
                                "missing_subscriptions": len(missing_subs),
                                "missing_subscription_details": should_be_in_invoice[should_be_in_invoice['completed_line_id'].isin(missing_subs)].to_dict('records') if len(missing_subs) > 0 else []
                            }
        
        # Transaction analysis
        if not data["partner_transactions"].empty:
            trans_df = data["partner_transactions"]
            
            # Check which transactions are in the invoice
            if not data["transactions"].empty and 'transaction_id' in data["transactions"].columns:
                invoice_trans = data["transactions"]
                
                if 'transaction_id' in invoice_trans.columns and 'transaction_id' in trans_df.columns:
                    invoice_trans_ids = set(invoice_trans['transaction_id'].astype(str).dropna())
                    all_trans_ids = set(trans_df['transaction_id'].astype(str).dropna())
                    
                    missing_trans = all_trans_ids - invoice_trans_ids
                    
                    # Filter by invoice month/year
                    if 'invoice_date' in trans_df.columns:
                        missing_trans_df = trans_df[trans_df['transaction_id'].astype(str).isin(missing_trans)]
                        missing_trans_df['invoice_date'] = pd.to_datetime(missing_trans_df['invoice_date'])
                        missing_trans_df['trans_month'] = missing_trans_df['invoice_date'].dt.month
                        missing_trans_df['trans_year'] = missing_trans_df['invoice_date'].dt.year
                        
                        should_be_in_invoice = missing_trans_df[
                            (missing_trans_df['trans_month'] == invoice_month) & 
                            (missing_trans_df['trans_year'] == invoice_year)
                        ]
                        
                        results["missing_transactions"] = len(should_be_in_invoice)
                        
                        # Add detailed transaction analysis
                        results["transaction_analysis"] = {
                            "total_transactions": len(trans_df),
                            "distinct_transaction_ids": len(all_trans_ids),
                            "duplicate_transactions": len(trans_df) - len(all_trans_ids),
                            "missing_transactions": len(should_be_in_invoice),
                            "missing_transaction_details": should_be_in_invoice.to_dict('records') if len(should_be_in_invoice) > 0 else [],
                            "monthly_distribution": missing_trans_df.groupby(['trans_year', 'trans_month']).size().to_dict()
                        }
        
        # Line item analysis
        if not data["invoice_line_items"].empty and not data["partner_line_items"].empty:
            invoice_line_items = data["invoice_line_items"]
            partner_line_items = data["partner_line_items"]
            
            invoice_line_item_ids = set(invoice_line_items['line_item_id'].astype(str)) if 'line_item_id' in invoice_line_items.columns else set()
            partner_line_item_ids = set(partner_line_items['line_item_id'].astype(str)) if 'line_item_id' in partner_line_items.columns else set()
            
            missing_line_items = partner_line_item_ids - invoice_line_item_ids
            
            results["line_item_analysis"] = {
                "missing_line_items": len(missing_line_items),
                "missing_line_item_details": partner_line_items[partner_line_items['line_item_id'].astype(str).isin(missing_line_items)].to_dict('records') if len(missing_line_items) > 0 else []
            }
    
    return results

def render_invoice_validation_page():
    """Render the invoice validation page"""
    st.title("Invoice Validation")
    
    # Initialize service
    service = InvoiceValidationService(
        schema="cc.",
        database="redshift"
    )
    
    # Input for invoice ID
    if 'invoice_id_input' not in st.session_state:
        st.session_state.invoice_id_input = 1570272
        
    invoice_id = st.number_input(
        "Enter Invoice ID", 
        min_value=1, 
        value=st.session_state.invoice_id_input, 
        key="invoice_id_input_widget",
        on_change=lambda: st.session_state.update(invoice_id_input=st.session_state.invoice_id_input_widget)
    )
    
    # Initialize placeholder for analysis results in session state
    if 'cli_analysis_results' not in st.session_state:
        st.session_state.cli_analysis_results = {}
    if 'modified_partner_clis_df' not in st.session_state:
        st.session_state.modified_partner_clis_df = pd.DataFrame()

    if st.button("Validate Invoice"):
        st.session_state.cli_analysis_results = {}
        st.session_state.modified_partner_clis_df = pd.DataFrame()
        
        with st.spinner(f"Fetching and analyzing data for Invoice ID: {invoice_id}..."):
            # Step 1: Fetch all data via validate_invoice (which calls fetch_full_invoice_data)
            result = service.validate_invoice(invoice_id)
            
            if not result["success"]:
                st.error(f"Error validating invoice: {result['error']}")
                st.stop()
            
            invoice_data_dict = result.get("invoice_data", {})
            if not invoice_data_dict or invoice_data_dict.get("error"):
                 st.error(f"Error fetching detailed data: {invoice_data_dict.get('error', 'Unknown data fetch error')}")
                 st.stop()

            # Step 2: Extract necessary DataFrames
            partner_subscriptions_df = invoice_data_dict.get('partner_subscriptions', pd.DataFrame())
            partner_clis_df = invoice_data_dict.get('partner_completed_line_items', pd.DataFrame())
            invoice_line_items_df = invoice_data_dict.get('invoice_line_items', pd.DataFrame())
            all_partner_transactions_df = invoice_data_dict.get('partner_transactions', pd.DataFrame())
            invoice_df = invoice_data_dict.get('invoice', pd.DataFrame())

            if invoice_df.empty:
                st.error("Invoice header data is missing. Cannot proceed.")
                st.stop()
            if partner_clis_df.empty:
                 st.warning("Partner Completed Line Items data is missing or empty. CLI analysis will be skipped.")
            
            # Step 3: Get Invoice Period
            try:
                invoice_date_str = invoice_df.iloc[0]['invoice_date']
                invoice_date = pd.to_datetime(invoice_date_str)
                invoice_month = invoice_date.month
                invoice_year = invoice_date.year
                st.info(f"Analyzing for Invoice Period: {invoice_year}-{invoice_month:02d}")
            except Exception as e:
                st.error(f"Error determining invoice period: {e}")
                st.stop()

            # Step 4: Identify Potentially Billable CLIs (only if partner CLIs exist)
            potential_cli_ids = []
            if not partner_clis_df.empty and not partner_subscriptions_df.empty:
                st.write("Identifying potentially billable CLIs...")
                potential_cli_ids = service.identify_potentially_billable_clis(
                    partner_subscriptions=partner_subscriptions_df,
                    partner_completed_line_items=partner_clis_df,
                    invoice_month=invoice_month,
                    invoice_year=invoice_year
                )
                st.write(f"Found {len(potential_cli_ids)} potentially billable CLIs to analyze.")
            elif partner_clis_df.empty:
                 st.warning("Skipping potential CLI identification: Partner CLIs DataFrame is empty.")
            elif partner_subscriptions_df.empty:
                 st.warning("Skipping potential CLI identification: Partner Subscriptions DataFrame is empty.")

            # Step 5 & 6: Loop, Analyze Each Potential CLI, and Store Results
            cli_analysis_results_temp = {}
            if potential_cli_ids:
                st.write("Analyzing individual CLIs...")
                # Pre-convert relevant columns to numeric for faster lookups
                if 'id' in partner_clis_df.columns: partner_clis_df['id'] = pd.to_numeric(partner_clis_df['id'], errors='coerce')
                if 'completed_line_id' in partner_subscriptions_df.columns: partner_subscriptions_df['completed_line_id'] = pd.to_numeric(partner_subscriptions_df['completed_line_id'], errors='coerce')
                if 'completed_line_item_id' in all_partner_transactions_df.columns: all_partner_transactions_df['completed_line_item_id'] = pd.to_numeric(all_partner_transactions_df['completed_line_item_id'], errors='coerce')
                if 'completed_line_item_id' in invoice_line_items_df.columns: invoice_line_items_df['completed_line_item_id'] = pd.to_numeric(invoice_line_items_df['completed_line_item_id'], errors='coerce')
                
                progress_bar = st.progress(0)
                total_clis = len(potential_cli_ids)
                for i, cli_id in enumerate(potential_cli_ids):
                    # Find records (using numeric cli_id)
                    cli_record_dict = find_row_as_dict(partner_clis_df, 'id', cli_id)
                    linked_subscription_dict = find_row_as_dict(partner_subscriptions_df, 'completed_line_id', cli_id)
                    
                    # Filter transactions (handle if column doesn't exist)
                    if 'completed_line_item_id' in all_partner_transactions_df.columns:
                        linked_transactions_df = all_partner_transactions_df[
                            all_partner_transactions_df['completed_line_item_id'] == cli_id
                        ].copy()
                    else: 
                        linked_transactions_df = pd.DataFrame()

                    if not cli_record_dict or not linked_subscription_dict:
                        continue

                    # Call analyzer
                    single_analysis = service.analyze_single_cli(
                        cli_record=cli_record_dict,
                        linked_subscription=linked_subscription_dict,
                        linked_transactions=linked_transactions_df,
                        invoice_line_items=invoice_line_items_df, 
                        invoice_month=invoice_month,
                        invoice_year=invoice_year
                    )
                    cli_analysis_results_temp[cli_id] = single_analysis
                    progress_bar.progress((i + 1) / total_clis)
                progress_bar.empty()
            st.session_state.cli_analysis_results = cli_analysis_results_temp

            # Step 7: Add Analysis Results to Partner CLIs DataFrame (if analysis was run)
            modified_partner_clis = partner_clis_df.copy()
            if st.session_state.cli_analysis_results:
                analysis_map = st.session_state.cli_analysis_results
                modified_partner_clis['id'] = pd.to_numeric(modified_partner_clis['id'], errors='coerce')
                
                modified_partner_clis['_analysis_in_invoice'] = modified_partner_clis['id'].map(
                    lambda x: analysis_map.get(x, {}).get('cli_in_invoice') if pd.notna(x) else None
                 )
                modified_partner_clis['_analysis_should_bill'] = modified_partner_clis['id'].map(
                    lambda x: analysis_map.get(x, {}).get('cli_should_be_billable') if pd.notna(x) else None
                 )
                modified_partner_clis['_analysis_has_tx'] = modified_partner_clis['id'].map(
                     lambda x: analysis_map.get(x, {}).get('has_transaction_for_period') if pd.notna(x) else None
                 )
                st.write("CLI analysis complete. Added analysis columns to Partner Completed Line Items.")
            st.session_state.modified_partner_clis_df = modified_partner_clis
            
            # *** ADD THIS LINE: Store the main result object in session state ***
            st.session_state.latest_result = result 
            
            st.success("Validation Data Fetched and Initial Analysis Complete!")
            # Rerun to display results in tabs immediately after calculation
            st.rerun()

    # --- Display Area (Uses data potentially calculated in the button press above) --- 
    st.divider()
    st.subheader("Validation Results") # Add a header for the display section
    
    # --- Debugging Session State --- 
    st.write("--- Debug Info (Post Rerun) ---")
    result_from_state_debug = st.session_state.get('latest_result')
    st.write(f"st.session_state.latest_result exists: {result_from_state_debug is not None}")
    if result_from_state_debug is not None:
        st.write(f"Is dict: {isinstance(result_from_state_debug, dict)}")
        if isinstance(result_from_state_debug, dict):
            st.write(f"Has 'invoice_data' key: {'invoice_data' in result_from_state_debug}")
            if 'invoice_data' in result_from_state_debug:
                 st.write(f"Type of 'invoice_data': {type(result_from_state_debug['invoice_data'])}")
                 if isinstance(result_from_state_debug['invoice_data'], dict):
                     st.write(f"'invoice_data' dict has 'invoice' key: {'invoice' in result_from_state_debug['invoice_data']}")
                     st.write(f"'invoice_data' dict has 'error' key: {'error' in result_from_state_debug['invoice_data']}")
                     st.write(f"Value of 'error' key: {result_from_state_debug['invoice_data'].get('error')}")
    st.write("--- End Debug Info ---")
    # --- End Debugging --- 
    
    # Check if results from a previous validation run are stored in session state
    result_from_state = st.session_state.get('latest_result')
    modified_partner_clis = st.session_state.get('modified_partner_clis_df', pd.DataFrame()) # Get modified df or empty
    
    # Refined check: Ensure invoice_data exists and doesn't contain an error itself
    if result_from_state and isinstance(result_from_state, dict) and \
       'invoice_data' in result_from_state and isinstance(result_from_state['invoice_data'], dict) and \
       result_from_state['invoice_data'].get('error') is None:
        # Use the results stored in session state
        result = result_from_state
        # We already fetched modified_partner_clis above
        st.write("(Using results stored in session state)") # Confirmation message
    else:
        # No valid results in session state, show initial message
        st.info("Enter an Invoice ID and click 'Validate Invoice' to see details.")
        # Add reason if possible
        if result_from_state and isinstance(result_from_state, dict) and 'invoice_data' in result_from_state and result_from_state['invoice_data'].get('error') is not None:
             st.warning(f"Found stored results, but they contained an error: {result_from_state['invoice_data'].get('error')}")
        elif not result_from_state:
             st.warning("No results found in session state.")
        else:
             st.warning("Stored results format is invalid.")
        st.stop()
         
    # --- Proceed with Tab Rendering using 'result' and 'modified_partner_clis' --- 
    # Create tabs
    tab_names = [
        "Data Counts", 
        "Analysis Summary", # Renamed from "Analysis" 
        "Anniv. Billing (Invoice)", # Shortened 
        "Anniv. Billing (Partner)", # Shortened
        "Subscriptions",
        "Transactions",
        "Line Items (CIRA)", # Added CIRA 
        "Completed Line Items" # Main focus for new analysis
    ]
    tabs = st.tabs(tab_names)
    
    # --- Tab Rendering --- 
    # Ensure result dictionary is valid before accessing keys
    if not result or 'invoice_data' not in result:
        st.error("Unexpected error: Result data is missing or invalid after state check.")
        st.stop()
        
    data_dict = result["invoice_data"]
    # modified_partner_clis is already fetched from session state above
    
    with tabs[0]:
        st.subheader("Data Counts")
        counts = result["counts"]
        metrics = {
            "Invoice Line Items (CIRA)": counts["invoice_line_items"],
            "Subscriptions": counts["subscriptions"],
            "Transactions": counts["transactions"],
            "Completed Line Items": counts["completed_line_items"],
            "Partner Invoice Line Items (CIRA)": counts["partner_line_items"],
            "Partner Subscriptions": counts["partner_subscriptions"],
            "Partner Transactions": counts["partner_transactions"],
            "Partner Completed Line Items": counts["partner_completed_line_items"]
        }
        display_metrics_in_columns(metrics)
        
        st.subheader("Invoice Data")
        display_dataframe_with_expander(
            data_dict["invoice"],
            "Invoice Header",
            "Basic invoice information"
        )
        
        display_dataframe_with_expander(
            data_dict["invoice_line_items"],
            "Invoice Line Items (CIRA)",
            "Line items from the invoice"
        )
        
        display_dataframe_with_expander(
            data_dict["subscriptions"],
            "Subscriptions",
            "Subscriptions in the invoice"
        )
        
        display_dataframe_with_expander(
            data_dict["transactions"],
            "Transactions",
            "Transactions in the invoice"
        )

        display_dataframe_with_expander(
            data_dict["completed_line_items"],
            "Completed Line Items",
            "Completed line items in the invoice"
        )
        
        st.subheader("Partner Data")

        display_dataframe_with_expander(
            data_dict["partner_line_items"],
            "Partner Invoice Line Items (CIRA)",
            "All line items for this partner"
        )
        
        display_dataframe_with_expander(
            data_dict["partner_transactions"],
            "Partner Transactions",
            "All transactions for this partner"
        )
        
        display_dataframe_with_expander(
            data_dict["partner_subscriptions"],
            "Partner Subscriptions",
            "All subscriptions for this partner"
        )
        
        display_dataframe_with_expander(
            data_dict["partner_completed_line_items"],
            "Partner Completed Line Items",
            "All completed line items for this partner"
        )
    
    with tabs[1]:
        st.subheader("High-Level Analysis Summary (Legacy)")
        st.warning("This tab uses the older analysis logic. See 'Completed Line Items' tab for detailed CLI checks.")
        legacy_analysis_results = analyze_invoice_data(data_dict)
        pass

    with tabs[2]:
        st.subheader("Anniversary Billing Items")
        data = result["invoice_data"]
        
        metrics = {
            "Invoice Line Items": len(data["invoice_line_items"]),
            "Subscriptions": len(data["subscriptions"]),
            "Transactions": len(data["transactions"]),
            "Completed Line Items": len(data["completed_line_items"])
        }
        display_metrics_in_columns(metrics)
        
        display_dataframe_with_expander(
            data["invoice_line_items"],
            "Invoice Line Items (CIRA)",
            "These are the line items from the invoice that are associated with anniversary billing products."
        )
        
        display_dataframe_with_expander(
            data["subscriptions"],
            "Subscriptions",
            "These are the subscriptions associated with anniversary billing products in this invoice."
        )
        
        display_dataframe_with_expander(
            data["transactions"],
            "Transactions",
            "These are the transactions associated with anniversary billing products in this invoice."
        )
        
        display_dataframe_with_expander(
            data["completed_line_items"],
            "Completed Line Items",
            "These are the completed line items associated with anniversary billing products in this invoice."
        )
    
    with tabs[3]:
        st.subheader("Partner Anniversary Billing Items")
        data = result["invoice_data"]
        
        metrics = {
            "Partner Transactions": len(data["partner_transactions"]),
            "Partner Subscriptions": len(data["partner_subscriptions"]),
            "Partner Line Items": len(data["partner_line_items"]),
            "Partner Completed Line Items": len(data["partner_completed_line_items"])
        }
        display_metrics_in_columns(metrics)
        
        display_partner_and_invoice_data(
            data["partner_transactions"],
            data["transactions"],
            "Transactions",
            "transactions",
            "transaction_id",
            date_filter_column="invoice_date",
            date_filter_key="partner_transactions_date_filter"
        )
        
        display_partner_and_invoice_data(
            data["partner_subscriptions"],
            data["subscriptions"],
            "Subscriptions",
            "subscriptions",
            "completed_line_id",
            status_filter_key="partner_anniversary_subscriptions_status_filter"
        )
        
        display_partner_and_invoice_data(
            data["partner_line_items"],
            data["invoice_line_items"],
            "Line Items",
            "line items",
            "line_item_id",
            date_filter_column="start_period",
            date_filter_key="partner_line_items_date_filter"
        )
        
        display_partner_and_invoice_data(
            data["partner_completed_line_items"],
            data["completed_line_items"],
            "Completed Line Items",
            "completed line items",
            "id",
            date_filter_column="created_dt",
            date_filter_key="partner_completed_line_items_date_filter"
        )
    
    with tabs[4]:
        st.subheader("Subscriptions")
        data = result["invoice_data"]
        
        metrics = {
            "Invoice Subscriptions": len(data["subscriptions"]),
            "Partner Subscriptions": len(data["partner_subscriptions"])
        }
        display_metrics_in_columns(metrics, num_columns=2)
        
        display_partner_and_invoice_data(
            data["partner_subscriptions"],
            data["subscriptions"],
            "Subscriptions",
            "subscriptions",
            "completed_line_id",
            status_filter_key="subscriptions_status_filter"
        )
    
    with tabs[5]:
        st.subheader("Transactions")
        data = result["invoice_data"]
        
        metrics = {
            "Invoice Transactions": len(data["transactions"]),
            "Partner Transactions": len(data["partner_transactions"])
        }
        display_metrics_in_columns(metrics, num_columns=2)
        
        display_partner_and_invoice_data(
            data["partner_transactions"],
            data["transactions"],
            "Transactions",
            "transactions",
            "transaction_id",
            date_filter_column="invoice_date",
            date_filter_key="transactions_date_filter"
        )
    
    with tabs[6]:
        st.subheader("Line Items")
        data = result["invoice_data"]
        
        metrics = {
            "Invoice Line Items": len(data["invoice_line_items"]),
            "Partner Line Items": len(data["partner_line_items"])
        }
        display_metrics_in_columns(metrics, num_columns=2)
        
        display_partner_and_invoice_data(
            data["partner_line_items"],
            data["invoice_line_items"],
            "Line Items",
            "line items",
            "line_item_id",
            date_filter_column="start_period",
            date_filter_key="line_items_date_filter_2"
        )
    
    with tabs[7]:
        st.subheader("Completed Line Items Analysis")
        
        metrics = {
            "Invoice CLIs": len(data_dict.get("completed_line_items", pd.DataFrame())),
            "Partner CLIs (Analyzed)": len(modified_partner_clis)
        }
        display_metrics_in_columns(metrics, num_columns=2)
        
        st.write("Partner Completed Line Items (with analysis flags)")
        st.info("Highlighting: Green = In Invoice, Red = Should Bill but Not In Invoice")
        display_partner_and_invoice_data(
            modified_partner_clis,
            data_dict.get("completed_line_items", pd.DataFrame()),
            "Completed Line Items",
            "completed line items",
            "id",
            date_filter_column="created_dt",
            date_filter_key="partner_completed_line_items_date_filter_2",
            analysis_in_invoice_col="_analysis_in_invoice",
            analysis_should_bill_col="_analysis_should_bill"
        )

if __name__ == "__page__":
    render_invoice_validation_page()