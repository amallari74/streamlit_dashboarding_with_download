import asyncio
import streamlit as st
st.set_page_config(page_title="Marketplace Operations Insights", layout="wide")
from utils import db_util, auth_util, cookie_util
from streamlit_cookies_manager import EncryptedCookieManager
import router.roles as roles


def pages(cookies):
    if {} == auth_util.get_user_profile():
        auth_util.refresh_user_profile(cookies)

    # Initialize navigation section in session state if not present
    if "nav_section" not in st.session_state:
        st.session_state.nav_section = "Home"

    landing_pages_dict = {
        "Billing": st.Page("landing_pages/billing_landing.py", title="Billing Home", icon=":material/receipt:"),
        "Operations": st.Page("landing_pages/operations_landing.py", title="Operations Home", icon=":material/insights:"),
        "Internal Development": st.Page("landing_pages/internal_dev_landing.py", title="Internal Development Home", icon=":material/code:")
    }
    # Basic structure with Home always shown
    all_pages = {
        "": [st.Page("landing_pages/home_page.py", title="Home", icon=":material/home:", default=True)],
    }
    if st.session_state.nav_section == "Home":
        landing_pages = landing_pages_dict.values()
        all_pages["Sections"] = landing_pages
    else:
        all_pages[""] = [
            st.Page("landing_pages/home_page.py", title="Home", icon=":material/home:", default=True),
            landing_pages_dict[st.session_state.nav_section]
        ]

    # Add section-specific pages based on current navigation section
    if st.session_state.nav_section == "Billing":
        if auth_util.check_for(roles.BILLING_RUN_ROLES):
            billing_run_pages = [
                st.Page("billing_run/task_manager.py", title="Tasks Monitoring", icon=":material/calendar_clock:"),
                st.Page("billing_run/billable_usage_monitoring.py", title="Billable Usage Monitoring", icon=":material/calendar_clock:"),
                st.Page("billing_run/invoice_generation.py", title="Invoice Generation Monitoring", icon=":material/receipt_long:"),
                st.Page("billing_run/invoice_release.py", title="Invoice Release Monitoring", icon=":material/send:"),
                # st.Page("billing_run/pages/invoice_validation_page.py", title="Invoice Validation Page", icon=":material/receipt_long:"),
                st.Page("billing_run/pages/invoice_validation_page_2.py", title="Invoice Validation Page 2", icon=":material/receipt_long:")
            ] 

            if auth_util.check_for(roles.DOWNLOAD_ROLES):
                billing_run_pages.append(st.Page("billing_run/download_datasets.py", title="Data Download", icon=":material/download:", url_path="data_download"))
            all_pages["Billing Run"] = billing_run_pages

            all_pages["Billing Analytics"] = [
                st.Page("billing_run/pages/monthly_billing_summary.py", title="Monthly Billing Summary", icon=":material/receipt_long:"),
                st.Page("billing_run/pages/arrears_task_monitoring.py", title="Billable Usage Tasks", icon=":material/query_stats:", url_path="arrears_task_monitoring"),
                st.Page("billing_run/pages/billing_task_monitoring.py", title="Billing Tasks", icon=":material/receipt_long:", url_path="billing_task_monitoring"),
                st.Page("billing_run/pages/invoice_task_duration_monitoring.py", title="Invoice Task Duration", icon=":material/timer:", url_path="invoice_task_duration_monitoring"),
            ]
    
    elif st.session_state.nav_section == "Operations":
        diagnostics = []
        if auth_util.check_for(roles.DIAGNOSTICS_ROLES):
            diagnostics.append(st.Page("diagnostics/transaction_monitoring.py", title="Transaction Monitoring", icon=":material/calendar_clock:"))
            diagnostics.append(st.Page("diagnostics/bob_assessment_monitoring.py", title="Bill-On-Behalf Assessment", icon=":material/calendar_clock:"))


            all_pages["Operations Tools"] = diagnostics
    
    elif st.session_state.nav_section == "Internal Development":
        reports = []
        if auth_util.check_for(roles.INTERNAL_DEVELOPMENT_ROLES):
            reports.append(st.Page("reports/subscription_details.py", title="Subscription Details WIP", icon=":material/subscriptions:"))
            all_pages["Development Tools"] = reports
    
    return all_pages


async def authenticate_user(cookies: EncryptedCookieManager):
    # Authentication flow
    if not auth_util.is_logged_in(cookies):
        # Hide navigation when not authenticated
        st.navigation.position = "hidden"
        # This solution is used by multiple streamlit auth libraries...
        # Session state is loaded late in the initial lifecycle, so try again.
        await asyncio.sleep(1)
    if not auth_util.is_logged_in(cookies):
        # Check for Auth0 redirect with authorization code
        if not auth_util.redirect_startup(cookies):
            if st.button("Login"):
                # Redirect to Auth0 for authentication
                auth_url = auth_util.get_auth_url(cookies)
                st.write(f'<meta http-equiv="refresh" content="0; URL={auth_url}">', unsafe_allow_html=True)
    else:
        st.navigation.position = "sidebar"
        return True

def main():
       
    # Initialize the cookie manager
    cookie_util.set_cookie_manager(EncryptedCookieManager(
        prefix="pax8/marketplace-operations-insights",  # Optional: prefix for cookie names
        # The key should be a string of 16 bytes (128 bits) or 32 bytes (256 bits)
        password=st.secrets["auth0"]["cookie_secret"],
    ))
    cookies = cookie_util.get_cookie_manager()

    # Check if authentication is enabled in secrets
    auth_enabled = st.secrets["auth0"].get("enabled", True)
    if auth_enabled and not auth_util.is_logged_in(cookies):
        st.write("User is not logged in.")
        pg = st.navigation([st.Page("landing_pages/home_page.py", title="Home", default=True)])
        pg.run()
        asyncio.run(authenticate_user(cookies))
        return

    with st.sidebar:
        st.warning(
            """
            This is an internal toolkit to aid in operations and analysis,
            DO NOT use this to inform business decisions without formal validation.
            """
        )
        if st.button("Clear Cache & Reset DB"):
            db_util.reset()
            st.cache_data.clear()
        if st.button("Logout"):
            auth_util.logout(cookies)

    # Show navigation
    pg = st.navigation(pages(cookies))
    pg.run()

if __name__ == "__main__":
    main()
