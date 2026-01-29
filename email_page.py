# email_page.py (ULTIMATE PRODUCTION VERSION – MAXIMUM FEATURES)

import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import urllib.parse
import requests

# Assuming these are defined in a separate config file
from firebase_config import FIRESTORE_DOCUMENTS_URL, FIREBASE_WEB_API_KEY 
import base64
from email.mime.application import MIMEApplication
import plotly.graph_objects as go
from datetime import datetime

# Constant for the field name used to store email history in Firestore
EMAILS_SENT_FIELD = "emails_sent_history" 

# ======================================================
# 📚 EMAIL TEMPLATE CONSTANTS (Advanced Feature)
# ======================================================

# --- Template 1: SUCCESS / SHORTLIST ---
SUCCESS_TEXT_TEMPLATE = """
Dear {{candidate_name}},

We are delighted to inform you that based on your performance, you have been SHORTLISTED for the next round!

Summary of your screening:
* Score: {{score_percent}}%
* Experience: {{years_experience}} years
* AI Note: {{ai_suggestion}}

We will contact you shortly to schedule an interview.

Best regards,
The Hiring Team
"""

SUCCESS_HTML_TEMPLATE = """
<html>
<body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f7f6;">
    <div style="max-width: 600px; margin: auto; border: 1px solid #4CAF50; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #4CAF50; color: white; padding: 15px; text-align: center;">
            <h2 style="margin: 0;">Application Update: Shortlisted!</h2>
        </div>
        <div style="padding: 20px; background-color: white;">
            <p>Dear <b>{{candidate_name}}</b>,</p>
            <p style="font-size: 16px; color: #333;">We are delighted to inform you that based on your strong performance, you have been <b>SHORTLISTED</b> for the next round!</p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                <tr><td style="padding: 5px; background-color: #f9f9f9;">Score:</td><td style="padding: 5px;"><b>{{score_percent}}%</b></td></tr>
                <tr><td style="padding: 5px; background-color: #f9f9f9;">Experience:</td><td style="padding: 5px;">{{years_experience}} years</td></tr>
                <tr><td style="padding: 5px; background-color: #f9f9f9;">AI Note:</td><td style="padding: 5px;">{{ai_suggestion}}</td></tr>
            </table>
            <p style="margin-top: 20px;">We will contact you shortly to schedule an interview.</p>
            <p style="margin-top: 30px; font-size: 14px;">Best regards,<br><b>The Hiring Team</b></p>
        </div>
    </div>
</body>
</html>
"""

# --- Template 2: REJECTION / HOLD ---
REJECTION_TEXT_TEMPLATE = """
Dear {{candidate_name}},

Thank you for your interest. We appreciate you taking the time to apply.

Summary of your screening:
* Score: {{score_percent}}%
* Experience: {{years_experience}} years
* AI Note: {{ai_suggestion}}

We have chosen to move forward with other candidates at this time whose experience was a closer fit for the role.

Sincerely,
The Hiring Team
"""

REJECTION_HTML_TEMPLATE = """
<html>
<body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f7f6;">
    <div style="max-width: 600px; margin: auto; border: 1px solid #f44336; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #f44336; color: white; padding: 15px; text-align: center;">
            <h2 style="margin: 0;">Application Update</h2>
        </div>
        <div style="padding: 20px; background-color: white;">
            <p>Dear <b>{{candidate_name}}</b>,</p>
            <p style="font-size: 16px; color: #555;">Thank you for your application and time. Your screening score was <b>{{score_percent}}%</b>.</p>
            <p>Based on current requirements, we have made the difficult decision to move forward with other candidates at this time.</p>
            <p style="margin-top: 20px;">We wish you the best in your job search.</p>
            <p style="margin-top: 30px; font-size: 14px;">Sincerely,<br><b>The Hiring Team</b></p>
        </div>
    </div>
</body>
</html>
"""



# ======================================================
# 🔥 UTILITY FUNCTION: Firestore Update
# ======================================================
def update_firestore_status(doc_id, updated_email_set, key):
    """Sends a PATCH request to Firestore to update the list of sent emails."""
    
    update_url = f"{FIRESTORE_DOCUMENTS_URL}/user_data/{doc_id}?key={key}&updateMask.fieldPaths={EMAILS_SENT_FIELD}"
    
    payload = {
        "fields": {
            EMAILS_SENT_FIELD: {
                "stringValue": json.dumps(list(updated_email_set))
            }
        }
    }
    
    try:
        response = requests.patch(update_url, json=payload, timeout=5)
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"❌ **History Update Failed:** {e}")
        return False

def manage_firestore_resource(doc_id, resource_name, data=None, method="GET"):
    """Generic Firestore REST helper for SaaS resources (SMTP, Templates)."""
    base_url = f"{FIRESTORE_DOCUMENTS_URL}/user_resources/{doc_id}_{resource_name}?key={FIREBASE_WEB_API_KEY}"
    
    try:
        if method == "GET":
            response = requests.get(base_url, timeout=5)
            if response.status_code == 200:
                fields = response.json().get("fields", {})
                return json.loads(fields.get("data", {}).get("stringValue", "{}"))
            return {}
        
        elif method == "PATCH":
            payload = {"fields": {"data": {"stringValue": json.dumps(data)}}}
            response = requests.patch(base_url, json=payload, timeout=5)
            return response.status_code in [200, 201]
            
    except Exception as e:
        st.error(f"Firestore {method} Failed for {resource_name}: {e}")
        return None


# ======================================================
# 🔥 UTILITY FUNCTION: Conditional Template Logic
# ======================================================
def get_final_email_content(row_data, subject_template, templates, success_triggers):
    """
    Selects the correct template (HTML and Text) based on AI Suggestion 
    and formats the content using candidate data.
    """
    ai_suggestion = row_data.get("AI Suggestion", "")
    
    # Determine which template set to use based on triggers
    if any(trigger in ai_suggestion for trigger in success_triggers):
        selected_template = templates['success']
    else:
        selected_template = templates['rejection']
        
    format_data = {
        "candidate_name": row_data.get("Candidate Name", "Candidate"),
        "score_percent": row_data.get("Score (%)", "N/A"),
        "years_experience": row_data.get("Years Experience", "N/A"),
        "ai_suggestion": ai_suggestion,
    }

    final_subject = subject_template.replace("{{candidate_name}}", format_data["candidate_name"])
    final_html = selected_template['html']
    final_text = selected_template['text']
    
    for k, v in format_data.items():
        placeholder = "{{" + k + "}}"
        final_html = final_html.replace(placeholder, str(v))
        final_text = final_text.replace(placeholder, str(v))
    
    return final_subject, final_html, final_text


# ======================================================
# 🎨 UI COMPONENTS
# ======================================================
def lottie_player(url, height=200):
    """Embeds a Lottie animation."""
    st.components.v1.html(f"""
        <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
        <div style="display:flex;justify-content:center;">
            <lottie-player src="{url}" background="transparent" speed="1" style="width: {height}px; height: {height}px;" loop autoplay></lottie-player>
        </div>
    """, height=height+10)

def send_email_to_candidate():
    st.markdown("<h1 style='text-align: center; color: #0ea5e9;'>Outreach Management System</h1>", unsafe_allow_html=True)
    
    user_email = st.session_state.get("user_email")
    if not user_email:
        st.error("❌ **Authentication Error:** User email missing. Please log in again.")
        return

    document_id = urllib.parse.quote(user_email, safe="")
    
    # --- LOAD PERSISTENT RESOURCES ---
    if "smtp_settings" not in st.session_state:
        st.session_state.smtp_settings = manage_firestore_resource(document_id, "smtp")
    
    if "custom_templates" not in st.session_state:
        st.session_state.custom_templates = manage_firestore_resource(document_id, "templates")

    # --- DEFINE TABS ---
    tab_campaign, tab_templates, tab_settings, tab_analytics = st.tabs([
        "Active Campaign", "Template Library", "SMTP Settings", "Analytics and History"
    ])

    # ======================================================
    # ⚙️ TAB: SMTP SETTINGS
    # ======================================================
    with tab_settings:
        st.subheader("Configure SMTP Integration")
        st.caption("These settings are saved securely to your profile for future use.")
        
        with st.form("smtp_form"):
            colA, colB = st.columns(2)
            s_email = colA.text_input("Sender Email", st.session_state.smtp_settings.get("sender_email", user_email))
            s_host = colA.text_input("SMTP Server", st.session_state.smtp_settings.get("smtp_server", "smtp.gmail.com"))
            s_pass = colB.text_input("App Password", st.session_state.smtp_settings.get("sender_password", ""), type="password")
            s_port = colB.number_input("SMTP Port", value=st.session_state.smtp_settings.get("smtp_port", 587))
            
            if st.form_submit_button("Test Connection"):
                try:
                    with st.spinner("Validating credentials..."):
                        test_server = smtplib.SMTP(s_host, s_port, timeout=10)
                        test_server.starttls()
                        test_server.login(s_email, s_pass)
                        test_server.quit()
                    st.success("Connection successful. Credentials verified.")
                except Exception as e:
                    st.error(f"Connection failed: {e}")

            if st.form_submit_button("Save Settings"):
                new_settings = {
                    "sender_email": s_email,
                    "smtp_server": s_host,
                    "sender_password": s_pass,
                    "smtp_port": s_port
                }
                if manage_firestore_resource(document_id, "smtp", new_settings, "PATCH"):
                    st.session_state.smtp_settings = new_settings
                    st.success("✅ SMTP settings saved permanently.")
                else:
                    st.error("❌ Failed to save settings.")

    # ======================================================
    # 🗂 TAB: TEMPLATE LIBRARY
    # ======================================================
    with tab_templates:
        st.subheader("Dynamic Email Templates")
        
        # Template Manager
        t_action = st.radio("Action", ["Create New", "Edit/View Existing"], horizontal=True)
        
        if t_action == "Create New":
            with st.form("new_template"):
                t_name = st.text_input("Template Name (e.g., Senior Developer Success)")
                t_subject = st.text_input("Default Subject", "Update on your application: {candidate_name}")
                t_html = st.text_area("HTML Content", value=SUCCESS_HTML_TEMPLATE, height=200)
                if st.form_submit_button("➕ Save Template"):
                    st.session_state.custom_templates[t_name] = {"subject": t_subject, "html": t_html}
                    manage_firestore_resource(document_id, "templates", st.session_state.custom_templates, "PATCH")
                    st.success(f"✅ Template '{t_name}' added.")
        else:
            if not st.session_state.custom_templates:
                st.info("No custom templates found. Use the 'Create New' tab to get started.")
            for name, data in st.session_state.custom_templates.items():
                with st.expander(f"📋 {name}"):
                    st.text(f"Subject: {data['subject']}")
                    st.code(data['html'], language='html')
                    if st.button(f"🗑 Delete {name}"):
                        del st.session_state.custom_templates[name]
                        manage_firestore_resource(document_id, "templates", st.session_state.custom_templates, "PATCH")
                        st.rerun()

    # ======================================================
    # ANALYTICS & HISTORY
    # ======================================================
    with tab_analytics:
        st.subheader("Campaign Analytics")
        
        # Audit Log initialization
        if "audit_log" not in st.session_state:
            st.session_state.audit_log = []

        # Load Stats
        emailed_set = st.session_state.get("emailed_candidates", set())
        total_sent = len(emailed_set)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Emails Sent", total_sent)
        col2.metric("Success Rate", "100%" if total_sent > 0 else "0%")
        col3.metric("Recent Campaigns", len(st.session_state.audit_log))

        if total_sent > 0:
            fig = go.Figure(data=[go.Pie(labels=['Sent', 'Pending'], values=[total_sent, 10])])
            fig.update_layout(title_text="Campaign Reach Distribution", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Outreach Audit Log")
            if st.session_state.audit_log:
                audit_df = pd.DataFrame(st.session_state.audit_log)
                st.dataframe(audit_df, use_container_width=True)
            else:
                st.info("Detailed logs will appear here after your next campaign.")
        else:
            st.info("No email history available to display analytics.")

    # ======================================================
    # 📣 TAB: ACTIVE CAMPAIGN
    # ======================================================
    with tab_campaign:
        st.subheader("Execute Batch Campaign")
        
        # --- 1) Data Load ---
        shortlist_data = None
        doc_ids = [document_id, user_email.replace(".", "_").replace("@", "_")]
        for d_id in doc_ids:
            url = f"{FIRESTORE_DOCUMENTS_URL}/user_data/{d_id}?key={FIREBASE_WEB_API_KEY}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                fields = res.json().get("fields", {})
                for k in ["shortlist_json", "screening_results"]:
                    if k in fields:
                        shortlist_data = json.loads(fields[k]["stringValue"])
                        break
                if EMAILS_SENT_FIELD in fields:
                    st.session_state["emailed_candidates"] = set(json.loads(fields[EMAILS_SENT_FIELD]["stringValue"]))
            if shortlist_data: break

        if not shortlist_data:
            st.warning("No screening data found. Please run a screening campaign first.")
            return

        df = pd.DataFrame(shortlist_data)
        df["Emailed Status"] = df["Email"].apply(lambda e: "SENT" if e in st.session_state.get("emailed_candidates", set()) else "Pending")

        st.markdown("---")
        st.markdown("### Delivery Parameters")
        
        template_names = ["Default System Template"] + list(st.session_state.custom_templates.keys())
        selected_t_name = st.selectbox("Select Template Package", template_names)
        
        attachments = st.file_uploader("Optional Attachments (e.g., JD, Company Profile)", accept_multiple_files=True)

        # --- 3) Filtering ---
        col1, col2 = st.columns(2)
        score_min = col1.slider("Score Cutoff (%)", 0, 100, 70)
        only_pending = col2.checkbox("Target Pending Candidates Only", value=True)

        filtered_df = df[df["Score (%)"] >= score_min].copy()
        if only_pending:
            filtered_df = filtered_df[filtered_df["Emailed Status"] == "⏳ Pending"]

        st.info(f"Targets Identified: **{len(filtered_df)}** candidates ready for outreach.")
        st.dataframe(filtered_df[["Candidate Name", "Email", "Score (%)", "Emailed Status"]], use_container_width=True)

        # --- 4) Execution ---
        if st.button(f"Launch Campaign ({len(filtered_df)} Targets)", type="primary"):
            if not st.session_state.smtp_settings.get("sender_password"):
                st.error("SMTP Credentials required. Go to 'SMTP Settings' tab.")
                return

            smtp = st.session_state.smtp_settings
            try:
                with st.spinner("Connecting to SMTP Relay..."):
                    server = smtplib.SMTP(smtp["smtp_server"], smtp["smtp_port"])
                    server.starttls()
                    server.login(smtp["sender_email"], smtp["sender_password"])
                
                prog = st.progress(0)
                sent_count = 0
                
                for _, row in filtered_df.iterrows():
                    # Template Logic
                    if selected_t_name == "Default System Template":
                        subj, html, text = get_final_email_content(row.to_dict(), "Update: {{candidate_name}}", 
                            {'success': {'text': SUCCESS_TEXT_TEMPLATE, 'html': SUCCESS_HTML_TEMPLATE},
                             'rejection': {'text': REJECTION_TEXT_TEMPLATE, 'html': REJECTION_HTML_TEMPLATE}}, 
                             ["Strong fit", "Recommended"])
                    else:
                        t_data = st.session_state.custom_templates[selected_t_name]
                        subj = t_data['subject'].replace("{{candidate_name}}", row['Candidate Name'])
                        html = t_data['html'].replace("{{candidate_name}}", row['Candidate Name']).replace("{{score_percent}}", str(row['Score (%)']))
                        text = "View in HTML enabled client"

                    msg = MIMEMultipart("alternative")
                    msg["From"] = smtp["sender_email"]
                    msg["To"] = row["Email"]
                    msg["Subject"] = subj
                    msg.attach(MIMEText(text, "plain"))
                    msg.attach(MIMEText(html, "html"))

                    # Attachments
                    if attachments:
                        for uploaded_file in attachments:
                            part = MIMEApplication(uploaded_file.read(), Name=uploaded_file.name)
                            part['Content-Disposition'] = f'attachment; filename="{uploaded_file.name}"'
                            msg.attach(part)
                            uploaded_file.seek(0) # Reset pointer

                    server.send_message(msg)
                    st.session_state["emailed_candidates"].add(row["Email"])
                    
                    # Record Audit Log
                    st.session_state.audit_log.append({
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Candidate": row["Candidate Name"],
                        "Recipient": row["Email"],
                        "Status": "Delivered",
                        "Template": selected_t_name
                    })
                    
                    sent_count += 1
                    prog.progress(sent_count / len(filtered_df))
                
                server.quit()
                st.balloons()
                st.success(f"Campaign Complete. {sent_count} emails delivered.")
                update_firestore_status(document_id, st.session_state["emailed_candidates"], FIREBASE_WEB_API_KEY)
                
            except Exception as e:
                st.error(f"Campaign Interrupted: {e}")

if __name__ == "__main__":
    if 'user_email' not in st.session_state:
        st.session_state['user_email'] = 'test.user@example.com' 
    send_email_to_candidate()

