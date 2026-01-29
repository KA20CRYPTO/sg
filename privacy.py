import streamlit as st
from nav_utils import load_unified_css, render_universal_sidebar
from privacy_policy import privacy_policy_page

# Standard Page Setup
st.set_page_config(
    page_title="ScreenerPro • Privacy & Terms",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Branding & Styles
load_unified_css()
render_universal_sidebar("Privacy Policy & Terms")

# Render the Page
privacy_policy_page()
