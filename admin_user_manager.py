import streamlit as st
import requests
import datetime
import secrets
import string

from firebase_config import (
    FIRESTORE_DOCUMENTS_URL,
    FIREBASE_WEB_API_KEY,
    FIREBASE_AUTH_SIGNUP_URL,
)

# 🔔 EXISTING EMAIL FUNCTION (DO NOT CHANGE)
from activation_email import send_activation_email


# ==================================================
# 🔐 HELPERS
# ==================================================

def generate_temp_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(chars) for _ in range(length))


def firestore_format(data: dict):
    fields = {}
    for k, v in data.items():
        if isinstance(v, bool):
            fields[k] = {"booleanValue": v}
        else:
            fields[k] = {"stringValue": str(v)}
    return {"fields": fields}


def save_pending_user(email: str, payload: dict):
    email_doc = email.replace(".", "_").replace("@", "_")
    url = f"{FIRESTORE_DOCUMENTS_URL}/pending_users/{email_doc}?key={FIREBASE_WEB_API_KEY}"
    return requests.patch(url, json=firestore_format(payload))


def get_same_company_users(company_name: str):
    if not company_name:
        return []

    url = f"{FIRESTORE_DOCUMENTS_URL}:runQuery?key={FIREBASE_WEB_API_KEY}"

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
                doc = item["document"]
                fields = doc.get("fields", {})
                user = {
                    k: v.get("stringValue") or v.get("booleanValue")
                    for k, v in fields.items()
                }
                user["id"] = doc["name"].split("/")[-1]
                users.append(user)

    return users


# ==================================================
# 📩 INVITATION EMAIL (NEW)
# ==================================================

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_invitation_email(email, company, role, temp_password):
    """
    Sends an invitation email with temporary credentials
    using SMTP (Gmail App Password).
    """

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USER = "screenerpro.ai@gmail.com"        # ✅ your email
    SMTP_PASSWORD = "udwi life nbdv kgdt"     # ❗ app password only

    subject = "👋 You’ve been invited to ScreenerPro"

    html_body = f"""
    <html>
    <body style="font-family: Inter, Arial, sans-serif; background:#f7f9fc; padding:30px;">
        <table width="600" align="center"
               style="background:#ffffff; border-radius:12px; padding:30px;
                      box-shadow:0 10px 30px rgba(0,0,0,0.1);">

            <tr>
                <td style="text-align:center;">
                    <h1 style="color:#2563eb; margin-bottom:5px;">
                        You’re Invited 🎉
                    </h1>
                    <p style="color:#555; font-size:15px;">
                        Welcome to <b>ScreenerPro</b>
                    </p>
                </td>
            </tr>

            <tr><td style="height:20px;"></td></tr>

            <tr>
                <td style="font-size:15px; color:#333;">
                    <p>
                        You have been invited to join
                        <b>{company}</b> on ScreenerPro.
                    </p>

                    <p><b>Role:</b> {role}</p>

                    <div style="background:#f1f5f9; padding:16px;
                                border-radius:8px; margin:20px 0;">
                        <p style="margin:0;"><b>Login Credentials</b></p>
                        <p style="margin:6px 0;">📧 Email: <b>{email}</b></p>
                        <p style="margin:6px 0;">🔐 Temporary Password:
                           <b>{temp_password}</b></p>
                    </div>

                    <p style="color:#dc2626;">
                        ⚠️ This password is temporary.<br>
                        You must reset it after first login.
                    </p>

                    <div style="text-align:center; margin:30px 0;">
                        <a href="https://screenerpro.streamlit.app"
                           style="background:#2563eb; color:#ffffff;
                                  padding:14px 28px; border-radius:8px;
                                  text-decoration:none; font-weight:600;">
                            Login to ScreenerPro
                        </a>
                    </div>

                    <p style="font-size:13px; color:#666;">
                        If you were not expecting this invitation,
                        you can safely ignore this email.
                    </p>
                </td>
            </tr>

            <tr><td style="height:20px;"></td></tr>

            <tr>
                <td style="text-align:center; font-size:12px; color:#999;">
                    © 2025 ScreenerPro • AI Hiring Intelligence Platform
                </td>
            </tr>

        </table>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = email
        msg.attach(MIMEText(html_body, "html"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, email, msg.as_string())
        server.quit()

        return True

    except Exception as e:
        print("❌ Invitation email failed:", e)
        return False


def admin_user_manager():

    # --------------------------
    # AUTH GUARD
    # --------------------------
    if not st.session_state.get("authenticated", False):
        st.warning("Please login first.")
        return

    # --------------------------
    # COMPANY ADMIN GUARD
    # --------------------------
    if not st.session_state.get("is_company_admin", False):
        st.warning("⛔ Only company admins can manage users.")
        return

    company_name = (st.session_state.get("user_company") or "").strip()
    if not company_name:
        st.error("Company not set for your account.")
        return

    # --------------------------
    # HEADER
    # --------------------------
    st.header("👑 Admin User Manager")
    st.caption("Create users with auto-generated credentials")

    st.divider()

    # ==================================================
    # ➕ CREATE USER (AUTO PASSWORD)
    # ==================================================
    st.subheader("➕ Create User")

    col1, col2 = st.columns(2)

    with col1:
        email = st.text_input("User Email")
        full_name = st.text_input("Full Name")
        role = st.selectbox("Role", ["hr", "recruiter", "manager", "viewer"])

    with col2:
        department = st.text_input("Department")
        st.text_input("Company", company_name, disabled=True)

    if st.button("🚀 Create User", type="primary"):
        if not email or not full_name:
            st.error("Email and full name are required.")
            return

        # 🔐 Generate password
        temp_password = generate_temp_password()

        # --------------------------
        # CREATE FIREBASE AUTH USER
        # --------------------------
        auth_res = requests.post(
            FIREBASE_AUTH_SIGNUP_URL,
            json={
                "email": email,
                "password": temp_password,
                "returnSecureToken": True,
            }
        )

        if auth_res.status_code != 200:
            st.error("❌ Failed to create Firebase Auth user.")
            st.json(auth_res.json())
            return

        uid = auth_res.json()["localId"]

        # --------------------------
        # SAVE USER PROFILE
        # --------------------------
        profile_payload = {
            "email": email,
            "full_name": full_name,
            "company": company_name,
            "role": role,
            "department": department,
            "status": "active",
            "is_company_admin": False,
            "must_change_password": True,
            "password_changed_at": None,
            "created_by": st.session_state.get("username"),
            "created_at": datetime.datetime.utcnow().isoformat(),
        }

        profile_url = (
            f"{FIRESTORE_DOCUMENTS_URL}/user_profiles/{uid}"
            f"?key={FIREBASE_WEB_API_KEY}"
        )

        profile_res = requests.patch(
            profile_url,
            json=firestore_format(profile_payload)
        )

        if profile_res.status_code not in (200, 201):
            st.error("❌ User created in Auth but profile save failed.")
            return

        # --------------------------
        # ACTIVATION TOKEN
        # --------------------------
        activation_token = secrets.token_hex(16)

        save_pending_user(
            email,
            {
                "email": email,
                "company": company_name,
                "isVerified": False,
                "created_by_admin": True,
                "activation_token": activation_token,
                "created_at": datetime.datetime.utcnow().isoformat(),
            }
        )

        activation_link = (
            f"https://screenerpro.streamlit.app/"
            f"?activate={activation_token}&email={email}"
        )

        # --------------------------
        # 📩 SEND EMAILS
        # --------------------------
        send_invitation_email(
            email=email,
            company=company_name,
            role=role,
            temp_password=temp_password
        )

        send_activation_email(
            email,
            full_name,
            activation_link
        )

        # --------------------------
        # UI CONFIRMATION
        # --------------------------
        st.success("✅ User created & emails sent")

        st.info("📩 Invitation + activation emails delivered")

    # ==================================================
    # 👥 COMPANY USERS
    # ==================================================
    st.divider()
    st.subheader("👥 Company Users")

    users = get_same_company_users(company_name)

    # if st.checkbox("🔍 Debug: show raw users"):
    #     st.json(users)

    if not users:
        st.info("No users found.")
        return

    for user in users:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])

            full_name = user.get("full_name", "—")
            role = user.get("role", "—")
            department = user.get("department", "—")
            email = user.get("email", "—")
            status = user.get("status", "active")

            # 👤 USER INFO
            c1.markdown(f"**{full_name}**")
            c2.write(role)
            c3.write(department)
            c4.caption(email)

            # --------------------------
            # 🚦 STATUS + ACTION
            # --------------------------
            if status == "active":
                c4.markdown("🟢 **Active**")
                if st.button("⛔ Deactivate", key=f"deact_{user['id']}"):
                    requests.patch(
                        f"{FIRESTORE_DOCUMENTS_URL}/user_profiles/{user['id']}?key={FIREBASE_WEB_API_KEY}",
                        json={
                            "fields": {
                                "status": {"stringValue": "inactive"}
                            }
                        }
                    )
                    st.warning("User deactivated")
                    st.rerun()
            else:
                c4.markdown("🔴 **Inactive**")
                if st.button("✅ Reactivate", key=f"react_{user['id']}"):
                    requests.patch(
                        f"{FIRESTORE_DOCUMENTS_URL}/user_profiles/{user['id']}?key={FIREBASE_WEB_API_KEY}",
                        json={
                            "fields": {
                                "status": {"stringValue": "active"}
                            }
                        }
                    )
                    st.success("User reactivated")
                    st.rerun()
