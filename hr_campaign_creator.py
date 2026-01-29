import streamlit as st
import requests
import json
from datetime import datetime, date, timedelta
import uuid
from io import BytesIO
import os
import re
import plotly.express as px
import pandas as pd
import urllib.parse # Import urllib.parse for URL encoding
import zipfile # Added for handling ZIP file uploads
import tempfile # Added for creating temporary directories
import smtplib # For sending emails
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
import uuid, base64, os
# Import core screening logic functions from screener_logic.py
from screener_logic import (
    load_skill_library,
    extract_text_from_file,
    process_single_resume_logic,
)
# Import new services
from utils.matching_service import calculate_match_score, filter_eligible_candidates
from utils.email_service import send_email, generate_instant_match_email_html, generate_plain_text_match_email

def run_campaign_matchmaking(campaign_id, job_title, company_name, location, required_skills, min_experience, min_score=70.0):
    """
    Finds matching candidates for a campaign and sends notification emails.
    Returns the count of emails sent.
    """
    try:
        # 1. Fetch all candidates
        users_collection = f"artifacts/{FIREBASE_PROJECT_ID}/public/data/user_profiles"
        all_candidates = get_docs_from_firestore_rest(users_collection)
        
        # 2. Prepare job data for matching
        job_data_for_matching = {
            "required_skills": required_skills,
            "min_experience": min_experience,
            "job_title": job_title,
            "company_name": company_name,
            "location": location
        }
        
        # 3. Filter candidates
        matches = filter_eligible_candidates(all_candidates, job_data_for_matching, min_threshold=min_score)
        
        # 4. Batch send emails (Limit to top 20 to prevent timeout)
        sent_count = 0
        for match in matches[:20]:
            cand = match['candidate']
            score = match['score']
            c_email = cand.get('email')
            c_name = cand.get('name') or cand.get('first_name') or "Candidate"
            
            if c_email:
                html_content = generate_instant_match_email_html(
                    c_name, job_title, company_name, location, score, campaign_id
                )
                plain_content = generate_plain_text_match_email(
                    c_name, job_title, company_name, score, campaign_id
                )
                
                # Send
                send_email(c_email, f"🎯 New Job Match: {job_title} ({score}%)", plain_content, html_content)
                sent_count += 1
        return sent_count
    except Exception as e:
        print(f"Matchmaking error: {e}")
        return 0

from google import generativeai as genai

# Safely access secrets to prevent crash on load
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    # We will handle the missing key error gracefully when generation is attempted
    pass
def safe_gemini_generate(
    prompt: str,
    model_name: str,
    fallback_text: str,
    context_label: str = "Gemini Failure"
):
    """
    Central Gemini wrapper.
    - Returns Gemini output if OK
    - Returns fallback_text if Gemini fails
    - Emails admin ONLY when fallback is used
    """

    ADMIN_EMAIL = "manav.nagpal2005@gmail.com"
    GMAIL_ADDRESS = "screenerpro.ai@gmail.com"
    GMAIL_APP_PASSWORD = st.secrets.get("GMAIL_APP_PASSWORD")

    def notify_admin(error_msg):
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)

            msg = MIMEMultipart()
            msg["From"] = GMAIL_ADDRESS
            msg["To"] = ADMIN_EMAIL
            msg["Subject"] = f"⚠️ ScreenerPro Gemini Fallback Used"

            body = f"""
Context: {context_label}

Error:
{error_msg}

Prompt:
{prompt[:1500]}
"""
            msg.attach(MIMEText(body, "plain"))
            server.sendmail(GMAIL_ADDRESS, ADMIN_EMAIL, msg.as_string())
            server.quit()
        except Exception:
            pass  # silent

    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)

        if not response or not getattr(response, "text", None):
            raise Exception("Empty Gemini response")

        return response.text.strip()

    except Exception as e:
        notify_admin(str(e))
        return fallback_text


# Firebase Project ID and API Key from environment variables
FIREBASE_PROJECT_ID = globals().get('__app_id', 'screenerproapp')
FIREBASE_WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY', 'AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw')
FIRESTORE_DATABASE_ROOT_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)"
import base64

def _safe_date(value):
    """
    Converts Firestore dates, strings, timestamps, or None into a safe Python date.
    Always returns a valid datetime.date object.
    """
    if not value:
        return date.today()

    # Already a date object
    if isinstance(value, date):
        return value

    # Firestore timestamp dict: {"seconds": ..., "nanoseconds": ...}
    if isinstance(value, dict) and "seconds" in value:
        try:
            return datetime.fromtimestamp(value["seconds"]).date()
        except:
            return date.today()

    # String (ISO or other formats)
    if isinstance(value, str):
        try:
            # Handle ISO format with 'Z'
            return datetime.fromisoformat(value.replace('Z', '')).date()
        except:
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except:
                return date.today()

    # Fallback
    try:
        return value.date()
    except:
        return date.today()

def encode_file_to_base64(uploaded_file):
    if uploaded_file is None:
        return None
    return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")

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
            # FIX 1: Use _safe_date for robust date handling
            data[key] = _safe_date(value_obj["timestampValue"])
        # FIX 2: Correctly parse array elements without incorrect dictionary wrapping
        elif "arrayValue" in value_obj:
            values = value_obj["arrayValue"].get("values", [])
            parsed_list = []
            for item in values:
                if "stringValue" in item:
                    parsed_list.append(item["stringValue"])
                elif "integerValue" in item:
                    try:
                        parsed_list.append(int(item["integerValue"]))
                    except ValueError:
                        parsed_list.append(0) 
                elif "doubleValue" in item:
                    parsed_list.append(float(item["doubleValue"]))
                elif "booleanValue" in item:
                    parsed_list.append(item["booleanValue"])
                elif "mapValue" in item:
                    # Recursively parse nested maps
                    parsed_list.append(from_firestore_format({"fields": item["mapValue"]["fields"]}))
                # Handle nulls inside arrays
                elif "nullValue" in item:
                    parsed_list.append(None)
                else:
                    # Fallback for unexpected types
                    parsed_list.append(str(item) if item else None)
            data[key] = parsed_list
        # END FIX 2
        elif "mapValue" in value_obj and "fields" in value_obj["mapValue"]:
            data[key] = from_firestore_format({"fields": value_obj["mapValue"]["fields"]})
        elif "nullValue" in value_obj:
            data[key] = None
        else:
            data[key] = str(value_obj)
    return data

def add_doc_to_firestore_rest(collection_path: str, data: dict, doc_id: str = None):
    """Adds a document to a Firestore collection using REST API."""
    url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents/{collection_path}?key={FIREBASE_WEB_API_KEY}"
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
    url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents/{collection_path}?key={FIREBASE_WEB_API_KEY}"
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

@st.cache_data(ttl=1) # Cache for 1 second
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
def delete_doc_firestore_rest(collection_path, doc_id):
    """
    Deletes a document from Firestore using the Google REST API.
    Path format: artifacts/<PROJECT_ID>/public_campaigns
    """

    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/{collection_path}/{doc_id}"

    response = requests.delete(url)

    if response.status_code in [200, 204]:
        print(f"🔥 Deleted Firestore document: {doc_id}")
        return True
    else:
        print(f"❌ Failed to delete document {doc_id}: {response.text}")
        return False
def get_applications_for_campaign(campaign_id: str, user_uid: str, firebase_project_id: str, firestore_database_root_url: str, firebase_web_api_key: str):
    """Retrieves all applications for a specific job campaign."""
    if not campaign_id or not user_uid:
        return []
    
    collection_path = f"artifacts/{firebase_project_id}/users/{user_uid}/my_campaigns/{campaign_id}/applications"
    url = f"{firestore_database_root_url}/documents/{collection_path}?key={FIREBASE_WEB_API_KEY}"

    try:
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            applications = []
            if 'documents' in data:
                for doc in data['documents']:
                    app_id = doc['name'].split('/')[-1]
                    doc_data = from_firestore_format(doc)
                    doc_data['id'] = app_id
                    applications.append(doc_data)
            return applications
        elif res.status_code == 404:
            return []
        else:
            st.error(f"Failed to fetch applications for campaign `{campaign_id}`: {res.status_code} - {res.text}")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Firebase connection error fetching applications for campaign `{campaign_id}`: {e}")
        return []

def update_campaign_metrics(campaign_id: str, hr_user_uid: str):
    """
    Fetches all applications for a campaign, recalculates metrics, and updates
    the campaign document in both private and public collections.
    """
    try:
        private_campaign_path = f"artifacts/{FIREBASE_PROJECT_ID}/users/{hr_user_uid}/my_campaigns"
        public_campaign_path = f"artifacts/{FIREBASE_PROJECT_ID}/public_campaigns"

        existing_private_campaign = get_single_doc_from_firestore_rest(private_campaign_path, campaign_id)
        existing_public_campaign = get_single_doc_from_firestore_rest(public_campaign_path, campaign_id)

        if not existing_private_campaign and not existing_public_campaign:
            return False

        campaign_to_update = existing_public_campaign if existing_public_campaign else existing_private_campaign
        
        if not campaign_to_update:
            return False

        applications_data = get_applications_for_campaign(
            campaign_id,
            hr_user_uid,
            FIREBASE_PROJECT_ID,
            FIRESTORE_DATABASE_ROOT_URL,
            FIREBASE_WEB_API_KEY
        )

        total_applications = len(applications_data)
        # Ensure safe conversion to float for calculation
        total_score_sum = sum(float(app.get('ai_score', 0)) for app in applications_data)
        new_avg_score = (total_score_sum / total_applications) if total_applications > 0 else 0.0

        # Update only the relevant fields in the fetched campaign data
        campaign_to_update["application_count"] = total_applications
        campaign_to_update["avg_match_score"] = new_avg_score
        campaign_to_update["last_updated"] = datetime.now().isoformat()

        # Update private campaign (essential)
        update_doc_in_firestore_rest(private_campaign_path, campaign_id, campaign_to_update)
        # Ensure public campaign is also updated with full data
        update_doc_in_firestore_rest(public_campaign_path, campaign_id, campaign_to_update)

        return True
    except Exception as e:
        st.error(f"An error occurred while updating campaign metrics for `{campaign_id}`: {e}")
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

# The old _normalize_date function was removed as part of the fix.

def extract_skills_from_text(job_description, skill_library):
    """Extracts skills from a job description based on the provided skill library."""
    jd_lower = job_description.lower()
    found_skills = []

    if isinstance(skill_library, dict):
        
        for skill_category in skill_library.values():
            if isinstance(skill_category, (list, tuple, set)):
                for skill in skill_category:
                    if isinstance(skill, str) and skill.lower() in jd_lower:
                        found_skills.append(skill)
            else:
                st.warning(f"Unexpected skill_category format in skill_library (dict case): {type(skill_category)}. Expected a list of skills. Content: {skill_category}")
                
    elif isinstance(skill_library, (list, tuple, set)):
        
        for skill in skill_library:
            if isinstance(skill, str) and skill.lower() in jd_lower:
                found_skills.append(skill)
            else:
                st.warning(f"Unexpected skill format in skill_library (list case): {type(skill)}. Expected a string. Content: {skill}")
    else:
        st.error(f"Internal Error: skill_library is neither a dictionary nor a list in extract_skills_from_text. Type: {type(skill_library)}. Content: {skill_library}")
        return [] # Return an empty list to prevent further errors

    return list(set(found_skills))[:15] # Limit to top 15 unique skills

import json
from google import generativeai as genai

def generate_jd_with_gemini(
    job_title,
    skills,
    experience_level,
    location,
    min_exp,
    max_exp,
    min_cgpa
):
    """
    Generates a Job Description using Gemini.
    Always returns:
    {
      "jd": <string>,
      "skills": <list>
    }
    """

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    ADMIN_EMAIL = "manav.nagpal2005@gmail.com"
    GMAIL_ADDRESS = "screenerpro.ai@gmail.com"
    GMAIL_APP_PASSWORD = st.secrets.get("GMAIL_APP_PASSWORD")

    def notify_admin(error_msg):
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)

            msg = MIMEMultipart()
            msg["From"] = GMAIL_ADDRESS
            msg["To"] = ADMIN_EMAIL
            msg["Subject"] = "⚠️ Gemini JD Generation Fallback Used"

            body = f"""
Job Title: {job_title}

Error:
{error_msg}
"""
            msg.attach(MIMEText(body, "plain"))
            server.sendmail(GMAIL_ADDRESS, ADMIN_EMAIL, msg.as_string())
            server.quit()
        except Exception:
            pass  # silent fail

    # ------------------ SAFE FALLBACK JD ------------------
    fallback_jd = f"""
Job Title: {job_title}
Location: {location}
Experience Level: {experience_level}

We are looking for a {job_title} to join our team and contribute to core responsibilities
related to this role.

Key Responsibilities:
- Work on role-specific responsibilities and deliver high-quality outcomes
- Collaborate with cross-functional teams to support business objectives
- Follow best practices, compliance standards, and company policies

Requirements:
- Experience between {min_exp} and {max_exp} years
- Strong foundational and role-relevant skills
- Minimum CGPA: {min_cgpa}

This role is ideal for candidates who are motivated, adaptable, and eager to grow.
"""

    fallback_skills = skills[:8] if skills else []

    # ------------------ GEMINI ATTEMPT ------------------
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("models/gemini-2.5-flash")

        prompt = f"""
You are an expert HR consultant and JD writer.

STRICT JSON ONLY:
{{
  "jd": "",
  "skills": []
}}

INPUT:
Job Title: {job_title}
Experience Level: {experience_level}
Location: {location}
Experience Range: {min_exp}–{max_exp} years
Minimum CGPA: {min_cgpa}
Provided Skills: {", ".join(skills)}
"""

        output = model.generate_content(prompt).text
        output = output.replace("```json", "").replace("```", "").strip()

        data = json.loads(output)

        jd_text = data.get("jd")
        skill_list = data.get("skills")

        if not jd_text or not isinstance(skill_list, list):
            raise Exception("Invalid Gemini JSON structure")

        return {
            "jd": jd_text.strip(),
            "skills": skill_list
        }

    # ------------------ FALLBACK ------------------
    except Exception as e:
        notify_admin(str(e))

        return {
            "jd": fallback_jd.strip(),
            "skills": fallback_skills
        }



# send_email function has been moved to utils.email_service

def generate_email_template_content(template_type, candidate_name, job_title, company_name, interview_details, custom_notes):
    """Generates email subject and body based on template type."""
    subject = ""
    body = ""

    if template_type == "Shortlist":
        subject = f"Congratulations! Your Application for {job_title} at {company_name}"
        body = f"""Dear {candidate_name},

We are pleased to inform you that you have been shortlisted for the {job_title} position at {company_name}. Your profile stood out, and we are very impressed with your qualifications.

{custom_notes}

We will be in touch shortly with the next steps in the hiring process.

Best regards,
The {company_name} Hiring Team"""
    elif template_type == "Rejection":
        subject = f"Update on Your Application for {job_title} at {company_name}"
        body = f"""Dear {candidate_name},

Thank you for your interest in the {job_title} position at {company_name}. We appreciate you taking the time to apply.

After careful consideration, we regret to inform you that we will not be moving forward with your application at this time.

{custom_notes}

We wish you the best in your job search.

Sincerely,
The {company_name} Hiring Team"""
    elif template_type == "Interview Invite":
        subject = f"Interview Invitation: {job_title} at {company_name}"
        body = f"""Dear {candidate_name},

Thank you for your application for the {job_title} position at {company_name}. We were very impressed with your qualifications and would like to invite you for an interview.

Your interview is scheduled for: {interview_details}

{custom_notes}

We look forward to speaking with you.

Best regards,
The {company_name} Hiring Team"""
    return subject, body

# Callback function to clear email fields after sending
def _clear_email_fields():
    st.session_state['generated_email_subject_value'] = ""
    st.session_state['generated_email_body_value'] = ""
    st.session_state['recipient_email_input_value'] = ""
    st.session_state['email_cand_name_input_value'] = "[Candidate Name]"
    st.session_state['email_job_title_input_value'] = "[Job Title]"
    st.session_state['email_company_name_input_value'] = st.session_state.get('user_company', '[Your Company]')
    if 'email_interview_details_input_value' in st.session_state: # Defensive check
        st.session_state['email_interview_details_input_value'] = "[Date, Time, Link]"
    if 'email_custom_notes_input_value' in st.session_state: # Defensive check
        st.session_state['email_custom_notes_input_value'] = ""
    # Removed st.rerun() from here as it's a no-op in a callback

def extract_job_details_with_gemini(text):
    """
    Extracts structured job details from raw text using Gemini.
    """
    try:
        model = genai.GenerativeModel("models/gemini-2.0-flash-exp")
        prompt = f"""
        Extract job details from the following text into JSON format.
        
        Text:
        {text[:4000]}

        STRICT JSON OUTPUT ONLY:
        {{
            "job_title": "String",
            "company_name": "String",
            "job_description": "String (cleaned full text)",
            "required_skills": ["List", "of", "Strings"],
            "experience_level": "Entry-level" | "Mid-level" | "Senior-level" | "Lead" | "Manager",
            "job_type": "Full-time" | "Part-time" | "Contract" | "Internship",
            "location": "String",
            "min_experience": Integer,
            "max_experience": Integer,
            "min_cgpa": Float (default 0.0)
        }}
        """
        response = model.generate_content(prompt)
        # simplistic cleanup
        cleaned = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)
        return data
    except Exception as e:
        print(f"Extraction error: {e}")
        return {}

def hr_campaign_creator_page():
    st.markdown('<div class="dashboard-header">✨ HR Campaign Creator</div>', unsafe_allow_html=True)

    user_uid = st.session_state.get('user_uid', 'anonymous')
    username = st.session_state.get('username', 'anonymous@example.com')

    if user_uid == 'anonymous':
        st.warning("Please log in to create campaigns.")
        return

    # Load skill library (needed for screening logic in bulk upload)
    raw_skill_library = load_skill_library()
    skill_library = {} # Initialize to empty dict as a safe default

    

    if isinstance(raw_skill_library, dict):
        skill_library = raw_skill_library
       
    elif isinstance(raw_skill_library, (list, tuple, set)):
        # If it's a list, we can still use it for keyword extraction, but warn that dict was expected.
        skill_library = raw_skill_library
       
        
    else:
        st.error(f"CRITICAL ERROR: load_skill_library() returned an unhandled type: {type(raw_skill_library)}. Expected a dictionary or a list. AI screening will be limited.")
        
        skill_library = {} # Ensure it's an empty dict if unusable

    if not skill_library: # This check now only triggers if skill_library is truly empty (e.g., empty dict or empty list)
        st.error("Skill library is empty or could not be loaded effectively. AI screening for bulk upload and skill extraction will be limited.")
        # Do not return here, allow the rest of the page to load, but prevent skill extraction/bulk upload
        # if skill_library is None.
        pass

    # Custom CSS for better UI (Royal Blue Theme)
    st.markdown("""
    <style>
    .campaign-card {
        background-color: #ffffff;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        padding: 24px;
        margin-bottom: 24px;
        transition: all 0.2s ease-in-out;
        border: 1px solid #e2e8f0; /* Slate-200 */
    }
    .campaign-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        border-color: #3b82f6; /* Blue-500 */
    }
    .campaign-card h4 {
        color: #1e293b; /* Slate-800 */
        margin-top: 0;
        margin-bottom: 12px;
        font-size: 1.25rem;
        font-weight: 700;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .campaign-card p {
        margin-bottom: 8px;
        font-size: 0.95rem;
        color: #64748b; /* Slate-500 */
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Action Buttons in Card */
    .campaign-card .stButton button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
        padding: 10px 16px;
        border: 1px solid #e2e8f0;
        cursor: pointer;
        transition: all 0.2s;
        margin-top: 12px;
        background-color: #f8fafc; /* Slate-50 */
        color: #0f172a; /* Slate-900 */
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    .campaign-card .stButton button:hover {
        background-color: #2563eb; /* Blue-600 */
        color: white;
        border-color: #2563eb;
    }
    
    /* Status Badge styling */
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        background-color: #dbeafe; /* Blue-100 */
        color: #1e40af; /* Blue-800 */
    }
    
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state for screening criteria outside of campaign_form_defaults
    if 'current_min_score' not in st.session_state:
        st.session_state.current_min_score = 70
    if 'current_min_experience' not in st.session_state:
        st.session_state.current_min_experience = 0
    if 'current_max_experience' not in st.session_state:
        st.session_state.current_max_experience = 20
    if 'current_min_cgpa' not in st.session_state:
        st.session_state.current_min_cgpa = 0.0

    default_campaign_form_values = {
        "job_title": "",
        "company_name": st.session_state.get('user_company', ''),
        "job_description": "",
        "required_skills": "",
        "experience_level": "Entry-level",
        "job_type": "Full-time",
        "location": "",
        "posted_date": date.today(),
        "deadline": date.today(),
        "campaign_type": "Public",
    }

    # ------------------------------------------------------------
    # 1. Initialize campaign_form_defaults safely
    # ------------------------------------------------------------
    if 'campaign_form_defaults' not in st.session_state:
        st.session_state.campaign_form_defaults = default_campaign_form_values
    else:
        for key, default_value in default_campaign_form_values.items():
            if key not in st.session_state.campaign_form_defaults:
                st.session_state.campaign_form_defaults[key] = default_value

        st.session_state.campaign_form_defaults["posted_date"] = _safe_date(
            st.session_state.campaign_form_defaults.get("posted_date", date.today())
        )
        st.session_state.campaign_form_defaults["deadline"] = _safe_date(
            st.session_state.campaign_form_defaults.get("deadline", date.today())
        )

    st.write("### ➕ Create a New Job Campaign")

    # ------------------------------------------------------------
    # 2. Load existing campaigns (for cloning)
    # ------------------------------------------------------------
    campaigns_data = get_docs_from_firestore_rest(
        f"artifacts/{FIREBASE_PROJECT_ID}/users/{user_uid}/my_campaigns"
    )
    campaign_titles = [c.get('job_title', 'Untitled Campaign') for c in campaigns_data] if campaigns_data else []

    if st.session_state.get("reset_clone_campaign_flag"):
        st.session_state["clone_campaign_select"] = ""
        del st.session_state["reset_clone_campaign_flag"]

    clone_option = st.selectbox(
        "Or, clone an existing campaign to pre-fill the form:",
        options=[""] + campaign_titles,
        index=0,
        key="clone_campaign_select"
    )

    # ------------------------------------------------------------
    # 3. Apply cloning if user selects a campaign
    # ------------------------------------------------------------
    # ------------------------------------------------------------
    # 3. Apply cloning if user selects a campaign
    # ------------------------------------------------------------
    if clone_option and clone_option != st.session_state.campaign_form_defaults.get("cloned_from_title", ""):
        selected_campaign = next((c for c in campaigns_data if c.get('job_title') == clone_option), None)
        if selected_campaign:
            st.session_state.campaign_form_defaults.update({
                "job_title": f"Clone of {selected_campaign.get('job_title', 'Untitled Campaign')}",
                "company_name": selected_campaign.get('company_name', st.session_state.get('user_company', '')),
                "job_description": selected_campaign.get('job_description', ''),
                "required_skills": ", ".join(selected_campaign.get('required_skills', [])),
                "experience_level": selected_campaign.get('experience_level', 'Entry-level'),
                "job_type": selected_campaign.get('job_type', 'Full-time'),
                "location": selected_campaign.get('job_location', ''),
                "source_type": "internal", # Reset source for clones
                "cloned_from_title": clone_option # Track what we cloned to prevent infinite loop
            })
            
            # Update screening defaults
            st.session_state.current_min_score = selected_campaign.get('min_score', 70)
            st.session_state.current_min_experience = selected_campaign.get('min_experience', 0)
            st.session_state.current_max_experience = selected_campaign.get('max_experience', 20)
            st.session_state.current_min_cgpa = selected_campaign.get('min_cgpa', 0.0)

            st.session_state["reset_clone_campaign_flag"] = True
            st.rerun()

    # ------------------------------------------------------------
    # 3b. Feature C: Import from Text UI (New)
    # ------------------------------------------------------------
    with st.expander("📥 Import Job from Text", expanded=False):
        st.info("Paste a raw job description below. AI will extract details and fill the form for you.")
        import_text = st.text_area("Paste Job Text / URL Content", height=150, key="import_jd_text")
        
        if st.button("✨ Analyze & Import Details"):
            if import_text and len(import_text) > 20: # Basic validation
                with st.spinner("Analyzing text with AI..."):
                    extracted = extract_job_details_with_gemini(import_text)
                    if extracted:
                        st.session_state.campaign_form_defaults.update({
                            "job_title": extracted.get("job_title", ""),
                            "company_name": extracted.get("company_name", st.session_state.get('user_company', '')),
                            "job_description": extracted.get("job_description", import_text),
                            "required_skills": ", ".join(extracted.get("required_skills", [])),
                            "experience_level": extracted.get("experience_level", "Entry-level"),
                            "job_type": extracted.get("job_type", "Full-time"),
                            "location": extracted.get("location", ""),
                            "source_type": "imported_text", # Feature D: Source Tracking
                            "source_content": import_text[:500] # Store snippet
                        })
                        
                        # Update criteria
                        st.session_state.current_min_experience = extracted.get("min_experience", 0)
                        st.session_state.current_max_experience = extracted.get("max_experience", 20)
                        st.session_state.current_min_cgpa = extracted.get("min_cgpa", 0.0)
                        
                        st.success("Analysis complete! Form pre-filled below. Review and Save.")
                        st.rerun()
                    else:
                        st.error("Could not extract details. Please try manually.")
            else:
                 st.warning("Please paste some text to analyze.")


    # ------------------------------------------------------------
    # 4. FORM STARTS HERE
    # ------------------------------------------------------------
    with st.form("new_job_campaign_form", clear_on_submit=True):

        # ------------------ TITLE + COMPANY ------------------
        col_title_company = st.columns(2)
        with col_title_company[0]:
            job_title = st.text_input(
                "Job Title",
                value=st.session_state.campaign_form_defaults["job_title"],
                key="form_job_title"
            )
        with col_title_company[1]:
            company_name = st.text_input(
                "Company Name",
                value=st.session_state.campaign_form_defaults["company_name"],
                key="form_company_name"
            )

        # ------------------ JD + BUTTONS ------------------
        col_jd_gen, col_skills_extract = st.columns([3, 1])

        with col_jd_gen:
            job_description = st.text_area(
                "Job Description",
                height=200,
                value=st.session_state.campaign_form_defaults["job_description"],
                key="form_job_description"
            )

        with col_skills_extract:
            st.markdown("<br>", unsafe_allow_html=True)

            # ------------------ GEMINI AI JD GENERATOR ------------------
            if st.form_submit_button("Generate JD "):

                if job_title:
                    # USE ONLY SAFE DEFAULTS (NOT form_* KEYS)
                    current_skills = [
                        s.strip()
                        for s in st.session_state.campaign_form_defaults["required_skills"].split(",")
                        if s.strip()
                    ]

                    # ✅ FIX HERE
                    current_exp_level = st.session_state.campaign_form_defaults.get(
                        "experience_level", "Entry-level"
                    )
                    current_loc = st.session_state.campaign_form_defaults.get(
                        "location", ""
                    )

                    current_min_exp = st.session_state.current_min_experience
                    current_max_exp = st.session_state.current_max_experience
                    current_min_cgpa = st.session_state.current_min_cgpa

                    # ---------- SAFE FALLBACK (NEVER FAILS) ----------
                    fallback_data = {
                        "jd": f"""
Job Title: {job_title}
Location: {current_loc}
Experience Level: {current_exp_level}

We are looking for a {job_title} to join our team.

Key Responsibilities:
- Work on core responsibilities related to the role
- Collaborate with cross-functional teams
- Follow best practices and company standards

Requirements:
- Experience between {current_min_exp} and {current_max_exp} years
- Strong foundational skills
- Minimum CGPA: {current_min_cgpa}

This role is ideal for candidates willing to learn, grow, and contribute effectively.
""",
                        "skills": current_skills[:8] if current_skills else []
                    }

                    with st.spinner("🤖 Generating Job Description using AI..."):
                        try:
                            model = genai.GenerativeModel("models/gemini-2.5-flash")

                            prompt = f"""
You are an expert HR specialist and JD writer.

STRICT JSON ONLY:
{{
  "jd": "",
  "skills": []
}}

INPUT:
Title: {job_title}
Experience Level: {current_exp_level}
Location: {current_loc}
Skills Provided: {", ".join(current_skills)}
Experience Range: {current_min_exp}–{current_max_exp}
Min CGPA: {current_min_cgpa}
"""

                            response = model.generate_content(prompt)

                            raw_output = (
                                response.text if response and response.text else ""
                            ).replace("```json", "").replace("```", "").strip()

                            data = json.loads(raw_output)

                            st.session_state.campaign_form_defaults["job_description"] = data.get(
                                "jd", fallback_data["jd"]
                            )
                            st.session_state.campaign_form_defaults["required_skills"] = ", ".join(
                                data.get("skills", fallback_data["skills"])
                            )

                        except Exception:
                            # ✅ SILENT FALLBACK
                            st.session_state.campaign_form_defaults["job_description"] = fallback_data["jd"]
                            st.session_state.campaign_form_defaults["required_skills"] = ", ".join(
                                fallback_data["skills"]
                            )

                st.rerun()

            # ------------------ SKILL EXTRACTION ------------------
            if st.form_submit_button("Extract Skills from JD"):
                if job_description:
                    with st.spinner("Extracting skills..."):
                        extracted = extract_skills_from_text(job_description, skill_library)
                        st.session_state.campaign_form_defaults["required_skills"] = ", ".join(extracted)

                    st.success(f"Extracted {len(extracted)} skills.")
                    st.rerun()
                else:
                    st.warning("Please enter a Job Description to extract skills.")

        # ------------------ REQUIRED SKILLS INPUT ------------------
        required_skills_input = st.text_input(
            "Required Skills (Comma-separated)",
            value=st.session_state.campaign_form_defaults["required_skills"],
            key="form_required_skills"
        )

        # ------------------ DETAILS & REQUIREMENTS ------------------
        st.subheader("Details & Requirements")
        col_details = st.columns(4)

        with col_details[0]:
            experience_level = st.selectbox(
                "Experience Level",
                ["Entry-level", "Mid-level", "Senior-level", "Lead", "Manager"],
                index=["Entry-level", "Mid-level", "Senior-level", "Lead", "Manager"].index(
                    st.session_state.campaign_form_defaults["experience_level"]
                ),
                key="form_experience_level"
            )

        with col_details[1]:
            job_type = st.selectbox(
                "Job Type",
                ["Full-time", "Part-time", "Contract", "Internship"],
                index=["Full-time", "Part-time", "Contract", "Internship"].index(
                    st.session_state.campaign_form_defaults["job_type"]
                ),
                key="form_job_type"
            )

        with col_details[2]:
            location = st.text_input(
                "Location (e.g., Remote, NYC, London)",
                value=st.session_state.campaign_form_defaults["location"],
                key="form_location"
            )

        with col_details[3]:
            campaign_type = st.selectbox(
                "Visibility",
                ["Public", "Private"],
                index=["Public", "Private"].index(
                    st.session_state.campaign_form_defaults["campaign_type"].capitalize()
                ),
                key="form_campaign_type"
            )

        # ------------------ DATES ------------------
        col_dates = st.columns(2)
        with col_dates[0]:
            posted_date = st.date_input(
                "Posted Date",
                value=_safe_date(st.session_state.campaign_form_defaults["posted_date"])
            )
        with col_dates[1]:
            deadline = st.date_input(
                "Application Deadline",
                value=_safe_date(st.session_state.campaign_form_defaults["deadline"])
            )

        # ------------------ SCREENING CRITERIA ------------------
        st.subheader("AI Screening Criteria")
        col_screen_1, col_screen_2, col_screen_3, col_screen_4 = st.columns(4)

        with col_screen_1:
            st.session_state.current_min_score = st.slider(
                "Min AI Match Score (%)",
                0, 100,
                st.session_state.current_min_score,
                key="form_min_score"
            )

        with col_screen_2:
            st.session_state.current_min_experience = st.number_input(
                "Min Years Experience",
                0, 50,
                st.session_state.current_min_experience,
                key="form_min_experience"
            )

        with col_screen_3:
            st.session_state.current_max_experience = st.number_input(
                "Max Years Experience",
                st.session_state.current_min_experience,
                50,
                st.session_state.current_max_experience,
                key="form_max_experience"
            )

        with col_screen_4:
            st.session_state.current_min_cgpa = st.number_input(
                "Min CGPA (4.0 Scale)",
                0.0, 4.0,
                st.session_state.current_min_cgpa,
                step=0.01,
                key="form_min_cgpa"
            )

        # ------------------------------------------------------------
        # SAVE CAMPAIGN
        # ------------------------------------------------------------
        if st.form_submit_button("💾 Save Campaign"):

            if not all([job_title, company_name, job_description, required_skills_input, location, posted_date, deadline]):
                st.error("Please fill in all required fields.")
            elif deadline < posted_date:
                st.error("Deadline cannot be before posted date.")
            elif st.session_state.current_min_experience > st.session_state.current_max_experience:
                st.error("Min experience cannot exceed max experience.")
            else:

                campaign_id = str(uuid.uuid4())
                required_skills_list = [s.strip() for s in required_skills_input.split(",") if s.strip()]

                new_campaign = {
                    "campaign_id": campaign_id,
                    "job_title": job_title,
                    "company_name": company_name,
                    "job_description": job_description,
                    "required_skills": required_skills_list,
                    "experience_level": experience_level,
                    "job_type": job_type,
                    "job_location": location,
                    "posted_date": posted_date.isoformat(),
                    "application_deadline": deadline.isoformat(),
                    "campaign_type": campaign_type.lower(),
                    "created_by_uid": user_uid,
                    "created_by_username": st.session_state.get('username', 'anonymous'),
                    "created_at": datetime.now().isoformat(),
                    "status": "active",
                    "application_count": 0,
                    "avg_match_score": 0.0,
                    "views_count": 0,
                    "min_score": st.session_state.current_min_score,
                    "min_experience": st.session_state.current_min_experience,
                    "max_experience": st.session_state.current_max_experience,
                    "min_cgpa": st.session_state.current_min_cgpa,
                    "last_updated": datetime.now().isoformat(),
                    # Feature D: Source Tracking (Default to internal if not set by import)
                    "source_type": st.session_state.campaign_form_defaults.get("source_type", "internal"),
                    "source_content": st.session_state.campaign_form_defaults.get("source_content", None)
                }

                path1 = f"artifacts/{FIREBASE_PROJECT_ID}/users/{user_uid}/my_campaigns"
                add_doc_to_firestore_rest(path1, new_campaign, doc_id=campaign_id)

                if campaign_type.lower() == "public":
                    path2 = f"artifacts/{FIREBASE_PROJECT_ID}/public_campaigns"
                    add_doc_to_firestore_rest(path2, new_campaign, doc_id=campaign_id)

                st.success(f"Campaign '{job_title}' created successfully!")
                st.markdown(f"**Campaign ID:** `{campaign_id}`")
                
                # --- TRIGGER INSTANT NOTIFICATIONS ---
                with st.spinner("Finding and notifying matching candidates..."):
                    sent_count = run_campaign_matchmaking(
                        campaign_id, job_title, company_name, location, 
                        required_skills_list, st.session_state.current_min_experience
                    )
                    if sent_count > 0:
                        st.success(f"📧 Notification sent to {sent_count} matching candidates!")
                # -------------------------------------

                # Reset only the form defaults
                st.session_state.campaign_form_defaults = default_campaign_form_values.copy()
                st.cache_data.clear()
                st.rerun()

    st.markdown("---")


    st.markdown("---")
    st.write("### 🗂️ My Campaigns")
    
    if not campaigns_data:
        st.info("You have no active job campaigns. Use the form above to create one!")
        return

    df_campaigns = pd.DataFrame(campaigns_data)

    # Clean and standardize column names and data
    # Ensure 'required_skills' column is present before trying to convert it
    if 'required_skills' not in df_campaigns.columns or not isinstance(df_campaigns['required_skills'].iloc[0], list) if not df_campaigns.empty and 'required_skills' in df_campaigns.columns else False:
        # Create a placeholder if missing or not a list to prevent crash
        col = 'required_skills'
        if col not in df_campaigns.columns:
            df_campaigns[col] = [[] for _ in range(len(df_campaigns))]
        elif not df_campaigns[col].apply(lambda x: isinstance(x, list)).any():
            # If the column exists but no element is a list (e.g., all are strings/None)
            df_campaigns[col] = [[] for _ in range(len(df_campaigns))]
    
    string_cols_to_fill = [
        'job_title', 'company_name', 'status', 'campaign_type', 
        'job_location', 'experience_level', 'job_type', 'job_description'
    ]
    for col in string_cols_to_fill:
        if col in df_campaigns.columns:
            df_campaigns[col] = df_campaigns[col].fillna('')

    if 'required_skills' in df_campaigns.columns:
        df_campaigns['required_skills'] = df_campaigns['required_skills'].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else ''
        )

    if 'location' in df_campaigns.columns and 'job_location' not in df_campaigns.columns:
        df_campaigns['job_location'] = df_campaigns['location']
    df_campaigns = df_campaigns.drop(columns=['location'], errors='ignore')

    # FIX: Rely on _safe_date in from_firestore_format (timestampValue) for conversion
    df_campaigns['created_at'] = pd.to_datetime(df_campaigns['created_at'], errors='coerce')
    # Use .dt.date on the timezone-naive part for compatibility with st.date_input
    df_campaigns['application_deadline'] = df_campaigns['application_deadline'].apply(_safe_date)
    df_campaigns['posted_date'] = df_campaigns['posted_date'].apply(_safe_date)
    df_campaigns['last_updated'] = pd.to_datetime(df_campaigns['last_updated'], errors='coerce')

    df_campaigns = df_campaigns.sort_values(by='created_at', ascending=False)

    # --- Share Link Configuration ---
    with st.expander("⚙️ Share Link Settings"):
        st.caption("Customize the base URL used for sharing jobs (useful for localhost or custom domains).")
        base_url_input = st.text_input("App Base URL", value=st.session_state.get('APP_BASE_URL', 'https://screenerpro.streamlit.app'))
        if base_url_input:
            st.session_state['APP_BASE_URL'] = base_url_input.rstrip('/')
    
    st.subheader("🔎 Search & Filter Campaigns")
    col_filter1, col_filter2, col_filter3, col_filter4 = st.columns(4)
    with col_filter1:
        search_query = st.text_input("Search (Title/Description):", "")
    with col_filter2:
        filter_status = st.selectbox("Status:", ["All", "active", "closed"], index=0)
    with col_filter3:
        filter_exp_level = st.selectbox("Experience Level:", ["All"] + ["Entry-level", "Mid-level", "Senior-level", "Lead", "Manager"], index=0)
    with col_filter4:
        filter_location = st.text_input("Location:", "")

    filtered_df = df_campaigns.copy()

    if search_query:
        filtered_df = filtered_df[
            filtered_df['job_title'].str.contains(search_query, case=False, na=False) |
            filtered_df['job_description'].str.contains(search_query, case=False, na=False)
        ]

    if filter_status != "All":
        filtered_df = filtered_df[filtered_df['status'] == filter_status]

    if filter_exp_level != "All":
        filtered_df = filtered_df[filtered_df['experience_level'] == filter_exp_level]
    
    if filter_location:
        filtered_df = filtered_df[filtered_df['job_location'].str.contains(filter_location, case=False, na=False)]


    st.markdown(f"#### Showing {len(filtered_df)} of {len(df_campaigns)} campaigns")

    for _, campaign in filtered_df.iterrows():
        with st.container(border=True):
            st.markdown(f"#### 💼 {campaign['job_title']} at {campaign['company_name']}")
            
            col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
            with col1:
                st.metric("Applications", campaign.get('application_count', 0))
            with col2:
                # Ensure avg_match_score is float for formatting
                st.metric("Avg Score", f"{float(campaign.get('avg_match_score', 0.0)):.1f}%")
            with col3:
                status_color = 'green' if campaign['status'] == 'active' else 'red'
                st.markdown(f"**Status:** <span style='color:{status_color}'>{campaign['status'].capitalize()}</span>", unsafe_allow_html=True)
            with col4:
                st.markdown(f"**ID:** `{campaign['id']}`")

            with st.expander("Details & Sharing"):
                # --- Metrics ---
                public_count = campaign.get('public_link_applications', 0)
                if public_count > 0:
                    st.info(f"🚀 **{public_count}** applications received via Public Job Board Link.")

                # --- Share Section ---
                import urllib.parse
                current_base_url = st.session_state.get('APP_BASE_URL', 'https://screenerpro.streamlit.app')
                share_link = f"{current_base_url.rstrip('/')}/Public_Job_Board?job_id={campaign['id']}"
                share_link_enc = urllib.parse.quote(share_link)
                share_title_enc = urllib.parse.quote(f"Hiring: {campaign['job_title']} at {campaign['company_name']}")
                
                st.markdown(f"**📢 Share Link:** [`{share_link}`]({share_link})")
                st.markdown(
                    f"""
                    <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                        <a href="https://www.linkedin.com/sharing/share-offsite/?url={share_link_enc}" target="_blank">
                            <button style="background:#0077b5; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">LinkedIn</button>
                        </a>
                        <a href="https://twitter.com/intent/tweet?text={share_title_enc}&url={share_link_enc}" target="_blank">
                            <button style="background:#1da1f2; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">Twitter</button>
                        </a>
                        <a href="https://api.whatsapp.com/send?text={share_title_enc}%20{share_link_enc}" target="_blank">
                            <button style="background:#25D366; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">WhatsApp</button>
                        </a>
                    </div>
                    """, unsafe_allow_html=True
                )
                st.markdown("---")
                st.markdown(f"**Location:** {campaign.get('job_location', 'N/A')} | **Type:** {campaign.get('job_type', 'N/A')} | **Level:** {campaign.get('experience_level', 'N/A')}")
                st.markdown(f"**Posted:** {campaign.get('posted_date', 'N/A')} | **Deadline:** {campaign.get('application_deadline', 'N/A')}")
                st.markdown(f"**Skills:** {campaign.get('required_skills', 'N/A')}")
                st.markdown(f"**Description:** {campaign.get('job_description', 'N/A')}")
                
                st.markdown("---")
                st.markdown("##### AI Screening Criteria")
                col_c1, col_c2, col_c3, col_c4 = st.columns(4)
                col_c1.metric("Min Score", f"{campaign.get('min_score', 0)}%")
                col_c2.metric("Min Exp", f"{campaign.get('min_experience', 0)} years")
                col_c3.metric("Max Exp", f"{campaign.get('max_experience', 50)} years")
                col_c4.metric("Min CGPA", f"{campaign.get('min_cgpa', 0.0)}")

            col_actions1, col_actions2, col_actions3 = st.columns(3)
            with col_actions1:
                if campaign['status'] == 'active':
                    if st.button("Close Campaign", key=f"close_camp_{campaign['id']}", help="Make this campaign inactive"):
                        update_doc_in_firestore_rest(f"artifacts/{FIREBASE_PROJECT_ID}/users/{user_uid}/my_campaigns", campaign['id'], {"status": "closed", "last_updated": datetime.now().isoformat()})
                        update_doc_in_firestore_rest(f"artifacts/{FIREBASE_PROJECT_ID}/public_campaigns", campaign['id'], {"status": "closed", "last_updated": datetime.now().isoformat()})
                        st.success(f"Campaign '{campaign['job_title']}' closed.")
                        st.cache_data.clear()
                        st.rerun()
                else:
                    if st.button("Reopen Campaign", key=f"reopen_camp_{campaign['id']}", help="Make this campaign active again"):
                        update_doc_in_firestore_rest(f"artifacts/{FIREBASE_PROJECT_ID}/users/{user_uid}/my_campaigns", campaign['id'], {"status": "active", "last_updated": datetime.now().isoformat()})
                        update_doc_in_firestore_rest(f"artifacts/{FIREBASE_PROJECT_ID}/public_campaigns", campaign['id'], {"status": "active", "last_updated": datetime.now().isoformat()})
                        st.success(f"Campaign '{campaign['job_title']}' reopened.")
                        st.cache_data.clear()
                        st.rerun()

            with col_actions2:
                if st.button("Clone Campaign", key=f"clone_camp_{campaign['id']}", help="Create a new campaign with these details"):
                    st.session_state.campaign_form_defaults = {
                        "job_title": f"Clone of {campaign.get('job_title', 'Untitled Campaign')}",
                        "company_name": campaign.get('company_name', st.session_state.get('user_company', '')),
                        "job_description": campaign.get('job_description', ''),
                        "required_skills": campaign.get('required_skills', ''), # This will be a comma-separated string from the DataFrame
                        "experience_level": campaign.get('experience_level', 'Entry-level'),
                        "job_type": campaign.get('job_type', 'Full-time'),
                        "location": campaign.get('job_location', ''),
                        # PATCH: Use _safe_date for cloning
                        "posted_date": _safe_date(campaign.get('posted_date')),
                        "deadline": _safe_date(campaign.get('application_deadline')),
                        "campaign_type": campaign.get('campaign_type', 'public').capitalize(),
                    }
                    # When cloning, also update the persistent screening criteria
                    st.session_state.current_min_score = campaign.get('min_score', 70)
                    st.session_state.current_min_experience = campaign.get('min_experience', 0)
                    st.session_state.current_max_experience = campaign.get('max_experience', 20)
                    st.session_state.current_min_cgpa = campaign.get('min_cgpa', 0.0)
                    st.session_state["reset_clone_campaign_flag"] = True # Set flag to reset the selectbox
                    st.rerun()

            with col_actions3:
                if st.button("Delete Campaign", key=f"delete_camp_{campaign['id']}", help="Permanently delete this campaign"):
                    if delete_doc_from_firestore_rest(f"artifacts/{FIREBASE_PROJECT_ID}/users/{user_uid}/my_campaigns", campaign['id']):
                        delete_doc_from_firestore_rest(f"artifacts/{FIREBASE_PROJECT_ID}/public_campaigns", campaign['id']) # Also delete from public
                        st.success(f"Campaign '{campaign['job_title']}' and all its data deleted.")
                        st.cache_data.clear()
                        st.rerun()

            # --- Backfill / Manual Trigger Button ---
            st.markdown("---")
            if st.button("📢 Send Match Emails to Candidates", key=f"blast_{campaign['id']}", help="Manually trigger email notifications to matching candidates for this job."):
                with st.spinner("Finding and notifying matching candidates..."):
                    # Parse skills from string if needed
                    skills_val = campaign.get('required_skills', '')
                    skills_list_bf = [s.strip() for s in skills_val.split(',')] if isinstance(skills_val, str) else skills_val
                    
                    sent_count = run_campaign_matchmaking(
                        campaign['id'], 
                        campaign.get('job_title', 'Job'), 
                        campaign.get('company_name', 'Company'), 
                        campaign.get('job_location', ''), 
                        skills_list_bf, 
                        campaign.get('min_experience', 0)
                    )
                    if sent_count > 0:
                        st.success(f"📧 Sent {sent_count} emails successfully!")
                    else:
                        st.info("No matching candidates found (or emails already sent).")

    # --- Campaign Applicant View ---
    st.markdown("---")
    st.write("### 👥 View Applicants")

    campaign_options_map = {c.get('job_title', f"Untitled Campaign ({c.get('id', 'N/A')})"): c.get('id') for c in campaigns_data}
    campaign_display_names = ["-- Select a Campaign --"] + list(campaign_options_map.keys())

    # Get the last selected campaign title or default to the first entry
    initial_select_index = 0
    if 'selected_campaign_for_applicants_id' in st.session_state:
        # Find the title corresponding to the stored ID
        for display_name, camp_id in campaign_options_map.items():
            try:
                if camp_id == st.session_state.selected_campaign_for_applicants_id:
                    initial_select_index = campaign_display_names.index(display_name)
                    break
            except ValueError:
                initial_select_index = 0

    # ================================
    # ⭐ Modern Select Dropdown
    # ================================
    st.markdown("#### 🎯 Select a Campaign")
    selected_campaign_for_applicants_title = st.selectbox(
        "",
        options=campaign_display_names,
        index=initial_select_index,
        key="view_applicants_campaign_select"
    )

    if selected_campaign_for_applicants_title and selected_campaign_for_applicants_title != "-- Select a Campaign --":
        st.session_state.selected_campaign_for_applicants_id = campaign_options_map[selected_campaign_for_applicants_title]
    else:
        st.session_state.selected_campaign_for_applicants_id = None

    if st.session_state.selected_campaign_for_applicants_id:
        selected_campaign_id_for_applicants = st.session_state.selected_campaign_for_applicants_id
        
        # Modern Title Block
        st.markdown(
            f"""
            <div style="
                margin-top: 15px; 
                margin-bottom: 10px; 
                padding: 12px; 
                background:#f8fafc; 
                border-radius: 10px; 
                border:1px solid #e2e8f0;">
                <h3 style="margin:0; font-size:20px; color:#1e293b;"> 
                    📄 Applicants for: <b>{selected_campaign_for_applicants_title}</b> 
                </h3>
            </div>
            """, unsafe_allow_html=True
        )

        applicants_for_selected_campaign = get_applications_for_campaign(
            selected_campaign_id_for_applicants,
            user_uid,
            FIREBASE_PROJECT_ID,
            FIRESTORE_DATABASE_ROOT_URL,
            FIREBASE_WEB_API_KEY
        )

        if applicants_for_selected_campaign:
            df_applicants = pd.DataFrame(applicants_for_selected_campaign)

            applicant_display_cols = [
                "applicant_name", "applicant_email", "applied_at", "status", "ai_score", 
                "years_experience", "cgpa", "matched_skills", "missing_skills", 
                "ai_suggestion", "resume_filename", "AI_Decision"
            ]
            for col in applicant_display_cols:
                if col not in df_applicants.columns:
                    df_applicants[col] = None
            
            df_applicants['applied_at'] = pd.to_datetime(df_applicants['applied_at'], errors='coerce')
            df_applicants = df_applicants.sort_values(by='applied_at', ascending=False)
            
            # --- Filtering and Sorting Controls ---
            st.subheader("Filter and Sort Applicants")
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                filter_status_app = st.selectbox("Filter by Status", ["All", "shortlisted", "submitted", "rejected"], key="filter_status_app")
            with col_f2:
                sort_by = st.selectbox("Sort by", ["Applied Date (Newest)", "AI Score (High → Low)", "AI Score (Low → High)"], key="sort_by_app")
            with col_f3:
                # Get the selected campaign details to show screening criteria
                selected_campaign_details = next((c for c in campaigns_data if c.get('id') == selected_campaign_id_for_applicants), {})
                # FIX 1: Ensure min_score_req is an integer for safe comparison
                min_score_req = int(selected_campaign_details.get('min_score', 0))
                st.info(f"Min Score Required: {min_score_req}%")


            filtered_apps = applicants_for_selected_campaign # Start with the full list

            # Apply Status Filter
            if filter_status_app != "All":
                filtered_apps = [app for app in filtered_apps if app.get("status") == filter_status_app]

            # Apply Sorting
            if sort_by == "Applied Date (Newest)":
                # For safety, we'll sort based on the datetime object
                filtered_apps = sorted(filtered_apps, key=lambda x: pd.to_datetime(x.get("applied_at", date.min), errors='coerce'), reverse=True)
            elif sort_by == "AI Score (High → Low)":
                filtered_apps = sorted(filtered_apps, key=lambda x: x.get("ai_score", 0), reverse=True)
            elif sort_by == "AI Score (Low → High)":
                filtered_apps = sorted(filtered_apps, key=lambda x: x.get("ai_score", 0), reverse=False)

            # ================================
            # 📄 PAGINATION
            # ================================
            items_per_page = st.selectbox("Applicants per page", [5, 10, 20, 50], index=1)
            
            # --- FIX 2 & 3: Final Robust Validation Change ---
            def is_valid_application(app):
                """
                FIXED: The validation that caused candidates to disappear after scoring 0.0 or
                status change is now removed by returning True, ensuring all saved applications
                are displayed.
                """
                return True

            # Use the filtered list that has been sorted
            valid_filtered_apps = [app for app in filtered_apps if is_valid_application(app)]
            # --- END FIX 2 & 3 ---

            total_apps = len(valid_filtered_apps)
            total_pages = (total_apps - 1) // items_per_page + 1 if total_apps > 0 else 1

            if "resume_page" not in st.session_state:
                st.session_state.resume_page = 1
            
            # Ensure page state is valid after filtering/sorting
            if st.session_state.resume_page > total_pages and total_pages > 0:
                st.session_state.resume_page = total_pages
            elif total_pages == 0:
                st.session_state.resume_page = 1


            col_p1, col_p2, col_p3 = st.columns([1,2,1])
            with col_p1:
                if st.button("⬅ Previous", disabled=st.session_state.resume_page == 1):
                    st.session_state.resume_page -= 1
            with col_p3:
                if st.button("Next ➡", disabled=st.session_state.resume_page >= total_pages):
                    st.session_state.resume_page += 1
            with col_p2:
                st.markdown(
                    f"<div style='text-align:center; font-weight:600; color:#334155;'>Page {st.session_state.resume_page} of {total_pages}</div>",
                    unsafe_allow_html=True
                )
            
            start = (st.session_state.resume_page - 1) * items_per_page
            end = start + items_per_page
            apps_to_show = valid_filtered_apps[start:end]

            # ================================
            # 📄 LIST OF APPLICANTS (CARDS)
            # ================================
            st.write("### 📄 Applicant Resumes")
            
            if not apps_to_show and total_apps > 0:
                # This should only happen if the filtering removed applicants on the last page
                st.info("No more applicants on this page. Adjusting page...")
                st.session_state.resume_page = total_pages
                st.rerun()
            elif total_apps == 0:
                st.info("No valid applicants found for this campaign.")
                
            for app in apps_to_show:
                applicant_name = app.get("applicant_name", "Unknown Applicant")
                resume_filename = app.get("resume_filename", "resume.pdf")
                encoded_file = app.get("resume_file_base64")
                ext = app.get("resume_file_extension", "pdf")

                # ================================
                # 🌟 Applicant Card (Premium Design)
                # ================================
                with st.container(border=True):
                    
                    header_col1, header_col2, header_col3 = st.columns([2, 1, 1])
                    
                    with header_col1:
                        st.markdown(f"**{applicant_name}**")
                        st.markdown(f"*{app.get('applicant_email', 'N/A')}*")
                        # Format date display nicely
                        applied_date_obj = pd.to_datetime(app.get('applied_at', 'N/A'), errors='coerce')
                        applied_date_str = applied_date_obj.strftime("%b %d, %Y") if pd.notna(applied_date_obj) else 'N/A'
                        st.markdown(f"Applied: {applied_date_str}")
                    
                    with header_col2:
                        # FIX 1: Ensure 'score' is a float for safe comparison
                        score = float(app.get('ai_score', 0))
                        # The original traceback line is fixed here:
                        score_color = 'green' if score >= min_score_req else 'orange' if score >= min_score_req * 0.8 else 'red'
                        st.markdown(f"<span style='font-size: 1.5em; font-weight: bold; color: {score_color};'>{score:.1f}%</span> Match", unsafe_allow_html=True)
                        st.markdown(f"**AI Status:** {app.get('AI_Decision', 'N/A')}")
                    
                    with header_col3:
                        st.markdown(f"**Experience:** {app.get('years_experience', 'N/A')} yrs")
                        st.markdown(f"**CGPA:** {app.get('cgpa', 'N/A')}")
                        

                    # --- Expander for detailed AI feedback ---
                    with st.expander(f"AI Screening Report for {resume_filename}"):
                        st.markdown(f"**AI Suggestion:** {app.get('ai_suggestion', 'N/A')}")
                        st.markdown("---")
                        # Ensure matched/missing skills are joined strings, as they are lists in Firestore
                        matched_skills_str = ", ".join(app.get('matched_skills', [])) if isinstance(app.get('matched_skills'), list) else 'N/A'
                        missing_skills_str = ", ".join(app.get('missing_skills', [])) if isinstance(app.get('missing_skills'), list) else 'N/A'
                        
                        st.markdown(f"**Matched Skills:** {matched_skills_str}")
                        st.markdown(f"**Missing Skills:** {missing_skills_str}")
                        
                        # --- Download & Email Controls ---
                        st.markdown("---")
                        col_dl, col_email, col_status_update = st.columns(3)
                        
                        with col_dl:
                            if encoded_file:
                                try:
                                    pdf_bytes = base64.b64decode(encoded_file)
                                    st.download_button(
                                        label=f"⬇ Download Resume (.{ext})",
                                        data=pdf_bytes,
                                        file_name=resume_filename,
                                        mime=f"application/{ext}",
                                        key=f"dl_{app['id']}"
                                    )
                                except Exception as e:
                                    st.error(f"Error decoding file for download: {e}")
                        
                        with col_email:
                            if st.button("✉ Send Email", key=f"email_{app['id']}"):
                                # Pre-fill email session state
                                st.session_state['recipient_email_input_value'] = app.get('applicant_email', '')
                                st.session_state['email_cand_name_input_value'] = applicant_name
                                st.session_state['email_job_title_input_value'] = app.get('job_title', selected_campaign_for_applicants_title)
                                st.session_state['email_company_name_input_value'] = app.get('company_name', st.session_state.get('user_company', '[Your Company]'))
                                st.session_state['email_custom_notes_input_value'] = f"The AI Match Score for your resume was {score:.1f}% against the job requirements."
                                st.rerun() # Rerun to show the email panel updated

                        with col_status_update:
                            new_status = st.selectbox("Update Status", ["submitted", "shortlisted", "rejected"], index=["submitted", "shortlisted", "rejected"].index(app.get('status', 'submitted')), key=f"status_update_{app['id']}")
                            if new_status != app.get('status'):
                                if st.button(f"Save '{new_status}' Status", key=f"save_status_{app['id']}"):
                                    update_doc_in_firestore_rest(
                                        f"artifacts/{FIREBASE_PROJECT_ID}/users/{user_uid}/my_campaigns/{selected_campaign_id_for_applicants}/applications",
                                        app['id'],
                                        {"status": new_status},
                                        update_mask_fields=["status"]   # ⭐ FIX ADDED HERE
                                    )
                                    st.success(f"Status for {applicant_name} updated to '{new_status}'.")
                                    st.cache_data.clear()
                                    st.rerun()


            
            # --- Export & Trends ---
            st.markdown("---")
            st.write("### 📈 Campaign Insights")

            col_export, col_refresh = st.columns([1, 4])
            with col_export:
                csv = df_applicants.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Export to CSV",
                    data=csv,
                    file_name=f"{selected_campaign_for_applicants_title}_applicants.csv",
                    mime="text/csv",
                    key=f"export_applicants_for_selected_{selected_campaign_id_for_applicants}"
                )
            
            st.markdown("---")
            st.subheader("Applicant Trends Over Time")
            
            df_applicants['applied_date'] = df_applicants['applied_at'].dt.date
            daily_applicants = df_applicants.groupby('applied_date').size().reset_index(name='Applicants')
            daily_applicants.columns = ['Date', 'Applicants']

            if not daily_applicants.empty:
                min_date = daily_applicants['Date'].min()
                max_date = daily_applicants['Date'].max()
                all_dates = pd.date_range(start=min_date, end=max_date, freq='D').date
                full_date_range_df = pd.DataFrame({'Date': all_dates})
                daily_applicants = pd.merge(full_date_range_df, daily_applicants, on='Date', how='left').fillna(0)
                daily_applicants['Date'] = pd.to_datetime(daily_applicants['Date'])

                fig_trends = px.line(daily_applicants, x='Date', y='Applicants', title='Daily Applicant Submissions')
                st.plotly_chart(fig_trends, use_container_width=True)
            else:
                st.info("No application data available to display trends yet.")

        else:
            st.info(f"No applicants found for '{selected_campaign_for_applicants_title}' yet.")
    else:
        st.info("Select a campaign from the dropdown above to view its applicants.")

    st.markdown("---")
    st.write("### 🛠️ Advanced Tools & Integrations")

    st.subheader("📦 Bulk Resume Upload for Screening")
    st.info("Upload a ZIP file containing multiple resumes to screen them against a selected campaign. Each resume will be processed and saved as an application.")
    
    # Get list of campaigns for selection
    bulk_campaign_options_map = {c.get('job_title', f"Untitled Campaign ({c.get('id', 'N/A')})"): c.get('id') for c in campaigns_data}
    bulk_campaign_display_names = ["-- Select a Campaign for Bulk Upload --"] + list(bulk_campaign_options_map.keys())
    
    selected_bulk_campaign_title = st.selectbox(
        "Select a campaign to screen resumes against:",
        options=bulk_campaign_display_names,
        key="bulk_upload_campaign_select"
    )

    bulk_uploaded_file = st.file_uploader("Upload ZIP file of Resumes (.zip)", type=["zip"], key="bulk_resume_zip_uploader")

    if selected_bulk_campaign_title != "-- Select a Campaign for Bulk Upload --" and bulk_uploaded_file:
        selected_bulk_campaign_id = bulk_campaign_options_map[selected_bulk_campaign_title]
        campaign_details = next((c for c in campaigns_data if c.get('id') == selected_bulk_campaign_id), None)
        
        if campaign_details is None:
            st.error("Could not retrieve details for the selected campaign.")
        elif not skill_library:
            st.error("Cannot perform AI screening: Skill library could not be loaded.")
        else:
            
            if st.button(f"Start Bulk Screening against '{selected_bulk_campaign_title}'"):
                
                temp_dir = tempfile.mkdtemp()
                success_count = 0
                failed_count = 0
                
                try:
                    with zipfile.ZipFile(bulk_uploaded_file, 'r') as zip_ref:
                        # Only extract files (ignore directories)
                        files_to_extract = [f for f in zip_ref.namelist() if not f.endswith('/') and not f.startswith('__MACOSX')]
                        
                        if not files_to_extract:
                            st.error("The ZIP file contains no readable files.")
                        else:
                            st.info(f"Processing {len(files_to_extract)} resumes...")
                            progress_bar = st.progress(0)
                            
                            for i, file_name in enumerate(files_to_extract):
                                
                                try:
                                    zip_ref.extract(file_name, temp_dir)
                                    extracted_file_path = os.path.join(temp_dir, file_name)

                                    with open(extracted_file_path, 'rb') as f:
                                        resume_bytes_io = BytesIO(f.read())
                                        file_type = f"application/{file_name.split('.')[-1]}" if '.' in file_name else "application/octet-stream"
                                        
                                        # Create a dummy uploaded_file object for the base64 function
                                        class DummyUploadedFile:
                                            def __init__(self, content):
                                                self._content = content
                                            def getvalue(self):
                                                return self._content
                                        
                                        # Extract text
                                        resume_text = extract_text_from_file(resume_bytes_io, file_name, file_type)
                                        
                                        if resume_text.startswith("[ERROR]"):
                                            st.error(f"Error processing {file_name}: {resume_text.replace('[ERROR] ', '')}")
                                            failed_count += 1
                                            continue
                                        
                                        # Perform AI screening
                                        screening_results = process_single_resume_logic(
                                            file_name=file_name,
                                            text=resume_text,
                                            jd_text=campaign_details.get('job_description', ''),
                                            jd_name_for_results=campaign_details.get('job_title', 'Bulk Upload'),
                                            skill_library=skill_library,
                                            max_experience=campaign_details.get('max_experience', 20),
                                            summary_tone="Professional" # Default tone for bulk upload
                                        )

                                        final_score = screening_results.get('Score (%)', 0)
                                        meets_exp = (screening_results.get('Years Experience', 0) >= campaign_details.get('min_experience', 0) and screening_results.get('Years Experience', 0) <= campaign_details.get('max_experience', 20))
                                        meets_cgpa = (screening_results.get('CGPA (4.0 Scale)') is None or screening_results.get('CGPA (4.0 Scale)') >= campaign_details.get('min_cgpa', 0.0))

                                        if final_score >= campaign_details.get('min_score', 0) and meets_exp and meets_cgpa:
                                            application_status = "shortlisted"
                                            ai_decision = "Shortlisted by AI"
                                        else:
                                            application_status = "submitted"
                                            ai_decision = "Submitted"

                                        # --- NEW: Encode original resume file as Base64 (FREE STORAGE, exact file preserved) ---
                                        # Need to reset the file pointer of the bytes_io object before encoding its value
                                        resume_bytes_io.seek(0)
                                        encoded_resume = base64.b64encode(resume_bytes_io.getvalue()).decode("utf-8")
                                        resume_extension = file_name.split('.')[-1] if '.' in file_name else "pdf"

                                        application_data = {
                                            "application_id": str(uuid.uuid4()),
                                            "campaign_id": campaign_details.get('id', 'N/A'),
                                            "job_title": campaign_details.get('job_title', 'N/A'),
                                            "company_name": campaign_details.get('company_name', 'N/A'),
                                            "applicant_name": screening_results.get('Candidate Name', file_name.split('.')[0]), # Use file name if name not extracted
                                            "applicant_email": "bulk_upload_na@example.com", # Placeholder for bulk
                                            "applied_at": datetime.now().isoformat(),
                                            "status": application_status,
                                            "ai_score": final_score,
                                            "years_experience": screening_results.get('Years Experience', 0),
                                            "cgpa": screening_results.get('CGPA (4.0 Scale)'),
                                            "matched_skills": screening_results.get('Matched Skills', []),
                                            "missing_skills": screening_results.get('Missing Skills', []),
                                            "ai_suggestion": screening_results.get('Summary', ''),
                                            "resume_filename": file_name,
                                            "resume_file_base64": encoded_resume,
                                            "resume_file_extension": resume_extension,
                                            "AI_Decision": ai_decision,
                                        }

                                        app_collection_path = f"artifacts/{FIREBASE_PROJECT_ID}/users/{user_uid}/my_campaigns/{selected_bulk_campaign_id}/applications"
                                        doc_id_saved = add_doc_to_firestore_rest(app_collection_path, application_data)

                                        if doc_id_saved:
                                            success_count += 1
                                            # --- FIX 1: Update campaign metrics immediately after saving an application (User's request) ---
                                            update_campaign_metrics(selected_bulk_campaign_id, user_uid) 
                                            # --- END FIX 1 ---
                                        else:
                                            failed_count += 1

                                except Exception as e:
                                    st.error(f"Critical error during processing of {file_name}: {e}")
                                    failed_count += 1
                                
                                # Update progress bar
                                progress_bar.progress((i + 1) / len(files_to_extract))

                            progress_bar.empty()
                            st.success(f"Bulk Screening Complete! Successfully processed {success_count} resumes. {failed_count} failed.")
                            
                            # Update campaign metrics after bulk upload (Final check, safer for totals)
                            update_campaign_metrics(selected_bulk_campaign_id, user_uid)

                            st.cache_data.clear()
                            st.rerun()

                finally:
                    # Clean up the temporary directory
                    try:
                        os.rmdir(temp_dir)
                    except OSError as e:
                        # Sometimes rmdir fails if it's not truly empty (e.g., hidden files)
                        import shutil
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        

    # --- Email Generator Panel ---
    st.markdown("---")
    st.write("### 📧 Email Generator")

    # Initialize session state for the text input widgets
    if 'email_cand_name_input_value' not in st.session_state:
        st.session_state['email_cand_name_input_value'] = "[Candidate Name]"
    if 'email_job_title_input_value' not in st.session_state:
        st.session_state['email_job_title_input_value'] = "[Job Title]"
    if 'email_company_name_input_value' not in st.session_state:
        st.session_state['email_company_name_input_value'] = st.session_state.get('user_company', '[Your Company]')
    if 'email_interview_details_input_value' not in st.session_state:
        st.session_state['email_interview_details_input_value'] = "[Date, Time, Link]"
    if 'email_custom_notes_input_value' not in st.session_state:
        st.session_state['email_custom_notes_input_value'] = ""
    if 'recipient_email_input_value' not in st.session_state:
        st.session_state['recipient_email_input_value'] = ""
    if 'generated_email_subject_value' not in st.session_state:
        st.session_state['generated_email_subject_value'] = ""
    if 'generated_email_body_value' not in st.session_state:
        st.session_state['generated_email_body_value'] = ""


    email_template_type = st.selectbox(
        "Select Email Template",
        ["Shortlist", "Rejection", "Interview Invite"],
        key="email_template_type",
        help="Select a template to generate the standard email content."
    )

    col_email_details = st.columns(3)
    with col_email_details[0]:
        st.session_state['email_cand_name_input_value'] = st.text_input("Candidate Name", value=st.session_state['email_cand_name_input_value'], key="email_cand_name_input")
    with col_email_details[1]:
        st.session_state['email_job_title_input_value'] = st.text_input("Job Title", value=st.session_state['email_job_title_input_value'], key="email_job_title_input")
    with col_email_details[2]:
        st.session_state['email_company_name_input_value'] = st.text_input("Company Name", value=st.session_state['email_company_name_input_value'], key="email_company_name_input")

    if email_template_type == "Interview Invite":
        st.session_state['email_interview_details_input_value'] = st.text_input("Interview Details (Date, Time, Link)", value=st.session_state['email_interview_details_input_value'], key="email_interview_details_input")
    
    st.session_state['email_custom_notes_input_value'] = st.text_area("Custom Notes / Personalized Message", value=st.session_state['email_custom_notes_input_value'], key="email_custom_notes_input")

    if st.button("✨ Generate Email Content"):
        subject, body = generate_email_template_content(
            email_template_type,
            st.session_state['email_cand_name_input_value'],
            st.session_state['email_job_title_input_value'],
            st.session_state['email_company_name_input_value'],
            st.session_state.get('email_interview_details_input_value', ''),
            st.session_state['email_custom_notes_input_value']
        )
        st.session_state['generated_email_subject_value'] = subject
        st.session_state['generated_email_body_value'] = body
        st.success("Email content generated. Review and send below.")

    st.subheader("Final Email Review")
    st.session_state['recipient_email_input_value'] = st.text_input("Recipient Email Address (REQUIRED to send)", value=st.session_state['recipient_email_input_value'], key="recipient_email_input")
    
    st.session_state['generated_email_subject_value'] = st.text_input("Subject", value=st.session_state['generated_email_subject_value'], key="generated_email_subject")
    st.session_state['generated_email_body_value'] = st.text_area("Body", height=300, value=st.session_state['generated_email_body_value'], key="generated_email_body")
    
    # Send button using the helper function
    if st.button("🚀 Send Email", type="primary", use_container_width=True, on_click=_send_and_clear_email, args=(
        st.session_state['recipient_email_input_value'], 
        st.session_state['generated_email_subject_value'],
        st.session_state['generated_email_body_value']
    )):
        pass # The action is handled by the on_click callback

# Helper function for on_click to send email and then clear fields
def _send_and_clear_email(recipient_email, subject, body):
    if not recipient_email:
        st.error("Please enter a recipient email address.")
    else:
        with st.spinner("Sending email..."):
            if send_email(recipient_email, subject, body):
                st.success(f"Email sent successfully to {recipient_email}!")
                _clear_email_fields() # Call the clearing function
            else:
                st.error("Failed to send email. Check error messages above.")

    st.subheader("🔗 Integration with External Job Boards & ATS (Future Feature)")
    st.info("This feature aims to automate posting to popular job boards and synchronize applicant data with your existing Applicant Tracking System (ATS). It requires API integrations with various external platforms.")

    st.subheader("💰 Campaign Budget Tracking (Future Feature)")
    st.info("This feature will allow you to manage and track the recruitment budget allocated per campaign, including advertising costs and screening expenses. It would involve financial tracking and reporting functionalities.")

if __name__ == "__main__":
    st.set_page_config(page_title="ScreenerPro - HR Campaign Creator", layout="wide", page_icon="✨")
    hr_campaign_creator_page()
