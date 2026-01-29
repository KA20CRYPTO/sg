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
    # 🎨 PREMIUM LOGIN UI (BLUE THEME)
    # ==================================================

    # We rely on style.css for global background. 
    # Here we inject specific login animations if needed, but mostly use structure.

    # ==================================================
    # LOGIN VIEW
    # ==================================================
    
    # Centered Layout with Glass Card
    st.markdown("""
        <div class="animate-fade-in" style="display: flex; justify-content: center; align-items: center; min-height: 80vh;">
            <div class="glass-card animate-slide-up" style="width: 100%; max-width: 480px; text-align: center;">
                <div style="font-size: 3.5rem; margin-bottom: 1rem; animation: pulse-glow 3s infinite;">🧠</div>
                <h1 style="color: white; margin-bottom: 0.5rem; font-size: 2.2rem;">Screener Pro HR</h1>
                <p style="color: var(--text-secondary); margin-bottom: 2.5rem;">Enterprise AI Recruitment Platform</p>
                
                <!-- Placeholder for Form Injection -->
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # We need to inject the form INSIDE the glass card, but Streamlit forms are top-level blocks.
    # To simulate this visually, we can't easily nest a Streamlit form inside an HTML div open tag 
    # that closes in another markdown block because Streamlit renders blocks sequentially.
    
    # WORKAROUND: We use standard Streamlit form but style it to look like it is inside the card
    # purely via CSS targeting `[data-testid="stForm"]`. 
    # In style.css, we already added .glass-card styles. 
    # We will just rely on the 'stForm' targeting in style.css or add a specific one here.
    
    # Let's adjust style.css approach or use a container.
    # Given the previous step updated styles globally, let's just render the form and header.
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
         # Header
         st.markdown("""
            <div style="text-align: center; margin-bottom: 2rem;" class="animate-slide-up">
                <div style="font-size: 4rem; margin-bottom: 0.5rem; text-shadow: 0 0 20px var(--accent-blue);">🧠</div>
                <h1 style="background: linear-gradient(to right, #fff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.5rem; font-weight: 800;">Screener Pro HR</h1>
                <p style="color: #94a3b8; font-size: 1.1rem; letter-spacing: 1px;">AI-Powered Recruitment</p>
            </div>
         """, unsafe_allow_html=True)

         with st.form("login_form"):
            st.markdown('<div style="padding-top: 10px;"></div>', unsafe_allow_html=True)
            email = st.text_input("Work Email", placeholder="recruiter@company.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            
            st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
            
            submitted = st.form_submit_button("Sign In to Dashboard", type="primary", use_container_width=True)
            
            if submitted:
                 login_btn = True # Logical mapping
            else:
                 login_btn = False

    # Footer Actions
    st.markdown("""
        <div style="text-align: center; margin-top: 1.5rem;" class="animate-fade-in">
            <a href="#" style="color: var(--text-secondary); text-decoration: none; font-size: 0.9rem; margin-right: 15px;">Forgot Password?</a>
            <span style="color: var(--glass-border);">|</span>
            <a href="#" style="color: var(--accent-blue); text-decoration: none; font-size: 0.9rem; margin-left: 15px; font-weight: 600;">Request Access</a>
        </div>
    """, unsafe_allow_html=True)
    
    # We emulate the return logic expected by the original code
    reset_btn = False 

    # Logic Handling (kept essentially same as before but variable names mapped)




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










