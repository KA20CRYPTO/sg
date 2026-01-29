import streamlit as st
import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import plotly.express as px
import requests
import io
import streamlit.components.v1 as components

# --- Page Config (MUST be first) ---
st.set_page_config(
    page_title="Screener Pro HR",
    layout="wide",
    page_icon="🧠",
    initial_sidebar_state="collapsed" # We hide it anyway via CSS
)

# --- Global Style Injection ---
def load_css(css_file_name):
    try:
        with open(css_file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file '{css_file_name}' not found.")

load_css("style.css")

# --- Imports (Page Modules) ---
# Import Firebase authentication and user management functions
from login import login_section
# Import other pages
from about_us import about_us_page
from privacy_policy import privacy_policy_page
from partners import partner_with_us_page
from resume_counter import live_resume_counter_page
from employee_management import employee_management_page
from screener import resume_screener_page
from feedback import feedback_and_help_page
from collaboration import collaboration_hub_page
from email_page import send_email_to_candidate
from certificate_verification import certificate_verification_page
from manage_jds import manage_jds_page
from client_page import client_dashboard_page
from hr_campaign_creator import hr_campaign_creator_page
from public_job_board import public_job_board_page
from dashboard import show_authenticated_home_page # Assumed existing dashboard function
# Check if `show_authenticated_home_page` exists in dashboard.py, usually it does or similar.
# In the original main.py, it was imported as `show_authenticated_home_page` (inferred from usage line 1716) 
# but I don't see the import line in the view. I'll check dashboard usage.
# If dashboard.py has a main function, I'll use it. 
# Re-reading main.py snippet: `from dashboard import show_authenticated_home_page` wasn't explicitly shown in top 80 lines 
# but line 1716 calls `show_authenticated_home_page(log_activity_main)`.
# Since I haven't seen the `dashboard` import, I will add it.
from dashboard import show_authenticated_home_page 
# If `dashboard` module is missing or named differently, this will fail. 
# `dashboard.py` exists (referenced in task).

# --- Constants & Config ---
FIREBASE_PROJECT_ID = globals().get('__app_id', 'screenerproapp')
FIREBASE_WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY', 'AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw')
FIRESTORE_DATABASE_ROOT_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)"

if 'APP_BASE_URL' not in st.session_state:
    st.session_state['APP_BASE_URL'] = 'https://screenerpro.streamlit.app'

# --- Session Initialization ---
def initialize_session_state():
    defaults = {
        "authenticated": False,
        "username": None,
        "current_page": "Dashboard",
        "sidebar_state": "expanded",
        "activity_log": [],
        "dark_mode_main": False,
        "history_data": [],
        "comprehensive_df": pd.DataFrame()
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

initialize_session_state()

# --- Helper Functions ---
def log_activity_main(message):
    if 'activity_log' not in st.session_state:
        st.session_state.activity_log = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.activity_log.insert(0, f"[{timestamp}] {message}")
    st.session_state.activity_log = st.session_state.activity_log[:50]

# --- Custom Navigation Sidebar ---
def custom_sidebar():
    st.markdown("""
        <div style="font-size: 2rem; font-weight: 800; color: #fff; margin-bottom: 2rem; padding-left: 10px;">
            <span style="color: var(--accent-blue);">🧠</span> Screener Pro
        </div>
    """, unsafe_allow_html=True)
    
    pages = [
        {"name": "Dashboard", "icon": "📊"},
        {"name": "Resume Screener", "icon": "📄"},
        {"name": "Manage JDs", "icon": "💼"},
        {"name": "Screening Analytics", "icon": "📈"},
        {"name": "HR Campaign Creator", "icon": "📢"},
        {"name": "Collaboration Hub", "icon": "🤝"},
        {"name": "Email Candidates", "icon": "✉️"},
        {"name": "Admin Panel", "icon": "🛠️"},
        {"name": "Logout", "icon": "🚪"},
    ]
    
    for page in pages:
        # Style buttons to look like sidebar links
        # We use a unique key for each button
        label = f"{page['icon']}  {page['name']}"
        if st.button(label, key=f"nav_{page['name']}", use_container_width=True):
            if page["name"] == "Logout":
                st.session_state.authenticated = False
                st.session_state.username = None
                st.rerun()
            else:
                st.session_state.current_page = page["name"]
                st.rerun()
                
    st.markdown("---")
    st.markdown(f"<div style='color: #64748b; font-size: 0.8rem; padding: 10px;'>User: {st.session_state.get('username', 'Guest')}</div>", unsafe_allow_html=True)


# --- Main Application Logic ---
def main():
    
    # AUTH CHECK
    if not st.session_state.get("authenticated"):
        # Show Login Section full screen
        login_section()
        return

    # LAYOUT: Custom Sidebar + Content
    # We use columns to simulate sidebar
    col_nav, col_content = st.columns([1, 5])
    
    with col_nav:
        custom_sidebar()
        
    with col_content:
        # Top Header (Optional)
        st.markdown(f"""
        <div class="top-header">
            <div>
                <h1>{st.session_state.current_page}</h1>
                <p style="color: var(--text-secondary); margin-top: -10px;">Overview & Actions</p>
            </div>
            <div class="profile">
                <span>{st.session_state.get('username', '')}</span>
                <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #2563eb, #00f2ff); border-radius: 50%;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Page Routing
        page = st.session_state.current_page
        
        try:
            if page == "Dashboard":
                # Assuming this function needs log callback
                show_authenticated_home_page(log_activity_main)
            elif page == "Resume Screener":
                resume_screener_page()
            elif page == "Manage JDs":
                manage_jds_page()
            elif page == "Screening Analytics":
                # Assuming imported from somewhere, analytics.py usually
                # Need to import it if strictly required, I'll try generic import
                from analytics import analytics_dashboard_page
                analytics_dashboard_page()
            elif page == "HR Campaign Creator":
                hr_campaign_creator_page()
            elif page == "Collaboration Hub":
                 collaboration_hub_page(app_id=FIREBASE_PROJECT_ID, FIREBASE_WEB_API_KEY=FIREBASE_WEB_API_KEY, FIRESTORE_BASE_URL=FIRESTORE_DATABASE_ROOT_URL)
            elif page == "Email Candidates":
                send_email_to_candidate()
            elif page == "Client Portal":
                client_dashboard_page()
            elif page == "Admin Panel":
                # Import here to avoid circular dependencies if any
                from admin_panel import admin_panel_page
                admin_panel_page()
            else:
                st.info(f"Page '{page}' is under construction in this new UI.")
                
        except Exception as e:
            st.error(f"Something went wrong on the {page} page: {e}")

if __name__ == "__main__":
    main()
