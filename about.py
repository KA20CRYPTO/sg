import streamlit as st
from nav_utils import load_unified_css, render_universal_sidebar
from about_us import about_us_page

# Standard Page Setup
st.set_page_config(
    page_title="ScreenerPro • About Us",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Branding & Styles
load_unified_css()
render_universal_sidebar("About Us")

# Render the Page
about_us_page()
