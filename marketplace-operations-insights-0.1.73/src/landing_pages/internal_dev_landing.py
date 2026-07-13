import streamlit as st

def main():
    # Check if we need to update navigation
    if st.session_state.get("nav_section") != "Internal Development":
        # Update navigation mode
        st.session_state.nav_section = "Internal Development"
        # Rerun the app to refresh navigation
        st.rerun()
    
    # Internal Development landing page content
    st.title("Internal Development")
    
    st.markdown("""
    Welcome to the Internal Development area. Use the sidebar to access:
    
    - **Subscription Details** - WIP subscription analysis

    """)
    
    st.warning("""
    These are works in progress and proof of concept implementations.
    They may be unstable or incomplete.
    """)

if __name__ == "__page__":
    main() 