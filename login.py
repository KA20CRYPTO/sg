import streamlit as st
import re
import json
import requests
import datetime
import os
import html

# ======================================================
# FIREBASE CONFIG IMPORTS
# ======================================================
from firebase_config import (
    FIRESTORE_DOCUMENTS_URL,
    FIREBASE_WEB_API_KEY,
    FIREBASE_AUTH_SIGNUP_URL,
    FIREBASE_AUTH_SIGNIN_URL,
    FIREBASE_AUTH_RESET_PASSWORD_URL,
)

from activation_email import send_activation_email
from admin_panel import log_user_login, fs_patch
def force_password_change_screen():
    st.markdown("## 🔐 Set a New Password")
    st.caption("For security reasons, you must update your password before continuing.")

    with st.form("change_password_form"):
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Update Password")

    if not submit:
        return

    # ==========================
    # VALIDATION
    # ==========================
    if not new_password or not confirm_password:
        st.error("All fields are required.")
        return

    if new_password != confirm_password:
        st.error("Passwords do not match.")
        return

    if len(new_password) < 8:
        st.error("Password must be at least 8 characters long.")
        return

    # ==========================
    # 🔑 UPDATE PASSWORD (FIREBASE)
    # ==========================
    res = requests.post(
        "https://identitytoolkit.googleapis.com/v1/accounts:update",
        params={"key": FIREBASE_WEB_API_KEY},
        json={
            "idToken": st.session_state.temp_id_token,
            "password": new_password,
            "returnSecureToken": True
        }
    )

    if res.status_code != 200:
        st.error("❌ Failed to update password.")
        return

    # ==========================
    # ✅ PATCH FIRESTORE (SAFE – NO OVERWRITE)
    # ==========================
    fs_patch(
        f"user_profiles/{st.session_state.temp_user_uid}",
        {
            "must_change_password": False,
            "password_changed_at": datetime.datetime.utcnow().isoformat()
        }
    )

    # ==========================
    # 🔄 RELOAD FULL PROFILE (CRITICAL FIX)
    # ==========================
    load_profile_from_firestore(st.session_state.temp_user_uid)

    # ==========================
    # 🔐 FINALIZE AUTH SESSION
    # ==========================
    st.session_state.authenticated = True
    st.session_state.username = st.session_state.temp_email
    st.session_state.user_email = st.session_state.temp_email
    st.session_state.user_uid = st.session_state.temp_user_uid

    # ==========================
    # 🧹 CLEAN TEMP SESSION STATE
    # ==========================
    for k in (
        "force_password_change",
        "temp_user_uid",
        "temp_id_token",
        "temp_email"
    ):
        st.session_state.pop(k, None)

    st.success("✅ Password updated successfully")
    st.rerun()

# ======================================================
# FIRESTORE REST CONFIG
# ======================================================
FIREBASE_PROJECT_ID = os.environ.get("__app_id", "screenerproapp")

FIRESTORE_DATABASE_ROOT_URL = (
    f"https://firestore.googleapis.com/v1/projects/"
    f"{FIREBASE_PROJECT_ID}/databases/(default)"
)

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

ADMIN_EMAILS = (
    "admin@forscreenerpro.com",
    "admin@forscreenerpro2.com",
    "manav.nagpal2005@gmail.com",
)

# ======================================================
# HELPERS
# ======================================================
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)


def firestore_format(data: dict):
    return {"fields": {k: {"stringValue": str(v)} for k, v in data.items()}}


def load_legal_doc(path):
    url = f"{FIRESTORE_DOCUMENTS_URL}/{path}?key={FIREBASE_WEB_API_KEY}"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    try:
        fields = r.json().get("fields", {})
        return {k: v.get("stringValue", "") for k, v in fields.items()}
    except Exception:
        return None


# ======================================================
# PROFILE LOADER (UID BASED)
# ======================================================
def load_profile_from_firestore(uid):
    url = (
        f"{FIRESTORE_DATABASE_ROOT_URL}/documents/user_profiles/{uid}"
        f"?key={FIREBASE_WEB_API_KEY}"
    )

    r = requests.get(url)
    if r.status_code != 200:
        return

    fields = r.json().get("fields", {})

    def _get_string(k):
        return fields.get(k, {}).get("stringValue", "")

    def _get_bool(k):
        return fields.get(k, {}).get("booleanValue", False)

    # 🔹 BASIC PROFILE
    st.session_state.user_full_name = _get_string("full_name")
    st.session_state.user_company = _get_string("company")
    st.session_state.user_phone = _get_string("phone")
    st.session_state.user_role = _get_string("role")
    st.session_state.user_avatar_base64 = _get_string("avatar_base64")

    # 🔹 COMPANY ADMIN FLAG (🔥 CRITICAL)
    st.session_state.is_company_admin = _get_bool("is_company_admin")

    # 🔹 OPTIONAL (future-proof)
    st.session_state.user_department = _get_string("department")
    st.session_state.user_location = _get_string("location")
    st.session_state.user_linkedin = _get_string("linkedin")

# ======================================================
# FIRESTORE HELPERS
# ======================================================
def save_pending_user(email, data):
    email_doc = email.replace(".", "_").replace("@", "_")
    url = f"{FIRESTORE_DOCUMENTS_URL}/pending_users/{email_doc}?key={FIREBASE_WEB_API_KEY}"
    return requests.patch(url, json=firestore_format(data))


def check_user_verified(email):
    email_doc = email.replace(".", "_").replace("@", "_")
    url = f"{FIRESTORE_DOCUMENTS_URL}/pending_users/{email_doc}?key={FIREBASE_WEB_API_KEY}"
    r = requests.get(url)
    if r.status_code != 200:
        return True
    return r.json().get("fields", {}).get("isVerified", {}).get("booleanValue", False)


def move_pending_to_verified(email, uid):
    email_doc = email.replace(".", "_").replace("@", "_")
    pending_url = f"{FIRESTORE_DOCUMENTS_URL}/pending_users/{email_doc}?key={FIREBASE_WEB_API_KEY}"

    r = requests.get(pending_url).json()
    pending = r.get("fields", {})

    profile = {
        "email": email,
        "company": pending.get("company", {}).get("stringValue", ""),
        "status": "active",
        "verified_at": datetime.datetime.utcnow().isoformat(),
        "terms_accepted_at": pending.get("terms_accepted_at", {}).get("stringValue", ""),
    }

    fs_patch(f"user_profiles/{uid}", profile)
    requests.delete(pending_url)
    return profile


def get_user_profile_firestore(uid, id_token):
    headers = {"Authorization": f"Bearer {id_token}"}
    r = requests.get(
        f"{FIRESTORE_DOCUMENTS_URL}/user_profiles/{uid}",
        headers=headers
    )

    if r.status_code != 200:
        return None

    fields = r.json().get("fields", {})
    profile = {}

    for k, v in fields.items():
        if "stringValue" in v:
            profile[k] = v["stringValue"]
        elif "booleanValue" in v:
            profile[k] = v["booleanValue"]
        else:
            profile[k] = None

    return profile


# ======================================================
# PASSWORD RESET
# ======================================================
def reset_password(email):
    if not email:
        st.warning("Enter email first.")
        return

    payload = {"requestType": "PASSWORD_RESET", "email": email}
    r = requests.post(FIREBASE_AUTH_RESET_PASSWORD_URL, json=payload)
    if r.status_code == 200:
        st.success("📧 Password reset email sent.")
    else:
        st.error("❌ Failed to send reset email.")


# ======================================================
# LEGAL DIALOGS
# ======================================================
@st.dialog("🔐 Privacy Policy", width="large")
def privacy_dialog():
    policy = load_legal_doc("site_content/privacy_policy")
    if not policy:
        st.error("Privacy policy not available.")
        return
    st.markdown(html.unescape(policy.get("html", "")), unsafe_allow_html=True)


@st.dialog("📜 Terms & Conditions", width="large")
def terms_dialog():
    terms = load_legal_doc("site_content/terms_conditions")
    if not terms:
        st.error("Terms not available.")
        return
    st.markdown(html.unescape(terms.get("html", "")), unsafe_allow_html=True)


# ======================================================
# REGISTER SECTION
# ======================================================
def register_section():
    st.markdown("## 📝 Create Account")

    if st.button("⬅ Back to Login"):
        st.session_state.active_login_tab_selection = "Login"
        st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📜 View Terms & Conditions"):
            terms_dialog()
    with col2:
        if st.button("🔐 View Privacy Policy"):
            privacy_dialog()

    with st.form("register_form", clear_on_submit=True):
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        company = st.text_input("Company")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        agree = st.checkbox("I accept Terms & Privacy Policy")
        submit = st.form_submit_button("Create Account")

    if not submit:
        return

    if not agree:
        st.error("You must accept Terms & Privacy Policy.")
        return

    if not all([name, email, company, password, confirm]):
        st.error("Fill all fields.")
        return

    if password != confirm:
        st.error("Passwords do not match.")
        return

    auth_res = requests.post(
        FIREBASE_AUTH_SIGNUP_URL,
        json={"email": email, "password": password, "returnSecureToken": True},
    )

    if auth_res.status_code != 200:
        st.error("Signup failed.")
        return

    token = os.urandom(16).hex()
    now = datetime.datetime.utcnow().isoformat()

    save_pending_user(
        email,
        {
            "email": email,
            "name": name,
            "company": company,
            "isVerified": False,
            "activation_token": token,
            "created_at": now,
            "terms_accepted_at": now,
        },
    )

    send_activation_email(
        email,
        name,
        f"https://screenerpro.streamlit.app/?activate={token}&email={email}",
    )

    st.success("🎉 Account created! Check email to activate.")
    st.stop()


# ======================================================
# LOGIN SECTION
# ======================================================
def login_section():

    if "active_login_tab_selection" not in st.session_state:
        st.session_state.active_login_tab_selection = "Login"

    # ==================================================
    # REGISTER VIEW
    # ==================================================
    
    if st.session_state.active_login_tab_selection == "Register":
        register_section()
        return False

    # ==================================================
    # 🎨 CUSTOM LOGIN UI STYLING (PURPLE GLASSMORPHISM)
    # ==================================================
    st.markdown("""
    <style>
    /* 1. Global Background - Deep Purple Gradient */
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgb(69, 43, 104) 0%, rgb(28, 0, 50) 90%);
        background-attachment: fixed;
    }

    /* 2. Glassmorphism Card (Form Container) */
    div[data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 3rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        max-width: 450px;
        margin: 0 auto; /* Center horizontally */
    }

    /* 3. Input Fields - Transparent Glass Style */
    .stTextInput > div > div > input {
        background: rgba(0, 0, 0, 0.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 12px 15px !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: rgba(255, 255, 255, 0.6);
    }
    .stTextInput > label {
        color: rgba(255, 255, 255, 0.8) !important;
    }

    /* 4. "Login" Button - Neon Gradient */
    div[data-testid="stForm"] .stButton > button {
        background: linear-gradient(90deg, #a18cd1 0%, #fbc2eb 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: bold !important;
        font-size: 1.2rem !important;
        text-transform: uppercase;
        border-radius: 12px !important;
        padding: 0.8rem 0 !important;
        width: 100%;
        box-shadow: 0 4px 15px rgba(251, 194, 235, 0.4);
        transition: all 0.3s ease;
    }
    div[data-testid="stForm"] .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(251, 194, 235, 0.6);
    }

    /* 5. "Sign Up with Google" Button - Outline Style */
    .google-btn-container {
        display: flex;
        justify-content: center;
        margin-top: 1rem;
    }
    .google-btn {
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: white;
        padding: 10px 20px;
        border-radius: 30px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 10px;
        text-decoration: none;
        transition: background 0.3s;
        font-size: 0.9rem;
    }
    .google-btn:hover {
        background: rgba(255, 255, 255, 0.1);
    }
    
    /* 6. Headers & Text */
    .shruhh-logo {
        font-family: 'Arial', sans-serif;
        font-size: 3rem;
        font-weight: 100;
        color: rgba(255, 255, 255, 0.9);
        text-align: center;
        letter-spacing: 2px;
        margin-bottom: 0px;
    }
    .shruhh-icon {
        font-size: 4rem;
        text-align: center;
        display: block;
        /* Using a unicode character as a placeholder logo shape if needed, or just text */
        color: rgba(161, 140, 209, 0.8);
        margin-bottom: -20px;
    }
    .welcome-text {
        color: rgba(255, 255, 255, 0.9);
        text-align: center;
        font-size: 1.2rem;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    /* Hide the standard "Forgot Password" button inside form to reposition it? 
       Actually, standard Streamlit columns inside forms can be tricky with width. 
       We will keep them for now but maybe style the secondary button differently.
    */
    
    /* Remove default main padding interactions if they conflict */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 100% !important;
    }
    
    </style>
    """, unsafe_allow_html=True)

    # ==================================================
    # LOGIN VIEW
    # ==================================================
    
    # Logo & Welcome Header
    st.markdown("""
        <div class="shruhh-icon">▱</div> 
        <h1 class="shruhh-logo">SHRUHH</h1>
        <p class="welcome-text">Welcome Back, User</p>
    """, unsafe_allow_html=True)

    col_spacer_l, col_form, col_spacer_r = st.columns([1, 2, 1])

    with col_form:
        with st.form("login_form"):
            email = st.text_input("Email address")
            password = st.text_input("Password", type="password")
            
            # Forgot Password link (Visual Only for now text-wise, actionable via button below?)
            # Streamlit forms require buttons to be submit buttons or they don't work reliably inside.
            # We will use the existing logic but style it.
            
            st.markdown("<p style='text-align: right; color: rgba(255,255,255,0.7); font-size: 0.8rem; cursor: pointer;'>Forget Password?</p>", unsafe_allow_html=True)

            # Main Login Button
            login_btn = st.form_submit_button("Login")
            
            # Hidden Reset Button Trigger (Workaround to keep existing logic if needed, 
            # or we can move Forgot Password outside the form if it was a separate button)
            # The original code had two buttons in columns: Login and Forgot Password.
            # To match the UI, "Forgot Password?" is usually a link.
            # For this implementation, I will keep the logical button invisible or secondary if strictly needed,
            # but the requested UI shows a single big layout. 
            # I will add a secondary "Forgot Password" submit button for functionality preservation but styled minimally if possible,
            # OR just rely on the user typing email and hitting a 'reset' action we provide below.
            
            # Let's stick to the visual request: Big Login Button.
            # I will place the "Forgot Password" functional button below the form or make it a small link-like button.
            
        # We need to preserve the `reset_btn` logic from the original code which was:
        # col1, col2 = st.columns(2)
        # login_btn = col1.form_submit_button("Login")
        # reset_btn = col2.form_submit_button("Forgot Password")
        
        # Since I replaced the form content, `reset_btn` is gone from the form scope.
        # I must handle it. The UI image shows "Forget Password ?" as text.
        # In Streamlit, making a clickable text trigger an action without a page reload/button is hard.
        # I will add a "Forgot your password?" button OUTSIDE the form or inside as a secondary transparent button.
        
    # Re-instantiate reset_btn logic outside standard form flow or add a secondary button.
    # To match the "Single Card" look, I'll put it below or finding a way.
    # For now, let's keep it simple: generic Streamlit button for "Forgot Password" below the form, styled to look like text.
    
    col_centered = st.columns([1, 1, 1])
    with col_centered[1]:
         if st.button("Forgot Password?", type="secondary", key="forgot_pass_link"):
             st.session_state.reset_password_trigger = True
    
    if st.session_state.get("reset_password_trigger"):
         reset_btn = True
         st.session_state.reset_password_trigger = False # Reset trigger
    else:
         reset_btn = False

    # Google Sign Up Button (Fake/UI only as requested)
    st.markdown("""
        <div class="google-btn-container">
            <button class="google-btn">
                <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" width="18" height="18">
                Sign Up with Google
            </button>
        </div>
    """, unsafe_allow_html=True)

    # Sign Up Link
    st.markdown("""
        <div style="text-align: center; margin-top: 2rem; color: rgba(255,255,255,0.7);">
            Are You New Member? 
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Sign UP", type="primary", use_container_width=True):
         st.session_state.active_login_tab_selection = "Register"
         st.rerun()



    # ==================================================
    # 🔁 MANUAL PASSWORD RESET
    # ==================================================
    if reset_btn:
        if not email:
            st.warning("Please enter your email first.")
            return False

        reset_password(email)
        st.success("📧 Password reset link sent (if account exists).")
        return False

    # ==================================================
    # LOGIN NOT SUBMITTED
    # ==================================================
    if not login_btn:
        st.markdown("---")
        if st.button("Create an Account"):
            st.session_state.active_login_tab_selection = "Register"
            st.rerun()
        return False

    # ==================================================
    # AUTHENTICATE WITH FIREBASE
    # ==================================================
    auth_res = requests.post(
        FIREBASE_AUTH_SIGNIN_URL,
        json={
            "email": email,
            "password": password,
            "returnSecureToken": True
        },
    )

    if auth_res.status_code != 200:
        st.error("❌ Invalid email or password.")
        st.info("💡 If admin created your account, use the temporary password sent to you.")
        return False

    auth = auth_res.json()
    uid = auth["localId"]
    id_token = auth["idToken"]

    # ==================================================
    # EMAIL VERIFICATION CHECK
    # ==================================================
    if not check_user_verified(email):
        st.error("❌ Please activate your account first.")
        return False

    # ==================================================
    # LOAD PROFILE FROM FIRESTORE
    # ==================================================
    profile = get_user_profile_firestore(uid, id_token)
    if not profile:
        profile = move_pending_to_verified(email, uid)

    # ==================================================
    # ⛔ BLOCK DEACTIVATED USERS (🔥 CRITICAL)
    # ==================================================
    if profile.get("status") == "inactive":
        st.error("⛔ Your account has been deactivated by your administrator.")
        st.info("Please contact your company admin to regain access.")
        return False

    # ==================================================
    # 🔐 SaaS PASSWORD CHANGE ENFORCEMENT
    # ==================================================
    if profile.get("must_change_password") is True:
        st.session_state.force_password_change = True
        st.session_state.temp_user_uid = uid
        st.session_state.temp_id_token = id_token
        st.session_state.temp_email = email
        st.rerun()

    # ==================================================
    # AUTH SESSION (NORMAL LOGIN)
    # ==================================================
    st.session_state.authenticated = True
    st.session_state.username = email
    st.session_state.user_email = email
    st.session_state.user_uid = uid
    st.session_state.user_status = profile.get("status", "active")

    # ==================================================
    # LOAD FULL PROFILE
    # ==================================================
    load_profile_from_firestore(uid)

    # ==================================================
    # SAFE DEFAULTS
    # ==================================================
    for key in [
        "user_full_name",
        "user_company",
        "user_phone",
        "user_role",
        "user_avatar_base64",
    ]:
        st.session_state[key] = st.session_state.get(key) or ""

    log_user_login(uid)
    st.rerun()




# ======================================================
# ADMIN CHECK
# ======================================================
def is_current_user_admin():
    return (
        st.session_state.get("authenticated", False)
        and st.session_state.get("username") in ADMIN_EMAILS
    )










