import streamlit as st
from utils import db_util
from components.data_freshness import render_data_freshness_section

def main():
    # Check if we need to update navigation
    if st.session_state.get("nav_section") != "Billing":
        # Update navigation mode
        st.session_state.nav_section = "Billing"
        # Rerun the app to refresh navigation
        st.rerun()
    
    # Billing landing page content
    st.title("Billing & Invoicing")
    
    st.markdown("""
    Welcome to the Billing Operations dashboard. Use the sidebar to access:
    
    ## Billing Run
    - **Tasks Monitoring** - Overview of all billing tasks in one page
    - **Billable Usage Monitoring** - Arrears tasks and usage variance monitoring
    - **Invoice Generation Monitoring** - Invoice generation and invoice row variance
    - **Invoice Release Monitoring** - Track invoice delivery and sending status
    
    ## Billing Analytics
    - **Monthly Billing Summary** - Overview of billing metrics, similar to executive summary report
    - **Billable Usage Tasks** - Arrears tasks analytics
    - **Billing Tasks** - Invoice and tax billing tasks analytics
    - **Invoice Task Duration** - Performance monitoring with alerting for createPartnerInvoice and createCompanyInvoice tasks
    """)
    
    # Add Data Warehouse Freshness section
    st.divider()
    with st.container(border=True):
        render_data_freshness_section()

if __name__ == "__page__":
    main() 