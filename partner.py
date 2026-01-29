import streamlit as st
from nav_utils import load_unified_css, render_universal_sidebar
from partners import partner_with_us_page

# Standard Page Setup
st.set_page_config(
    page_title="ScreenerPro • Partner With Us",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Branding & Styles
load_unified_css()
render_universal_sidebar("Partner With Us")

# Render the Page
partner_with_us_page()
