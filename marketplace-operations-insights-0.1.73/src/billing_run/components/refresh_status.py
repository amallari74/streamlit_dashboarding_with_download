import streamlit as st
from typing import Callable, Optional

def show_refresh_status(func_name: str, refresh_func: Optional[Callable] = None):
    """
    Show when data was last refreshed in the sidebar.
    
    Args:
        func_name: The function name to check last refresh time for
        refresh_func: Optional function to call when refresh button is clicked
    """
    from billing_run.models.repositories import get_last_refresh_formatted
    
    refresh_status = get_last_refresh_formatted(func_name)
    
    # Show a badge with refresh time in the sidebar
    st.sidebar.markdown(f"""
    <div style="background-color:#f0f2f6; padding:8px; border-radius:5px; 
         font-size:0.8em; margin-bottom:10px;">
        <span style="color:#666;">Last refreshed:</span> {refresh_status}
    </div>
    """, unsafe_allow_html=True)
    
    # Add a refresh button if a refresh function was provided
    if refresh_func and st.sidebar.button("Refresh Now"):
        with st.spinner("Refreshing data..."):
            refresh_func()
        st.experimental_rerun()


def show_multiple_refresh_status(func_names, title="Data Last Refreshed"):
    """
    Show refresh status for multiple functions in a collapsible section.
    
    Args:
        func_names: List of function names to check
        title: Optional title for the section
    """
    from billing_run.models.repositories import get_last_refresh_formatted
    
    with st.sidebar.expander(title, expanded=False):
        for func_name in func_names:
            # Get a friendly display name (remove fetch_ prefix and underscores)
            display_name = func_name.replace("fetch_", "").replace("_", " ").title()
            refresh_status = get_last_refresh_formatted(func_name)
            
            st.markdown(f"""
            <div style="font-size:0.8em; margin-bottom:5px;">
                <span style="color:#666;">{display_name}:</span> {refresh_status}
            </div>
            """, unsafe_allow_html=True) 