import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager


_cookies = None

def set_cookie_manager(cookies):
    global _cookies
    _cookies = cookies


def get_cookie_manager():
    global _cookies
    if _cookies is None:
        st.error("No cookie manager available. Cannot save login.")
        raise ValueError("No cookie manager available.")

    # Used this to figure out wtf it does
    # for attribute in dir(_cookies):
    #     value = getattr(_cookies, attribute)
    #     if callable(value):
    #         st.write(attribute)

    if not _cookies.ready():
        st.spinner()
        st.stop()

    return _cookies