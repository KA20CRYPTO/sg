import streamlit as st
from nav_utils import load_unified_css, render_universal_sidebar
from login import login_section

# Standard Page Setup
st.set_page_config(
    page_title="ScreenerPro • Authentication",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Branding & Styles
load_unified_css()
render_universal_sidebar("Login / Register")

# If user is already logged in, redirect them to the home/dashboard
if st.session_state.get("authenticated", False):
    st.info("You are already logged in. Redirecting to Dashboard...")
    st.session_state.current_page = "Dashboard"
    try:
        st.switch_page("pages/dashboard.py")
    except:
        st.switch_page("dashboard.py")

# Render the Login Section
login_section()
