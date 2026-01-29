import streamlit as st
from nav_utils import load_unified_css, render_universal_sidebar
from feedback import feedback_and_help_page

# Standard Page Setup
st.set_page_config(
    page_title="ScreenerPro • Feedback & Help",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Branding & Styles
load_unified_css()
render_universal_sidebar("Feedback & Help")

# Render the Page
feedback_and_help_page()
