import streamlit as st
import os
from nav_utils import load_unified_css, render_universal_sidebar
from certificate_verification import certificate_verification_page
from firebase_config import FIREBASE_WEB_API_KEY

# Standard Page Setup
st.set_page_config(
    page_title="ScreenerPro • Certificate Verification",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Branding & Styles
load_unified_css()
render_universal_sidebar("Certificate Verification")

# Configuration for the verification service
FIREBASE_PROJECT_ID = os.environ.get("__app_id", "screenerproapp")

# Render the Verification Page
certificate_verification_page(FIREBASE_PROJECT_ID, FIREBASE_WEB_API_KEY)
