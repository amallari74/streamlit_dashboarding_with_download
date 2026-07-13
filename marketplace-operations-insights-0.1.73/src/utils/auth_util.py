
import requests
import secrets
from urllib.parse import urlencode
import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
from router.users import VERY_SECURE_RBAC

AUTH0_CLIENT_ID = st.secrets["auth0"]["client_id"]
AUTH0_CLIENT_SECRET = st.secrets["auth0"]["client_secret"]
AUTH0_DOMAIN = st.secrets["auth0"]["domain"]  # e.g., 'YOUR_AUTH0_DOMAIN.auth0.com'
AUTH0_CALLBACK_URL = st.secrets["auth0"]["callback_url"]  # e.g., 'http://localhost:8501'
AUTH0_AUDIENCE = f'https://{AUTH0_DOMAIN}/userinfo'


def auth_for(ROLES: list[str]):
    if not st.session_state.get("authenticated", False):
        st.switch_page("home_page.py")
        return False
    if not st.session_state.get("profile"):
        st.switch_page("home_page.py")
        return False
    if check_for(ROLES):
        return True
    st.switch_page("home_page.py")
    return False


def check_for(ROLES: list[str]):
    user_roles = get_user_roles()
    return any(role in user_roles for role in ROLES)


def get_auth_url(cookies: EncryptedCookieManager):
    # Generate random state string for CSRF protection
    state = secrets.token_urlsafe(16)
    cookies["auth0/oauth_state"] = state  # Store state in cookie
    cookies.save()  # Save cookies to the browser
    params = {
        'client_id': AUTH0_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': AUTH0_CALLBACK_URL,
        'scope': 'openid profile email',
        'audience': AUTH0_AUDIENCE,
        'state': state
    }
    url = f"https://{AUTH0_DOMAIN}/authorize?{urlencode(params)}"
    return url


def get_user_roles():
    user_profile = get_user_profile()
    if not user_profile:
        return ["pax8"]  # Return default role if no profile
    user_email = user_profile.get("email")
    if not user_email:
        return ["pax8"]
    user_roles = VERY_SECURE_RBAC.get(user_email, [])
    return user_roles + ["pax8"]


def get_user_profile(cookies: EncryptedCookieManager = None):
    if not st.session_state.get("profile"):
        if not cookies:
            return {}
        refresh_user_profile(cookies)
    return st.session_state.get("profile", {})


def refresh_user_profile(cookies: EncryptedCookieManager):
    access_token = cookies.get("auth0/access_token")
    if access_token:
        userinfo_url = f"https://{AUTH0_DOMAIN}/userinfo"
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(userinfo_url, headers=headers)
        if response.status_code == 200:
            st.session_state["profile"] = response.json()
            return response.json()
        else:
            # Clear the profile if refresh fails
            st.session_state["profile"] = {}
            st.error("Failed to fetch user profile.")
            return None
    else:
        # Ensure profile is cleared if no access token
        st.session_state["profile"] = {}
        return None


def exchange_code_for_token(code):
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'authorization_code',
        'client_id': AUTH0_CLIENT_ID,
        'client_secret': AUTH0_CLIENT_SECRET,
        'code': code,
        'redirect_uri': AUTH0_CALLBACK_URL
    }
    response = requests.post(token_url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to exchange code for token.")
        return None


def redirect_startup(cookies: EncryptedCookieManager):
    query_params = st.query_params
    if 'code' in query_params and 'state' in query_params:
        code = query_params['code']
        returned_state = query_params['state']
        stored_state = cookies.get("auth0/oauth_state")
        if returned_state != stored_state:
            st.error("State mismatch. Possible CSRF attack.")
            return False
        token = exchange_code_for_token(code)
        if token:
            st.write("Found token.")
            st.session_state['authenticated'] = True
            cookies["auth0/access_token"] = token['access_token']
            cookies["auth0/oauth_state"] = ""  # Clear the state cookie
            cookies.save()
            st.query_params.clear()
            st.write("Authenticated successfully.")
            st.rerun()
            return True
        else:
            st.error("Failed to authenticate.")
            return False
    st.write("Cannot login automatically. Please refresh your SSO session.")
    return False


def is_logged_in(cookies: EncryptedCookieManager):
    if st.session_state.get("authenticated", False):
        return True

    token = cookies.get("auth0/access_token")
    if token:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(AUTH0_AUDIENCE, headers=headers)
        if response.status_code == 200:
            st.session_state['authenticated'] = True
            return True
        else:
            st.toast("Failed to authenticate user.", icon=":material/block:")
            return False
    else:
        return False


def logout(cookies: EncryptedCookieManager):
    # Clear cookies
    cookies["auth0/access_token"] = ""
    cookies["auth0/oauth_state"] = ""
    cookies.save()
    # Redirect to Auth0 logout URL
    params = {
        'client_id': AUTH0_CLIENT_ID,
        'returnTo': AUTH0_CALLBACK_URL
    }
    logout_url = f"https://{AUTH0_DOMAIN}/v2/logout?{urlencode(params)}"
    st.write(f'<meta http-equiv="refresh" content="0; URL={logout_url}">', unsafe_allow_html=True)

