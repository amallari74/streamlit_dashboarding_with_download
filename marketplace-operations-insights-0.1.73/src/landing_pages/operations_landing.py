import streamlit as st

def main():
    # Check if we need to update navigation
    if st.session_state.get("nav_section") != "Operations":
        # Update navigation mode
        st.session_state.nav_section = "Operations"
        # Rerun the app to refresh navigation
        st.rerun()
    
    # Operations landing page content
    st.title("Operations Dashboard")
    
    st.markdown("""
    Welcome to the Operations dashboard. Use the sidebar to access:
    
    - **EDSB UAT** - Testing and validation tool for EDSB
    - **Billing Eyes** - Monitor billing operations
    - **Microsoft Reconciliation** - View Microsoft Renewals against Pax8 renewals
    """)
    

if __name__ == "__page__":
    main() 