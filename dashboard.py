import streamlit as st
import json
import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import plotly.express as px
import statsmodels.api as sm
import collections
import requests
import io
from wordcloud import WordCloud
import streamlit.components.v1 as components
from nav_utils import load_unified_css, render_universal_sidebar
# Import admin panel (FULL MODULE)
#from admin_panel import admin_panel_page
from activation_email import send_activation_email
import base64
import requests
from admin_user_manager import admin_user_manager
from employee_management import employee_management_page
from payroll_management import payroll_management_page
from firebase_config import (
    FIRESTORE_DOCUMENTS_URL,
    FIREBASE_WEB_API_KEY,
    FIREBASE_AUTH_SIGNUP_URL,
    FIREBASE_AUTH_SIGNIN_URL,
    FIREBASE_AUTH_RESET_PASSWORD_URL,
)
from login import force_password_change_screen
import requests

# Pages allowed for unauthenticated users
PUBLIC_ALLOWED = [
    "Home", "Login / Register", "Public Job Board", "ScreenerPro Insights",
    "Certificate Verification", "Our Clients", "Partner With Us", "About Us",
    "Privacy Policy & Terms", "Feedback & Help"
]

if st.session_state.get("force_password_change"):
    force_password_change_screen()
    st.stop()

def save_pending_user(email, data):
    email_doc = email.replace(".", "_").replace("@", "_")
    url = f"{FIRESTORE_DOCUMENTS_URL}/pending_users/{email_doc}?key={FIREBASE_WEB_API_KEY}"

    firestore_payload = to_firestore_format(data)

    return requests.patch(url, json=firestore_payload)

def image_file_to_base64(uploaded_file):
    if uploaded_file is None:
        return None
    return base64.b64encode(uploaded_file.read()).decode("utf-8")
def get_same_company_users(company_name: str):
    if not company_name:
        return []

    url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents:runQuery?key={FIREBASE_WEB_API_KEY}"

    query = {
        "structuredQuery": {
            "from": [{"collectionId": "user_profiles"}],
            "where": {
                "fieldFilter": {
                    "field": {"fieldPath": "company"},
                    "op": "EQUAL",
                    "value": {"stringValue": company_name}
                }
            }
        }
    }

    res = requests.post(url, json=query)
    users = []

    if res.status_code == 200:
        for item in res.json():
            if "document" in item:
                users.append(from_firestore_format(item["document"]))

    return users



def image_url_to_base64(url):
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return base64.b64encode(res.content).decode("utf-8")
    except Exception:
        pass
    return None
 
def edit_profile_modal():
    # 🔐 Auth guard
    if not st.session_state.get("authenticated", False):
        return

    if not st.session_state.get("show_profile_modal", False):
        return

    with st.expander("👤 Edit Profile", expanded=True):

        uid = st.session_state.get("user_uid")
        email = st.session_state.get("username", "")

        # Existing fields
        full_name = st.session_state.get("user_full_name", "")
        company = st.session_state.get("user_company", "")
        phone = st.session_state.get("user_phone", "")
        role = st.session_state.get("user_role", "")

        # 🆕 New fields
        department = st.session_state.get("user_department", "")
        location = st.session_state.get("user_location", "")
        linkedin = st.session_state.get("user_linkedin", "")
        experience_years = st.session_state.get("user_experience_years", "")
        bio = st.session_state.get("user_bio", "")

        avatar_base64 = st.session_state.get("user_avatar_base64")
        

        col1, col2 = st.columns(2)

        with col1:
            new_full_name = st.text_input("Full Name", full_name)
            new_company = st.text_input("Company Name", company)
            new_department = st.text_input("Department", department)
            new_location = st.text_input("Location", location)

        with col2:
            new_phone = st.text_input("Phone", phone)
            new_role = st.text_input("Role / Designation", role)
            new_linkedin = st.text_input("LinkedIn Profile", linkedin)
            new_experience_years = st.number_input(
                "Experience (Years)", min_value=0, max_value=50,
                value=int(experience_years or 0)
            )

        new_bio = st.text_area("About You", bio, height=100)

        st.text_input("Email", email, disabled=True)

        col_save, col_cancel = st.columns(2)

        with col_save:
            if st.button("💾 Save Changes", key="save_profile_modal"):
                # Update session
                st.session_state.user_full_name = new_full_name
                st.session_state.user_company = new_company
                st.session_state.user_phone = new_phone
                st.session_state.user_role = new_role
                st.session_state.user_department = new_department
                st.session_state.user_location = new_location
                st.session_state.user_linkedin = new_linkedin
                st.session_state.user_experience_years = new_experience_years
                st.session_state.user_bio = new_bio

                # Save to Firestore
                save_profile_to_firestore(
                    uid=uid,
                    email=email,
                    full_name=new_full_name,
                    company=new_company,
                    phone=new_phone,
                    role=new_role,
                    department=new_department,
                    location=new_location,
                    linkedin=new_linkedin,
                    experience_years=new_experience_years,
                    bio=new_bio,
                    avatar_base64=avatar_base64,
                )

                st.session_state.show_profile_modal = False
                st.rerun()

        with col_cancel:
            if st.button("❌ Cancel", key="cancel_profile_modal"):
                st.session_state.show_profile_modal = False
                st.rerun()

def edit_profile_page():
    if not st.session_state.get("authenticated"):
        st.warning("Please login to access your profile.")
        return

    uid = st.session_state.get("user_uid")
    email = st.session_state.get("username")
    is_company_admin = st.session_state.get("is_company_admin", False)

    # ==================================================
    # 🧭 PAGE HEADER
    # ==================================================
    st.markdown("## 👤 Profile & Organization")
    st.caption("Your identity • Your role • Your company")
    st.divider()

    # ==================================================
    # 📊 PROFILE HEALTH SCORE
    # ==================================================
    fields = {
        "Name": st.session_state.get("user_full_name"),
        "Phone": st.session_state.get("user_phone"),
        "Role": st.session_state.get("user_role"),
        "Department": st.session_state.get("user_department"),
        "Bio": st.session_state.get("user_bio"),
        "Avatar": st.session_state.get("user_avatar_base64"),
    }

    filled = sum(bool(v) for v in fields.values())
    score = int((filled / len(fields)) * 100)

    st.progress(score)
    st.caption(f"Profile strength: **{score}%**")

    if score < 60:
        st.warning("Complete your profile to improve collaboration visibility.")
    elif score < 90:
        st.info("Almost there! A few more details will complete your profile.")
    else:
        st.success("Excellent! Your profile is fully optimized.")

    st.divider()

    # ==================================================
    # 🧾 MAIN PROFILE FORM
    # ==================================================
    col_left, col_right = st.columns([3, 1.5])

    with col_left:
        st.subheader("🧾 Personal Details")

        full_name = st.text_input(
            "Full Name",
            st.session_state.get("user_full_name", ""),
            placeholder="e.g. Kaaysha Rao"
        )

        phone = st.text_input(
            "Phone Number",
            st.session_state.get("user_phone", ""),
            placeholder="+91 XXXXX XXXXX"
        )

        st.text_input("Email Address", email, disabled=True)
        st.divider()

        st.subheader("🏢 Organization")

        # 🔒 Company is ALWAYS locked
        company = st.text_input(
            "Company",
            st.session_state.get("user_company", ""),
            disabled=True,
            help="Company is locked and controlled by admins"
        )

        # 👑 Role / Dept editable ONLY by company admin
        if is_company_admin:
            role = st.selectbox(
                "Role",
                ["hr", "recruiter", "manager", "viewer"],
                index=(
                    ["hr", "recruiter", "manager", "viewer"]
                    .index(st.session_state.get("user_role"))
                    if st.session_state.get("user_role") in
                    ["hr", "recruiter", "manager", "viewer"]
                    else 0
                )
            )
            department = st.text_input(
                "Department",
                st.session_state.get("user_department", "")
            )
        else:
            role = st.session_state.get("user_role", "")
            department = st.session_state.get("user_department", "")

            st.text_input("Role", role, disabled=True)
            st.text_input("Department", department, disabled=True)

        bio = st.text_area(
            "Professional Summary",
            st.session_state.get("user_bio", ""),
            height=120,
            placeholder="Brief description about you"
        )

    # ==================================================
    # 🖼 PROFILE PHOTO
    # ==================================================
    with col_right:
        st.subheader("🖼 Profile Image")

        avatar_base64 = st.session_state.get("user_avatar_base64")

        if avatar_base64:
            st.image(
                f"data:image/png;base64,{avatar_base64}",
                width=160
            )
        else:
            initials = full_name[:1].upper() if full_name else "👤"
            st.markdown(
                f"<div style='font-size:64px;text-align:center'>{initials}</div>",
                unsafe_allow_html=True
            )

        upload = st.file_uploader(
            "Upload Image",
            type=["png", "jpg", "jpeg"]
        )

        image_url = st.text_input("Or paste image URL")

        if upload:
            avatar_base64 = image_file_to_base64(upload)
        elif image_url:
            avatar_base64 = image_url_to_base64(image_url)

    # ==================================================
    # 💾 SAVE ACTION (SAFE)
    # ==================================================
    st.divider()
    col_save, col_reset = st.columns(2)

    with col_save:
        if st.button("💾 Save Profile", type="primary", use_container_width=True):
            if not full_name.strip():
                st.error("Full name is required.")
                return

            # 🔐 Update SESSION (NO ADMIN FLAGS TOUCHED)
            st.session_state.user_full_name = full_name
            st.session_state.user_phone = phone
            st.session_state.user_role = role
            st.session_state.user_department = department
            st.session_state.user_bio = bio
            st.session_state.user_avatar_base64 = avatar_base64

            # 🔒 Save ONLY profile-safe fields
            save_profile_to_firestore(
                uid=uid,
                email=email,
                full_name=full_name,
                company=company,
                phone=phone,
                role=role,
                department=department,
                location=st.session_state.get("user_location", ""),
                linkedin=st.session_state.get("user_linkedin", ""),
                experience_years=st.session_state.get("user_experience_years", 0),
                bio=bio,
                avatar_base64=avatar_base64,
            )

            st.success("✅ Profile saved successfully")
            st.rerun()

    with col_reset:
        if st.button("↺ Reset Changes", use_container_width=True):
            st.rerun()

    # ==================================================
    # 👥 COMPANY DIRECTORY (READ-ONLY)
    # ==================================================
    st.divider()
    st.subheader("👥 Company Directory")
    st.caption("People associated with your organization (read-only)")

    company_name = (company or "").strip()
    if not company_name:
        st.info("Company name is not set. Add it to view team members.")
        return

    users = get_same_company_users(company_name)

    # Remove current user from list
    users = [
        u for u in users
        if u.get("email") != email
    ]

    if not users:
        st.info("No other users are registered under this company yet.")
        return

    # 🔍 Search & overview
    col_search, col_count = st.columns([3, 1])
    with col_search:
        search = st.text_input(
            "🔍 Search team members",
            placeholder="Search by name, email, role, or department"
        )
    with col_count:
        st.metric("Total Members", len(users))

    if search:
        search_lower = search.lower()
        users = [
            u for u in users
            if search_lower in (
                f"{u.get('full_name','')}"
                f"{u.get('email','')}"
                f"{u.get('role','')}"
                f"{u.get('department','')}"
            ).lower()
        ]

    if not users:
        st.warning("No matching members found.")
        return

    # ==================================================
    # 👤 USER DETAILS (CLEAN, READABLE)
    # ==================================================
    for user in users:
        with st.container(border=True):
            col_avatar, col_main, col_meta = st.columns([1, 4, 3])

            # Avatar or initials
            avatar = user.get("avatar_base64")
            if avatar:
                col_avatar.image(
                    f"data:image/png;base64,{avatar}",
                    width=48
                )
            else:
                initials = (
                    user.get("full_name", "U")[:1].upper()
                )
                col_avatar.markdown(
                    f"<div style='font-size:32px;text-align:center'>{initials}</div>",
                    unsafe_allow_html=True
                )

            # Main identity info
            col_main.markdown(
                f"**{user.get('full_name', 'Unknown User')}**"
            )
            col_main.caption(user.get("email", "—"))

            # Metadata (text-only, no badges)
            col_meta.markdown(
                f"""
                **Role:** {user.get('role', 'Not specified')}  
                **Department:** {user.get('department', 'Not specified')}  
                **Phone:** {user.get('phone') or 'Not provided'} 
                **Location:** {user.get('location', 'Not specified')}
                """
            )

            # Optional bio / summary
            bio = user.get("bio", "")
            if bio:
                st.markdown("**About:**")
                st.write(bio)


def save_profile_to_firestore(
    uid,
    email,
    full_name,
    company,
    phone,
    role,
    department,
    location,
    linkedin,
    experience_years,
    bio,
    avatar_base64,
):
    if not uid:
        st.error("UID missing")
        return

    url = (
        f"{FIRESTORE_DATABASE_ROOT_URL}/documents/user_profiles/{uid}"
        f"?key={FIREBASE_WEB_API_KEY}"
    )

    # 🔒 PRESERVE ADMIN FLAG
    is_company_admin = st.session_state.get("is_company_admin", False)

    payload = {
        "uid": uid,
        "email": email,
        "full_name": full_name,
        "company": company,
        "phone": phone,
        "role": role,
        "department": department,
        "location": location,
        "linkedin": linkedin,
        "experience_years": int(experience_years or 0),
        "bio": bio,
        "avatar_base64": avatar_base64 or "",
        "is_company_admin": is_company_admin,   # ✅ CRITICAL
        "updated_at": datetime.utcnow().isoformat(),
    }

    firestore_payload = {
        "fields": {
            k: (
                {"booleanValue": v} if isinstance(v, bool)
                else {"integerValue": str(v)} if isinstance(v, int)
                else {"stringValue": str(v)}
            )
            for k, v in payload.items()
        }
    }

    # # 🔍 DEBUG
    # st.write("📤 Saving profile (admin preserved):", payload)

    res = requests.patch(url, json=firestore_payload)

    if res.status_code not in (200, 201):
        st.error("❌ Failed to save profile")
        st.write(res.text)
    else:
        st.success("✅ Profile saved (admin preserved)")





import streamlit.components.v1 as components

import streamlit.components.v1 as components



def render_minimal_header():
    if not st.session_state.get("authenticated"):
        return

    email = st.session_state.get("username", "")
    page = st.session_state.get("current_page", "Dashboard")
    avatar_base64 = st.session_state.get("user_avatar_base64")

    initials = "👤"
    if email:
        parts = email.split("@")[0].split(".")
        initials = "".join(p[0].upper() for p in parts[:2])

    avatar_html = (
        f"<img src='data:image/png;base64,{avatar_base64}' class='sp-avatar-img'/>"
        if avatar_base64
        else f"<div class='sp-avatar'>{initials}</div>"
    )

    html_code = """
<style>
/* Disable Streamlit header click interception */
header[data-testid="stHeader"],
div[data-testid="stToolbar"] {
    pointer-events: none !important;
}

/* NAVBAR */
.sp-navbar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 64px;
    background: linear-gradient(90deg, #1e3a8a, #2563eb);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    color: white;
    z-index: 999999;
    font-family: Inter, sans-serif;
    pointer-events: auto;
}

.sp-left {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 18px;
    font-weight: 700;
}

.sp-right {
    display: flex;
    align-items: center;
    gap: 14px;
    position: relative;
    cursor: pointer;
}

.sp-avatar, .sp-avatar-img {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: rgba(255,255,255,0.25);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
}

.sp-avatar-img {
    object-fit: cover;
    border: 2px solid rgba(255,255,255,0.4);
}

/* DROPDOWN */
.sp-dropdown {
    position: absolute;
    top: 54px;
    right: 0;
    background: white;
    color: #111;
    border-radius: 10px;
    width: 180px;
    box-shadow: 0 15px 40px rgba(0,0,0,0.15);
    display: none;
    overflow: hidden;
}

.sp-dropdown a {
    display: block;
    padding: 12px 16px;
    text-decoration: none;
    color: #111;
    font-size: 14px;
}

.sp-dropdown a:hover {
    background: #f1f5f9;
}
</style>

<div class="sp-navbar">
    <div class="sp-left">
        <img src="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhhq_OCSv-QmuBjXeRQXr60EfsvVA4chRPCNslo3NhjVQkoKjUtiRfTPpGoQjyQXS7sMsJifQC6Yq34cAhNbq9lMwBXZqIIbCij1adyXSuNoyxuzOTDfrPU2dnna0baimldd7Y1KCkvaAfrWC1yLGxp25SJ9s4exJ-JAc8kNcTyUSgkLWbW2DdvhpWH4GlO/s320/logo.png"
             height="34"/>
        <span>{PAGE}</span>
    </div>

    <div class="sp-right" onclick="toggleDropdown(event)">
        <span style="font-size:13px;">{EMAIL}</span>
        {AVATAR}

        <div class="sp-dropdown" id="spDropdown">
            <a href="#" onclick="goProfile()">👤 Edit Profile</a>
            <a href="#" onclick="doLogout()">🚪 Logout</a>
        </div>
    </div>
</div>

<script>
function toggleDropdown(e) {
    e.stopPropagation();
    const d = document.getElementById("spDropdown");
    d.style.display = d.style.display === "block" ? "none" : "block";
}

document.addEventListener("click", () => {
    const d = document.getElementById("spDropdown");
    if (d) d.style.display = "none";
});

function goProfile() {
    window.parent.postMessage({ type: "streamlit:setProfile" }, "*");
}

function doLogout() {
    window.parent.postMessage({ type: "streamlit:logout" }, "*");
}
</script>
"""

    # SAFE VARIABLE INSERT (NO f-string CSS)
    html_code = (
        html_code
        .replace("{EMAIL}", email)
        .replace("{PAGE}", page)
        .replace("{AVATAR}", avatar_html)
    )

    components.html(html_code, height=64)

def profile_page():
    st.header("👤 Edit Profile")

    avatar = st.file_uploader("Upload Avatar", type=["png", "jpg", "jpeg"])
    full_name = st.text_input("Full Name", st.session_state.get("user_full_name", ""))
    company = st.text_input("Company", st.session_state.get("user_company", ""))

    if st.button("Save"):
        st.session_state.user_full_name = full_name
        st.session_state.user_company = company
        st.success("Profile updated")

def show_public_home_page():
    """
    Displays the public home page, converting the feature cards 
    to native Streamlit columns for guaranteed rendering.
    """

    # 1. --- STYLES (Kept for background and card styling) ---
    st.markdown("""
    <style>
    /* === GLOBAL STYLES & BACKGROUND (LIGHT MODE) === */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #ffffff 0%, #f7f9fc 100%) !important;
        color: #2d3436 !important;
        font-family: 'Inter', sans-serif;
        padding-top: 1rem;
    }
    [data-testid="stHeader"], [data-testid="stToolbar"] {
        background: rgba(255,255,255,0.6) !important;
        backdrop-filter: blur(10px);
    }
    /* Re-purposing feature card CSS for st.container */
    .stContainer {
        border-radius: 20px !important;
        padding: 1.8rem !important;
        transition: transform 0.3s ease, box-shadow 0.3s ease !important;
        box-shadow: 0 6px 18px rgba(0,0,0,0.08) !important;
        border: 1px solid rgba(0,0,0,0.05) !important;
        background: #ffffff !important;
        height: 100%; /* Important for equal height in columns */
    }
    .stContainer:hover {
        transform: translateY(-6px) !important;
        box-shadow: 0 18px 35px rgba(0,0,0,0.15) !important;
    }
    .feature-icon-style {
        color: #0ea5e9;
        font-size: 2.2rem;
        margin-bottom: 0.8rem;
        display: block; /* Ensure the icon sits on its own line */
    }
    
    /* === HERO SECTION STYLING (Unchanged for layout/animation) === */
    .hero-box {
        text-align: center;
        padding: 3.5rem 1.5rem;
        border-radius: 24px;
        backdrop-filter: blur(15px);
        background: rgba(255, 255, 255, 0.9);
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        max-width: 1000px;
        margin: 3rem auto 2.5rem;
        border: 1px solid rgba(0,0,0,0.05);
    }
    @keyframes typing-anim { 0% { width: 0 } 50% { width: 100% } 100% { width: 0 } }
    @keyframes caret-blink { from, to { border-color: transparent } 50% { border-color: #0ea5e9 } }
    .typing-tagline {
        font-size: 2.8rem;
        font-weight: 800;
        color: #0ea5e9;
        white-space: nowrap;
        overflow: hidden;
        border-right: 3px solid #0ea5e9;
        width: 0;
        margin: 1rem auto 2rem;
        animation: typing-anim 5s steps(32, end) infinite, caret-blink 0.75s step-end infinite;
    }
    .hero-subtext {
        font-size: 1.1rem;
        color: #4b5563;
        max-width: 800px;
        margin: 0 auto 1.5rem;
        line-height: 1.8;
    }
    /* === ABOUT SECTION STYLING === */
    .about-section {
        margin-top: 4rem;
        text-align: center;
        padding: 3rem 1rem;
        background: #f0f4f8;
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True) 

    # 2. --- HERO SECTION (Content from the last robust version) ---
    st.markdown(
        """
        <div style="text-align:center; padding-top: 2rem;">
            <img src="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhhq_OCSv-QmuBjXeRQXr60EfsvVA4chRPCNslo3NhjVQkoKjUtiRfTPpGoQjyQXS7sMsJifQC6Yq34cAhNbq9lMwBXZqIIbCij1adyXSuNoyxuzOTDfrPU2dnna0baimldd7Y1KCkvaAfrWC1yLGxp25SJ9s4exJ-JAc8kNcTyUSgkLWbW2DdvhpWH4GlO/s320/logo.png" width="100">
        </div>

        <div class="hero-box">
            <h1 style="font-size: 2.2rem; color: #1f2937; font-weight: 700; margin-bottom: 0.5rem;">
                The Future of Hiring Intelligence
            </h1>
            <div class="typing-tagline">Welcome to ScreenerPro</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    with st.container():
        st.markdown(
            """
            <p class="hero-subtext">
                ScreenerPro is a hiring intelligence platform designed to help organizations
                screen resumes efficiently, evaluate candidates objectively, and manage
                recruitment workflows at scale. Our platform combines structured data analysis
                with automation to reduce manual effort while maintaining transparency and
                fairness throughout the hiring process.
            </p>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        if st.button("Get Started Today", type="primary", use_container_width=False):
            st.info("Initiating onboarding workflow...")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)


    # 3. --- FEATURES SECTION (NOW USING NATIVE st.columns and st.container) ---
    st.header("🔑 Key Features", anchor=False, divider='blue')
    st.markdown(
        """
        <p style="text-align: center; color: #6b7280; font-size: 1.05rem; margin-bottom: 2rem;">
            A suite of tools designed for modern recruitment efficiency.
        </p>
        """,
        unsafe_allow_html=True
    )

    # Define features data to make the creation process clean
    features_data = [
        ("✨", "Intelligent Screening", "Automatically evaluate resumes against job requirements using structured, data-driven relevance scoring."),
        ("📊", "Candidate Analytics", "Gain clear insights into skills, experience alignment, and qualification coverage through visual reports."),
        ("⚙️", "Configurable Rules", "Define role-specific criteria like minimum scores, experience ranges, academic thresholds, and skill filters."),
        ("📢", "Public Job Listings", "Publish job openings publicly and route applications directly into the automated screening workflow."),
        ("🏆", "Verifiable Certificates", "Generate verifiable certificates for candidates with public validation support for authenticity."),
        ("📁", "Bulk Processing", "Upload large resume sets in ZIP format and process hundreds of applications within seconds."),
    ]

    # Use 3 columns per row
    cols = st.columns(3)
    
    for i, (icon, title, desc) in enumerate(features_data):
        with cols[i % 3]: # Cycle through the 3 columns
            # Use st.container to apply the 'feature-card' styling via the CSS selector
            with st.container(border=False): 
                st.markdown(f"<span class='feature-icon-style'>{icon}</span>", unsafe_allow_html=True)
                st.subheader(title, anchor=False)
                st.write(desc)


    # 4. --- ABOUT SECTION (Unchanged) ---
    st.markdown("---") 
    st.markdown(
        """
        <div class="about-section">
            <h2 style="font-size: 1.9rem; font-weight: 700; color: #0ea5e9; margin-bottom: 1rem;">
                Our Mission
            </h2>
            <p style="color:#4b5563; font-size:1.05rem; max-width:800px; margin:auto; line-height:1.7;">
                ScreenerPro is built to support hiring teams with structured intelligence and
                automation. Our objective is to **reduce bias**, **improve efficiency**, and allow
                recruiters to focus on informed decision-making rather than manual screening tasks.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    
# To run this function, make sure you call it in your Streamlit app:
# show_public_home_page_native_features()
def set_body_class():
    """
    Sets a class on the body element to force light mode styling.
    This function is kept for consistency but the main CSS is now inline.
    """
    body_class = "light-mode"
    js_code = f"""
    <script>
        var body = window.parent.document.querySelector('body');
        if (body) {{
            body.className = '';
            body.classList.add('{body_class}');
            body.setAttribute('data-theme', 'light');
        }}
    </script>
    """
    st.markdown(js_code, unsafe_allow_html=True)

from hr_campaign_creator import get_docs_from_firestore_rest
if "history_data" not in st.session_state:
    st.session_state.history_data = []
@st.cache_data(ttl=60)
def cached_get_applications(campaign_id):
    path = f"campaigns/{campaign_id}/applications"
    return get_docs_from_firestore_rest(path)
# ---- CACHED FIRESTORE HELPERS ----

@st.cache_resource
def firestore_get():
    # Return the Firestore REST getter once (cached)
    from hr_campaign_creator import get_docs_from_firestore_rest
    return get_docs_from_firestore_rest


@st.cache_data(ttl=120)
def load_firestore_collection(path: str):
    """Fast cached Firestore loader"""
    get_docs = firestore_get()     # ← this MUST exist first
    return get_docs(path)


REQUIRED_DF_COLUMNS = [
    "Candidate Name", "Email", "Phone", "Location", "Years Experience",
    "Score (%)", "Exact Match Score", "Semantic Similarity",
    "CGPA", "Education", "Matched Keywords", "JD Used",
    "Resume Raw Text", "Manual Shortlist"
]
# ---- CACHED FIRESTORE FUNCTIONS ----
@st.cache_data(ttl=60)   # cache for 60 sec (adjust as you want)
def cached_get_docs(path):
    return get_docs_from_firestore_rest(path)

@st.cache_data(ttl=60)
def cached_load_session(username):
    return load_session_data_from_firestore_rest(username)


dark_mode = False
st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
/* Ensure header is visible but specific elements within it are hidden */
# header {{
#     visibility: visible !important;
#     height: auto !important;
#     display: block !important;
#     margin: initial !important;
#     padding: initial !important;
#     position: initial !important;
#     top: initial !important;
# }}
html, body, [class*="css"] {{
    font-family: 'Inter', stylesheet;
    background-color: #f8f5f0;
    color: #333333;
    margin: 0 !important; /* Ensure no default margin */
    padding: 0 !important; /* Ensure no default padding */
}}
.main .block-container {{
    padding: 2rem;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.96);
    box-shadow: 0 12px 30px rgba(0,0,0,0.1);
    animation: fadeIn 0.8s ease-in-out;
}}
@keyframes fadeIn {{
    0% {{ opacity: 0; transform: translateY(20px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
}}
h1, h2, h3, h4, h5, h6 {{
    color: #00cec9;
    font-weight: 700;
}}
.dashboard-header {{
    font-size: 2.2rem;
    font-weight: 700;
    color: #222;
    padding-bottom: 0.5rem;
    border-bottom: 3px solid #00cec9;
    display: inline-block;
    margin-bottom: 2rem;
    animation: slideInLeft 0.8s ease-out;
}}
@keyframes slideInLeft {{
    0% {{ transform: translateX(-40px); opacity: 0; }}
    100% {{ transform: translateX(0); opacity: 1; }}
}}
@keyframes slideInDownFadeIn {{
    0% {{ opacity: 0; transform: translateY(-20px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
}}
.greeting-message {{
    font-size: 1.5rem;
    font-weight: 600;
    color: #00cec9;
    margin-bottom: 1.5rem;
    animation: slideInDownFadeIn 0.7s ease-out;
}}
.stMetric {{
    background-color: #f0f2f6;
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    transition: transform 0.2s ease;
}}
.stMetric:hover {{
    transform: translateY(-3px);
}}
.stMetric > div[data-testid="stMetricValue"] {{
    font-size: 2.5rem;
    font-weight: 700;
    color: #00cec9;
}}
.stMetric > div[data-testid="stMetricLabel"] {{
    font-size: 1rem;
    color: #555555;
}}
.stButton>button {{
    background-color: #00cec9;
    color: white;
    border-radius: 8px;
    padding: 0.6rem 1.2rem;
    font-weight: 600;
    border: none;
    transition: all 0.3s ease;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}}
.stButton>button:hover {{
    background-color: #00b0a8;
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.15);
}}
.stExpander {{
    background-color: #f0f2f6;
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}}
.stExpander > div > div > div > p {{
    color: #333333;
}}
.stExpander > div[data-testid="stExpanderToggle"] {{
    color: #00cec9;
}}
.stExpander > div[data-testid="stExpanderToggle"] svg {{
    fill: #00cec9;
}}
.stSelectbox > div > div {{
    background-color: #f0f2f6;
    color: #333333;
    border-radius: 8px;
}}
.stSelectbox > label {{
    color: #333333;
}}
.stTextInput > div > div > input {{
    background-color: #f0f2f6;
    color: #333333;
    border-radius: 8px;
}}
.stTextInput > label {{
    color: #333333;
}}
.stTextArea > div > div {{
    background-color: #f0f2f6;
    color: #333333;
    border-radius: 8px;
}}
.stTextArea > label {{
    color: #333333;
}}
.stRadio > label {{
    color: #333333;
}}
.stRadio div[role="radiogroup"] label {{
    background-color: #f0f2f6;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    margin: 0.2rem;
    color: #333333;
}}
.stRadio div[role="radiogroup"] label:hover {{
    background-color: #e0e2e6;
}}
.stRadio div[role="radiogroup"] label[data-baseweb="radio"] span:first-child {{
    background-color: #00cec9 !important;
}}
.stCheckbox span {{
    color: #333333;
}}
.stCheckbox div[data-testid="stCheckbox"] svg {{
    fill: #00cec9;
}}
</style>
""", unsafe_allow_html=True)

# CSS for hiding specific Streamlit elements globally (no media queries for sidebar)
st.markdown("""
<style>
/* Hide specific Streamlit default header elements on all devices */
.st-emotion-cache-16txt4y, /* For the main header buttons */
.st-emotion-cache-1gh866l, /* Specific for the GitHub icon/link */
.st-emotion-cache-30do4w, /* Another specific class ID to hide */
.stToolbarActionButtonLabel, /* New ID to hide */
.st-emotion-cache-1wbqy5l, /* New class to hide */
#_link_gzau3_10, /* New ID to hide */
.st-emotion-cache-h6us5p /* New class to hide the "Manage app" button */
{
    display: none !important;
    visibility: hidden !important;
    height: 0px !important;
    width: 0px !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* Ensure body and html have no default margins/paddings */
html, body {
    margin: 0 !important;
    padding: 0 !important;
}

/* Ensure the main content starts from the top */
.main .block-container {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

/* Revert sidebar specific CSS to allow Streamlit's native behavior */
/* Streamlit's internal JS will handle the transform/transition for collapsing/expanding */
/* No explicit display, visibility, width, height, position, top, left, z-index overrides here */
</style>
""", unsafe_allow_html=True)


def lottie_player(url, height=200, width=200):
    """Embed a Lottie animation by URL inside Streamlit."""
    return components.html(f"""
        <div style="display:flex;justify-content:center;align-items:center;">
            <lottie-player src="{url}" background="transparent" speed="1"
                style="width:{width}px; height:{height}px;" loop autoplay></lottie-player>
        </div>
        <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
    """, height=height + 30, width=width)

# Initialize a session state variable that tracks the sidebar state (either 'expanded' or 'collapsed').
if 'sidebar_state' not in st.session_state:
    st.session_state.sidebar_state = 'expanded' # Default state

# --- Page Config (MUST be the first Streamlit command) ---
st.set_page_config(
    page_title="ScreenerPro - AI Hiring Dashboard",
    layout="wide",
    page_icon="🧠",
    initial_sidebar_state=st.session_state.sidebar_state
)

st.session_state.theme = "light"
st._config.set_option("theme.base", "light")

# Import Firebase authentication and user management functions
from login import (
    login_section,
    is_current_user_admin,
    ADMIN_EMAILS,
)

# Import analytics page
from analytics import analytics_dashboard_page

# Import other pages
from about_us import about_us_page
from privacy_policy import privacy_policy_page
from partners import partner_with_us_page
from resume_counter import live_resume_counter_page
from employee_management import employee_management_page
from screener import resume_screener_page, APP_BASE_URL # APP_BASE_URL is imported here
from feedback import feedback_and_help_page
from collaboration import collaboration_hub_page
from email_page import send_email_to_candidate

from certificate_verification import certificate_verification_page
from manage_jds import manage_jds_page # Import the manage_jds_page function
# Import the new client page module
from client_page import client_dashboard_page

# Import the advanced HR Campaign Creator page
from hr_campaign_creator import hr_campaign_creator_page # Only need hr_campaign_creator_page

# Import the public job board page
from public_job_board import public_job_board_page # Import the actual public job board page


# Firebase Project ID (using __app_id from Canvas environment if available)
FIREBASE_PROJECT_ID = globals().get('__app_id', 'screenerproapp')

# Firebase Web API Key (from environment variables or default)
FIREBASE_WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY', 'AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw')

# Firestore Database Root URL for REST API
FIRESTORE_DATABASE_ROOT_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)"

# --- Set APP_BASE_URL in session state for other modules to use ---
# This ensures consistency across pages for generating links
if 'APP_BASE_URL' not in st.session_state:
    # This URL should match your deployed Streamlit app's base URL
    st.session_state['APP_BASE_URL'] = 'https://screenerpro.streamlit.app' # Replace with your actual deployed URL if different

# --- Firebase Data Persistence Functions (REST API) ---
def to_firestore_format(data: dict) -> dict:
    """Converts a Python dictionary to Firestore REST API 'fields' format."""
    fields = {}
    for key, value in data.items():
        if isinstance(value, str):
            fields[key] = {"stringValue": value}
        elif isinstance(value, int):
            fields[key] = {"integerValue": str(value)}
        elif isinstance(value, float):
            fields[key] = {"doubleValue": value}
        elif isinstance(value, bool):
            fields[key] = {"booleanValue": value}
        elif isinstance(value, datetime):
            fields[key] = {"timestampValue": value.isoformat() + "Z"}
        elif isinstance(value, list):
            array_values = []
            for item in value:
                if isinstance(item, str):
                    array_values.append({"stringValue": item})
                elif isinstance(item, int):
                    array_values.append({"integerValue": str(item)})
                elif isinstance(item, float):
                    array_values.append({"doubleValue": item})
                elif isinstance(item, dict):
                    array_values.append({"mapValue": {"fields": to_firestore_format(item)['fields']}})
            fields[key] = {"arrayValue": {"values": array_values}}
        elif isinstance(value, dict):
            fields[key] = {"mapValue": {"fields": to_firestore_format(value)['fields']}}
        elif value is None:
            fields[key] = {"nullValue": None}
        else:
            fields[key] = {"stringValue": str(value)}
    return {"fields": fields}


def save_session_data_to_firestore_rest(username):
    """
    Append-mode save:
    Loads existing → merges with new → writes merged dataframe back.
    """
    if not username:
        st.warning("No username found.")
        return

    try:
        # Unified document path
        doc_path = f"documents/user_data/{username}"
        url = f"{FIRESTORE_DATABASE_ROOT_URL}/{doc_path}?key={FIREBASE_WEB_API_KEY}"

        # -------------------------------------------
        # 1. Load existing cloud data
        # -------------------------------------------
        res = requests.get(url)
        if res.status_code == 200:
            raw = res.json()
            parsed = from_firestore_format(raw)

            if "comprehensive_df_json" in parsed:
                try:
                    existing_df = pd.read_json(
                        io.StringIO(parsed["comprehensive_df_json"]),
                        orient="records"
                    )
                except Exception:
                    existing_df = pd.DataFrame()
            else:
                existing_df = pd.DataFrame()
        else:
            existing_df = pd.DataFrame()

        # -------------------------------------------
        # 2. Load NEW screening results
        # -------------------------------------------
        if (
            "comprehensive_df" not in st.session_state
            or st.session_state["comprehensive_df"].empty
        ):
            st.warning("No screening results to save.")
            return

        new_df = st.session_state["comprehensive_df"].copy()
        new_df = new_df.drop(columns=["Resume Raw Text"], errors="ignore")

        # add shortlist column if missing
        if "Shortlisted" not in new_df.columns:
            cutoff = st.session_state.get("screening_cutoff_score", 75)
            new_df["Shortlisted"] = new_df["Score (%)"].apply(
                lambda x: f"Yes (Score ≥ {cutoff}%)" if x >= cutoff else "No"
            )

        # -------------------------------------------
        # 3. TRUE MERGE (THE MOST IMPORTANT FIX)
        # -------------------------------------------
        merged_df = pd.concat([existing_df, new_df], ignore_index=True)
        merged_df = merged_df.drop_duplicates()

        # -------------------------------------------
        # 4. Save merged data back
        # -------------------------------------------
        payload = {
            "comprehensive_df_json": merged_df.to_json(orient="records"),
            "screened_count": len(merged_df),
            "timestamp": str(datetime.now())
        }

        firestore_payload = to_firestore_format(payload)

        save_res = requests.patch(url, json=firestore_payload)

        if save_res.status_code in [200, 201]:
            st.success("✅ Cloud updated — append successful")
            st.session_state["comprehensive_df"] = merged_df
            st.session_state.total_screened_count_from_cloud = len(merged_df)
        else:
            st.error(f"❌ Save failed {save_res.status_code}: {save_res.text}")

    except Exception as e:
        st.error(f"🔥 Unexpected saving error: {e}")



def from_firestore_format(firestore_data: dict) -> dict:
    """Converts Firestore REST API 'fields' format to a Python dictionary."""
    data = {}
    if "fields" not in firestore_data:
        return data

    for key, value_obj in firestore_data["fields"].items():
        if "stringValue" in value_obj:
            data[key] = value_obj["stringValue"]
        elif "integerValue" in value_obj:
            data[key] = int(value_obj["integerValue"])
        elif "doubleValue" in value_obj:
            data[key] = float(value_obj["doubleValue"])
        elif "booleanValue" in value_obj:
            data[key] = value_obj["booleanValue"]
        elif "timestampValue" in value_obj:
            try:
                data[key] = datetime.fromisoformat(value_obj["timestampValue"].replace('Z', ''))
            except ValueError:
                data[key] = value_obj["timestampValue"]
        elif "arrayValue" in value_obj and "values" in value_obj["arrayValue"]:
            data[key] = [from_firestore_format({"fields": {"_": item}})["_"] if "mapValue" not in item else from_firestore_format({"fields": item["mapValue"]["fields"]}) for item in value_obj["arrayValue"]["values"]]
        elif "mapValue" in value_obj and "fields" in value_obj["mapValue"]:
            data[key] = from_firestore_format({"fields": value_obj["mapValue"]["fields"]})
        elif "nullValue" in value_obj:
            data[key] = None
        else:
            data[key] = str(value_obj)
    return data


def load_session_data_from_firestore_rest(username):
    """
    Loads full appended session data for a user from Firestore (REST API).
    Restores the comprehensive_df into session state.
    """
    try:
        if not username:
            st.warning("No username found. Please log in.")
            return

        # Always read from the single append-mode document
        doc_path = f"documents/user_data/{username}"
        url = f"{FIRESTORE_DATABASE_ROOT_URL}/{doc_path}?key={FIREBASE_WEB_API_KEY}"

        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            loaded_data = from_firestore_format(data)

            if 'comprehensive_df_json' in loaded_data:
                df_json_content = loaded_data['comprehensive_df_json']
                try:
                    if isinstance(df_json_content, str):
                        loaded_df = pd.read_json(io.StringIO(df_json_content), orient='records')
                    else:
                        loaded_df = pd.DataFrame.from_records(df_json_content)

                    # Ensure required columns exist
                    for col in REQUIRED_DF_COLUMNS:
                        if col not in loaded_df.columns:
                            loaded_df[col] = None
                    loaded_df = loaded_df.reindex(columns=REQUIRED_DF_COLUMNS, fill_value=None)

                    if 'Manual Shortlist' in loaded_df.columns:
                        loaded_df['Manual Shortlist'] = loaded_df['Manual Shortlist'].astype(bool)

                    # ==============================
                    # FIX 1 — ALWAYS LOAD FULL HISTORY ON LOGIN
                    # AND DO NOT OVERWRITE LIVE SCREENER VIEW
                    # ==============================

                    # Always load cloud history into session
                    st.session_state['comprehensive_df'] = loaded_df
                    st.session_state.total_screened_count_from_cloud = len(loaded_df)

                    # Keep a safe backup for screener page
                    st.session_state['history_data'] = loaded_df.copy()

                    # If user is currently in screener, do NOT overwrite its working dataset
                    if st.session_state.get("current_page") in ["Resume Screener", "Job Description Matcher"]:
                        pass




                except Exception as e:
                    st.error(f"Error reconstructing DataFrame: {e}")
                    st.session_state['comprehensive_df'] = pd.DataFrame(columns=REQUIRED_DF_COLUMNS)

            else:
                st.info("No saved data found for this user.")
                st.session_state['comprehensive_df'] = pd.DataFrame(columns=REQUIRED_DF_COLUMNS)
                st.session_state.total_screened_count_from_cloud = 0


        elif res.status_code == 404:
            st.info("No session data found in Cloud .")
            st.session_state['comprehensive_df'] = pd.DataFrame(columns=REQUIRED_DF_COLUMNS)
            st.session_state.total_screened_count_from_cloud = 0
        else:
            st.error(f"❌  Load failed: {res.status_code}, {res.text}")
            st.session_state['comprehensive_df'] = pd.DataFrame(columns=REQUIRED_DF_COLUMNS)
            st.session_state.total_screened_count_from_cloud = 0

    except Exception as e:
        st.error(f"🔥 Error loading session: {e}")
        st.session_state['comprehensive_df'] = pd.DataFrame(columns=REQUIRED_DF_COLUMNS)
        st.session_state.total_screened_count_from_cloud = 0


def log_activity_main(message):
    """Logs an activity with a timestamp to the session state for main.py's activities."""
    if 'activity_log' not in st.session_state:
        st.session_state.activity_log = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.activity_log.insert(0, f"[{timestamp}] {message}")
    st.session_state.activity_log = st.session_state.activity_log[:50]


def load_css(css_file_name):
    """Loads CSS from a local file and injects it into the Streamlit app."""
    try:
        with open(css_file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file '{css_file_name}' not found. Please ensure it's in the same directory as main.py.")

load_css("style.css")

plt.style.use('default')
sns.set_palette("coolwarm")


# --- Branding ---
st.sidebar.image("https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhhq_OCSv-QmuBjXeRQXr60EfsvVA4chRPCNslo3NhjVQkoKjUtiRfTPpGoQjyQXS7sMsJifQC6Yq34cAhNbq9lMwBXZqIIbCij1adyXSuNoyxuzOTDfrPU2dnna0baimldd7Y1KCkvaAfrWC1yLGxp25SJ9s4exJ-JAc8kNcTyUSgkLWbW2DdvhpWH4GlO/s578/logo.png", width=150)
st.sidebar.title("ScreenerPro")

# --- Authentication Logic ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "user_email" not in st.session_state:
    st.session_state.user_email = st.session_state.get("username")
if "user_uid" not in st.session_state:
    st.session_state.user_uid = None
if "user_company" not in st.session_state:
    st.session_state.user_company = None
if "user_status" not in st.session_state:
    st.session_state.user_status = None
if 'data_loaded_on_startup' not in st.session_state:
    st.session_state.data_loaded_on_startup = False
# The 'mobile_menu_open' state is no longer needed for a custom menu.
# if 'mobile_menu_open' not in st.session_state:
#     st.session_state.mobile_menu_open = False


REQUIRED_DF_COLUMNS = [
    "Manual Shortlist",
    "Name",
    "Candidate Name", "Score (%)", "Years Experience", "CGPA (4.0 Scale)",
    "Email", "Phone Number", "Location", "Languages Known",
    "Education Details",
    "Work History", "Project Details", "AI Suggestion", "Detailed HR Assessment",
    "Matched Keywords", "Missing Skills",
    "Semantic Similarity", "Exact Match Score",
    "Resume Raw Text", "Resume Word Count",
    "Latest Education",
    "Most Recent Job",
    "Certifications",
    "Resume Consistency Score",
    "JD Used", "Date Screened", "Certificate ID", "Certificate Rank", "Tag",
    "Top Skills Highlight",
    "Availability",
    "Soft Skills",
    "Notable Projects Highlight",
    "Awards/Recognitions",
    "Tools Used Highlight",
    "Publications",
    "Portfolio/GitHub"
]

def _load_initial_screened_count(username):
    """
    Loads only the 'screened_count' from Firestore for the current user.
    This is a lightweight operation for displaying the count on startup.
    """
    try:
        if not username:
            return

        doc_path = f"documents/artifacts/{FIREBASE_PROJECT_ID}/users/{username}/session_data_rest/current_session"
        url = f"{FIRESTORE_DATABASE_ROOT_URL}/{doc_path}?key={FIREBASE_WEB_API_KEY}"

        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            loaded_data = from_firestore_format(data)
            if 'screened_count' in loaded_data:
                st.session_state.total_screened_count_from_cloud = loaded_data['screened_count']
                log_activity_main(f"Initial screened count loaded for '{username}': {loaded_data['screened_count']}.")
            else:
                st.session_state.total_screened_count_from_cloud = 0
        elif res.status_code == 404:
            st.session_state.total_screened_count_from_cloud = 0
        else:
            log_activity_main(f"Failed to load initial screened count for '{username}': {res.status_code}, {res.text}")
            st.session_state.total_screened_count_from_cloud = 0
    except requests.exceptions.RequestException as e:
        log_activity_main(f"Firebase connection error during initial count load for '{username}': {e}")
        st.session_state.total_screened_count_from_cloud = 0
    except Exception as e:
        log_activity_main(f"Unexpected error during initial count load for '{username}': {e}")
        st.session_state.total_screened_count_from_cloud = 0


def initialize_session_state():
    # ===============================
    # DATAFRAME SAFETY
    # ===============================
    if 'comprehensive_df' not in st.session_state or st.session_state['comprehensive_df'].empty:
        st.session_state['comprehensive_df'] = pd.DataFrame(columns=REQUIRED_DF_COLUMNS)
    else:
        if 'File Name' in st.session_state['comprehensive_df'].columns and 'Name' not in st.session_state['comprehensive_df'].columns:
            st.session_state['comprehensive_df'].rename(columns={'File Name': 'Name'}, inplace=True)
            log_activity_main("Renamed 'File Name' to 'Name'")

        current_cols = st.session_state['comprehensive_df'].columns.tolist()
        missing_cols = [c for c in REQUIRED_DF_COLUMNS if c not in current_cols]
        for col in missing_cols:
            st.session_state['comprehensive_df'][col] = None

        st.session_state['comprehensive_df'] = st.session_state['comprehensive_df'].reindex(
            columns=REQUIRED_DF_COLUMNS, fill_value=None
        )

        if 'Manual Shortlist' in st.session_state['comprehensive_df']:
            st.session_state['comprehensive_df']['Manual Shortlist'] = (
                st.session_state['comprehensive_df']['Manual Shortlist'].astype(bool)
            )

    # ===============================
    # GLOBAL SESSION FLAGS
    # ===============================
    if 'activity_log_main' not in st.session_state:
        st.session_state.activity_log_main = []

    if 'user_company' not in st.session_state:
        st.session_state.user_company = ""

    if 'dark_mode_main' not in st.session_state:
        st.session_state.dark_mode_main = False

    if 'current_page' not in st.session_state:
        # Smart Init: If job_id is present, start directly on the Public Job Board
        # This prevents the need for a forced rerun later, fixing the loading loop.
        if "job_id" in st.query_params:
            st.session_state.current_page = "Public Job Board"
        else:
            st.session_state.current_page = "Home"

    if 'screener_needs_reset' not in st.session_state:
        st.session_state.screener_needs_reset = False

    if 'total_screened_count_from_cloud' not in st.session_state:
        st.session_state.total_screened_count_from_cloud = 0

    if 'show_profile_modal' not in st.session_state:
        st.session_state.show_profile_modal = False

    # 🔐 VERY IMPORTANT — ADMIN FLAG
    if 'is_company_admin' not in st.session_state:
        st.session_state.is_company_admin = False
initialize_session_state()
# st.sidebar.markdown("---")
# st.sidebar.markdown("### 🔐 Admin State Debug")
# st.sidebar.write("📧 Email:", st.session_state.get("username"))
# st.sidebar.write("🏢 Company:", st.session_state.get("user_company"))
# st.sidebar.write("👑 is_company_admin:", st.session_state.get("is_company_admin"))


# st.sidebar.info(
#     f"🔐 Company Admin: {st.session_state.get('is_company_admin')}"
# )


#edit_profile_modal()



def job_description_matcher_page():
    """Combines Resume Screener and Manage JDs functionalities."""
    st.markdown('<div class="dashboard-header"> Job Description Matcher</div>', unsafe_allow_html=True)
    
    matcher_tab1, matcher_tab2 = st.tabs(["Resume Screener", "Manage Job Descriptions"])

    with matcher_tab1:
        st.subheader("Resume Screening")
        try:
            resume_screener_page()
            if 'comprehensive_df' in st.session_state and not st.session_state['comprehensive_df'].empty:
                current_df_len = len(st.session_state['comprehensive_df'])
                if st.session_state.get('last_screen_log_count', 0) < current_df_len:
                    log_activity_main(f"Performed resume screening for {current_df_len} candidates.")
                    st.session_state.last_screen_log_count = current_df_len

                for result in st.session_state['comprehensive_df'].to_dict('records'):
                    if result.get('Score (%)', 0) >= 90 and result['Candidate Name'] not in [app['candidate_name'] for app in st.session_state.get('pending_approvals', []) if app['status'] == 'pending' or app['status'] == 'approved']:
                        if 'pending_approvals' not in st.session_state:
                            st.session_state.pending_approvals = []
                        st.session_state.pending_approvals.append({
                            "candidate_name": result['Candidate Name'],
                            "score": result['Score (%)'],
                            "experience": result['Years Experience'],
                            "jd_used": result.get('JD Used', 'N/A'),
                            "status": "pending",
                            "notes": f"High-scoring candidate from recent screening."
                        })
                        log_activity_main(f"Candidate '{result['Candidate Name']}' sent for approval (high score).")
                        st.toast(f"Candidate {result['Candidate Name']} sent for approval!")

        except ImportError:
            st.error("`screener.py` not found or `resume_screener_page` function not defined. Please ensure 'screener.py' exists and contains the 'resume_screener_page' function.")
        except Exception as e:
            st.error(f"Error loading Resume Screener: {e}")

    with matcher_tab2:
        st.subheader("Manage Job Descriptions")
        try:
            manage_jds_page()
        except Exception as e:
            st.error(f"Error loading Manage JDs: {e}")

def contact_us_page():
    """A simple page for contact information."""
    st.markdown('<div class="dashboard-header">📞 Contact Us</div>', unsafe_allow_html=True)
    st.write("### Get in Touch with ScreenerPro")
    st.write("We're here to help! Whether you have questions, feedback, or need support, feel free to reach out.")
    
    st.markdown("---")
    
    st.subheader("General Inquiries")
    st.write("For general questions about ScreenerPro or partnership opportunities:")
    st.markdown("📧 **Email:** `info@screenerpro.com`")
    st.markdown("📞 **Phone:** `+1 (555) 123-4567`")
    
    st.subheader("Our Office")
    st.write("While we primarily operate online, you can reach us at our main office:")
    st.markdown("""
    **ScreenerPro Inc.** 123 AI Avenue,  
    Innovation City, AI 90210  
    Country
    """)
    
    st.markdown("---")
    st.write("We look forward to hearing from you!")
def save_candidate_to_firestore(candidate, username):
    """Save a candidate approval entry to Firestore."""
    try:
        if not username:
            st.warning("No username found. Please log in.")
            return

        # SAFE DOCUMENT ID (email becomes document, no slash)
        user_doc = username.replace(".", "_")  # optional sanitization
        candidate_id = candidate["candidate_name"].replace(" ", "_") + "_" + str(int(datetime.now().timestamp()))

        url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents/approvals/{user_doc}/candidates/{candidate_id}?key={FIREBASE_WEB_API_KEY}"

        firestore_data = to_firestore_format(candidate)
        res = requests.patch(url, json=firestore_data)

        if res.status_code in [200, 201]:
            log_activity_main(f"Candidate '{candidate['candidate_name']}' saved to approvals.")
        else:
            st.error(f"❌ Failed to save approval: {res.status_code}, {res.text}")
    except Exception as e:
        st.error(f"🔥 Error saving candidate to Firestore: {e}")


def load_pending_approvals_from_firestore(username):
    """Load all candidate approvals for a user from Firestore."""
    try:
        if not username:
            return []

        user_doc = username.replace(".", "_")

        url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents:runQuery?key={FIREBASE_WEB_API_KEY}"
        query = {
            "parent": f"projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/approvals/{user_doc}",
            "structuredQuery": {
                "from": [{"collectionId": "candidates"}],
                "where": {
                    "fieldFilter": {
                        "field": {"fieldPath": "status"},
                        "op": "EQUAL",
                        "value": {"stringValue": "pending"}
                    }
                }
            }
        }

        res = requests.post(url, json=query)
        if res.status_code == 200:
            approvals = []
            for doc in res.json():
                if "document" in doc:
                    approvals.append(from_firestore_format(doc["document"]))
            return approvals
        else:
            st.error(f"❌ Failed to load approvals: {res.status_code}, {res.text}")
            return []
    except Exception as e:
        st.error(f"🔥 Error loading approvals: {e}")
        return []


def load_reviewed_candidates_from_firestore(username):
    """Load all candidates that have already been approved or rejected."""
    try:
        if not username:
            return []

        user_doc = username.replace(".", "_")

        url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents:runQuery?key={FIREBASE_WEB_API_KEY}"
        query = {
            "parent": f"projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/approvals/{user_doc}",
            "structuredQuery": {
                "from": [{"collectionId": "candidates"}],
                "where": {
                    "fieldFilter": {
                        "field": {"fieldPath": "status"},
                        "op": "IN",
                        "value": {"arrayValue": {"values": [
                            {"stringValue": "approved"},
                            {"stringValue": "rejected"}
                        ]}}
                    }
                }
            }
        }

        res = requests.post(url, json=query)
        if res.status_code == 200:
            reviewed = []
            for doc in res.json():
                if "document" in doc:
                    reviewed.append(from_firestore_format(doc["document"]))
            return reviewed
        else:
            st.error(f"❌ Failed to load reviewed candidates: {res.status_code}, {res.text}")
            return []
    except Exception as e:
        st.error(f"🔥 Error loading reviewed candidates: {e}")
        return []




def login_page_wrapper():
    """Handles login/logout based on authentication state."""
    st.markdown('<div class="dashboard-header">🔐 Login / Sign up</div>', unsafe_allow_html=True)
    
    if st.session_state.authenticated:
   

        st.success(f"You are currently logged in as **{st.session_state.username}**.")
        st.write("You can access all features of ScreenerPro.")
        if st.button("🚪 Logout", key="logout_button_wrapper"):
            log_activity_main(f"User '{st.session_state.get('username', 'anonymous_user')}' logged out.")
            st.session_state.authenticated = False
            st.session_state.pop('username', None)
            st.session_state.pop('user_uid', None)
            st.session_state.pop('user_company', None)
            st.session_state.pop('user_status', None)
            st.success("✅ Logged out successfully.")
            st.rerun()
    else:
        st.info("Please log in or register to access ScreenerPro's features.")
        login_section()


import streamlit as st





def show_authenticated_home_page(log_activity_callback):
    """Displays the Dashboard page content for authenticated users."""

    company_name = (st.session_state.get("user_company") or "").strip() or "Your Company"

    st.markdown(
        f'<div class="dashboard-header">{company_name} Overview</div>',
        unsafe_allow_html=True
    )

    # continue with rest of dashboard content below

    #st.markdown('<div class="dashboard-header">Overview Dashboard</div>', unsafe_allow_html=True)

    resume_count = st.session_state.total_screened_count_from_cloud
    
    if not os.path.exists("data"):
        os.makedirs("data")
    jd_count = len([f for f in os.listdir("data") if f.endswith(".txt")])
    shortlisted = 0
    avg_score = 0.0
    df_results = pd.DataFrame(columns=REQUIRED_DF_COLUMNS)

    cutoff_score = st.session_state.get('screening_cutoff_score', 75)
    min_exp_required = st.session_state.get('screening_min_experience', 2)
    max_exp_allowed = st.session_state.get('screening_max_experience', 10)
    min_cgpa_required = st.session_state.get('screening_min_cgpa', 2.5)

    if 'comprehensive_df' in st.session_state and not st.session_state['comprehensive_df'].empty:
        try:
            df_results = st.session_state['comprehensive_df'].copy()
            
            df_results['CGPA (4.0 Scale)'] = pd.to_numeric(df_results['CGPA (4.0 Scale)'], errors='coerce').astype(float)

            shortlisted_df = df_results[
                ((df_results["Score (%)"] >= cutoff_score) &
                (df_results["Years Experience"] >= min_exp_required) &
                (df_results["Years Experience"] <= max_exp_allowed) &
                ((df_results['CGPA (4.0 Scale)'].isnull()) | (df_results['CGPA (4.0 Scale)'] >= min_cgpa_required)))
                |
                (df_results['Manual Shortlist'] == True)
            ].copy()
            shortlisted = shortlisted_df.shape[0]

            avg_score = df_results["Score (%)"].mean()
        except Exception as e:
            st.error(f"Error processing screening results from session state: {e}")
            df_results = pd.DataFrame(columns=REQUIRED_DF_COLUMNS)
            shortlisted_df = pd.DataFrame(columns=REQUIRED_DF_COLUMNS)
    else:
        st.info("No screening results available in this session yet. Please run the Resume Screener.")
        shortlisted_df = pd.DataFrame(columns=REQUIRED_DF_COLUMNS)
    
    st.subheader("Key Performance Indicators")

    # =========================
    # NEW METRICS ADDED HERE
    # =========================

    # ---- Candidate Pipeline Metrics ----
    applied = 0
    user_uid = st.session_state.get("user_uid")
    username_email = st.session_state.get("username")  # for user_data lookup

    # -----------------------------------------
    # 1️⃣ REAL APPLICATIONS → Public Job Board
    # -----------------------------------------
    if user_uid:
        try:
            campaign_docs = load_firestore_collection(
                f"artifacts/{FIREBASE_PROJECT_ID}/users/{user_uid}/my_campaigns"
            )
            for camp in campaign_docs:
                camp_id = camp.get("id", "")
                try:
                    apps = load_firestore_collection(
                        f"campaigns/{camp_id}/applications"
                    )
                    applied += len(apps)
                except:
                    pass
        except:
            pass

    # -----------------------------------------
    # 2️⃣ ADMIN PANEL APPLIED CANDIDATES (FAKE)
    # documents/user_data/<email>
    # -----------------------------------------
    if username_email:
        import urllib.parse
        encoded_email = urllib.parse.quote(username_email, safe="")
        url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents/user_data/{encoded_email}?key={FIREBASE_WEB_API_KEY}"

        try:
            res = requests.get(url)
            if res.status_code == 200:
                data = res.json().get("fields", {})
                applied_fake = int(data.get("applied_candidates", {}).get("integerValue", 0))
                applied += applied_fake
        except:
            pass


    # ---- Hiring Efficiency Score ----
    hiring_efficiency = 0
    if resume_count > 0:
        hiring_efficiency = round((shortlisted / resume_count) * 100, 1)

    # =========================
    # END NEW METRICS
    # =========================

    # ---- Existing KPI Columns, now 6 columns ----
    metric_cols = st.columns(6)

    metric_cols[0].metric("Resumes Screened", resume_count,
                          help="Total unique resumes processed across all sessions (from cloud).")

    metric_cols[1].metric("Applied Candidates", applied,
                          help="Total candidates who applied to your campaigns.")

    metric_cols[2].metric("Shortlisted Candidates", shortlisted,
                          help=f"Candidates meeting AI criteria or manually shortlisted.")

    metric_cols[3].metric("Hiring Efficiency", f"{hiring_efficiency}%",
                          help="Shortlisted ÷ Screened × 100")

    metric_cols[4].metric("Job Descriptions", jd_count,
                          help="Number of job descriptions available.")

    metric_cols[5].metric("Average Score", f"{avg_score:.1f}%",
                          help="Average matching score of all screened resumes.")


    st.subheader("Cloud Session Data Management")
    cloud_data_cols = st.columns(2)
    with cloud_data_cols[0]:
        if st.button("💾 Save Session Data to Cloud ", key="save_session_data_button"):
            save_session_data_to_firestore_rest(st.session_state.get('username', 'anonymous'))
    with cloud_data_cols[1]:
        if st.button("🔄 Load Session Data from Cloud", key="load_session_data_button"):
            load_session_data_from_firestore_rest(st.session_state.get('username', 'anonymous'))
            st.session_state['screener_needs_reset'] = False
            st.rerun()

    st.markdown("---")

    st.subheader("⚙️ Customize Your Dashboard")
    with st.expander("Select Widgets to Display"):
        if 'dashboard_widgets' not in st.session_state:
            st.session_state.dashboard_widgets = {
                'Candidate Distribution': True,
                'Experience Distribution': True,
                'Top 5 Most Common Skills': True,
                'My Recent Screenings': True,
                'Top Performing JDs': True,
                'Pending Approvals': True,
            }

        st.session_state.dashboard_widgets['Candidate Distribution'] = st.checkbox("Candidate Quality Distribution", value=st.session_state.dashboard_widgets['Candidate Distribution'], key="widget_cand_dist")
        st.session_state.dashboard_widgets['Experience Distribution'] = st.checkbox("Experience Level Breakdown", value=st.session_state.dashboard_widgets['Experience Distribution'], key="widget_exp_dist")
        st.session_state.dashboard_widgets['Top 5 Most Common Skills'] = st.checkbox("Top 5 Matched Skills", value=st.session_state.dashboard_widgets['Top 5 Most Common Skills'], key="widget_top_skills")
        st.session_state.dashboard_widgets['My Recent Screenings'] = st.checkbox("My Recent Screenings Table", value=st.session_state.dashboard_widgets['My Recent Screenings'], key="widget_recent_screenings")
        st.session_state.dashboard_widgets['Top Performing JDs'] = st.checkbox("Top Performing Job Descriptions", value=st.session_state.dashboard_widgets['Top Performing JDs'], key="widget_top_jds")
        st.session_state.dashboard_widgets['Pending Approvals'] = st.checkbox("Pending Approvals", value=st.session_state.dashboard_widgets['Pending Approvals'], key="widget_pending_approvals")

    st.markdown("### 📊 Dashboard Insights")

    if not df_results.empty:
        try:
            if 'Tag' not in df_results.columns:
                df_results['Tag'] = df_results.apply(lambda row:
                    "👑 Exceptional Match" if row['Score (%)'] >= 90 and row['Years Experience'] >= 5 and row.get('Semantic Similarity', 0) >= 0.85 else (
                    "🔥 Strong Candidate" if row['Score (%)'] >= 80 and row['Years Experience'] >= 3 and row.get('Semantic Similarity', 0) >= 0.7 else (
                    "✨ Promising Fit" if row['Score (%)'] >= 60 and row['Years Experience'] >= 1 else (
                    "⚠️ Needs Review" if row['Score (%)'] >= 40 else
                    "❌ Limited Match"))), axis=1)

            col_g1, col_g2 = st.columns(2)

            if st.session_state.dashboard_widgets['Candidate Distribution']:
                with col_g1:
                    st.markdown("##### 🔥 Candidate Quality Distribution")
                    pie_data = df_results['Tag'].value_counts().reset_index()
                    pie_data.columns = ['Tag', 'Count']
                    fig_plotly_pie = px.pie(pie_data, values='Count', names='Tag', title='Candidate Quality Breakdown',
                                            color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig_plotly_pie, use_container_width=True)

            if st.session_state.dashboard_widgets['Experience Distribution']:
                with col_g2:
                    st.markdown("##### 📊 Experience Level Breakdown")
                    bins = [0, 2, 5, 10, 20, 50]
                    labels = ['0-2 yrs', '3-5 yrs', '6-10 yrs', '10-20 yrs', '20+ yrs']
                    df_results['Experience Group'] = pd.cut(df_results['Years Experience'], bins=bins, labels=labels, right=False)
                    exp_counts = df_results['Experience Group'].value_counts().sort_index()

                    fig_plotly_bar = px.bar(exp_counts, x=exp_counts.index, y=exp_counts.values, title='Experience Distribution',
                                            labels={'x': 'Experience Range', 'y': 'Number of Candidates'},
                                            color_discrete_sequence=px.colors.sequential.Viridis)
                    st.plotly_chart(fig_plotly_bar, use_container_width=True)

            st.markdown("##### 📋 Candidate Quality Summary")
            tag_summary = df_results['Tag'].value_counts().reset_index()
            tag_summary.columns = ['Candidate Tag', 'Count']
            st.dataframe(tag_summary, use_container_width=True, hide_index=True)

            if st.session_state.dashboard_widgets['Top 5 Most Common Skills']:
                st.markdown("##### Top 5 Matched Skills")
                if 'Matched Keywords' in df_results.columns:
                    all_skills = []
                    for skills in df_results['Matched Keywords'].dropna():
                        all_skills.extend([s.strip().lower() for s in skills.split(",") if s.strip()])
                    skill_counts = pd.Series(all_skills).value_counts().head(5)
                    if not skill_counts.empty:
                        fig_skills, ax3 = plt.subplots(figsize=(5.8, 3))

                        palette = sns.color_palette("cool", len(skill_counts))
                        sns.barplot(
                            x=skill_counts.values,
                            y=skill_counts.index,
                            palette=palette,
                            ax=ax3
                        )
                        ax3.set_title("Top 5 Skills", fontsize=13, fontweight='bold', color='black')
                        ax3.set_xlabel("Frequency", fontsize=11, color='black')
                        ax3.set_ylabel("Skill", fontsize=11, color='black')
                        ax3.tick_params(labelsize=10, colors='black')

                        for i, v in enumerate(skill_counts.values):
                            ax3.text(v + 0.3, i, str(v), color='black', va='center', fontweight='bold', fontsize=9)
                        fig_skills.tight_layout()
                        st.pyplot(fig_skills)
                        plt.close(fig_skills)
                    else:
                        st.info("No skill data available in results for the Top 5 Skills chart.")
                else:
                    st.info("No 'Matched Keywords' column found in results for skill analysis.")
        except Exception as e:
            st.warning(f"⚠️ Could not render insights due to data error: {e}")

    st.markdown("---")

    if st.session_state.dashboard_widgets['My Recent Screenings']:
        st.subheader("My Recent Screenings")
        if not df_results.empty:
            with st.expander(f"View {len(df_results)} Screened Resumes in current session"):
                for idx, row in df_results.iterrows():
                    st.markdown(f"- **{row['Candidate Name']}** (Score: {row['Score (%)']:.1f}%, File: {row['Name']})")
            st.dataframe(df_results[['Candidate Name', 'Score (%)', 'Years Experience', 'Name']].head(5), use_container_width=True, hide_index=True)
            if st.button("View All Screenings in Analytics", key="view_all_screenings_dashboard"):
                st.session_state.current_page = '📊 Screening Analytics'
                st.rerun()
        else:
            st.info("No recent screenings to display. Run the Resume Screener to see results here.")

    if st.session_state.dashboard_widgets['Top Performing JDs']:
        st.subheader("Top Performing Job Descriptions")
        if 'comprehensive_df' in st.session_state and not st.session_state['comprehensive_df'].empty:
            df_all_results = st.session_state['comprehensive_df'].copy()

            if 'JD Used' not in df_all_results.columns:
                df_all_results['JD Used'] = 'Default Job Description'
                st.warning("Note: 'JD Used' column not found in screening results. Using 'Default Job Description' for display. Please update your screener to track the JD used.")

            if 'JD Used' in df_all_results.columns:
                df_all_results['CGPA (4.0 Scale)'] = pd.to_numeric(df_all_results['CGPA (4.0 Scale)'], errors='coerce').astype(float)

                shortlisted_per_jd = df_all_results[
                    ((df_all_results["Score (%)"] >= cutoff_score) &
                    (df_all_results["Years Experience"] >= min_exp_required) &
                    (df_all_results["Years Experience"] <= max_exp_allowed) &
                    ((df_all_results['CGPA (4.0 Scale)'].isnull()) | (df_all_results['CGPA (4.0 Scale)'] >= min_cgpa_required)))
                    |
                    (df_all_results['Manual Shortlist'] == True)
                ]['JD Used'].value_counts().reset_index()
                shortlisted_per_jd.columns = ['Job Description', 'Shortlisted Count']

                if not shortlisted_per_jd.empty:
                    st.dataframe(shortlisted_per_jd, use_container_width=True, hide_index=True)
                else:
                    st.info("No shortlisted candidates found for any JD yet based on current criteria.")
            else:
                st.info("Still unable to determine top performing JDs. 'JD Used' column is missing even after fallback.")
        else:
            st.info("No screening results available to determine top performing JDs.")

        if st.button("Manage All Job Descriptions", key="manage_all_jds_dashboard"):
            st.session_state.current_page = '📁 Manage JDs'
            st.rerun()

    if st.session_state.dashboard_widgets['Pending Approvals']:
        st.subheader("Pending Approvals")

        # Load from Firestore instead of session_state
        pending_candidates = load_pending_approvals_from_firestore(st.session_state.get("username", "anonymous"))

        if not pending_candidates:
            st.info("No candidates currently awaiting approval.")
        else:
            st.write("Review the following candidates:")

            for candidate in pending_candidates:
                with st.expander(f"Candidate: {candidate['candidate_name']} (Score: {candidate['score']}%)"):
                    st.write(f"**JD Used:** {candidate['jd_used']}")
                    st.write(f"**Experience:** {candidate['experience']} years")
                    st.write(f"**Notes:** {candidate['notes']}")

                    col_approve, col_reject = st.columns(2)
                    with col_approve:
                        if st.button(f"✅ Approve {candidate['candidate_name']}", key=f"approve_{candidate['candidate_name']}"):
                            candidate['status'] = 'approved'
                            candidate['reviewed_by'] = st.session_state.get('username', 'Unknown')
                            candidate['reviewed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            save_candidate_to_firestore(candidate, st.session_state.get("username", "anonymous"))
                            log_activity_callback(f"Candidate '{candidate['candidate_name']}' approved.")
                            st.success(f"Approved {candidate['candidate_name']}!")
                            st.rerun()

                    with col_reject:
                        if st.button(f"❌ Reject {candidate['candidate_name']}", key=f"reject_{candidate['candidate_name']}"):
                            candidate['status'] = 'rejected'
                            candidate['reviewed_by'] = st.session_state.get('username', 'Unknown')
                            candidate['reviewed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            save_candidate_to_firestore(candidate, st.session_state.get("username", "anonymous"))
                            log_activity_callback(f"Candidate '{candidate['candidate_name']}' rejected.")
                            st.error(f"Rejected {candidate['candidate_name']}.")
                            st.rerun()

        # (Optional) Reviewed Candidates Section
        reviewed = load_reviewed_candidates_from_firestore(st.session_state.get("username", "anonymous"))
        if reviewed:
            st.markdown("---")
            st.subheader("Reviewed Candidates")
            reviewed_df = pd.DataFrame(reviewed)
            st.dataframe(reviewed_df[['candidate_name', 'score', 'experience', 'status', 'reviewed_by', 'reviewed_at']], use_container_width=True, hide_index=True)

# --- Main Application Logic ---
def main():

    # =====================================================
    # 🔰 SESSION INIT
    # =====================================================
    initialize_session_state()

    # ==========================
    # DEEP LINKING HANDLER
    # ==========================
    # Check if a specific job_id is requested via URL query params
    qp = st.query_params
    if "job_id" in qp:
        requested_job_id = qp["job_id"]
        
        # Scenario 1: We are not on the correct page -> Switch and Rerun
        if st.session_state.get('current_page') != "Public Job Board":
            st.session_state.current_page = "Public Job Board"
            st.session_state.expanded_job_id = requested_job_id
            st.session_state.last_processed_url_job_id = requested_job_id
            st.rerun()
            
        # Scenario 2: We are already on the correct page -> Update state, NO Rerun needed
        # (The public_job_board_page function will use this state downstream)
        elif st.session_state.get('expanded_job_id') != requested_job_id:
             st.session_state.expanded_job_id = requested_job_id
             st.session_state.last_processed_url_job_id = requested_job_id
             # No st.rerun() here, let the script continue to render the page

    if "screen_width" not in st.session_state:
        st.session_state.screen_width = 1000

    # =====================================================
    # 📐 SCREEN WIDTH TRACKER
    # =====================================================
    components.html("""
    <script>
        const width = window.innerWidth;
        window.parent.postMessage(
            { type: 'streamlit:setScreenWidth', value: width },
            '*'
        );
    </script>
    """, height=0)

    # =====================================================
    # 🔔 HEADER DROPDOWN LISTENER (JS → STREAMLIT)
    # =====================================================
    components.html("""
    <script>
    window.addEventListener("message", (event) => {
        if (!event.data || !event.data.type) return;

        const url = new URL(window.location.href);

        if (event.data.type === "streamlit:logout") {
            url.searchParams.set("action", "logout");
            window.location.href = url.toString();
        }

        if (event.data.type === "streamlit:setProfile") {
            url.searchParams.set("action", "profile");
            window.location.href = url.toString();
        }
    });
    </script>
    """, height=0)

    # =====================================================
    # 🎯 HEADER ACTION HANDLER (PROFILE / LOGOUT)
    # =====================================================
    query = st.query_params.to_dict()
    action = query.get("action", None)

    if action == "logout":
        st.session_state.authenticated = False
        for k in [
            "username",
            "user_uid",
            "user_company",
            "user_status",
            "is_company_admin",
            "current_page",
        ]:
            st.session_state.pop(k, None)

        st.query_params.clear()
        st.rerun()

    elif action == "profile":
        st.session_state.current_page = "Edit Profile"
        st.query_params.clear()
        st.rerun()

    # =====================================================
    # 🔐 CHECK LOGIN STATUS
    # =====================================================
    authenticated = st.session_state.get("authenticated", False)

    # =====================================================
    # 📚 SIDEBAR OPTIONS (START)
    # =====================================================
    current_sidebar_options = []
    default_sidebar_index = 0

    if authenticated:  # Use the 'authenticated' variable
        current_sidebar_options = [
            "Dashboard",
            "Resume Screener",
            "Manage JDs",
            "Screening Analytics",
            "HR Campaign Creator",
            "Public Job Board",
            "Advanced Tools",
            "Collaboration Hub",
            "Employee Management",
            "Payroll Management",
            "Live Resume Counter",
            "Email Candidates",
            "Search Resumes",
            "Candidate Notes",
            "Certificate Verification",
            "Edit Profile",
            "Partner With Us",
            "About Us",
            "Our Clients",
            "Privacy Policy & Terms",
            "Feedback & Help",
            "Logout",
        ]


        # ⭐ ADMIN OPTIONS (COMPANY ADMIN ONLY)
        if st.session_state.get("is_company_admin", False):
            current_sidebar_options.insert(
                current_sidebar_options.index("Edit Profile") + 1,
                "Admin User Manager"
            )


        default_tab_name = st.session_state.get("tab_override", "Dashboard")
        
        if default_tab_name in current_sidebar_options:
            default_sidebar_index = current_sidebar_options.index(default_tab_name)
        else:
            default_sidebar_index = current_sidebar_options.index("Dashboard")

    else:
        # Public (not logged in) sidebar
        render_universal_sidebar("Home")
        current_sidebar_options = [
            "Home",
            "Login / Register",
            "Public Job Board",
            "Certificate Verification",
            "Our Clients",
            "Partner With Us",
            "Privacy Policy & Terms",
            "Feedback & Help"
        ]
        selected_tab = "Home" # Fallback
    st.session_state.current_page = selected_tab
    render_minimal_header()


    # 🚨 Block private pages for not-logged users
    if not authenticated and selected_tab not in PUBLIC_ALLOWED:
        st.session_state.current_page = "Home"
        st.rerun()

    # Auto-load user history only for dashboard (not screener or JD Matcher)
    if (
        st.session_state.authenticated
        and not st.session_state.get("data_loaded_on_startup", False)
        and not st.session_state.get("skip_history_reload", False)
        and st.session_state.username
        and st.session_state.current_page not in ["Resume Screener", "Job Description Matcher"]
    ):
        with st.spinner("Loading your activity history..."):
            loaded = cached_load_session(st.session_state.username)

            # Store in history bucket ONLY (no leak into screener)
            if loaded:
                st.session_state.history_data = loaded  

        st.session_state.data_loaded_on_startup = True




    # Display greeting message for authenticated users (outside home page functions)
    if st.session_state.get("authenticated") and st.session_state.get("username"):

        # ✅ Safely resolve company name
        company_name = (st.session_state.get("user_company") or "").strip()
        if not company_name:
            company_name = "Your Company"

    # if st.session_state.get("authenticated") and st.session_state.get("username"):
    #     display_name = st.session_state.username.split('@')[0] if "@" in st.session_state.username else st.session_state.username

        st.markdown(
    f"""
    <style>
        @keyframes fadeInScale {{
            from {{ opacity: 0; transform: scale(0.9); }}
            to {{ opacity: 1; transform: scale(1); }}
        }}

        /* Typing + 3s pause before restarting */
        @keyframes typing-loop {{
            0% {{ width: 0 }}
            60% {{ width: 100% }}
            80% {{ width: 100% }}
            100% {{ width: 0 }}
        }}

        @keyframes blink-caret-loop {{
            from, to {{ border-color: transparent }}
            50% {{ border-color: #3498db }}
        }}

        .beautiful-greeting-card {{
            background: linear-gradient(135deg, #f0f2f5 0%, #e0e5ec 100%);
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
            text-align: center;
            animation: fadeInScale 0.7s ease-out forwards;
            position: relative;
            overflow: hidden;
        }}

        .beautiful-greeting-card::before {{
            content: '✨';
            position: absolute;
            top: 10px;
            left: 10px;
            font-size: 2em;
            opacity: 0.2;
            pointer-events: none;
        }}

        .beautiful-greeting-card::after {{
            content: '🌟';
            position: absolute;
            bottom: 10px;
            right: 10px;
            font-size: 2em;
            opacity: 0.2;
            pointer-events: none;
        }}

        .beautiful-greeting-title {{
            font-size: 2.2em;
            font-weight: 700;
            color: #2c3e50;
            margin-bottom: 10px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.05);
            white-space: nowrap;
            overflow: hidden;
            border-right: 2px solid #3498db;
            width: 0;
            animation: typing-loop 6s steps(32, end) infinite, blink-caret-loop 0.75s step-end infinite;
        }}

        .beautiful-username {{
            color: #3498db;
            font-weight: 800;
        }}

        .beautiful-welcome-text {{
            font-size: 1.15em;
            color: #555555;
            line-height: 1.6;
            margin-top: 15px;
        }}

        .beautiful-emoji {{
            font-size: 1.6em;
            vertical-align: middle;
            margin: 0 5px;
        }}
    </style>

    <div class="beautiful-greeting-card">
        <h1 class="beautiful-greeting-title">
            Welcome, <span class="beautiful-username">{company_name}</span>!
        </h1>
        <p class="beautiful-welcome-text">
            <span class="beautiful-emoji">👋</span> We're absolutely thrilled to have you here!
            Your journey with us officially begins now. <span class="beautiful-emoji">🚀</span>
            Get ready to explore! <span class="beautiful-emoji">🎉</span>
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
    # =========================================================
    #  LOG LOGIN EVENT
    # =========================================================
    if (
        st.session_state.get('last_login_logged_for_user') 
        != st.session_state.username 
        and st.session_state.authenticated
    ):
        log_activity_main(f"User '{st.session_state.username}' logged in.")
        st.session_state.last_login_logged_for_user = st.session_state.username

    # =========================================================
    #  PAGE ROUTING (PUBLIC + AUTHENTICATED)
    # =========================================================
    if st.session_state.current_page == "Home":
        
        show_public_home_page()

    elif st.session_state.current_page == "Admin Panel":
        admin_panel_page()   # <-- DO NOT REMOVE

    elif st.session_state.current_page == "Dashboard":
        # st.sidebar.write("🔐 Company Admin:", st.session_state.get("is_company_admin"))
        # st.sidebar.write("👤 User:", st.session_state.get("username"))

        show_authenticated_home_page(log_activity_main)

    elif st.session_state.current_page == "Client Portal":
        client_dashboard_page()
    elif st.session_state.current_page == "Edit Profile":
        edit_profile_page()
    elif st.session_state.current_page == "Admin User Manager":
        admin_user_manager()


    elif st.session_state.current_page == "Resume Screener":
        st.session_state.reset_screener = True
        st.session_state['screener_needs_reset'] = True
        try:
            resume_screener_page()

            if 'comprehensive_df' in st.session_state and not st.session_state['comprehensive_df'].empty:
                current_df_len = len(st.session_state['comprehensive_df'])

                if st.session_state.get('last_screen_log_count', 0) < current_df_len:
                    log_activity_main(
                        f"Performed resume screening for {current_df_len} candidates."
                    )
                    st.session_state.last_screen_log_count = current_df_len

                for result in st.session_state['comprehensive_df'].to_dict('records'):
                    if (
                        result.get('Score (%)', 0) >= 90
                        and result['Candidate Name']
                        not in [
                            app['candidate_name']
                            for app in st.session_state.get('pending_approvals', [])
                            if app['status'] in ['pending', 'approved']
                        ]
                    ):
                        if 'pending_approvals' not in st.session_state:
                            st.session_state.pending_approvals = []

                        st.session_state.pending_approvals.append({
                            "candidate_name": result['Candidate Name'],
                            "score": result['Score (%)'],
                            "experience": result['Years Experience'],
                            "jd_used": result.get('JD Used', 'N/A'),
                            "status": "pending",
                            "notes": "High-scoring candidate from screening."
                        })

                        log_activity_main(
                            f"Candidate '{result['Candidate Name']}' sent for approval."
                        )
                        st.toast(
                            f"Candidate {result['Candidate Name']} sent for approval!"
                        )

        except Exception as e:
            st.error(f"Error loading Resume Screener: {e}")

    elif st.session_state.current_page == "Manage JDs":
        try:
            manage_jds_page()
        except Exception as e:
            st.error(f"Error loading Manage JDs: {e}")

    elif st.session_state.current_page == "Screening Analytics":
        analytics_dashboard_page()

    elif st.session_state.current_page == "HR Campaign Creator":
        hr_campaign_creator_page()

    elif st.session_state.current_page == "Public Job Board":
        public_job_board_page()

    elif st.session_state.current_page == "Advanced Tools":
        from advanced import advanced_tools_page
        advanced_tools_page()

    elif st.session_state.current_page == "Collaboration Hub":
        collaboration_hub_page(
            app_id=FIREBASE_PROJECT_ID,
            FIREBASE_WEB_API_KEY=FIREBASE_WEB_API_KEY,
            FIRESTORE_BASE_URL=FIRESTORE_DATABASE_ROOT_URL
        )

    elif st.session_state.current_page == "Email Candidates":
        try:
            send_email_to_candidate()
        except Exception as e:
            st.error(f"Error loading Email Candidates: {e}")


    elif st.session_state.current_page == "Search Resumes":
        try:
            with open("search.py", encoding="utf-8") as f:
                exec(f.read())
        except Exception as e:
            st.error(f"Error loading Search Resumes: {e}")

    elif st.session_state.current_page == "Candidate Notes":
        try:
            with open("notes.py", encoding="utf-8") as f:
                exec(f.read())
        except Exception as e:
            st.error(f"Error loading Candidate Notes: {e}")

    elif st.session_state.current_page == "Live Resume Counter":
        live_resume_counter_page()
    elif st.session_state.current_page == "Payroll Management":
        payroll_management_page()

    elif st.session_state.current_page == "Employee Management":
        employee_management_page()

    elif st.session_state.current_page == "Our Clients":
        client_dashboard_page()

    elif st.session_state.current_page == "Certificate Verification":
        certificate_verification_page(
            app_id=FIREBASE_PROJECT_ID,
            FIREBASE_WEB_API_KEY=FIREBASE_WEB_API_KEY
        )

    elif st.session_state.current_page == "Partner With Us":
        partner_with_us_page()

    elif st.session_state.current_page == "About Us":
        about_us_page()

    elif st.session_state.current_page == "Privacy Policy & Terms":
        privacy_policy_page()

    elif st.session_state.current_page == "Feedback & Help":
        if 'user_email' not in st.session_state:
            st.session_state['user_email'] = st.session_state.get(
                'username', 'anonymous_user'
            )
        feedback_and_help_page()



    # =========================================================
    #  LOGOUT
    # =========================================================
    elif st.session_state.current_page == "Logout":
        log_activity_main(
            f"User '{st.session_state.get('username', 'anonymous_user')}' logged out."
        )
        st.session_state.authenticated = False
        st.session_state.pop('username', None)
        st.session_state.pop('user_email', None)
        st.session_state.pop('user_uid', None)
        st.session_state.pop('user_company', None)
        st.session_state.pop('user_status', None)

        st.success("✅ Logged out.")
        st.rerun()

    # =========================================================
    #  LOGIN / REGISTER
    # =========================================================
    elif st.session_state.current_page == "Login / Register":
        login_page_wrapper()
if __name__ == "__main__":
    main()
