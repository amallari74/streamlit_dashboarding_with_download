import streamlit as st
import pandas as pd
from datetime import datetime
from billing_run.models.download_datasets_model import fetch_invoice_report, fetch_credit_memo_report

# Import our repository functions instead of direct model functions
from billing_run.models.repositories import (
    fetch_business_units,
    fetch_vendors,
    fetch_invoice_row_details_dataset as fetch_invoice_row_details,
    fetch_invoices,
    fetch_filtered_arrears_tasks,
    fetch_filtered_billing_tasks,
    get_last_refresh_formatted
)
from billing_run.components.refresh_status import show_multiple_refresh_status

def show_download_datasets_page():
    st.title("Download Datasets")
    
    # Show refresh status in the sidebar
    # show_multiple_refresh_status([
    #     "fetch_business_units",
    #     "fetch_vendors",
    #     "fetch_invoice_row_details_dataset",
    #     "fetch_invoices",
    #     "fetch_filtered_arrears_tasks",
    #     "fetch_filtered_billing_tasks"
    # ])
    
    # General information about how the page works
    st.info("""
    ### How to Download Data
    1. Select a dataset type from the dropdown
    2. Choose your filter options in the form
    3. Click "Generate Dataset" to run the query
    4. Once processing is complete, click the "Download CSV" button that appears
    
    **Note:** Some queries may take a minute to process depending on the amount of data.
    Business Unit selection is required to prevent performance issues with large datasets.
    """)
    
    # Dataset selector dropdown
    dataset_options = ["Invoice Row Details", "Invoice", "Arrears Tasks", "Billing Tasks", "Invoice Report", "Credit Memo Report"]
    selected_dataset = st.selectbox("Select Dataset", dataset_options)
    
    # Get filter data - no need to pass schema and database now
    business_units = fetch_business_units()
    vendors = fetch_vendors()
    
    # Status options for tasks
    status_options = ["new", "error", "finished", "reviewed"]
    
    # Method options for billing tasks
    method_options = [
        "createPartnerInvoice", 
        "createCompanyInvoice", 
        "calculateAndStoreSalesTaxRatesForPartner",
        "calculateAndStoreSalesTaxRatesForCompany", 
        "sendInvoiceForCompany", 
        "sendInvoiceForPartner"
    ]
    
    # Initialize variables for query
    query_func = None
    params = {}
    
    # Initialize filter containers based on selection
    with st.form("dataset_filters"):
        if selected_dataset == "Invoice Row Details":
            # Dataset info
            st.markdown("""
            **Invoice Row Details**
            
            Individual line items from invoices including product details, prices, quantities, and tax information.
            Filtered by business unit and optionally by vendor.
            
            *Note: Query only returns non-voided line items due to performance constraints with large datasets.*
            """)
            
            # Show relevant filters
            business_unit = st.selectbox("Business Unit", business_units['unique_code'].tolist())
            vendor = st.selectbox("Vendor", ["All"] + vendors['vendor'].tolist())
            invoice_date = st.radio("Invoice Date", ["This Month", "Last Month"])
            
            # Function to call when downloading
            query_func = fetch_invoice_row_details
            params = {
                "business_unit": business_unit,
                "vendor": None if vendor == "All" else vendor, 
                "invoice_date": invoice_date
                # No need to pass schema and database
            }
            
        elif selected_dataset == "Invoice":
            # Dataset info
            st.markdown("""
            **Invoice Data**
            
            Invoice header information including totals, dates, and business unit details.
            Does not include individual line items.
            
            *Note: This dataset returns all invoices (both voided and non-voided).*
            """)
            
            # Show relevant filters
            business_unit = st.selectbox("Business Unit", business_units['unique_code'].tolist())
            invoice_date = st.radio("Invoice Date", ["This Month", "Last Month"])
            
            # Function to call when downloading
            query_func = fetch_invoices
            params = {
                "business_unit": business_unit,
                "invoice_date": invoice_date
                # No need to pass schema and database
            }
            
        elif selected_dataset == "Arrears Tasks":
            # Dataset info
            st.markdown("""
            **Arrears Tasks Data**
            
            Information about arrears billing tasks including status, run times, and any errors.
            Filter by status and vendor to narrow results.
            """)
            
            # Show relevant filters
            status = st.selectbox("Status", ["All"] + status_options)
            vendor = st.selectbox("Vendor", ["All"] + vendors['vendor'].tolist())
            
            # Function to call when downloading
            query_func = fetch_filtered_arrears_tasks
            params = {
                "status": None if status == "All" else status,
                "vendor": None if vendor == "All" else vendor
                # No need to pass schema and database
            }
            
        elif selected_dataset == "Billing Tasks":
            # Dataset info
            st.markdown("""
            **Billing Tasks Data**
            
            Details about billing process tasks including invoice generation, tax calculations, and sending.
            Filter by status and specific method types.
            """)
            
            # Show relevant filters
            status = st.selectbox("Status", ["All"] + status_options)
            method = st.selectbox("Method", ["All"] + method_options)
            
            # Function to call when downloading
            query_func = fetch_filtered_billing_tasks
            params = {
                "status": None if status == "All" else status,
                "method": None if method == "All" else method
                # No need to pass schema and database
            }

        elif selected_dataset == "Invoice Report":
            # Dataset info
            st.markdown("""
            **Invoice Report Data**

            Details about invoice report including partner_id, partner_name, vat_tax_amount, tax_id and business_unit_code .
            Filter by business_unit_code  and invoice_date.
            """)

            min_date = datetime(2012, 1, 1)
            max_date = datetime.now()
            # Show relevant filters
            business_unit = st.selectbox("Business Unit", business_units['unique_code'].tolist())
            invoice_date = st.date_input("Select Invoice Date", max_value=max_date, min_value=min_date)

            database = 'redshift'
            schema = 'cc.'
            # Function to call when downloading
            query_func = fetch_invoice_report
            params = {
                "business_unit": business_unit,
                "invoice_date": invoice_date,
                "schema": schema,
                "database": database
            }

        elif selected_dataset == "Credit Memo Report":
            # Dataset info
            st.markdown("""
            **Credit Memo Report Data**

            Details about credit memo report including partner_id, partner_name, vat_tax_amount, tax_id and business_unit_code .
            Filter by business_unit_code  and invoice_date.
            """)

            min_date = datetime(2012, 1, 1)
            max_date = datetime.now()
            # Show relevant filters
            business_unit = st.selectbox("Business Unit", business_units['unique_code'].tolist())
            transaction_date = st.date_input("Select Transaction Date", max_value=max_date, min_value=min_date)

            database = 'redshift'
            schema = 'cc.'
            # Function to call when downloading
            query_func = fetch_credit_memo_report
            params = {
                "business_unit": business_unit,
                "transaction_date": transaction_date,
                "schema": schema,
                "database": database
            }

        # Form submit button - don't include download functionality inside form
        st.session_state.generate_clicked = st.form_submit_button("Generate Dataset")

        # Store these for use outside the form
        if st.session_state.generate_clicked:
            st.session_state.current_params = params
            st.session_state.current_query_func = query_func
            st.session_state.current_dataset = selected_dataset

    # Handle dataset generation OUTSIDE the form
    if st.session_state.get("generate_clicked", False) and st.session_state.get("current_query_func"):
        with st.spinner("Generating dataset... This might take a moment for larger datasets"):
            # Run query with filters
            try:
                results = st.session_state.current_query_func(**st.session_state.current_params)
                # Generate download link - now outside the form
                if not results.empty:
                    csv = results.to_csv(index=False)
                    dataset_name = st.session_state.current_dataset.lower().replace(' ', '_')
                    st.download_button(
                        "Download CSV",
                        csv,
                        f"{dataset_name}_{datetime.now().strftime('%Y%m%d')}.csv"
                    )
                    st.success(f"Dataset ready! Generated {len(results)} rows.")
                else:
                    st.warning("No data found with selected filters. Try changing your criteria.")
            except Exception as e:
                st.error(f"Error generating dataset: {str(e)}")
                st.error("Please try different filters or contact support if the issue persists.")

# This ensures the page can be run directly or imported
if __name__ == "__page__":
    show_download_datasets_page()
