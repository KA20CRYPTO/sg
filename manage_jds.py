import streamlit as st
import requests
import uuid
from datetime import datetime
import google.generativeai as genai
import pandas as pd
import json
import base64
import re
import time
import sys
import smtplib 
from email.mime.text import MIMEText 

# ==================================================
# CONFIGURATION & SECRETS
# ==================================================
PROJECT_ID = "screenerproapp"
WEB_API_KEY = "AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw"
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "YOUR_FALLBACK_GEMINI_KEY") 

ADMIN_EMAIL = "manav.nagpal2005@gmail.com"
APP_NAME = "JD Management Suite"

# --- DIRECTLY DEFINED SMTP CREDENTIALS (Temporary for testing) ---
# !!! WARNING: This is a MAJOR SECURITY RISK. Move these to secrets.toml in production.
GMAIL_ADDRESS = "screenerpro.ai@gmail.com"
GMAIL_APP_PASSWORD = "udwi life nbdv kgdt" 
# --- END WARNING ---

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
# ----------------------------------------

genai.configure(api_key=GEMINI_API_KEY)

FIRESTORE_ROOT = (
    f"https://firestore.googleapis.com/v1/projects/"
    f"{PROJECT_ID}/databases/(default)/documents"
)

# --- USER AUDIT DATA (Placeholder) ---
def get_current_user_email():
    """Retrieves the current authenticated user's email for the audit trail."""
    return st.session_state.get("user_email", "system_user@yourcompany.com")

# ==================================================
# ADMIN ALERT SYSTEM (Real SMTP)
# ==================================================
def send_admin_email_alert(operation, error_details):
    """
    Sends an ACTUAL alert email to the admin using SMTP (Gmail).
    """
    
    if not all([SMTP_SERVER, SMTP_PORT, GMAIL_APP_PASSWORD]):
        st.session_state["admin_alert_sent"] = True 
        st.session_state["admin_alert_details"] = "SMTP configuration incomplete. Email simulated."
        return

    subject = f"ALERT: {APP_NAME} Gemini Failure during {operation}"
    body_text = f"""
    --- System Alert ---
    
    Time: {datetime.now().isoformat()}
    Operation: {operation}
    User: {get_current_user_email()}
    
    Error Details: 
    {error_details}
    
    --- Action Required ---
    Please check Gemini API key validity and quota immediately.
    """
    
    msg = MIMEText(body_text)
    msg['Subject'] = subject
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = ADMIN_EMAIL
    
    try:
        # Connect to the SMTP server
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Use TLS encryption
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, ADMIN_EMAIL, msg.as_string())
            
        st.session_state["admin_alert_sent"] = True
        st.session_state["admin_alert_details"] = "Real email sent successfully."

    except Exception as e:
        # If email itself fails, record the failure but allow the main app to continue
        st.session_state["admin_alert_sent"] = True
        st.session_state["admin_alert_details"] = f"Email SEND FAILED (SMTP Error): {e}"


# ==================================================
# HELPERS
# ==================================================
def fs_string(v):
    return {"stringValue": str(v)}

def now_utc():
    return datetime.utcnow().isoformat()

def get_html_download_link(file_data, file_name, button_text):
    """Generates an HTML download link for the file."""
    b64 = base64.b64encode(file_data.encode("utf-8")).decode()
    return f'<a href="data:text/html;base64,{b64}" download="{file_name}">{button_text}</a>'

def convert_markdown_to_html(markdown_text, title="Job Description"):
    """Converts simplified markdown text to a basic HTML string (ATS/Web-ready)."""
    content = re.sub(r'#{1,6}\s*(.*)', r'<h2>\1</h2>', markdown_text)
    content = content.replace('* ', '<li>')
    content = content.replace('\n\n', '<br><br>')
    
    html_content = f'<!DOCTYPE html><html><head><title>{title}</title><style>body{{font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: auto; padding: 20px;}} h1{{color:#003366;}} h2{{border-bottom: 2px solid #eee; padding-bottom: 5px;}}</style></head><body>'
    html_content += f'<h1>{title}</h1>'
    html_content += content
    html_content += '</body></html>'
    return html_content

# ==================================================
# FIRESTORE OPERATIONS
# ==================================================
def save_jd(company_id, title, description, jd_id=None):
    """Saves or updates a Job Description in Firestore."""
    is_new = jd_id is None
    jd_id = jd_id or str(uuid.uuid4())

    url = f"{FIRESTORE_ROOT}/companies/{company_id}/jds/{jd_id}?key={WEB_API_KEY}"
    
    fields = {
        "title": fs_string(title),
        "description": fs_string(description),
        "updated_at": fs_string(now_utc()),
    }
    
    if is_new: 
        fields["created_at"] = fs_string(now_utc())
        fields["created_by"] = fs_string(get_current_user_email())
        
    payload = {"fields": fields}
    
    res = requests.patch(url, json=payload) 
    return res.status_code in (200, 201) 

def delete_jd(company_id, jd_id):
    """Deletes a Job Description from Firestore."""
    url = f"{FIRESTORE_ROOT}/companies/{company_id}/jds/{jd_id}?key={WEB_API_KEY}"
    res = requests.delete(url)
    return res.status_code == 200

def fetch_jds(company_id):
    """Fetches all Job Descriptions for a given company."""
    url = f"{FIRESTORE_ROOT}/companies/{company_id}/jds?key={WEB_API_KEY}"
    res = requests.get(url)

    if res.status_code != 200:
        st.error(f"System Error: Cannot load JD data (Status: {res.status_code}).")
        return []

    raw_docs = res.json().get("documents", [])

    jds = []
    for d in raw_docs:
        fields = d.get("fields", {})
        
        jds.append({
            "id": d["name"].split("/")[-1],
            "title": fields.get("title", {}).get("stringValue", "Untitled Job"),
            "description": fields.get("description", {}).get("stringValue", "No content provided."),
            "updated_at": fields.get("updated_at", {}).get("stringValue", "N/A"),
            "created_at": fields.get("created_at", {}).get("stringValue", "N/A"),
            "created_by": fields.get("created_by", {}).get("stringValue", "System"),
        })

    return jds

# ==================================================
# AI JD UTILITIES
# ==================================================
def generate_jd(role, experience, skills, location):
    """Generates a professional, engaging job description."""
    operation = "JD Generation"
    
    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        
        prompt = f"""
        Create a highly professional, engaging, and inclusive job description (JD) based on the provided details.

        Details:
        - Role: {role}
        - Experience Level: {experience}
        - Key Skills: {skills}
        - Location: {location}

        Structure the output strictly using the following Markdown template:
        
        # [Role Title]
        
        ## The Opportunity (Job Overview)
        [1-2 paragraphs describing the role's impact and the team's mission.]
        
        ## What You'll Do (Key Responsibilities)
        - [5-7 bullet points focused on results and impact]
        - 
        
        ## What You'll Bring (Qualifications & Skills)
        - [3-5 required technical skills/experience]
        - [3-5 required behavioral skills/qualifications]
        
        ## Why Join Us (Culture & Benefits)
        [1-2 paragraphs on company culture, growth, and benefits.]
        """
        response = model.generate_content(prompt)
        return response.text.strip() if response and response.text else "AI did not return content."
        
    except Exception as e:
        error_details = f"Gemini Error: {e}. Exception Type: {sys.exc_info()[0].__name__}"
        send_admin_email_alert(operation, error_details)
        
        # Safe fallback content 
        return f"""
        # {role}
        
        ## The Opportunity
        We are seeking a highly qualified individual for the role of {role}. Due to a temporary failure in our AI generation system, please manually enter the job description details below.
        
        ## System Alert
        **ERROR**: AI Generation Failed. An alert email has been sent to {ADMIN_EMAIL}.
        """


def generate_competency_model(role, description):
    """Converts a JD into a structured competency model."""
    operation = "Competency Model Generation"
    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        prompt = f"""Based on '{role}', generate a structured competency model for interviews. 
        Output Markdown list: Core Technical Mastery, Collaboration, Problem Solving, Ownership."""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        error_details = f"Gemini Error: {e}. Exception Type: {sys.exc_info()[0].__name__}"
        send_admin_email_alert(operation, error_details)
        return f"Competency Model Generation Failed: System Error. Admin alerted."


def generate_screening_questions(role, description):
    """Generates structured interview questions."""
    operation = "Screening Question Generation"
    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        prompt = f"""For '{role}', generate 10 structured interview questions. 
        Categories: Technical (5), Behavioral (5, STAR method). Output Markdown list."""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        error_details = f"Gemini Error: {e}. Exception Type: {sys.exc_info()[0].__name__}"
        send_admin_email_alert(operation, error_details)
        return f"Screening Question Generation Failed: System Error. Admin alerted."


def optimize_jd_tone(description, optimization_type):
    """Rewrites the JD based on a specified tone."""
    operation = "Tone Optimization"
    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        
        tone_map = {
            "Candidate-Friendly Engagement": "Rewrite the JD to be highly engaging, focusing on career growth and the exciting challenges of the role, using a dynamic and positive voice.",
            "Compliance & Legal Tone": "Rewrite the JD to be strictly formal, compliant, and legally neutral, ensuring all required sections are clearly stated without emotional language.",
            "Gender-Neutral & Inclusive": "Rewrite the JD ensuring all language is completely gender-neutral and inclusive, removing any potentially biased words and focusing on skills and capabilities.",
            "Executive Summary (≤150 words)": "Summarize the entire JD into an Executive Summary no more than 150 words long, highlighting the core mission and top three requirements."
        }
        
        prompt = f"{tone_map[optimization_type]}\n\nOriginal Job Description:\n---\n{description}\n---"
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        error_details = f"Gemini Error: {e}. Exception Type: {sys.exc_info()[0].__name__}"
        send_admin_email_alert(operation, error_details)
        return f"Optimization Failed: System Error. Admin alerted."

# ==================================================
# KPI & DASHBOARD SECTION
# ==================================================
def render_kpis(company_id, jds):
    """Renders Key Performance Indicators (KPIs) for the JD management."""
    st.markdown("### JD Portfolio Overview")

    total_jds = len(jds)
    
    sorted_jds = sorted(jds, key=lambda x: x["updated_at"], reverse=True)
    recent_activity = sorted_jds[:5]

    col1, col2 = st.columns(2)
    col1.metric("Total Active JDs", total_jds)
    col2.metric("Company ID", company_id)
    
    st.markdown("---")
    st.markdown("#### Recent JD Activity (Audit Trail)")
    
    if recent_activity:
        df_recent = pd.DataFrame(recent_activity)
        st.table(df_recent[["title", "updated_at", "created_by"]].rename(columns={
            "title": "Job Title", "updated_at": "Last Updated", "created_by": "Updated By"
        }))
    else:
        st.info("No recent JD activity found.")


# ==================================================
# MAIN PAGE
# ==================================================
def manage_jds_page():
    st.title("JD Management Suite")
    st.markdown("---")
    
    # Display real/simulated alert status
    if st.session_state.get("admin_alert_sent"):
        alert_details = st.session_state.get("admin_alert_details", "Email alert status unknown.")
        st.error(f"SYSTEM ALERT: A Gemini failure occurred. Email attempted for {ADMIN_EMAIL}. Details: {alert_details}")
        st.session_state["admin_alert_sent"] = False # Reset the flag

    if not st.session_state.get("authenticated"):
        st.error("Please login to continue")
        return

    company_id = st.session_state.get("user_company")

    if not company_id:
        st.error("Company information not found. User session may be incomplete.")
        return

    jds = fetch_jds(company_id)
    render_kpis(company_id, jds)

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Create Manually",
        "Generate with AI",
        "Advanced Editor & Export",
        "AI Utilities"
    ])

    # --------------------------------------------------
    # CREATE JD
    # --------------------------------------------------
    with tab1:
        st.subheader("1. Create New Job Description")
        st.caption("Enter details below or upload an existing JD file (.txt).")

        title = st.text_input("Job Title", key="create_title")
        txt_file = st.file_uploader("Upload .txt file", type=["txt"], key="create_file")
        manual_text = st.text_area("Or paste content", height=260, key="create_manual_text")

        if st.button("Save New Job Description"):
            content = (
                txt_file.read().decode("utf-8").strip()
                if txt_file else manual_text.strip()
            )

            if not title.strip() or not content:
                st.error("Job title and content are required")
                return

            if save_jd(company_id, title, content):
                st.success(f"Job description '{title}' saved successfully. Audit Trail set.")
                st.rerun()

    # --------------------------------------------------
    # GENERATE JD
    # --------------------------------------------------
    with tab2:
        st.subheader("2. Generate Production-Ready JD")
        st.caption("Use Gemini AI to draft an engaging, structured JD instantly.")

        role = st.text_input("Core Role Title", key="gen_role")
        experience = st.selectbox(
            "Experience Level",
            ["Entry Level", "Mid Level", "Senior Level", "Lead"],
            key="gen_exp"
        )
        skills = st.text_input("Key Skills (comma separated)", key="gen_skills")
        location = st.text_input("Location", key="gen_loc")

        if st.button("Generate Draft", key="btn_generate"):
            if not role:
                st.warning("Please enter a Core Role Title.")
            else:
                with st.spinner("Generating engaging job description..."):
                    jd_text = generate_jd(role, experience, skills, location) 
                    st.session_state["generated_jd"] = jd_text
                    st.session_state["generated_role"] = role

        generated = st.session_state.get("generated_jd", "")
        if generated:
            final_text = st.text_area(
                "Generated Job Description (Review & Edit)",
                generated,
                height=340,
                key="final_gen_text"
            )

            if st.button("Save Generated Job Description", key="btn_save_gen"):
                if save_jd(company_id, st.session_state.get("generated_role", role), final_text):
                    st.success("Generated job description saved.")
                    if "generated_jd" in st.session_state: del st.session_state["generated_jd"]
                    if "generated_role" in st.session_state: del st.session_state["generated_role"]
                    st.rerun()

    # --------------------------------------------------
    # ADVANCED EDITOR & DELETE
    # --------------------------------------------------
    with tab3:
        st.subheader("3. Advanced JD Editor & Export")
        
        if not jds:
            st.info("No job descriptions available to edit. Please create one first.")
            return

        selected_jd = st.selectbox(
            "Select Job Description to Edit/Export",
            jds,
            format_func=lambda x: f"{x['title']} (Last Updated: {x['updated_at'].split('T')[0]})",
            key="adv_edit_select"
        )

        st.markdown(f"**Audit Trail:** Created by **{selected_jd['created_by']}** on {selected_jd['created_at'].split('T')[0]}. Last updated **{selected_jd['updated_at'].split('T')[0]}**.")
        st.markdown("---")

        col_editor, col_preview = st.columns(2)

        with col_editor:
            st.markdown("#### Editor")
            new_title = st.text_input("Job Title", selected_jd["title"], key="adv_edit_title")
            new_desc = st.text_area(
                "Job Description Content (Markdown Supported)",
                selected_jd["description"],
                height=500,
                key="adv_edit_desc"
            )

            if st.button("Update JD Content"):
                if save_jd(
                    company_id,
                    new_title.strip(),
                    new_desc.strip(),
                    selected_jd["id"]
                ):
                    st.success(f"Job description '{new_title}' updated successfully. Audit trail recorded.")
                    st.rerun()

        with col_preview:
            st.markdown("#### Live Markdown Preview")
            st.markdown("---")
            st.markdown(new_desc)
            st.markdown("---")
            
            st.markdown("#### Export Options")
            
            st.download_button(
                label="Download as Markdown (.md)",
                data=new_desc,
                file_name=f"{selected_jd['title'].replace(' ', '_')}.md",
                mime="text/markdown",
                key="download_md"
            )
            
            html_content = convert_markdown_to_html(new_title, new_desc)
            st.markdown(get_html_download_link(html_content, f"{new_title.replace(' ', '_')}.html", "Download as HTML (ATS Ready)"), unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### Secure Delete with Confirmation")
        st.warning("PERMANENT ACTION: Deleting this JD cannot be undone.")
        
        if st.checkbox("I confirm I want to permanently delete this Job Description.", key="delete_confirm"):
            if st.button(f"DELETE: {selected_jd['title']}", key="btn_delete"):
                if delete_jd(company_id, selected_jd['id']):
                    st.success(f"Job Description '{selected_jd['title']}' deleted successfully.")
                    st.rerun()

    # --------------------------------------------------
    # AI UTILITIES
    # --------------------------------------------------
    with tab4:
        st.subheader("4. AI Utilities")

        if not jds:
            st.info("No job descriptions available for utilities.")
            return

        selected_util = st.selectbox(
            "Select Job Description for Utilities",
            jds,
            format_func=lambda x: x["title"],
            key="util_select"
        )
        
        st.markdown(f"**Selected JD:** **{selected_util['title']}**")
        st.markdown("---")
        
        competency_tab, screening_tab, optimize_tab = st.tabs([
            "Competency Model", 
            "Screening Questions",
            "Tone Optimization"
        ])
        
        # --- Competency Model ---
        with competency_tab:
            st.markdown("##### Generate Interview/Review Competency Model")
            if st.button("Generate Competency Model", key="btn_competency"):
                with st.spinner("Generating structured competency model..."):
                    model_text = generate_competency_model(selected_util["title"], selected_util["description"])
                    st.session_state["comp_model_text"] = model_text
            
            if "comp_model_text" in st.session_state:
                st.markdown("---")
                st.markdown(st.session_state["comp_model_text"])
                st.download_button(
                    label="Download Competency Model (.md)",
                    data=st.session_state["comp_model_text"],
                    file_name=f"{selected_util['title']}_Competency_Model.md",
                    mime="text/markdown"
                )

        # --- Screening Questions ---
        with screening_tab:
            st.markdown("##### Generate Structured Interview Questions")
            if st.button("Generate Screening Questions", key="btn_screen_q"):
                with st.spinner("Generating 10 structured interview questions..."):
                    q_text = generate_screening_questions(selected_util["title"], selected_util["description"])
                    st.session_state["screening_q_text"] = q_text
            
            if "screening_q_text" in st.session_state:
                st.markdown("---")
                st.markdown(st.session_state["screening_q_text"])
                st.download_button(
                    label="Export Screening Questions (.md)",
                    data=st.session_state["screening_q_text"],
                    file_name=f"{selected_util['title']}_Screening_Questions.md",
                    mime="text/markdown"
                )

        # --- Tone Optimization ---
        with optimize_tab:
            st.markdown("##### Rewrite & Optimize JD Content")
            optimization_type = st.selectbox(
                "Select Optimization Goal",
                [
                    "Candidate-Friendly Engagement",
                    "Compliance & Legal Tone",
                    "Gender-Neutral & Inclusive",
                    "Executive Summary (≤150 words)"
                ],
                key="opt_type"
            )
            
            if st.button("Optimize JD Content", key="btn_optimize"):
                with st.spinner(f"Rewriting JD for: {optimization_type}..."):
                    optimized_text = optimize_jd_tone(selected_util["description"], optimization_type)
                    st.session_state["optimized_jd_text"] = optimized_text
                    st.session_state["optimized_jd_title"] = f"Optimized: {selected_util['title']}"

            if "optimized_jd_text" in st.session_state:
                st.markdown("---")
                st.markdown(f"**Result: {optimization_type}**")
                optimized_output = st.text_area(
                    "Optimized Content", 
                    st.session_state["optimized_jd_text"], 
                    height=340
                )
                
                colX, colY = st.columns(2)
                with colX:
                    if st.button("Save as New JD", key="btn_save_optimized_new"):
                        if save_jd(company_id, st.session_state["optimized_jd_title"], optimized_output):
                            st.success("Optimized JD saved successfully as a new draft.")
                            st.rerun()
                with colY:
                    st.download_button(
                        label="Download Optimized JD (.md)",
                        data=optimized_output,
                        file_name=f"{selected_util['title']}_Optimized.md",
                        mime="text/markdown"
                    )
