import streamlit as st
from nav_utils import load_unified_css, render_universal_sidebar
import requests
import json
from datetime import datetime, date, timedelta
import uuid
from io import BytesIO
import os
import pandas as pd
import traceback
import plotly.express as px # Added for charts
import smtplib # For sending emails
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
import google.generativeai as genai

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("❌ GEMINI_API_KEY not configured")

genai.configure(api_key=GEMINI_API_KEY)


def encode_file_to_base64(uploaded_file):
    if uploaded_file is None:
        return None
    return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
# Import core screening logic functions from screener_logic.py
from screener_logic import (
    load_skill_library,
    extract_text_from_file,
    process_single_resume_logic,
)

# Firebase Project ID (using __app_id from Canvas environment if available)
FIREBASE_PROJECT_ID = globals().get('__app_id', 'screenerproapp')

# Firebase Web API Key (from environment variables or default)
FIREBASE_WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY', 'AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw')

# Firestore Database Root URL for REST API
FIRESTORE_DATABASE_ROOT_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)"

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
            fields[key] = {"timestampValue": value.isoformat(timespec='milliseconds') + "Z"}
        elif isinstance(value, date):
            fields[key] = {"stringValue": value.isoformat()}
        elif isinstance(value, list):
            array_values = []
            for item in value:
                if isinstance(item, dict):
                    array_values.append({"mapValue": {"fields": to_firestore_format(item)['fields']}})
                elif isinstance(item, str):
                    array_values.append({"stringValue": item})
                elif isinstance(item, int):
                    array_values.append({"integerValue": str(item)})
                elif isinstance(item, float):
                    array_values.append({"doubleValue": item})
                elif isinstance(item, bool):
                    array_values.append({"booleanValue": item})
                else:
                    array_values.append({"stringValue": str(item)})
            fields[key] = {"arrayValue": {"values": array_values}}
        elif isinstance(value, dict):
            fields[key] = {"mapValue": {"fields": to_firestore_format(value)['fields']}}
        elif value is None:
            fields[key] = {"nullValue": None}
        else:
            fields[key] = {"stringValue": str(value)}
    return {"fields": fields}

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

def add_doc_to_firestore_rest(collection_path: str, data: dict, doc_id: str = None):
    """Adds a document to a Firestore collection using REST API."""
    url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents/{collection_path}?pageSize=10000&key={FIREBASE_WEB_API_KEY}"
    if doc_id:
        url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents/{collection_path}/{doc_id}?key={FIREBASE_WEB_API_KEY}"
        res = requests.patch(url, json=to_firestore_format(data))
    else:
        res = requests.post(url, json=to_firestore_format(data))

    if res.status_code in [200, 201]:
        st.cache_data.clear() # Clear cache after any write operation
        if not doc_id:
            return res.json().get('name', '').split('/')[-1]
        return doc_id
    else:
        st.error(f"Failed to save document: {res.status_code} - {res.text}")
        return None

@st.cache_data(ttl=1) # Cache for 1 second
def get_docs_from_firestore_rest(collection_path: str):
    """Retrieves all documents from a Firestore collection using REST API."""
    url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents/{collection_path}?pageSize=10000&key={FIREBASE_WEB_API_KEY}"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            documents = []
            if 'documents' in data:
                for doc in data['documents']:
                    doc_id = doc['name'].split('/')[-1]
                    doc_data = from_firestore_format(doc)
                    doc_data['id'] = doc_id
                    documents.append(doc_data)
            return documents
        else:
            st.error(f"Failed to fetch documents from `{collection_path}`: {res.status_code} - {res.text}")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Firebase connection error fetching documents from `{collection_path}`: {e}")
        return []

def get_single_doc_from_firestore_rest(collection_path: str, doc_id: str):
    """Retrieves a single document from Firestore using REST API."""
    url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents/{collection_path}/{doc_id}?key={FIREBASE_WEB_API_KEY}"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            doc_data = from_firestore_format(data)
            return doc_data
        elif res.status_code == 404:
            return None
        else:
            st.error(f"Failed to fetch single document `{collection_path}/{doc_id}`: {res.status_code} - {res.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Firebase connection error fetching single document `{collection_path}/{doc_id}`: {e}")
        return []

def update_doc_in_firestore_rest(collection_path: str, doc_id: str, data: dict, update_mask_fields: list = None):
    """
    Updates a document in Firestore using REST API.
    Optionally accepts update_mask_fields to specify which fields to update.
    """
    url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents/{collection_path}/{doc_id}?key={FIREBASE_WEB_API_KEY}"
    
    if update_mask_fields:
        mask_params = "&".join([f"updateMask.fieldPaths={field}" for field in update_mask_fields])
        url = f"{url}&{mask_params}"

    res = requests.patch(url, json=to_firestore_format(data))
    if res.status_code == 200:
        st.cache_data.clear() # Clear cache after any write operation
        return res.json()
    else:
        st.error(f"Failed to update document: {res.status_code} - {res.text}")
        return None

def delete_doc_from_firestore_rest(collection_path: str, doc_id: str):
    """Deletes a document from Firestore using REST API."""
    url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents/{collection_path}/{doc_id}?key={FIREBASE_WEB_API_KEY}"
    res = requests.delete(url)
    if res.status_code == 200:
        st.cache_data.clear() # Clear cache after any write operation
        return True
    else:
        st.error(f"Failed to delete document '{doc_id}': {res.status_code} - {res.text}")
        return False

def get_applications_for_campaign(campaign_id: str, user_uid: str, firebase_project_id: str, firestore_database_root_url: str, firebase_web_api_key: str):
    """Retrieves all applications for a specific job campaign."""
    if not campaign_id or not user_uid:
        return []
    
    collection_path = f"artifacts/{firebase_project_id}/users/{user_uid}/my_campaigns/{campaign_id}/applications"
    url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents/{collection_path}?pageSize=10000&key={FIREBASE_WEB_API_KEY}"

    try:
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            applications = []
            if 'documents' in data:
                for doc in data['documents']:
                    app_id = doc['name'].split('/')[-1]
                    app_data = from_firestore_format(doc)
                    app_data['id'] = app_id
                    applications.append(app_data)
            return applications
        elif res.status_code == 404:
            return []
        else:
            st.error(f"Failed to fetch applications for campaign `{campaign_id}`: {res.status_code} - {res.text}")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Firebase connection error fetching applications for campaign `{campaign_id}`: {e}")
        return []

def update_campaign_metrics(campaign_id: str, hr_user_uid: str, original_campaign_data: dict):
    """
    Fetches all applications for a campaign, recalculates metrics, and updates
    the campaign document in both private and public collections.
    Ensures job_title and company_name are preserved.
    """
    try:
        private_campaign_path = f"artifacts/{FIREBASE_PROJECT_ID}/users/{hr_user_uid}/my_campaigns"
        public_campaign_path = f"artifacts/{FIREBASE_PROJECT_ID}/public_campaigns"

        existing_private_campaign = get_single_doc_from_firestore_rest(private_campaign_path, campaign_id)
        existing_public_campaign = get_single_doc_from_firestore_rest(public_campaign_path, campaign_id)

        campaign_to_update = {}
        if existing_public_campaign:
            campaign_to_update.update(existing_public_campaign)
        elif existing_private_campaign:
            campaign_to_update.update(existing_private_campaign)
        else:
            return False

        if not campaign_to_update.get('job_title') or campaign_to_update.get('job_title') == 'N/A':
            campaign_to_update['job_title'] = original_campaign_data.get('job_title', 'Untitled Job')
        
        if not campaign_to_update.get('company_name') or campaign_to_update.get('company_name') == 'N/A':
            campaign_to_update['company_name'] = original_campaign_data.get('company_name', 'Undisclosed Company')

        applications_data = get_applications_for_campaign(
            campaign_id,
            hr_user_uid,
            FIREBASE_PROJECT_ID,
            FIRESTORE_DATABASE_ROOT_URL,
            FIREBASE_WEB_API_KEY
        )

        total_applications = len(applications_data)
        total_score_sum = sum(float(app.get('ai_score', 0)) for app in applications_data)
        new_avg_score = (total_score_sum / total_applications) if total_applications > 0 else 0.0
        
        # Count applications specifically from Public Job Board
        public_link_count = sum(1 for app in applications_data if app.get('source') == "Public Job Board")

        campaign_to_update["application_count"] = total_applications
        campaign_to_update["public_link_applications"] = public_link_count
        campaign_to_update["avg_match_score"] = new_avg_score
        campaign_to_update["last_updated"] = datetime.now().isoformat()

        update_doc_in_firestore_rest(private_campaign_path, campaign_id, campaign_to_update)
        update_doc_in_firestore_rest(public_campaign_path, campaign_id, campaign_to_update)

        return True
    except Exception as e:
        st.error(f"An error occurred while updating campaign metrics for `{campaign_id}`: {e}")
        st.exception(e)
        return False

def generate_certificate_html(candidate_data, jd_used, CERTIFICATE_HOSTING_URL):
    candidate_name = candidate_data.get('Candidate Name', 'N/A')
    score = candidate_data.get('Score (%)', 0.0)
    certificate_rank = candidate_data.get('Certificate Rank', 'Not Applicable')
    date_screened = candidate_data.get('Date Screened', datetime.now().date()).strftime("%B %d, %Y")
    certificate_id = candidate_data.get('Certificate ID', 'N/A')
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ScreenerPro Certificate</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            body {
                font-family: 'Inter', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                background-color: #f0f2f5;
                margin: 0;
                padding: 20px;
                box-sizing: border-box;
            }
            .certificate-container {
                width: 100%;
                max-width: 800px;
                background: linear-gradient(135deg, #ffffff, #f9f9f9);
                border: 10px solid #007bff;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
                padding: 40px;
                text-align: center;
                position: relative;
                overflow: hidden;
                border-radius: 15px;
            }
            .certificate-container::before {
                content: '';
                position: absolute;
                top: -50px;
                left: -50px;
                width: 150px;
                height: 150px;
                background: radial-gradient(circle, #007bff 0%, rgba(0, 123, 255, 0) 70%);
                opacity: 0.1;
            }
            .certificate-container::after {
                content: '';
                position: absolute;
                bottom: -50px;
                right: -50px;
                width: 150px;
                height: 150px;
                background: radial-gradient(circle, #007bff 0%, rgba(0, 123, 255, 0) 70%);
                opacity: 0.1;
            }
            .header {
                font-size: 2.5em;
                color: #007bff;
                margin-bottom: 20px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 2px;
            }
            .subheader {
                font-size: 1.2em;
                color: #555;
                margin-bottom: 30px;
            }
            .name {
                font-size: 2.8em;
                color: #333;
                margin: 20px 0;
                font-weight: 700;
                text-transform: capitalize;
            }
            .score {
                font-size: 2.2em;
                color: #28a745;
                font-weight: 700;
                margin-bottom: 15px;
            }
            .rank {
                font-size: 1.5em;
                color: #ffc107;
                font-weight: 600;
                margin-bottom: 25px;
            }
            .details {
                font-size: 1em;
                color: #666;
                margin-top: 20px;
                line-height: 1.6;
            }
            .details p {
                margin: 5px 0;
            }
            .footer {
                margin-top: 40px;
                font-size: 0.9em;
                color: #888;
            }
            .logo {
                margin-top: 30px;
                width: 150px;
                height: auto;
            }
            .certificate-id {
                font-size: 0.8em;
                color: #aaa;
                margin-top: 10px;
            }
            .qr-code {
                margin-top: 20px;
                width: 100px;
                height: 100px;
                border: 1px solid #ddd;
                padding: 5px;
            }
        </style>
    </head>
    <body>
        <div class="certificate-container">
            <div class="header">ScreenerPro Certification</div>
            <div class="subheader">This certifies that</div>
            <div class="name">{{CANDIDATE_NAME}}</div>
            <div class="subheader">has successfully completed the AI-powered resume screening for the role of</div>
            <div class="rank">{{JD_USED}}</div>
            <div class="subheader">and achieved an impressive AI Match Score of</div>
            <div class="score">{{SCORE}}%</div>
            <div class="rank">Rank: {{CERTIFICATE_RANK}}</div>
            <div class="details">
                <p>Date Screened: {{DATE_SCREENED}}</p>
                <p>Certificate ID: {{CERTIFICATE_ID}}</p>
                <p>Verify this certificate online at: <a href="{{CERTIFICATE_HOSTING_URL}}?cert_id={{CERTIFICATE_ID}}">{{CERTIFICATE_HOSTING_URL}}?cert_id={{CERTIFICATE_ID}}</a></p>
            </div>
            <img src="https://placehold.co/150x50/007bff/ffffff?text=ScreenerPro" alt="ScreenerPro Logo" class="logo">
            <div class="footer">
                ScreenerPro - Empowering HR with AI
            </div>
        </div>
    </body>
    </html>
    """

    html_content = html_template.replace("{{CANDIDATE_NAME}}", candidate_name)
    html_content = html_content.replace("{{SCORE}}", f"{score:.1f}")
    html_content = html_content.replace("{{CERTIFICATE_RANK}}", certificate_rank)
    html_content = html_content.replace("{{DATE_SCREENED}}", date_screened)
    html_content = html_content.replace("{{CERTIFICATE_ID}}", certificate_id)
    html_content = html_template.replace("{{CERTIFICATE_HOSTING_URL}}", CERTIFICATE_HOSTING_URL)
    html_content = html_content.replace("{{JD_USED}}", jd_used)

    return html_content

# New function to send application success email
def send_application_success_email(applicant_name, applicant_email, job_title, company_name, ai_score, ai_decision):
    """
    Sends a confirmation email to the applicant upon successful application.
    Requires GMAIL_ADDRESS and GMAIL_APP_PASSWORD to be set as environment variables.
    """
    gmail_address = "screenerpro.ai@gmail.com"
    gmail_app_password = "udwilifenbdvkgdt"

    if not gmail_address or not gmail_app_password:
        st.warning("Email sending is not configured. Please set GMAIL_ADDRESS and GMAIL_APP_PASSWORD environment variables for this feature to work.")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Application Received: {job_title} at {company_name}"
    msg['From'] = gmail_address
    msg['To'] = applicant_email

    plain_text_body = f"""Dear {applicant_name},

Thank you for applying for the {job_title} position at {company_name}.

Your application has been successfully received and processed by our AI screening system.

Here's a summary of your initial AI screening:
- Your AI Match Score: {ai_score:.1f}%
- AI Decision: {ai_decision}

We appreciate your interest in {company_name}. We will review your application and get back to you if you are shortlisted for further steps.

Best regards,
The {company_name} Hiring Team
"""

    html_body = f"""
    <html>
        <body>
            <p>Dear {applicant_name},</p>
            <p>Thank fo for applying for the <strong>{job_title}</strong> position at <strong>{company_name}</strong>.</p>
            <p>Your application has been successfully received and processed by our AI screening system.</p>
            <p>Here's a summary of your initial AI screening:</p>
            <ul>
                <li><strong>Your AI Match Score:</strong> {ai_score:.1f}%</li>
                <li><strong>AI Decision:</strong> {ai_decision}</li>
            </ul>
            <p>We appreciate your interest in {company_name}. We will review your application and get back to you if you are shortlisted for further steps.</p>
            <p>Best regards,</p>
            <p>The {company_name} Hiring Team</p>
        </body>
    </html>
    """

    msg_alternative = MIMEMultipart('alternative')
    msg_alternative.attach(MIMEText(plain_text_body, 'plain'))
    msg_alternative.attach(MIMEText(html_body, 'html'))
    
    msg.attach(msg_alternative)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(gmail_address, gmail_app_password)
            smtp.send_message(msg)
        st.success(f"✅ Application confirmation email sent to {applicant_email}!")
        return True
    except smtplib.SMTPAuthenticationError:
        st.error("❌ Failed to send email: Authentication error. Please check your Gmail address and App Password.")
        st.info("Ensure you have generated an App Password for your Gmail account and used it instead of your regular password.")
    except Exception as e:
        st.error(f"❌ Failed to send email: {e}")
    return False


# Callback function to handle form submission and clear fields
def _handle_application_submission(campaign_id, applicant_name_key, applicant_email_key, uploaded_resume_key):
    st.session_state[f'submit_triggered_{campaign_id}'] = True
    
    st.session_state[f'current_applicant_name_{campaign_id}'] = st.session_state[applicant_name_key]
    st.session_state[f'current_applicant_email_{campaign_id}'] = st.session_state[applicant_email_key]
    st.session_state[f'current_uploaded_resume_{campaign_id}'] = st.session_state.get(uploaded_resume_key)

    st.session_state[applicant_name_key] = ""
    st.session_state[applicant_email_key] = ""
    
    st.session_state.file_uploader_reset_key += 1
    
    st.session_state['form_submitted_feedback'][campaign_id] = "pending"

# Callback for "View Details" button on job cards
def _view_job_details(campaign_id):
    st.session_state.expanded_job_id = campaign_id

# Callback for "Close Details" button
def _close_job_details():
    st.session_state.expanded_job_id = None

# Callback to clear all filters
def _clear_filters():
    st.session_state.search_query_input = ""
    st.session_state.selected_job_types_multiselect = [] # Ensure this is an empty list
    st.session_state.selected_exp_levels_multiselect = [] # Ensure this is an empty list
    st.session_state.search_location_input = ""
    st.session_state.sort_by_select = "Posted Date (Newest First)" # Reset sort order
    get_docs_from_firestore_rest.clear() # Clear cache to re-fetch unfiltered data
    # Removed st.rerun() from here as changing session state already triggers a rerun




import urllib.parse # For encoding URLs

# --- Feature B: Google Jobs Integration (JSON-LD Schema) ---
# --- Feature B: Google Jobs Integration (JSON-LD Schema) ---
def generate_job_posting_schema(job_data, job_id):
    """Generates schema.org JobPosting JSON-LD for Google Jobs."""
    try:
        # Basic Description Cleaning
        description = job_data.get('job_description', '') or job_data.get('jd_text', '') or "No description available."
        
        posted_date = job_data.get('created_at')
        if not posted_date:
            posted_date = datetime.now().isoformat()
        elif isinstance(posted_date, (datetime, date)):
            posted_date = posted_date.isoformat()
            
        valid_through = job_data.get('application_deadline')
        if isinstance(valid_through, (datetime, date)):
             valid_through = valid_through.isoformat()

        schema = {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": job_data.get('job_title', 'Job Opening'),
            "description": description,
            "datePosted": posted_date,
            "validThrough": valid_through,
            "employmentType": job_data.get('job_type', 'FULL_TIME').replace(' ', '_').upper(),
            "hiringOrganization": {
                "@type": "Organization",
                "name": job_data.get('company_name', 'ScreenerPro'),
                 "sameAs": st.session_state.get('APP_BASE_URL', 'https://screenerpro.streamlit.app')
            },
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": job_data.get('job_location', 'Remote'),
                    "addressCountry": "IN"
                }
            },
            "baseSalary": {
                "@type": "MonetaryAmount",
                "currency": "INR",
                "value": {
                    "@type": "QuantitativeValue",
                    "value": job_data.get('salary_range', 'Not Disclosed'), # Example placeholder
                    "unitText": "YEAR"
                }
            } if job_data.get('salary_range') else None
        }
        
        # Clean up None values
        schema = {k: v for k, v in schema.items() if v is not None}

        return json.dumps(schema)
    except Exception as e:
        print(f"Schema generation error: {e}")
        return "{}"

def public_job_board_page():
    """
    Public Job Board page — polished UI, pagination (9 per page),
    safe session-state initialization, and preserves the original
    details + apply form flow (calls _handle_application_submission with keys).
    """
    # Ensure page context
    if 'selected_page' in st.session_state:
        st.session_state["selected_page"] = "Public Job Board"

    # Load Branding & Shared Nav
    load_unified_css()
    render_universal_sidebar("Public Job Board")

    # 🔥 Handle direct job open via URL (User Prescribed Fix)
    if "direct_job_id" in st.session_state:
        st.session_state.expanded_job_id = st.session_state["direct_job_id"]
        # Clear it so it doesn't persist forever
        del st.session_state["direct_job_id"] 

    # Page metadata
    st.set_page_config(page_title="ScreenerPro • Public Job Board", layout="wide", page_icon="🌐")

    # --- Feature A: Deep Linking (Handle ?job_id=...) ---
    # Check query params for 'job_id' on first load
    query_params = st.query_params
    url_job_id = query_params.get("job_id", None)
    
    # If a URL job_id is present and we haven't set it yet (or it's different), open it
    # We use a session state flag 'deep_link_processed' to avoid getting stuck on one job if user closes it
    if url_job_id and st.session_state.get('last_processed_url_job_id') != url_job_id:
         st.session_state.expanded_job_id = url_job_id
         st.session_state.last_processed_url_job_id = url_job_id

    # Sync query param when user manually opens/closes details
    # If expanded_job_id is set, ensure URL reflects it. If None, remove it.
    if st.session_state.get("expanded_job_id"):
        st.query_params["job_id"] = st.session_state.expanded_job_id
    else:
        # Clear specific param if no job is open
        if "job_id" in st.query_params:
            del st.query_params["job_id"]

    # --- SAFE session initialization (prevent KeyErrors) ---
    if 'file_uploader_reset_key' not in st.session_state:
        st.session_state.file_uploader_reset_key = 0
    if 'expanded_job_id' not in st.session_state:
        st.session_state.expanded_job_id = None
    if 'job_page' not in st.session_state:
        st.session_state.job_page = 1
    if 'form_submitted_feedback' not in st.session_state:
        st.session_state['form_submitted_feedback'] = {}
    if 'search_query_input' not in st.session_state:
        st.session_state.search_query_input = ""
    if 'selected_job_types_multiselect' not in st.session_state:
        st.session_state.selected_job_types_multiselect = []
    if 'selected_exp_levels_multiselect' not in st.session_state:
        st.session_state.selected_exp_levels_multiselect = []
    if 'search_location_input' not in st.session_state:
        st.session_state.search_location_input = ""
    if 'sort_by_select' not in st.session_state:
        st.session_state.sort_by_select = "Posted Date (Newest First)"

    APP_BASE_URL = st.session_state.get('APP_BASE_URL', 'https://screenerpro.streamlit.app')

    # --- Visual styles (Elevated UI - Version 2) ---
    st.markdown(
        """
    <style>
    /* HIDE DEFAULT STREAMLIT NAVIGATION & HEADER */
    [data-testid="stSidebarNav"] {display: none !important;}
    [data-testid="stHeader"] {display: none !important;}
    #MainMenu {display: none !important;}
    footer {visibility: hidden !important;}

    /* 1. Global Page Background & Containers */
    body { background-color: #f9faff; } /* Very light blue-grey background */
    
    .main-card {
      /* Dynamic, vibrant header gradient */
      background: linear-gradient(135deg, #045DE9 0%, #00d4ff 100%); 
      color: white; /* Text is white on blue gradient */
      padding: 30px; 
      border-radius: 16px; 
      box-shadow: 0 12px 50px rgba(4, 93, 233, 0.25); /* Prominent blue shadow for header */
      margin-bottom: 24px;
    }
    .main-card h1 {
        color: white; /* Ensure title is white */
        font-weight: 900;
    }
    .section-card {
      background: #ffffff;
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 4px 15px rgba(15, 23, 42, 0.04), 0 0 0 1px rgba(15, 23, 42, 0.02); /* Subtle inner border/shadow combination */
      margin-bottom: 24px;
      border: none; /* Removing border as shadow handles definition */
    }
    
    /* 2. Job Card Design (The star of the show) */
    .job-card {
      background: #ffffff;
      border-radius: 18px; /* Slightly more rounded */
      padding: 25px; /* More padding */
      margin-bottom: 20px;
      height: 250px; 
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      border: 1px solid #e9eef6; /* Light, defined border */
      transition: all 0.3s cubic-bezier(.25,.8,.25,1); /* Smoother, more complex transition */
      cursor: pointer;
      box-shadow: 0 2px 5px rgba(0,0,0,0.03); /* Initial subtle shadow */
    }
    .job-card:hover {
      transform: translateY(-10px); /* More dramatic lift */
      box-shadow: 0 20px 60px rgba(4, 93, 233, 0.15), 0 0 0 1px #045DE9; /* Blue halo on hover */
      border-color: #045DE9; /* Blue border highlight */
    }
    .job-title {
      color: #0d3b66; 
      font-weight: 800; 
      font-size: 1.25rem; /* Even larger, punchier title */
      margin-bottom: 6px;
      line-height: 1.3;
      overflow: hidden;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }
    .meta-muted { 
      color: #6b7280; 
      font-size: 0.95rem; 
      margin: 4px 0; 
      display: flex; 
      align-items: center; 
    }

    /* 3. Badges */
    .badge {
      display: inline-block;
      padding: 6px 14px; /* More horizontal padding */
      border-radius: 999px;
      font-weight: 700;
      font-size: 0.75rem;
      margin-right: 10px;
      text-transform: uppercase;
      letter-spacing: 0.8px; /* Added letter spacing */
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .badge-type { 
      background: #e6f0ff; 
      color: #045DE9; 
      border: 1px solid #cce0ff; 
    } 
    .badge-exp { 
      background: #fff9e6; 
      color: #e96704; 
      border: 1px solid #ffe6cc;
    } 

    /* 4. Forms and Buttons */
    .stTextInput>div>div>input, 
    .stSelectbox>div>div>div, 
    .stMultiSelect>div>div>div,
    .stTextArea>div>div>textarea {
      border-radius: 12px !important;
      padding: 14px !important; /* Extra padding */
      background: #fcfdff !important;
      border: 1px solid #dbe2ef !important; /* Soft, light border */
      box-shadow: inset 0 1px 4px rgba(0,0,0,0.05);
    }
    
    .apply-card {
      /* Smoother, less contrasting background */
      background: #f0f4ff; 
      border-radius: 18px;
      padding: 40px; /* More space */
      box-shadow: 0 10px 30px rgba(2,6,23,0.08);
      border: none;
      margin-top: 20px;
    }
    
    div[data-testid="stForm"] button,
    .stButton>button {
        border-radius: 10px !important;
        font-weight: 700 !important;
        padding: 12px 25px !important; /* Bigger buttons */
        transition: all 0.2s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* View Details button style */
    div[key^="view_"] button {
        background-color: #045DE9 !important;
        color: white !important;
        border: none;
        width: 100%;
        margin-top: 10px;
        box-shadow: 0 4px 15px rgba(4,93,233,0.3); /* Blue shadow */
    }
    div[key^="view_"] button:hover {
        background-color: #034ad1 !important;
        box-shadow: 0 6px 20px rgba(4,93,233,0.4); 
    }

    /* Clear button refinement */
    div:has(> button[title="Clear"]) button {
        background-color: #ffffff !important;
        color: #4b5563 !important;
        border: 1px solid #dbe2ef !important;
        margin-top: 25px; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    div:has(> button[title="Clear"]) button:hover {
        background-color: #f7f9ff !important;
    }
    
    /* Back button refinement */
    div:has(> button[title^="← Back to All Listings"]) button {
        background-color: #6c757d !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(108, 117, 125, 0.3);
    }

    /* 5. Pagination */
    .pagination button {
      background: #ffffff;
      border: 1px solid #dbe2ef;
      padding: 10px 18px; 
      margin: 0 5px;
      border-radius: 12px; 
      font-weight: 700;
      box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }
    .pagination button:hover:not(.active) { 
        background: #f7f9ff; 
        color: #045DE9; 
    }
    .pagination .active { 
        background: linear-gradient(135deg, #045DE9, #00d4ff) !important;
        color: white !important; 
        transform: none; 
        border-color: #045DE9 !important;
        box-shadow: 0 6px 20px rgba(4,93,233,0.4); 
    }

    /* Responsive adjustment for small screens */
    @media (max-width: 800px) {
      .job-card { height: auto; }
      .main-card, .section-card, .apply-card { padding: 18px; }
      .job-title { font-size: 1.1rem; }
      .pagination { flex-wrap: wrap; }
      .pagination button { margin: 4px; }
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # --- Title / Intro ---
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.title("🌐 ScreenerPro Public Job Board")
    st.write(
        "Welcome — explore active job campaigns, filter with advanced controls, view details and apply. "
        "ScreenerPro will instantly screen your resume and give you AI feedback."
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # --- Load skill library early (your existing function) ---
    skill_library = load_skill_library()
    if not skill_library:
        st.error("Cannot load skill library. AI screening will be limited.")
        return

    # --- Fetch campaigns ---
    campaigns = get_docs_from_firestore_rest(f"artifacts/{FIREBASE_PROJECT_ID}/public_campaigns")
    if not campaigns:
        st.info("No job opportunities are currently posted. Please check back later!")
        return

    # --- Insights Section (card) ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📊 Market Insights")
    df_campaigns = pd.DataFrame(campaigns) if campaigns else pd.DataFrame()
    if not df_campaigns.empty:
        df_campaigns['application_deadline'] = pd.to_datetime(df_campaigns['application_deadline'], errors='coerce').dt.date
        df_campaigns = df_campaigns[df_campaigns['application_deadline'] >= date.today()]
        df_campaigns = df_campaigns.dropna(subset=['job_type','experience_level'])

    metrics_col, charts_col = st.columns([1, 2])
    with metrics_col:
        st.metric("Active Listings", len(df_campaigns))
        if not df_campaigns.empty:
            exp_counts = df_campaigns['experience_level'].value_counts()
            most_common_exp = exp_counts.index[0] if not exp_counts.empty else "N/A"
            st.metric("Most Sought Level", most_common_exp)

    with charts_col:
        if not df_campaigns.empty:
            job_type_counts = df_campaigns['job_type'].value_counts().reset_index()
            job_type_counts.columns = ['Job Type','Count']
            fig = px.pie(
                job_type_counts, 
                values='Count', 
                names='Job Type', 
                hole=0.5, # Slightly larger hole
                color_discrete_sequence=px.colors.qualitative.Bold # Bolder colors
            )
            fig.update_layout(
                margin=dict(t=0, b=0, l=0, r=0), 
                height=250, # Slightly taller chart
                legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- Filters card ---
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("🔎 Search & Filters")

    # Create four columns for filters
    c1, c2, c3, c4 = st.columns([3,2,2,2])
    with c1:
        search_query = st.text_input("Search (title / company)", key="search_query_input", placeholder="e.g., Senior Data Scientist")
    with c2:
        all_job_types = sorted(df_campaigns['job_type'].unique().tolist()) if not df_campaigns.empty else []
        selected_job_types = st.multiselect("Job Type", options=all_job_types, key="selected_job_types_multiselect")
    with c3:
        all_exp = sorted(df_campaigns['experience_level'].unique().tolist()) if not df_campaigns.empty else []
        selected_exp_levels = st.multiselect("Experience Level", options=all_exp, key="selected_exp_levels_multiselect")
    with c4:
        search_location = st.text_input("Location", key="search_location_input", placeholder="e.g., Remote, San Francisco")

    # Sorting + clear
    sort_row, clear_row = st.columns([4,1])
    with sort_row:
        selected_sort_option = st.selectbox(
            "Sort by",
            options=[
                "Posted Date (Newest First)",
                "Posted Date (Oldest First)",
                "Application Deadline (Soonest First)",
                "Application Deadline (Latest First)",
                "Job Title (A-Z)",
            ],
            key="sort_by_select",
        )
    with clear_row:
        st.button("Clear", on_click=_clear_filters)

    st.markdown("</div>", unsafe_allow_html=True)

    # --- Apply filters to campaigns ---
    active_campaigns = [
        c for c in campaigns
        if not (c.get('application_deadline') and datetime.strptime(c['application_deadline'], '%Y-%m-%d').date() < date.today())
    ]

    filtered = []
    for c in active_campaigns:
        # search by title or company
        if search_query:
            target = (c.get('job_title','') + " " + c.get('company_name','')).lower()
            if search_query.lower() not in target:
                continue
        if selected_job_types and c.get('job_type') not in selected_job_types:
            continue
        if selected_exp_levels and c.get('experience_level') not in selected_exp_levels:
            continue
        if search_location and search_location.lower() not in c.get('job_location','').lower():
            continue
        filtered.append(c)

    # sorting
    def _sort_key(item):
        keymap = {
            "Posted Date (Newest First)": ("posted_date", True),
            "Posted Date (Oldest First)": ("posted_date", False),
            "Application Deadline (Soonest First)": ("application_deadline", False),
            "Application Deadline (Latest First)": ("application_deadline", True),
            "Job Title (A-Z)": ("job_title", False)
        }
        sk, rev = keymap.get(selected_sort_option, ("posted_date", True))
        if sk == "application_deadline" or sk == "posted_date":
            try:
                # Use a very distant past date for invalid/missing dates to push them to the end (or start if reversed)
                return datetime.strptime(item.get(sk, "1900-01-01"), "%Y-%m-%d") if item.get(sk) else datetime.min
            except Exception:
                return datetime.min
        return item.get(sk, "")
        
    # If option includes "Newest First" we invert by passing reverse True; map above sets rev, so:
    reverse_flag = selected_sort_option in ["Posted Date (Newest First)", "Application Deadline (Latest First)"]
    filtered.sort(key=_sort_key, reverse=reverse_flag)

    st.markdown("---")

    # --- Pagination & Listing ---
    jobs_per_page = 9
    total_jobs = len(filtered)
    total_pages = max(1, (total_jobs + jobs_per_page - 1) // jobs_per_page)
    current_page = max(1, min(st.session_state.job_page, total_pages))

    # Reset page if filters changed (nice UX): if current page > total_pages, clamp it
    st.session_state.job_page = current_page

    # If not in expanded detail mode, show grid + pagination
    if st.session_state.expanded_job_id is None:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader(f"💼 Available Job Openings ({total_jobs} results)")

        if total_jobs == 0:
            st.info("No job openings match your current search and filter criteria.")
        else:
            start = (current_page - 1) * jobs_per_page
            end = start + jobs_per_page
            page_jobs = filtered[start:end]

            cols = st.columns(3, gap="large")
            idx = 0
            for job in page_jobs:
                with cols[idx]:
                    st.markdown(
                        f"""
                        <div class="job-card">
                            <div>
                                <div class="job-title">{job.get('job_title','Untitled Job')}</div>
                                <div class="meta-muted" style="margin-bottom: 10px;">@ {job.get('company_name','Undisclosed')}</div>
                                <div class="meta-muted">📍 {job.get('job_location','N/A')}</div>
                                <div class="meta-muted">📅 Posted: {job.get('posted_date','N/A')}</div>
                            </div>
                            <div style='margin-top:12px; display:flex; gap:10px;'>
                                <span class="badge badge-type">{job.get('job_type','N/A')}</span>
                                <span class="badge badge-exp">{job.get('experience_level','N/A')}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    # only set expanded id via _view_job_details (it uses session state)
                    # NOTE: The custom CSS ensures this button is full width and styled blue.
                    st.button("View Details", key=f"view_{job['id']}", on_click=_view_job_details, args=(job['id'],))
                idx = (idx + 1) % 3
                if idx == 0:
                    cols = st.columns(3, gap="large")
            
            # Beautiful pagination controls
            st.markdown('<div class="pagination">', unsafe_allow_html=True)
            pag_cols = st.columns([1, 6, 1])
            with pag_cols[0]:
                if st.button("◀ Prev", key="pag_prev_btn", disabled=(current_page == 1)):
                    st.session_state.job_page = max(1, current_page - 1)
                    st.rerun()
            with pag_cols[1]:
                # generate page buttons in a row, but cap visible pages to a window (e.g., 7)
                visible = 7
                if total_pages <= visible:
                    pages_range = list(range(1, total_pages + 1))
                else:
                    half = visible // 2
                    start_page = max(1, current_page - half)
                    end_page = min(total_pages, start_page + visible - 1)
                    # shift if we're at the end
                    if end_page - start_page + 1 < visible:
                        start_page = max(1, end_page - visible + 1)
                    pages_range = list(range(start_page, end_page + 1))

                # Use columns to force horizontal layout
                if pages_range:
                    p_cols = st.columns(len(pages_range))
                    for i, p in enumerate(pages_range):
                        with p_cols[i]:
                            # Highlight current page with primary type
                            btn_type = "primary" if p == current_page else "secondary"
                            if st.button(str(p), key=f"page_{p}", type=btn_type, use_container_width=True):
                                st.session_state.job_page = p
                                st.rerun()


            with pag_cols[2]:
                if st.button("Next ▶", key="pag_next_btn", disabled=(current_page == total_pages)):
                    st.session_state.job_page = min(total_pages, current_page + 1)
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)  # close section-card

    else:
        # ----------- Keep your exact details + apply code block (with safe initialization) -----------
        # Display expanded job details if a job is selected
        selected_campaign = next((c for c in active_campaigns if c['id'] == st.session_state.expanded_job_id), None)
        
        # 🔥 Fail-safe: Direct fetch if not found in loaded list (e.g. deep link to old/filtered job)
        if not selected_campaign and st.session_state.expanded_job_id:
             selected_campaign = get_single_doc_from_firestore_rest(
                 f"artifacts/{FIREBASE_PROJECT_ID}/public_campaigns",
                 st.session_state.expanded_job_id
             )
        
        # 🔥 Step 3: Job Expiry Logic (User Prescribed)
        if selected_campaign:
             deadline = selected_campaign.get('application_deadline')
             if deadline:
                 # Check if deadline is string or date object and compare
                 try:
                     d_date = datetime.strptime(deadline, '%Y-%m-%d').date() if isinstance(deadline, str) else deadline
                     if isinstance(d_date, date) and d_date < date.today():
                         st.warning("⚠️ This job is no longer accepting applications.")
                         st.button("← Back to All Listings", on_click=_close_job_details)
                         st.stop()
                 except Exception:
                     pass # Fallback if date parsing fails, assume active
        
        st.button("← Back to All Listings", on_click=_close_job_details)
        st.markdown("---")

        if selected_campaign:
            st.markdown(f"## 📋 Details for {selected_campaign.get('job_title', 'Untitled Job')} at {selected_campaign.get('company_name', 'Undisclosed Company')}")
            
            # --- Feature B: Inject JSON-LD Schema ---
            schema_json = generate_job_posting_schema(selected_campaign, selected_campaign.get('id'))
            st.components.v1.html(
                f"<script type='application/ld+json'>{schema_json}</script>",
                 height=0
            )

            # --- Feature A: Share Buttons ---
            # Update Link to point to Native Page for stability
            base = APP_BASE_URL.rstrip("/")
            current_job_url = f"{base}/Public_Job_Board?job_id={selected_campaign.get('id')}"
            
            encoded_url = urllib.parse.quote(current_job_url)
            encoded_title = urllib.parse.quote(f"Check out this {selected_campaign.get('job_title')} role at {selected_campaign.get('company_name')}")
            
            st.markdown(
                f"""
                <div style="display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap;">
                    <a href="https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}" target="_blank" style="text-decoration:none;">
                        <button style="background-color:#0077b5; color:white; border:none; padding:8px 16px; border-radius:8px; font-weight:600; cursor:pointer;">LinkedIn</button>
                    </a>
                    <a href="https://twitter.com/intent/tweet?text={encoded_title}&url={encoded_url}" target="_blank" style="text-decoration:none;">
                        <button style="background-color:#1da1f2; color:white; border:none; padding:8px 16px; border-radius:8px; font-weight:600; cursor:pointer;">Twitter</button>
                    </a>
                    <a href="mailto:?subject={encoded_title}&body={encoded_url}" target="_blank" style="text-decoration:none;">
                        <button style="background-color:#ea4335; color:white; border:none; padding:8px 16px; border-radius:8px; font-weight:600; cursor:pointer;">Email</button>
                    </a>
                    <a href="https://api.whatsapp.com/send?text={encoded_title}%20{encoded_url}" target="_blank" style="text-decoration:none;">
                         <button style="background-color:#25D366; color:white; border:none; padding:8px 16px; border-radius:8px; font-weight:600; cursor:pointer;">WhatsApp</button>
                    </a>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            # --- Job Metadata Card ---
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown("### Job Overview")
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**🏢 Company:** **{selected_campaign.get('company_name', 'N/A')}**")
                st.markdown(f"**📍 Location:** **{selected_campaign.get('job_location', 'N/A')}**")
                st.markdown(f"**🗓️ Posted On:** {selected_campaign.get('posted_date', 'N/A')}")
                st.markdown(f"**⏳ Deadline:** **{selected_campaign.get('application_deadline', 'N/A')}**")
            with col2:
                st.markdown(f"**💼 Job Type:** {selected_campaign.get('job_type', 'N/A')}")
                st.markdown(f"**📈 Experience Level:** {selected_campaign.get('experience_level', 'N/A')}")
                # Fetch current views for the expanded job
                public_campaign_path = f"artifacts/{FIREBASE_PROJECT_ID}/public_campaigns"
                current_public_campaign_doc_data = get_single_doc_from_firestore_rest(public_campaign_path, selected_campaign.get('id'))
                current_views_expanded = current_public_campaign_doc_data.get('views_count', 0) if current_public_campaign_doc_data else selected_campaign.get('views_count', 0)
                st.markdown(f"**👁️ Views:** {current_views_expanded}")
                st.markdown(f"**🆔 Job ID:** `{selected_campaign.get('id', 'N/A')}`")
            st.markdown('</div>', unsafe_allow_html=True) # close section-card

            st.markdown("---")
            st.markdown("### 🔑 Key Requirements")
            
            # --- Requirements Card ---
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            req_col1, req_col2 = st.columns(2)
            with req_col1:
                min_exp = selected_campaign.get('min_experience', 0)
                max_exp = selected_campaign.get('max_experience', 20)
                st.markdown(f"**Years of Experience:** **{min_exp}** to **{max_exp}** years")
            with req_col2:
                min_cgpa = selected_campaign.get('min_cgpa', 0.0)
                if min_cgpa > 0:
                    st.markdown(f"**Minimum CGPA:** **{min_cgpa:.1f}** (on 4.0 scale)")
                else:
                    st.markdown("**Minimum CGPA:** Not specified")
            
            required_skills = selected_campaign.get('required_skills', [])
            if required_skills:
                st.markdown("**🎯 Required Skills:**")
                # Updated skill badge styling with a slight blue gradient look
                skill_badges = " ".join([f"<span class='badge badge-type' style='background: linear-gradient(180deg, #f7faff 0%, #e8edff 100%); color: #0d3b66; border: 1px solid #d0e0ff;'>{skill}</span>" for skill in required_skills])
                st.markdown(f"<div style='margin-top: 10px; margin-bottom: 10px;'>{skill_badges}</div>", unsafe_allow_html=True)
            else:
                st.markdown("**🎯 Required Skills:** Not specified.")
            st.markdown('</div>', unsafe_allow_html=True) # close section-card


            st.markdown("---")
            st.markdown("### 📝 Full Job Description")
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            # Use markdown for the description content to preserve formatting
            st.markdown(selected_campaign.get('job_description', 'No description provided.'))
            st.markdown('</div>', unsafe_allow_html=True) # close section-card
            st.markdown("---")

            st.markdown("### 🚀 Ready to Apply?")
            st.info("Fill out the form below to submit your application and get instant AI screening results!")
            
            # --- Application Form Card (apply-card) ---
            st.markdown("<div class='apply-card'>", unsafe_allow_html=True) 

            if 'form_submitted_feedback' not in st.session_state:
                st.session_state['form_submitted_feedback'] = {}
            if f'submit_triggered_{selected_campaign["id"]}' not in st.session_state:
                st.session_state[f'submit_triggered_{selected_campaign["id"]}'] = False

            applicant_name_key = f"applicant_name_form_{selected_campaign['id']}"
            applicant_email_key = f"applicant_email_form_{selected_campaign['id']}"
            uploaded_resume_key = f"resume_upload_form_{selected_campaign['id']}_{st.session_state.file_uploader_reset_key}"

            # ensure those keys exist in session_state (this prevents KeyError inside _handle_application_submission)
            if applicant_name_key not in st.session_state:
                st.session_state[applicant_name_key] = ""
            if applicant_email_key not in st.session_state:
                st.session_state[applicant_email_key] = ""
            # file uploader key will exist once the form renders (we can't pre-create streamlit file uploader values here)

            with st.form(key=f"apply_form_{selected_campaign['id']}", clear_on_submit=False):
                applicant_name_form = st.text_input(
                    "Your Full Name", 
                    value=st.session_state[applicant_name_key], 
                    key=applicant_name_key
                )
                applicant_email_form = st.text_input(
                    "Your Email", 
                    value=st.session_state[applicant_email_key], 
                    key=applicant_email_key
                )
                uploaded_resume_form_obj = st.file_uploader(
                    "Upload Your Resume (PDF, JPG, PNG)", 
                    type=["pdf", "jpg", "jpeg", "png"], 
                    key=uploaded_resume_key
                )
                
                submit_application = st.form_submit_button(
                    "Submit Application",
                    on_click=_handle_application_submission,
                    args=(selected_campaign['id'], applicant_name_key, applicant_email_key, uploaded_resume_key)
                )

            # --- Process the form submission from session_state (your original logic) ---
            if st.session_state.get(f'submit_triggered_{selected_campaign["id"]}', False):
                submitted_applicant_name = st.session_state.get(f'current_applicant_name_{selected_campaign["id"]}', "")
                submitted_applicant_email = st.session_state.get(f'current_applicant_email_{selected_campaign["id"]}', "")
                submitted_uploaded_resume_obj = st.session_state.get(f'current_uploaded_resume_{selected_campaign["id"]}')

                if not submitted_applicant_name or not submitted_applicant_email or not submitted_uploaded_resume_obj:
                    st.error("Validation Error: Please fill in all required fields and upload your resume.")
                    st.session_state['form_submitted_feedback'][selected_campaign['id']] = "error"
                else:
                    with st.spinner("Processing your application and screening your resume..."):
                        try:
                            resume_bytes_io = BytesIO(submitted_uploaded_resume_obj.read())
                            resume_text = extract_text_from_file(resume_bytes_io, submitted_uploaded_resume_obj.name, submitted_uploaded_resume_obj.type)

                            if resume_text.startswith("[ERROR]"):
                                st.error(f"Resume Processing Error: {resume_text.replace('[ERROR] ', '')}")
                                st.session_state['form_submitted_feedback'][selected_campaign['id']] = "error"
                                st.session_state[f'submit_triggered_{selected_campaign["id"]}'] = False
                                return

                            max_experience_campaign = selected_campaign.get('max_experience', 20)
                            min_experience_campaign = selected_campaign.get('min_experience', 0)
                            min_cgpa_campaign = selected_campaign.get('min_cgpa', 0.0)
                            min_score_campaign = selected_campaign.get('min_score', 0)

                            screening_results = process_single_resume_logic(
                                file_name=submitted_uploaded_resume_obj.name,
                                text=resume_text,
                                jd_text=selected_campaign.get('job_description', ''),
                                jd_name_for_results=selected_campaign.get('job_title', 'Public Job'),
                                skill_library=skill_library,
                                max_experience=max_experience_campaign,
                                summary_tone="Professional"
                            )

                            if submitted_applicant_name:
                                screening_results['Candidate Name'] = submitted_applicant_name
                            if submitted_applicant_email:
                                screening_results['Email'] = submitted_applicant_email

                            final_score = screening_results.get('Score (%)', 0)
                            
                            meets_exp = (screening_results.get('Years Experience', 0) >= min_experience_campaign and
                                         screening_results.get('Years Experience', 0) <= max_experience_campaign)
                            meets_cgpa = (screening_results.get('CGPA (4.0 Scale)') is None or
                                          screening_results.get('CGPA (4.0 Scale)') >= min_cgpa_campaign)

                            if final_score >= min_score_campaign and meets_exp and meets_cgpa:
                                application_status = "shortlisted"
                                ai_decision = "Shortlisted by AI"
                            else:
                                application_status = "submitted" 
                                ai_decision = "Submitted" 
# -----------------------------------------
# SAVE RESUME AS BASE64 (FULL APPLY) — FIXED
# -----------------------------------------
                            submitted_uploaded_resume_obj.seek(0)
                            resume_bytes = submitted_uploaded_resume_obj.read()

# extract text from same bytes
                            resume_text = extract_text_from_file(BytesIO(resume_bytes),
                                     submitted_uploaded_resume_obj.name,
                                     submitted_uploaded_resume_obj.type)

# encode file
                            encoded_resume = base64.b64encode(resume_bytes).decode("utf-8")
                            resume_extension = submitted_uploaded_resume_obj.name.split('.')[-1]
                            resume_filename = submitted_uploaded_resume_obj.name




                            application_data = {
                                "application_id": str(uuid.uuid4()),
                                "campaign_id": selected_campaign.get('id', 'N/A'),
                                "job_title": selected_campaign.get('job_title', 'N/A'),
                                "company_name": selected_campaign.get('company_name', 'N/A'),
                                "applicant_name": screening_results.get('Candidate Name', submitted_applicant_name),
                                "applicant_email": screening_results.get('Email', submitted_applicant_email),
                                "applied_at": datetime.now(),
                                "resume_filename": submitted_uploaded_resume_obj.name,
                                "resume_text_snippet": resume_text[:500] + "..." if len(resume_text) > 500 else resume_text,
                                "ai_score": final_score,
                                "resume_file_base64": encoded_resume,
                                "resume_file_extension": resume_extension,
                                "resume_filename": submitted_uploaded_resume_obj.name,
                                "ai_tag": screening_results.get('Tag', 'N/A'),
                                "ai_suggestion": screening_results.get('AI Suggestion', 'N/A'),
                                "years_experience": screening_results.get('Years Experience', 0),
                                "matched_skills": screening_results.get('Matched Keywords', ''),
                                "missing_skills": screening_results.get('Missing Skills', ''),
                                "certificate_id": screening_results.get('Certificate ID', str(uuid.uuid4())),
                                "certificate_rank": screening_results.get('Certificate Rank', 'Not Applicable'),
                                "status": application_status,
                                "AI_Decision": ai_decision,
                                "Manual Shortlist": 0,
                                "source": "Public Job Board"
                            }

                            hr_user_uid = selected_campaign.get('created_by_uid')
                            if hr_user_uid:
                                if add_doc_to_firestore_rest(
                                    f"artifacts/{FIREBASE_PROJECT_ID}/users/{hr_user_uid}/my_campaigns/{selected_campaign.get('id')}/applications",
                                    application_data,
                                    doc_id=application_data["application_id"]
                                ):
                                    st.success("Your application has been submitted and screened!")
                                    st.session_state['form_submitted_feedback'][selected_campaign['id']] = "success"

                                    update_campaign_metrics(selected_campaign.get('id'), hr_user_uid, selected_campaign)

                                    # Send application confirmation email
                                    send_application_success_email(
                                        applicant_name=application_data['applicant_name'],
                                        applicant_email=application_data['applicant_email'],
                                        job_title=application_data['job_title'],
                                        company_name=application_data['company_name'],
                                        ai_score=application_data['ai_score'],
                                        ai_decision=application_data['AI_Decision']
                                    )

                                    st.subheader("Your AI Screening Results")
                                    st.info(f"Your AI Match Score for **{selected_campaign.get('job_title', 'this role')}** is: **{screening_results.get('Score (%)', 0.0):.1f}%**")
                                    st.write(f"**AI Assessment:** {screening_results.get('AI Suggestion', 'No specific assessment.')}")
                                    st.write(f"**Your Certificate Rank:** {screening_results.get('Certificate Rank', 'Not Applicable')}")
                                    st.write(f"**Application Status:** {ai_decision}")
                                    
                                    if screening_results.get('Score (%)', 0.0) >= 60:
                                        st.success("Congratulations! You've earned a ScreenerPro Certificate for this screening.")
                                        cert_html = generate_certificate_html(
                                            screening_results, 
                                            selected_campaign.get('job_title', 'Public Job'),
                                            APP_BASE_URL
                                        )
                                        st.components.v1.html(cert_html, height=600, scrolling=True)
                                        st.markdown(f"You can verify your certificate online at: [{APP_BASE_URL}?page=Certificate%20Verification&cert_id={screening_results.get('Certificate ID', '')}]({APP_BASE_URL}?page=Certificate%20Verification&cert_id={screening_results.get('Certificate ID', '')})")
                                    else:
                                        st.info("While your application has been submitted, your score did not meet the threshold for a ScreenerPro Certificate for this role.")

                                else:
                                    st.error("Firestore Save Error: Failed to save application to Firestore. Please try again.")
                                    st.session_state['form_submitted_feedback'][selected_campaign['id']] = "error"
                            else:
                                st.error("Configuration Error: Could not determine the HR user associated with this campaign. Application cannot be saved.")
                                st.session_state['form_submitted_feedback'][selected_campaign['id']] = "error"

                        except Exception as e:
                            st.error(f"An unexpected error occurred during application processing: {e}")
                            st.exception(e)
                            st.session_state['form_submitted_feedback'][selected_campaign['id']] = "error"
                
                st.session_state[f'submit_triggered_{selected_campaign["id"]}'] = False

            feedback_status = st.session_state['form_submitted_feedback'].get(selected_campaign['id'])
            if feedback_status == "success":
                st.success("Thank you! Your application was submitted.")
            elif feedback_status == "error":
                st.error("There was an issue with your submission. Please try again.")
            elif feedback_status == "pending":
                st.info("Your application is being processed...")

            st.markdown("</div>", unsafe_allow_html=True) # close apply-card
        else:
            st.error("Selected job details not found. Please go back to listings.")

# Entry point for the Streamlit page
if __name__ == "__main__":
    st.set_page_config(page_title="ScreenerPro - Public Job Board", layout="wide", page_icon="🌐")
    if 'APP_BASE_URL' not in st.session_state:
        st.session_state['APP_BASE_URL'] = 'https://screenerpro.streamlit.app'
    public_job_board_page()


import google.generativeai as genai
def generate_llm_hr_summary(
    name, score, experience, matched_skills, missing_skills, cgpa, job_domain, tone
):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime

    # -------------------------------
    # ADMIN EMAIL NOTIFIER
    # -------------------------------
    def notify_admin(error_type, error_message):
        try:
            GMAIL_ADDRESS = st.secrets.get("GMAIL_ADDRESS")
            GMAIL_APP_PASSWORD = st.secrets.get("GMAIL_APP_PASSWORD")
            ADMIN_EMAIL = "manav.nagpal2005@gmail.com"

            if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
                return

            msg = MIMEMultipart()
            msg["From"] = GMAIL_ADDRESS
            msg["To"] = ADMIN_EMAIL
            msg["Subject"] = f"⚠️ ScreenerPro Gemini Error — {error_type}"

            body = f"""
Time: {datetime.now().isoformat()}
Candidate: {name}
Domain: {job_domain}
Score: {score}

Error Type: {error_type}
Error Message:
{error_message}
"""
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
                server.send_message(msg)

        except Exception:
            pass  # never crash app due to email failure

    # -------------------------------
    # PROMPT
    # -------------------------------
    prompt = f"""
You are an HR professional writing an internal candidate evaluation.

Rules:
- DO NOT mention AI, automation, or models
- Tone: {tone}

Candidate:
Name: {name}
Domain: {job_domain}
Score: {score}%
Experience: {experience} years
CGPA: {cgpa}
Matched Skills: {matched_skills}
Missing Skills: {missing_skills}

Write sections:
1. Overall Fit
2. Strengths
3. Weak Areas / Risks
4. Role Alignment
5. Final Recommendation
"""

    # -------------------------------
    # GEMINI EXECUTION
    # -------------------------------
    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        response = model.generate_content(prompt)

        text = (
            response.text
            or (
                response.candidates[0].content.parts[0].text
                if response.candidates and response.candidates[0].content.parts
                else ""
            )
        )

        if not text.strip():
            raise Exception("EMPTY_GEMINI_OUTPUT")

        return text.strip()

    except Exception as e:
        err = str(e).lower()

        if "429" in err or "quota" in err or "exceeded" in err:
            notify_admin("QUOTA_EXCEEDED", str(e))
        else:
            notify_admin("GENERAL_GEMINI_FAILURE", str(e))

        return f"""
### Overall Fit
{name} scored **{score}%** and shows potential in the {job_domain} domain.

### Strengths
- Experience: {experience} years
- Matched Skills: {matched_skills or "None"}

### Weak Areas / Risks
- Missing Skills: {missing_skills or "No major gaps"}

### Role Alignment
Partial alignment observed.

### Final Recommendation
Recommend targeted upskilling and practical exposure.
"""

