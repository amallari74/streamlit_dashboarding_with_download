import streamlit as st

from utils import auth_util, cookie_util
from components.data_freshness import render_data_freshness_section


def show_home_page():
        # Check if we need to update navigation
    if st.session_state.get("nav_section") != "Home":
        # Update navigation mode
        st.session_state.nav_section = "Home"
        # Rerun the app to refresh navigation
        st.rerun()
    st.title("Marketplace Operations Toolkit")
    st.markdown(
        """
        Operational tooling, visuals, and ad-hoc reports
        exploratory application for marketplace operations.
        """
    )

    cookies = cookie_util.get_cookie_manager()

    # Check if authenticated
    auth_enabled = st.secrets["auth0"].get("enabled", True)
    if auth_enabled and not auth_util.is_logged_in(cookies):
        st.write("User is not logged in.")
        return

    # User is authenticated, display the app content
    user_profile = auth_util.get_user_profile(cookies)
    if user_profile:
        st.write(f"Welcome, {user_profile.get('name')}!")
    else:
        st.error("Failed to fetch user profile.")
        # TODO(rwhite): Consider whether to force logout if the user profile is broken
        # auth_util.logout(cookies_auth0)
        
    # Home page content with cards for each section
    st.subheader("Quick Access")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container(border=True):
            st.markdown("### Billing")
            st.markdown("Access monthly billing summaries, task monitoring, and invoice generation tools.")
            st.page_link("landing_pages/billing_landing.py", label="Go to Billing", icon="🧾")
    
    with col2:
        with st.container(border=True):
            st.markdown("### Operations")
            st.markdown("Access diagnostic tools, testing environments, and reconciliation dashboards.")
            st.page_link("landing_pages/operations_landing.py", label="Go to Operations", icon="🔍")
    
    with col3:
        with st.container(border=True):
            st.markdown("### Internal Development")
            st.markdown("Access proof of concept tools and works in progress.")
            st.page_link("landing_pages/internal_dev_landing.py", label="Go to Internal Development", icon="💻")
    
    # Add data warehouse freshness section
    st.divider()
    with st.container(border=True):
        render_data_freshness_section()


if __name__ == "__page__":
    show_home_page()
