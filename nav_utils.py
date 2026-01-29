import streamlit as st
import os

def load_unified_css():
    """Injects global styles and hides default navigation."""
    css_file = "style.css"
    if not os.path.exists(css_file):
        css_file = "../style.css"
        
    try:
        with open(css_file) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except:
        pass
    
    # Force hide default sidebar nav and header elements
    st.markdown("""
        <style>
        [data-testid="stSidebarNav"] {display: none !important;}
        .stRadio div[role="radiogroup"] label span:first-child {
            display: none !important;
        }
        .stRadio div[role="radiogroup"] label {
            margin-bottom: 5px !important;
        }
        </style>
    """, unsafe_allow_html=True)

def render_universal_sidebar(active_page, extra_content_callback=None):
    """Renders the branded sidebar with synchronized navigation."""
    with st.sidebar:
        # Standard Branding
        st.image("https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhhq_OCSv-QmuBjXeRQXr60EfsvVA4chRPCNslo3NhjVQkoKjUtiRfTPpGoQjyQXS7sMsJifQC6Yq34cAhNbq9lMwBXZqIIbCij1adyXSuNoyxuzOTDfrPU2dnna0baimldd7Y1KCkvaAfrWC1yLGxp25SJ9s4exJ-JAc8kNcTyUSgkLWbW2DdvhpWH4GlO/s578/logo.png", width=150)
        st.title("🧠 ScreenerPro")
        
        # Public Navigation Master List
        nav_options = [
            "Home",
            "Login / Register",
            "Public Job Board",
            "ScreenerPro Insights",
            "Certificate Verification",
            "Our Clients",
            "Partner With Us",
            "About Us",
            "Privacy Policy & Terms",
            "Feedback & Help"
        ]
        
        # Map labels to page files
        page_map = {
            "Home": "landing.py", # Entry page
            "Login / Register": "pages/authentication.py",
            "Public Job Board": "pages/job_board.py",
            "ScreenerPro Insights": "pages/insights.py",
            "Certificate Verification": "pages/cert_verify.py",
            "Our Clients": "pages/clients.py",
            "Partner With Us": "pages/partner.py",
            "About Us": "pages/about.py",
            "Privacy Policy & Terms": "pages/privacy.py",
            "Feedback & Help": "pages/feedback_help.py",
            "Dashboard": "pages/dashboard.py" # Authenticated target
        }

        try:
            default_index = nav_options.index(active_page)
        except ValueError:
            default_index = 0

        selected = st.radio(
            "📍 Select Page",
            nav_options,
            index=default_index,
            key="universal_nav_radio"
        )
        
        # Navigation Logic
        if selected != active_page:
            target_file = page_map.get(selected)
            
            # Special case for session-state internal tabs
            if selected in ["Certificate Verification", "Our Clients", "Partner With Us", "About Us", "Privacy Policy & Terms", "Feedback & Help"]:
                st.session_state.current_page = selected
            elif selected == "Login / Register":
                st.session_state.current_page = "Login / Register"

            if target_file:
                # Handle potential path differences if running from pages/ or root
                if "pages/" in target_file and os.getcwd().endswith("pages"):
                     target_file = target_file.replace("pages/", "")
                
                try:
                    st.switch_page(target_file)
                except Exception as e:
                    # Fallback for root file from within pages/
                    if "/" not in target_file:
                        st.switch_page(target_file)
                    else:
                        st.error(f"Could not switch to {target_file}")
            st.rerun()

        st.markdown("---")
        
        if extra_content_callback:
            return extra_content_callback()
        
        return None
