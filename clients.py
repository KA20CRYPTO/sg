import streamlit as st
from nav_utils import load_unified_css, render_universal_sidebar
from client_page import client_dashboard_page

# Standard Page Setup
st.set_page_config(
    page_title="ScreenerPro • Our Clients",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Branding & Styles
load_unified_css()
render_universal_sidebar("Our Clients")

# Render the Page
client_dashboard_page()
