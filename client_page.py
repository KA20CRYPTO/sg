import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_lottie import st_lottie
import requests
import uuid
import os
import os
import datetime

from firebase_config import FIRESTORE_DOCUMENTS_URL, FIREBASE_WEB_API_KEY
from firebase_config import (
    FIREBASE_AUTH_SIGNUP_URL,
    FIREBASE_AUTH_SIGNIN_URL,
    FIREBASE_AUTH_RESET_PASSWORD_URL,
)

# ====================================================================
# 🔥 BACKEND IMPORTS (ASSUMED TO BE DEFINED IN YOUR PROJECT)
# ====================================================================
# NOTE: These must be available in your local environment for the code to run fully.
from activation_email import send_activation_email 
from firebase_config import FIRESTORE_DOCUMENTS_URL, FIREBASE_WEB_API_KEY

def show_signup_form():
    st.markdown('<div class="login-card-futuristic">', unsafe_allow_html=True)

    with st.form("signup_form"):
        st.markdown("<h2 style='color:white; text-align:center;'>Create Your Free Account</h2>", unsafe_allow_html=True)

        full_name = st.text_input("Full Name")
        email = st.text_input("Work Email")
        company = st.text_input("Company")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")

        submitted = st.form_submit_button("Create Account")

        if submitted:
            # ---------------- VALIDATION ----------------
            if not full_name or not email or not company or not password or not confirm:
                st.error("All fields are required.")
                return

            if password != confirm:
                st.error("Passwords do not match.")
                return

            # ---------------- FIREBASE AUTH CREATE USER ----------------
            auth_res = requests.post(
                FIREBASE_AUTH_SIGNUP_URL,
                json={"email": email, "password": password, "returnSecureToken": True},
            )

            if auth_res.status_code != 200:
                st.error("Signup failed. Email may already exist.")
                return

            # ---------------- CREATE ACTIVATION TOKEN ----------------
            token = os.urandom(16).hex()

            save_pending_user(
                email,
                {
                    "email": email,
                    "full_name": full_name,   # FIXED FIELD NAME
                    "company": company,
                    "isVerified": False,
                    "activation_token": token,
                    "created_at": datetime.datetime.utcnow().isoformat(),
                },
            )

            # ---------------- CORRECT ACTIVATION URL ----------------
            activation_link = (
                f"https://screenerpro.streamlit.app/?activate={token}&email={email}"
            )

            # ---------------- SEND ACTIVATION EMAIL ----------------
            send_activation_email(
                to_email=email,
                username=full_name,
                activation_link=activation_link
            )

            st.success("🎉 Account created! Check your email to activate.")
            st.stop()

    st.markdown('</div>', unsafe_allow_html=True)



# ====================================================================
# FIXED FIRESTORE HELPERS (REAL IMPLEMENTATION)
# ====================================================================

def firestore_format(data: dict):
    """Formats a Python dict into the required Firestore JSON structure."""
    fields = {}
    for key, value in data.items():
        if isinstance(value, str):
            fields[key] = {"stringValue": value}
        elif isinstance(value, bool):
            fields[key] = {"booleanValue": value}
    return {"fields": fields}


def save_pending_user(email, data):
    """Saves user data to the Firestore 'pending_users' collection."""
    email_doc = email.replace(".", "_").replace("@", "_")
    url = f"{FIRESTORE_DOCUMENTS_URL}/pending_users/{email_doc}?key={FIREBASE_WEB_API_KEY}"
    return requests.patch(url, json=firestore_format(data))


def get_pending_user(email):
    """Retrieves a pending user document from Firestore."""
    email_doc = email.replace(".", "_").replace("@", "_")
    url = f"{FIRESTORE_DOCUMENTS_URL}/pending_users/{email_doc}?key={FIREBASE_WEB_API_KEY}"
    r = requests.get(url)
    return r.json() if r.status_code == 200 else None


def verify_user(email):
    email_doc = email.replace(".", "_").replace("@", "_")
    url = f"{FIRESTORE_DOCUMENTS_URL}/pending_users/{email_doc}?key={FIREBASE_WEB_API_KEY}&updateMask.fieldPaths=isVerified"

    payload = {
        "fields": {
            "isVerified": {"booleanValue": True}
        }
    }

    return requests.patch(url, json=payload)



# ============================================================
# 🎨 LOAD ASSETS (No change here)
# ============================================================

def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except:
        return None


# ============================================================
# 🌈 GLOBAL DESIGN SYSTEM (CSS) - CLEANED UP
# ============================================================

def inject_css():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

            html, body, [class*="css"] {
                font-family: 'Outfit', sans-serif !important;
                background-color: #f3f4f6; 
            }

            .main .block-container {
                padding-top: 4rem; /* Increased top padding since the header is removed */
            }

            /* --- REMOVED STICKY HEADER CSS --- */
            .stApp > header {
                visibility: hidden; /* Hide default Streamlit header */
            }

            /* --- PREMIUM BACKGROUND EFFECT --- */
            .stApp {
                background:
                    radial-gradient(at 0% 0%, rgba(99,102,241,0.1) 0px, transparent 50%),
                    radial-gradient(at 100% 0%, rgba(14,165,233,0.1) 0px, transparent 50%),
                    radial-gradient(at 50% 100%, rgba(236,72,153,0.05) 0px, transparent 50%);
                background-attachment: fixed;
                background-color: #f3f4f6 !important;
            }
            
            /* --- ANIMATIONS --- */
            @keyframes float {
                0% { transform: translateY(0); }
                50% { transform: translateY(-8px); } 
                100% { transform: translateY(0); }
            }
            @keyframes slideUpFade {
                from { opacity: 0; transform: translateY(30px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes pulseShadow {
                0% { box-shadow: 0 0 0 0 rgba(79, 70, 229, 0.4); }
                70% { box-shadow: 0 0 0 10px rgba(79, 70, 229, 0); }
                100% { box-shadow: 0 0 0 0 rgba(79, 70, 229, 0); }
            }

            /* --- ETHEREAL CARD STYLE (Lifted/Sharp Shadow) --- */
            .ethereal-card {
                background: #ffffff; 
                padding: 30px;
                border-radius: 24px; 
                border: 1px solid rgba(226, 232, 240, 0.8); 
                box-shadow: 0 20px 40px -10px rgba(0,0,0,0.1), 0 0 0 1px rgba(255,255,255,0.7) inset; 
                transition: 0.4s cubic-bezier(0.2, 0.8, 0.2, 1); 
                animation: slideUpFade 0.9s ease-out both;
            }

            .ethereal-card:hover {
                transform: translateY(-5px); 
                box-shadow: 0 30px 60px -15px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.8) inset;
            }
            
            /* --- FUTURISTIC BLUE LOGIN CARD STYLE (No Change) --- */
            .login-card-futuristic {
                background: linear-gradient(150deg, #1e3a8a, #3b82f6); 
                padding: 45px 35px;
                border-radius: 30px;
                box-shadow: 0 20px 80px -10px rgba(0, 0, 0, 0.6), 0 0 0 10px rgba(59, 130, 246, 0.35); 
                animation: slideUpFade 1.2s ease-out both;
            }

            /* --- INPUT OVERRIDES (No Change) --- */
            div[data-testid="stTextInput"] input {
                border-radius: 14px; 
                border: 2px solid #e5e7eb; 
                background-color: #ffffff; 
                padding: 16px 20px;
                transition: border-color 0.3s, box-shadow 0.3s;
            }
            div[data-testid="stTextInput"] input:focus {
                border-color: #4f46e5;
                box-shadow: 0 0 0 5px rgba(79, 70, 229, 0.25); 
            }
            
            /* --- HERO BUTTON STYLE (3D Pressable Effect) --- */
            .btn-hero-3d > button {
                width: auto;
                background: linear-gradient(145deg, #4f46e5, #4338ca);
                color: white !important;
                border: none;
                padding: 20px 45px; 
                border-radius: 18px; 
                font-weight: 900;
                font-size: 1.2rem;
                transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 7px 0 0 #3730a3; 
                animation: pulseShadow 2s infinite; 
            }

            .btn-hero-3d > button:hover {
                transform: translateY(-2px); 
                box-shadow: 0 9px 0 0 #3730a3;
                background: linear-gradient(145deg, #4338ca, #4f46e5); 
                animation: none;
            }

            .btn-hero-3d > button:active {
                transform: translateY(3px); 
                box-shadow: 0 2px 0 0 #3730a3;
            }
            
            /* --- FUTURISTIC FORM BUTTON STYLE (Sign Up) --- */
            .login-card-futuristic div.stButton > button {
                width: 100%;
                padding: 18px 20px;
                border-radius: 18px; 
                background: linear-gradient(135deg, #f59e0b, #d97706); 
                color: #1e3a8a !important; 
                font-weight: 800;
                font-size: 1.2rem;
                border: none;
                box-shadow: 0 10px 20px rgba(245, 158, 11, 0.4); 
            }

            /* --- REVIEW SECTION ENHANCEMENT --- */
            .review-title {
                font-size: 2.8rem; /* Much larger title */
                font-weight: 900;
                color: #1e293b;
                text-align: center;
                margin-top: 2rem;
                padding-bottom: 0.5rem;
                border-bottom: 4px solid #4f46e5; /* Strong blue anchor line */
                display: inline-block;
                width: auto;
                max-width: 100%;
            }

        </style>
    """, unsafe_allow_html=True)

# ❌ REMOVED: This function is now completely removed as requested.
def show_sticky_header():
    """Removes the fixed header component."""
    # The header is implicitly removed by hiding the default Streamlit header in inject_css()
    # and not inserting a replacement component.
    pass 


# ============================================================
# FIXED ACTIVATION HANDLER (Using real Firestore getter)
def handle_activation():
    qp = st.query_params.to_dict()

    if "activate" not in qp or "email" not in qp:
        return False

    token = qp["activate"]
    email = qp["email"]

    user = get_pending_user(email)
    if not user:
        st.error("❌ Invalid or expired activation link.")
        return True

    stored_token = user.get("fields", {}).get("activation_token", {}).get("stringValue")
    if stored_token != token:
        st.error("❌ Activation failed. Token mismatch.")
        return True

    verify_user(email)
    st.success("🎉 Your account is now activated! You can now log in.")
    return True


def show_landing_page():
    
    anim_hero = load_lottieurl("https://assets7.lottiefiles.com/packages/lf20_qcrx8q4e.json") 

    # --- 1. HERO SECTION (Content + Form) ---
    c1, c2 = st.columns([1.4, 1])

    with c1:
        st.markdown("""
            <div style="padding-top:20px;">
                <h1 style="font-size:5.5rem; font-weight:900; line-height:1.0; letter-spacing:-3px;">
                    AI Talent Scoring,<br>
                    <span style="background:linear-gradient(135deg,#6366f1,#0ea5e9);
                    -webkit-background-clip:text; color:transparent;">
                        Unlocking Potential.
                    </span>
                </h1>
                <p style="font-size:1.5rem; color:#475569; line-height:1.5; font-weight:400;">
                    Eliminate bias and hire the **top 1%** faster than ever. Zero manual resume screen time required.
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        # Wrapped button in the new 3D class
        st.markdown('<div class="btn-hero-3d">', unsafe_allow_html=True)
        if st.button("🚀 Start Free Pilot", key="hero_pilot"):
            st.session_state["show_form"] = True
            st.rerun() 
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)


    with c2:
        if st.session_state.get("show_form"):
            show_signup_form()
        else:
            st.markdown('<div style="animation:float 6s infinite; padding-top: 30px;">', unsafe_allow_html=True)
            if anim_hero:
                st_lottie(anim_hero, height=400)
            st.markdown("</div>", unsafe_allow_html=True)
        
    st.markdown("---") 
    
    # --- 2. METRICS SECTION (No structural change) ---
    m1, m2, m3, m4 = st.columns(4)
    metrics = [("473k+", "Resumes Processed"), ("4.9/5", "Client Satisfaction"),
               ("95%", "Time Reduction"), ("15x+", "ROI Guaranteed")]
    
    for col, (v, l) in zip([m1, m2, m3, m4], metrics):
        with col:
            st.markdown(
                f"""
                <div class="ethereal-card" style="text-align:center; padding: 25px;">
                    <div style="font-size:3.0rem; font-weight:900; color:#1e293b; line-height:1.2;">{v}</div>
                    <div style="color:#64748b; font-weight:500;">{l}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---") 

    # --- 3. CHART & FEATURES SECTION (No structural change) ---
    col_chart, col_feat = st.columns([1.6, 1])

    with col_chart:
        st.markdown('<div class="ethereal-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='font-weight:800; color:#1e293b; margin-bottom:1.5rem;'>Hiring Velocity Comparison (Days)</h3>", unsafe_allow_html=True)
        df = pd.DataFrame({
            "Stage": ["Resume Review", "Phone Screen", "Assignment", "Offer"],
            "Traditional": [12, 5, 7, 3],
            "Screener Pro AI": [0.2, 1, 3, 1] 
        })
        fig = px.bar(
            df, x="Stage", y=["Traditional", "Screener Pro AI"],
            barmode="group",
            color_discrete_map={"Traditional": "#e2e8f0", "Screener Pro AI": "#4f46e5"}
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=350,
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor='#e5e7eb') 
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_feat:
        st.markdown("<h3 style='font-weight:800; color:#1e293b; margin-top:0;'>Core AI Advantages</h3>", unsafe_allow_html=True)
        features = [
            ("🧠", "Hyper-Accurate Screening", "AI ranks candidates based on skill fit and cognitive alignment."),
            ("🗓️", "Intelligent Scheduling", "Automated interview booking across global timezones."),
            ("🛡️", "Zero-Bias Review", "Anonymized candidate profiles ensure objective decision-making.")
        ]
        
        for icon, title, desc in features:
            st.markdown(
                f"""
                <div class="ethereal-card" style="margin-bottom:15px; padding:20px; cursor:pointer;">
                    <div style="display:flex; gap:15px; align-items:center;">
                        <div style="font-size:26px; width:45px; height:45px; display:flex; 
                                    align-items:center; justify-content:center; 
                                    background:linear-gradient(135deg, #e0f2fe, #bfdbfe); 
                                    border-radius:12px; box-shadow:0 5px 15px rgba(59,130,246,0.15);">
                            {icon}
                        </div>
                        <div>
                            <strong style="font-size:1.1rem; color:#1e293b; font-weight:700;">{title}</strong>
                            <p style="color:#64748b; font-size:0.95rem; margin:0; line-height:1.3;">{desc}</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---") 
    
    # --- 4. CLIENT STORIES SECTION (Review title enhanced) ---
    st.markdown('<div style="text-align:center;">', unsafe_allow_html=True)
    st.markdown('<h2 class="review-title">Client Success Stories</h2>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    t1, t2, t3 = st.columns(3)
    stories = [
        ("CG", "Chetan Garg, CEO", "Envirotech Instruments", "AI saved us hundreds of hours and improved quality. We hired 4 senior engineers in 3 weeks. ⭐⭐⭐⭐⭐", "#2563eb"),
        ("JD", "Jane Doe, Head of HR", "Innovatech", "Cut hiring time by 60%. Essential for scaling rapidly without losing talent quality. ⭐⭐⭐⭐⭐", "#7c3aed"),
        ("RS", "Rohit Sharma, VP of Eng.", "NextGen Tech", "Smart, fast and accurate. The best screening tool we've used—our technical hires are stronger than ever. ⭐⭐⭐⭐⭐", "#059669")
    ]
    for col, (init, name, org, review, color) in zip([t1, t2, t3], stories):
        with col:
            st.markdown(
                f"""
                <div class="ethereal-card" style="min-height:240px; padding:25px;">
                    <p style="font-size:1.05rem; color:#1e293b; font-style:italic; line-height:1.5;">"{review}"</p>
                    <div style="display:flex;align-items:center;margin-top:20px;">
                        <div style="width:55px;height:55px;background:{color};border-radius:50%;
                                     display:flex;align-items:center;justify-content:center;
                                     color:white;font-weight:700; font-size:1.3rem;
                                     box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
                            {init}
                        </div>
                        <div style="margin-left:15px;">
                            <strong style="color:#1e293b; font-size:1.05rem;">{name}</strong><br>
                            <span style="color:#64748b;font-size:0.9rem;">{org}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ============================================================
# MAIN ROUTER 
# ============================================================

def client_dashboard_page():
    
    if "show_form" not in st.session_state:
        st.session_state["show_form"] = False
    
    st.set_page_config(page_title="AI Hiring Platform", layout="wide")
    
    inject_css()
    show_sticky_header() # Now an empty function, but called for consistency

    if handle_activation():
        return

    show_landing_page()


# ============================================================

if __name__ == "__main__":
    client_dashboard_page()
