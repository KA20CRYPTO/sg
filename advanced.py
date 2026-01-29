# ============================---
import streamlit as st

# --- Data Handling ---
import pandas as pd
import numpy as np
import json
import csv

# --- Date & Time ---
from datetime import datetime, timedelta, date

# --- Visualization ---
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

# --- Machine Learning ---
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- File Handling ---
from pathlib import Path
import io
import base64
from google import generativeai as genai
# --- PDF extraction ---
import fitz  # PyMuPDF

# --- Firebase / Networking ---
import requests

# --- Email (if needed) ---
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

# --- Hashing ---
import hashlib

# --- Other utilities ---
import math
import collections
import pickle
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from google import generativeai as genai


# ================= ADMIN EMAIL (ONLY ON FALLBACK) =================
def notify_admin_fallback(reason, context="Interview Template AI"):
    try:
        gmail = st.secrets.get("GMAIL_ADDRESS")
        app_password = st.secrets.get("GMAIL_APP_PASSWORD")
        admin_email = "manav.nagpal2005@gmail.com"

        if not gmail or not app_password:
            return

        msg = MIMEMultipart()
        msg["From"] = gmail
        msg["To"] = admin_email
        msg["Subject"] = "⚠️ ScreenerPro – Gemini Fallback Triggered"

        body = f"""
Gemini AI fallback was used.

Context:
{context}

Reason:
{reason}

Time:
{datetime.now().isoformat()}
"""
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail, app_password)
            server.send_message(msg)

    except Exception:
        pass  # NEVER break UI


def generate_interview_template_safe(template_name):
    """
    Generates interview template in STRICT save-compatible format:
    Section: Q1; Q2; Q3

    Falls back safely if Gemini fails and emails admin.
    """

    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    ADMIN_EMAIL = "manav.nagpal2005@gmail.com"
    GMAIL_ADDRESS = "screenerpro.ai@gmail.com"
    GMAIL_APP_PASSWORD = "udwilifenbdvkgdt"  # already used by you

    def notify_admin(error_msg):
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)

            msg = MIMEMultipart()
            msg["From"] = GMAIL_ADDRESS
            msg["To"] = ADMIN_EMAIL
            msg["Subject"] = "⚠️ Interview Template AI Fallback Used"

            msg.attach(MIMEText(
                f"Template Name: {template_name}\n\nError:\n{error_msg}",
                "plain"
            ))

            server.sendmail(GMAIL_ADDRESS, ADMIN_EMAIL, msg.as_string())
            server.quit()
        except Exception:
            pass  # silent fail

    # ------------------ TRY GEMINI ------------------
    try:
        from google import generativeai as genai
        import streamlit as st

        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            raise Exception("Missing Gemini API key")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-2.0-flash")

        prompt = f"""
Create an interview template for the role: {template_name}

STRICT OUTPUT FORMAT (MANDATORY):
Section Title: Question 1; Question 2; Question 3

Rules:
- NO markdown
- NO numbering
- NO explanation
- Each section on a new line
- Use real interview questions only
"""

        response = model.generate_content(prompt)

        if not response.text:
            raise Exception("Empty Gemini response")

        output = response.text.strip()

        # ✅ HARD VALIDATION (critical)
        for line in output.split("\n"):
            if ":" not in line or ";" not in line:
                raise Exception("Invalid AI format")

        return output

    # ------------------ FALLBACK ------------------
    except Exception as e:
        notify_admin(str(e))

        # 🔒 SAFE, GUARANTEED-SAVE FORMAT
        return f"""Technical Skills: Core concepts related to {template_name}; Problem-solving scenarios; Tool proficiency
Behavioral Skills: Team collaboration experience; Conflict resolution; Ownership examples
Role Knowledge: Understanding of {template_name} responsibilities; Real-world challenges; Best practices
Communication: Explaining technical ideas clearly; Stakeholder interaction; Decision justification
Culture Fit: Work ethic alignment; Learning mindset; Adaptability"""

def save_dataframe_to_firestore(collection_path, doc_id, df, api_key, base_url):
    """Save a Pandas DataFrame as base64-encoded CSV to Firestore."""
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    b64_csv = base64.b64encode(csv_bytes).decode("utf-8")
    
    data = {
        "filename": f"{doc_id}.csv",
        "file_data": b64_csv,
        "uploaded_at": datetime.utcnow().isoformat()
    }
    return save_document_to_firestore(collection_path, doc_id, data, api_key, base_url)
from firebase_config import (
    FIREBASE_PROJECT_ID,
    FIREBASE_WEB_API_KEY,
    FIRESTORE_DOCUMENTS_URL
)

def load_dataframe_from_firestore(collection_path, doc_id, api_key, base_url):
    """Load a DataFrame previously saved in Firestore."""
    url = f"{base_url}/documents/{collection_path}/{doc_id}?key={api_key}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        doc = res.json()
        if "fields" in doc:
            data = from_firestore_format(doc)
            if "file_data" in data:
                csv_bytes = base64.b64decode(data["file_data"].encode("utf-8"))
                return pd.read_csv(io.BytesIO(csv_bytes))
        return None
    except:
        return None

def to_firestore_format(data: dict) -> dict:
    """Converts a Python dictionary to Firestore REST API 'fields' format."""
    fields = {}
    for key, value in data.items():
        if isinstance(value, str):
            fields[key] = {"stringValue": value}
        elif isinstance(value, int):
            fields[key] = {"integerValue": str(value)} # Firestore expects string for integerValue
        elif isinstance(value, float):
            fields[key] = {"doubleValue": value}
        elif isinstance(value, bool):
            fields[key] = {"booleanValue": value}
        elif isinstance(value, datetime):
            fields[key] = {"timestampValue": value.isoformat() + "Z"} # ISO 8601 with 'Z' for UTC
        elif isinstance(value, list):
            # For lists, convert each item and wrap in arrayValue
            array_values = []
            for item in value:
                if isinstance(item, str):
                    array_values.append({"stringValue": item})
                elif isinstance(item, int):
                    array_values.append({"integerValue": str(item)})
                elif isinstance(item, float):
                    array_values.append({"doubleValue": item})
                elif isinstance(item, bool):
                    array_values.append({"booleanValue": item})
                elif isinstance(item, dict): # Handle nested dicts in lists
                    array_values.append({"mapValue": {"fields": to_firestore_format(item)['fields']}})
                else: # Fallback for other types in list
                    array_values.append({"stringValue": str(item)})
            fields[key] = {"arrayValue": {"values": array_values}}
        elif isinstance(value, dict):
            # For nested dictionaries (maps), recursively convert
            fields[key] = {"mapValue": {"fields": to_firestore_format(value)['fields']}}
        elif value is None:
            fields[key] = {"nullValue": None}
        else:
            # Fallback for other types, try to stringify
            fields[key] = {"stringValue": str(value)}
    return {"fields": fields}

def delete_firestore_document(doc_id):
    if "id_token" not in st.session_state:
        return False, "Not authenticated."

    id_token = st.session_state.id_token

    url = f"{FIRESTORE_DOCUMENTS_URL}/hr_role_matches/{doc_id}"

    headers = {
        "Authorization": f"Bearer {id_token}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.delete(url, headers=headers, timeout=10)

        if r.status_code in (200, 204):
            return True, "Deleted"
        else:
            return False, f"Error: {r.text}"

    except Exception as e:
        return False, str(e)

def from_firestore_format(firestore_data: dict) -> dict:
    """Converts Firestore REST API 'fields' format to a Python dictionary."""
    data = {}
    if "fields" not in firestore_data:
        return data # Or raise an error if expected
    
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
            # Fallback for other types, try to stringify
            data[key] = str(value_obj)
    return data

def save_document_to_firestore(collection_path, doc_id, data, api_key, base_url):
    """Saves a document to Firestore using PATCH (create or update)."""
    url = f"{base_url}/documents/{collection_path}/{doc_id}?key={api_key}"
    firestore_data = to_firestore_format(data)
    try:
        res = requests.patch(url, json=firestore_data)
        res.raise_for_status() # Raise an exception for HTTP errors
        return True, res.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Firestore save error: {e}") # Keep user-facing error
        return False, str(e)

def add_document_to_firestore_collection(collection_path, data, api_key, base_url):
    """Adds a new document to a Firestore collection (Firestore assigns ID)."""
    url = f"{base_url}/documents/{collection_path}?key={api_key}"
    firestore_data = to_firestore_format(data)
    try:
        res = requests.post(url, json=firestore_data)
        res.raise_for_status()
        return True, res.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Firestore add error: {e}") # Keep user-facing error
        return False, str(e)

def load_collection_from_firestore(collection_path, api_key, base_url):
    """Loads all documents from a Firestore collection."""
    url = f"{base_url}/documents/{collection_path}?key={api_key}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        docs_data = []
        if 'documents' in res.json():
            for doc in res.json()['documents']:
                doc_id = doc['name'].split('/')[-1]
                data = from_firestore_format(doc)
                data['id'] = doc_id # Add document ID to the data
                docs_data.append(data)
        return True, docs_data
    except requests.exceptions.RequestException as e:
        # Only print error for non-404 issues, as 404 means collection is empty (which is fine)
        if e.response and e.response.status_code == 404:
            return True, [] # Collection not found, return empty list without error
        st.error(f"Firestore load error: {e}") # Keep user-facing error
        return False, str(e)

def fetch_firebase_analytics_data(user_uid):
    """Fetch all saved analysis entries for the current user from Firestore."""
    if "id_token" not in st.session_state:
        return pd.DataFrame()

    id_token = st.session_state.id_token

    # URL for listing ALL documents in hr_role_matches
    url = f"{FIRESTORE_DOCUMENTS_URL}/hr_role_matches"

    headers = {
        "Authorization": f"Bearer {id_token}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)

        if r.status_code != 200:
            st.error(f"Firestore fetch error: {r.text}")
            return pd.DataFrame()

        data = r.json()

        if "documents" not in data:
            return pd.DataFrame()

        rows = []
        for doc in data["documents"]:
            fields = doc.get("fields", {})
            doc_id = doc["name"].split("/")[-1]  # important for deletion

            # Only load records belonging to this user
            if fields.get("user_uid", {}).get("stringValue") != user_uid:
                continue

            rows.append({
                "doc_id": doc_id,
                "user_uid": user_uid,
                "Date": fields.get("created_at", {}).get("stringValue"),
                "Role": fields.get("predicted_role", {}).get("stringValue"),
                "Confidence": float(fields.get("confidence", {}).get("doubleValue", 0)),
                "JD Match Score": float(fields.get("jd_match", {}).get("doubleValue", 0)),
                "Seniority": fields.get("seniority", {}).get("stringValue", "N/A"),
                "source_type": fields.get("source_type", {}).get("stringValue", "N/A"),
            })

        df = pd.DataFrame(rows)

        if not df.empty:
            df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d %H:%M")
            df["Confidence"] = (df["Confidence"] * 100).round(1).astype(str) + "%"
            df["JD Match Score"] = (df["JD Match Score"] * 100).round(1).astype(str) + "%"

        return df

    except Exception as e:
        st.error(f"Error fetching history: {e}")
        return pd.DataFrame()


def send_actual_email(to_email, subject, body, from_email, app_password):
    try:
        # Create a multipart message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email

        # Add the HTML body
        html_part = MIMEText(body, "html")
        msg.attach(html_part)

        # Send email via Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_email, app_password)
            server.sendmail(from_email, to_email, msg.as_string())

        return True, "✅ Email sent successfully"
    except Exception as e:
        return False, f"❌ Failed to send email: {str(e)}"


# --- Mock Salary Data (More Realistic and Granular) ---
MOCK_SALARY_DATA = [
    # Software Engineer - Bengaluru (Annual Salaries in INR Lakhs)
    {"role": "Software Engineer", "seniority": "Junior", "location": "Bengaluru, India", "min_exp": 0, "max_exp": 1, "min_salary": 400000, "max_salary": 600000, "avg_bonus_pct": 5, "avg_equity_pct": 0},
    {"role": "Software Engineer", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 2, "max_exp": 4, "min_salary": 800000, "max_salary": 1300000, "avg_bonus_pct": 8, "avg_equity_pct": 5},
    {"role": "Software Engineer", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 5, "max_exp": 8, "min_salary": 1500000, "max_salary": 2500000, "avg_bonus_pct": 10, "avg_equity_pct": 10},
    {"role": "Software Engineer", "seniority": "Lead/Principal", "location": "Bengaluru, India", "min_exp": 9, "max_exp": 99, "min_salary": 2800000, "max_salary": 4500000, "avg_bonus_pct": 12, "avg_equity_pct": 15},
    {"role": "Software Engineer", "seniority": "Staff", "location": "Bengaluru, India", "min_exp": 12, "max_exp": 99, "min_salary": 4000000, "max_salary": 6000000, "avg_bonus_pct": 15, "avg_equity_pct": 20},

    # Data Scientist - Bengaluru
    {"role": "Data Scientist", "seniority": "Junior", "location": "Bengaluru, India", "min_exp": 0, "max_exp": 1, "min_salary": 500000, "max_salary": 750000, "avg_bonus_pct": 6, "avg_equity_pct": 0},
    {"role": "Data Scientist", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 2, "max_exp": 4, "min_salary": 1000000, "max_salary": 1600000, "avg_bonus_pct": 9, "avg_equity_pct": 7},
    {"role": "Data Scientist", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 5, "max_exp": 8, "min_salary": 1800000, "max_salary": 3000000, "avg_bonus_pct": 11, "avg_equity_pct": 12},
    {"role": "Data Scientist", "seniority": "Lead", "location": "Bengaluru, India", "min_exp": 9, "max_exp": 99, "min_salary": 3200000, "max_salary": 5000000, "avg_bonus_pct": 13, "avg_equity_pct": 16},

    # HR Manager - Bengaluru
    {"role": "HR Manager", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 3, "max_exp": 6, "min_salary": 700000, "max_salary": 1200000, "avg_bonus_pct": 7, "avg_equity_pct": 0},
    {"role": "HR Manager", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 7, "max_exp": 12, "min_salary": 1300000, "max_salary": 2000000, "avg_bonus_pct": 10, "avg_equity_pct": 5},
    {"role": "HR Manager", "seniority": "Lead/Principal", "location": "Bengaluru, India", "min_exp": 13, "max_exp": 99, "min_salary": 2100000, "max_salary": 3500000, "avg_bonus_pct": 15, "avg_equity_pct": 8},

    # Business Analyst - Bengaluru
    {"role": "Business Analyst", "seniority": "Junior", "location": "Bengaluru, India", "min_exp": 0, "max_exp": 2, "min_salary": 450000, "max_salary": 700000, "avg_bonus_pct": 5, "avg_equity_pct": 0},
    {"role": "Business Analyst", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 3, "max_exp": 6, "min_salary": 800000, "max_salary": 1300000, "avg_bonus_pct": 8, "avg_equity_pct": 3},
    {"role": "Business Analyst", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 7, "max_exp": 10, "min_salary": 1400000, "max_salary": 2200000, "avg_bonus_pct": 10, "avg_equity_pct": 5},

    # Product Manager - Bengaluru
    {"role": "Product Manager", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 4, "max_exp": 7, "min_salary": 1600000, "max_salary": 2500000, "avg_bonus_pct": 12, "avg_equity_pct": 10},
    {"role": "Product Manager", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 8, "max_exp": 12, "min_salary": 2800000, "max_salary": 4000000, "avg_bonus_pct": 15, "avg_equity_pct": 18},
    {"role": "Product Manager", "seniority": "Director", "location": "Bengaluru, India", "min_exp": 13, "max_exp": 99, "min_salary": 4500000, "max_salary": 7000000, "avg_bonus_pct": 20, "avg_equity_pct": 25},

    # Marketing Specialist - Delhi
    {"role": "Marketing Specialist", "seniority": "Junior", "location": "Delhi, India", "min_exp": 0, "max_exp": 2, "min_salary": 300000, "max_salary": 500000, "avg_bonus_pct": 4, "avg_equity_pct": 0},
    {"role": "Marketing Specialist", "seniority": "Mid", "location": "Delhi, India", "min_exp": 3, "max_exp": 6, "min_salary": 600000, "max_salary": 1000000, "avg_bonus_pct": 7, "avg_equity_pct": 0},
    {"role": "Marketing Specialist", "seniority": "Senior", "location": "Delhi, India", "min_exp": 7, "max_exp": 10, "min_salary": 1100000, "max_salary": 1800000, "avg_bonus_pct": 10, "avg_equity_pct": 3},

    # Software Engineer - Mumbai
    {"role": "Software Engineer", "seniority": "Junior", "location": "Mumbai, India", "min_exp": 0, "max_exp": 1, "min_salary": 350000, "max_salary": 550000, "avg_bonus_pct": 5, "avg_equity_pct": 0},
    {"role": "Software Engineer", "seniority": "Mid", "location": "Mumbai, India", "min_exp": 2, "max_exp": 4, "min_salary": 700000, "max_salary": 1100000, "avg_bonus_pct": 8, "avg_equity_pct": 4},
    {"role": "Software Engineer", "seniority": "Senior", "location": "Mumbai, India", "min_exp": 5, "max_exp": 8, "min_salary": 1200000, "max_salary": 2000000, "avg_bonus_pct": 10, "avg_equity_pct": 8},

    # Data Scientist - Hyderabad
    {"role": "Data Scientist", "seniority": "Junior", "location": "Hyderabad, India", "min_exp": 0, "max_exp": 1, "min_salary": 450000, "max_salary": 650000, "avg_bonus_pct": 6, "avg_equity_pct": 0},
    {"role": "Data Scientist", "seniority": "Mid", "location": "Hyderabad, India", "min_exp": 2, "max_exp": 4, "min_salary": 900000, "max_salary": 1400000, "avg_bonus_pct": 9, "avg_equity_pct": 6},
    {"role": "Data Scientist", "seniority": "Senior", "location": "Hyderabad, India", "min_exp": 5, "max_exp": 8, "min_salary": 1600000, "max_salary": 2800000, "avg_bonus_pct": 11, "avg_equity_pct": 10},

    # UX Designer - Bengaluru
    {"role": "UX Designer", "seniority": "Junior", "location": "Bengaluru, India", "min_exp": 0, "max_exp": 2, "min_salary": 400000, "max_salary": 650000, "avg_bonus_pct": 5, "avg_equity_pct": 0},
    {"role": "UX Designer", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 3, "max_exp": 6, "min_salary": 800000, "max_salary": 1400000, "avg_bonus_pct": 8, "avg_equity_pct": 4},
    {"role": "UX Designer", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 7, "max_exp": 10, "min_salary": 1500000, "max_salary": 2300000, "avg_bonus_pct": 10, "avg_equity_pct": 7},

    # Cloud Engineer - Pune
    {"role": "Cloud Engineer", "seniority": "Junior", "location": "Pune, India", "min_exp": 0, "max_exp": 2, "min_salary": 450000, "max_salary": 700000, "avg_bonus_pct": 6, "avg_equity_pct": 0},
    {"role": "Cloud Engineer", "seniority": "Mid", "location": "Pune, India", "min_exp": 3, "max_exp": 6, "min_salary": 900000, "max_salary": 1500000, "avg_bonus_pct": 9, "avg_equity_pct": 5},
    {"role": "Cloud Engineer", "seniority": "Senior", "location": "Pune, India", "min_exp": 7, "max_exp": 10, "min_salary": 1700000, "max_salary": 2700000, "avg_bonus_pct": 12, "avg_equity_pct": 9},

    # Financial Analyst - Chennai
    {"role": "Financial Analyst", "seniority": "Junior", "location": "Chennai, India", "min_exp": 0, "max_exp": 2, "min_salary": 350000, "max_salary": 550000, "avg_bonus_pct": 4, "avg_equity_pct": 0},
    {"role": "Financial Analyst", "seniority": "Mid", "location": "Chennai, India", "min_exp": 3, "max_exp": 6, "min_salary": 600000, "max_salary": 1000000, "avg_bonus_pct": 7, "avg_equity_pct": 0},

    # Sales Manager - Bengaluru
    {"role": "Sales Manager", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 3, "max_exp": 7, "min_salary": 800000, "max_salary": 1500000, "avg_bonus_pct": 15, "avg_equity_pct": 5},
    {"role": "Sales Manager", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 8, "max_exp": 12, "min_salary": 1800000, "max_salary": 3000000, "avg_bonus_pct": 20, "avg_equity_pct": 8},

    # Content Writer - Remote (India)
    {"role": "Content Writer", "seniority": "Junior", "location": "Remote, India", "min_exp": 0, "max_exp": 2, "min_salary": 300000, "max_salary": 500000, "avg_bonus_pct": 3, "avg_equity_pct": 0},
    {"role": "Content Writer", "seniority": "Mid", "location": "Remote, India", "min_exp": 3, "max_exp": 6, "min_salary": 550000, "max_salary": 900000, "avg_bonus_pct": 5, "avg_equity_pct": 0},

    # Operations Manager - Gurugram
    {"role": "Operations Manager", "seniority": "Mid", "location": "Gurugram, India", "min_exp": 4, "max_exp": 8, "min_salary": 900000, "max_salary": 1600000, "avg_bonus_pct": 10, "avg_equity_pct": 3},
    {"role": "Operations Manager", "seniority": "Senior", "location": "Gurugram, India", "min_exp": 9, "max_exp": 15, "min_salary": 1800000, "max_salary": 3000000, "avg_bonus_pct": 15, "avg_equity_pct": 6},

    # Cybersecurity Analyst - Bengaluru
    {"role": "Cybersecurity Analyst", "seniority": "Junior", "location": "Bengaluru, India", "min_exp": 0, "max_exp": 2, "min_salary": 500000, "max_salary": 800000, "avg_bonus_pct": 7, "avg_equity_pct": 0},
    {"role": "Cybersecurity Analyst", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 3, "max_exp": 6, "min_salary": 1000000, "max_salary": 1800000, "avg_bonus_pct": 10, "avg_equity_pct": 5},
    {"role": "Cybersecurity Analyst", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 7, "max_exp": 12, "min_salary": 2000000, "max_salary": 3500000, "avg_bonus_pct": 13, "avg_equity_pct": 10},

    # AI/ML Engineer - Bengaluru
    {"role": "AI/ML Engineer", "seniority": "Junior", "location": "Bengaluru, India", "min_exp": 0, "max_exp": 1, "min_salary": 600000, "max_salary": 900000, "avg_bonus_pct": 8, "avg_equity_pct": 3},
    {"role": "AI/ML Engineer", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 2, "max_exp": 4, "min_salary": 1200000, "max_salary": 2000000, "avg_bonus_pct": 10, "avg_equity_pct": 8},
    {"role": "AI/ML Engineer", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 5, "max_exp": 8, "min_salary": 2500000, "max_salary": 4000000, "avg_bonus_pct": 15, "avg_equity_pct": 15},

    # Digital Marketing Manager - Mumbai
    {"role": "Digital Marketing Manager", "seniority": "Mid", "location": "Mumbai, India", "min_exp": 3, "max_exp": 7, "min_salary": 700000, "max_salary": 1300000, "avg_bonus_pct": 9, "avg_equity_pct": 0},
    {"role": "Digital Marketing Manager", "seniority": "Senior", "location": "Mumbai, India", "min_exp": 8, "max_exp": 12, "min_salary": 1400000, "max_salary": 2200000, "avg_bonus_pct": 12, "avg_equity_pct": 5},

    # DevOps Engineer - Hyderabad
    {"role": "DevOps Engineer", "seniority": "Junior", "location": "Hyderabad, India", "min_exp": 0, "max_exp": 2, "min_salary": 480000, "max_salary": 750000, "avg_bonus_pct": 6, "avg_equity_pct": 0},
    {"role": "DevOps Engineer", "seniority": "Mid", "location": "Hyderabad, India", "min_exp": 3, "max_exp": 6, "min_salary": 950000, "max_salary": 1600000, "avg_bonus_pct": 9, "avg_equity_pct": 5},
    {"role": "DevOps Engineer", "seniority": "Senior", "location": "Hyderabad, India", "min_exp": 7, "max_exp": 10, "min_salary": 1800000, "max_salary": 3000000, "avg_bonus_pct": 12, "avg_equity_pct": 10},

    # Quality Assurance Engineer - Chennai
    {"role": "Quality Assurance Engineer", "seniority": "Junior", "location": "Chennai, India", "min_exp": 0, "max_exp": 1, "min_salary": 300000, "max_salary": 500000, "avg_bonus_pct": 4, "avg_equity_pct": 0},
    {"role": "Quality Assurance Engineer", "seniority": "Mid", "location": "Chennai, India", "min_exp": 2, "max_exp": 4, "min_salary": 600000, "max_salary": 1000000, "avg_bonus_pct": 7, "avg_equity_pct": 0},

    # Technical Writer - Remote (India)
    {"role": "Technical Writer", "seniority": "Junior", "location": "Remote, India", "min_exp": 0, "max_exp": 2, "min_salary": 300000, "max_salary": 500000, "avg_bonus_pct": 3, "avg_equity_pct": 0},
    {"role": "Technical Writer", "seniority": "Mid", "location": "Remote, India", "min_exp": 3, "max_exp": 6, "min_salary": 550000, "max_salary": 900000, "avg_bonus_pct": 5, "avg_equity_pct": 0},

    # Customer Support Specialist - Noida
    {"role": "Customer Support Specialist", "seniority": "Junior", "location": "Noida, India", "min_exp": 0, "max_exp": 1, "min_salary": 200000, "max_salary": 350000, "avg_bonus_pct": 2, "avg_equity_pct": 0},
    {"role": "Customer Support Specialist", "seniority": "Mid", "location": "Noida, India", "min_exp": 2, "max_exp": 4, "min_salary": 380000, "max_salary": 600000, "avg_bonus_pct": 4, "avg_equity_pct": 0},

    # Project Manager - Bengaluru
    {"role": "Project Manager", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 5, "max_exp": 8, "min_salary": 1500000, "max_salary": 2500000, "avg_bonus_pct": 10, "avg_equity_pct": 5},
    {"role": "Project Manager", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 9, "max_exp": 15, "min_salary": 2800000, "max_salary": 4500000, "avg_bonus_pct": 15, "avg_equity_pct": 10},

    # Research Scientist - Bengaluru (Higher salaries for specialized roles)
    {"role": "Research Scientist", "seniority": "Junior", "location": "Bengaluru, India", "min_exp": 0, "max_exp": 2, "min_salary": 700000, "max_salary": 1000000, "avg_bonus_pct": 8, "avg_equity_pct": 5},
    {"role": "Research Scientist", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 3, "max_exp": 6, "min_salary": 1400000, "max_salary": 2200000, "avg_bonus_pct": 12, "avg_equity_pct": 10},
    {"role": "Research Scientist", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 7, "max_exp": 12, "min_salary": 2800000, "max_salary": 5000000, "avg_bonus_pct": 18, "avg_equity_pct": 20},

    # Solutions Architect - Bengaluru
    {"role": "Solutions Architect", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 6, "max_exp": 10, "min_salary": 2000000, "max_salary": 3500000, "avg_bonus_pct": 15, "avg_equity_pct": 12},
    {"role": "Solutions Architect", "seniority": "Principal", "location": "Bengaluru, India", "min_exp": 11, "max_exp": 99, "min_salary": 4000000, "max_salary": 6500000, "avg_bonus_pct": 20, "avg_equity_pct": 25},

    # UI Developer - Hyderabad
    {"role": "UI Developer", "seniority": "Junior", "location": "Hyderabad, India", "min_exp": 0, "max_exp": 1, "min_salary": 380000, "max_salary": 580000, "avg_bonus_pct": 5, "avg_equity_pct": 0},
    {"role": "UI Developer", "seniority": "Mid", "location": "Hyderabad, India", "min_exp": 2, "max_exp": 4, "min_salary": 750000, "max_salary": 1200000, "avg_bonus_pct": 8, "avg_equity_pct": 3},

    # Data Analyst - Pune
    {"role": "Data Analyst", "seniority": "Junior", "location": "Pune, India", "min_exp": 0, "max_exp": 2, "min_salary": 350000, "max_salary": 550000, "avg_bonus_pct": 4, "avg_equity_pct": 0},
    {"role": "Data Analyst", "seniority": "Mid", "location": "Pune, India", "min_exp": 3, "max_exp": 6, "min_salary": 600000, "max_salary": 1000000, "avg_bonus_pct": 7, "avg_equity_pct": 0},

    # Embedded Systems Engineer - Chennai
    {"role": "Embedded Systems Engineer", "seniority": "Junior", "location": "Chennai, India", "min_exp": 0, "max_exp": 2, "min_salary": 450000, "max_salary": 700000, "avg_bonus_pct": 6, "avg_equity_pct": 0},
    {"role": "Embedded Systems Engineer", "seniority": "Mid", "location": "Chennai, India", "min_exp": 3, "max_exp": 6, "min_salary": 900000, "max_salary": 1500000, "avg_bonus_pct": 9, "avg_equity_pct": 5},

    # Game Developer - Bengaluru
    {"role": "Game Developer", "seniority": "Junior", "location": "Bengaluru, India", "min_exp": 0, "max_exp": 2, "min_salary": 400000, "max_salary": 600000, "avg_bonus_pct": 5, "avg_equity_pct": 0},
    {"role": "Game Developer", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 3, "max_exp": 6, "min_salary": 800000, "max_salary": 1300000, "avg_bonus_pct": 8, "avg_equity_pct": 3},

    # Blockchain Developer - Remote (India)
    {"role": "Blockchain Developer", "seniority": "Junior", "location": "Remote, India", "min_exp": 0, "max_exp": 2, "min_salary": 600000, "max_salary": 900000, "avg_bonus_pct": 8, "avg_equity_pct": 5},
    {"role": "Blockchain Developer", "seniority": "Mid", "location": "Remote, India", "min_exp": 3, "max_exp": 6, "min_salary": 1200000, "max_salary": 2000000, "avg_bonus_pct": 10, "avg_equity_pct": 10},

    # Technical Support Engineer - Noida
    {"role": "Technical Support Engineer", "seniority": "Junior", "location": "Noida, India", "min_exp": 0, "max_exp": 1, "min_salary": 250000, "max_salary": 400000, "avg_bonus_pct": 3, "avg_equity_pct": 0},
    {"role": "Technical Support Engineer", "seniority": "Mid", "location": "Noida, India", "min_exp": 2, "max_exp": 4, "min_salary": 450000, "max_salary": 700000, "avg_bonus_pct": 5, "avg_equity_pct": 0},
    # Cloud Architect - Bengaluru
    {"role": "Cloud Architect", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 8, "max_exp": 12, "min_salary": 2800000, "max_salary": 4500000, "avg_bonus_pct": 15, "avg_equity_pct": 15},
    {"role": "Cloud Architect", "seniority": "Principal", "location": "Bengaluru, India", "min_exp": 13, "max_exp": 99, "min_salary": 5000000, "max_salary": 8000000, "avg_bonus_pct": 20, "avg_equity_pct": 25},

    # Data Engineer - Hyderabad
    {"role": "Data Engineer", "seniority": "Junior", "location": "Hyderabad, India", "min_exp": 0, "max_exp": 2, "min_salary": 500000, "max_salary": 750000, "avg_bonus_pct": 6, "avg_equity_pct": 0},
    {"role": "Data Engineer", "seniority": "Mid", "location": "Hyderabad, India", "min_exp": 3, "max_exp": 6, "min_salary": 1000000, "max_salary": 1700000, "avg_bonus_pct": 9, "avg_equity_pct": 6},
    {"role": "Data Engineer", "seniority": "Senior", "location": "Hyderabad, India", "min_exp": 7, "max_exp": 10, "min_salary": 1900000, "max_salary": 3200000, "avg_bonus_pct": 12, "avg_equity_pct": 10},

    # UI/UX Lead - Mumbai
    {"role": "UI/UX Lead", "seniority": "Lead", "location": "Mumbai, India", "min_exp": 6, "max_exp": 10, "min_salary": 1500000, "max_salary": 2500000, "avg_bonus_pct": 10, "avg_equity_pct": 8},

    # Network Engineer - Pune
    {"role": "Network Engineer", "seniority": "Junior", "location": "Pune, India", "min_exp": 0, "max_exp": 2, "min_salary": 380000, "max_salary": 600000, "avg_bonus_pct": 4, "avg_equity_pct": 0},
    {"role": "Network Engineer", "seniority": "Mid", "location": "Pune, India", "min_exp": 3, "max_exp": 6, "min_salary": 700000, "max_salary": 1200000, "avg_bonus_pct": 7, "avg_equity_pct": 0},

    # Business Development Manager - Bengaluru
    {"role": "Business Development Manager", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 3, "max_exp": 7, "min_salary": 850000, "max_salary": 1600000, "avg_bonus_pct": 18, "avg_equity_pct": 5},
    {"role": "Business Development Manager", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 8, "max_exp": 12, "min_salary": 1900000, "max_salary": 3200000, "avg_bonus_pct": 25, "avg_equity_pct": 10},

    # Legal Counsel - Delhi
    {"role": "Legal Counsel", "seniority": "Junior", "location": "Delhi, India", "min_exp": 0, "max_exp": 3, "min_salary": 600000, "max_salary": 1000000, "avg_bonus_pct": 5, "avg_equity_pct": 0},
    {"role": "Legal Counsel", "seniority": "Mid", "location": "Delhi, India", "min_exp": 4, "max_exp": 8, "min_salary": 1200000, "max_salary": 2000000, "avg_bonus_pct": 8, "avg_equity_pct": 0},

    # Supply Chain Manager - Chennai
    {"role": "Supply Chain Manager", "seniority": "Mid", "location": "Chennai, India", "min_exp": 4, "max_exp": 8, "min_salary": 750000, "max_salary": 1400000, "avg_bonus_pct": 9, "avg_equity_pct": 0},

    # Research Analyst - Mumbai
    {"role": "Research Analyst", "seniority": "Junior", "location": "Mumbai, India", "min_exp": 0, "max_exp": 2, "min_salary": 350000, "max_salary": 550000, "avg_bonus_pct": 4, "avg_equity_pct": 0},
    {"role": "Research Analyst", "seniority": "Mid", "location": "Mumbai, India", "min_exp": 3, "max_exp": 6, "min_salary": 600000, "max_salary": 1000000, "avg_bonus_pct": 7, "avg_equity_pct": 0},

    # Embedded Software Engineer - Bengaluru
    {"role": "Embedded Software Engineer", "seniority": "Junior", "location": "Bengaluru, India", "min_exp": 0, "max_exp": 2, "min_salary": 500000, "max_salary": 800000, "avg_bonus_pct": 7, "avg_equity_pct": 3},
    {"role": "Embedded Software Engineer", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 3, "max_exp": 6, "min_salary": 1000000, "max_salary": 1800000, "avg_bonus_pct": 10, "avg_equity_pct": 6},

    # Machine Learning Engineer - Delhi
    {"role": "Machine Learning Engineer", "seniority": "Junior", "location": "Delhi, India", "min_exp": 0, "max_exp": 1, "min_salary": 550000, "max_salary": 850000, "avg_bonus_pct": 7, "avg_equity_pct": 3},
    {"role": "Machine Learning Engineer", "seniority": "Mid", "location": "Delhi, India", "min_exp": 2, "max_exp": 4, "min_salary": 1100000, "max_salary": 1900000, "avg_bonus_pct": 10, "avg_equity_pct": 8},

    # Data Architect - Bengaluru
    {"role": "Data Architect", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 9, "max_exp": 15, "min_salary": 3500000, "max_salary": 6000000, "avg_bonus_pct": 18, "avg_equity_pct": 20},

    # Frontend Developer - Pune
    {"role": "Frontend Developer", "seniority": "Junior", "location": "Pune, India", "min_exp": 0, "max_exp": 1, "min_salary": 350000, "max_salary": 550000, "avg_bonus_pct": 5, "avg_equity_pct": 0},
    {"role": "Frontend Developer", "seniority": "Mid", "location": "Pune, India", "min_exp": 2, "max_exp": 4, "min_salary": 700000, "max_salary": 1100000, "avg_bonus_pct": 8, "avg_equity_pct": 3},

    # Backend Developer - Hyderabad
    {"role": "Backend Developer", "seniority": "Junior", "location": "Hyderabad, India", "min_exp": 0, "max_exp": 1, "min_salary": 400000, "max_salary": 600000, "avg_bonus_pct": 5, "avg_equity_pct": 0},
    {"role": "Backend Developer", "seniority": "Mid", "location": "Hyderabad, India", "min_exp": 2, "max_exp": 4, "min_salary": 800000, "max_salary": 1300000, "avg_bonus_pct": 8, "avg_equity_pct": 4},

    # Mobile Developer (Android/iOS) - Bengaluru
    {"role": "Mobile Developer", "seniority": "Junior", "location": "Bengaluru, India", "min_exp": 0, "max_exp": 1, "min_salary": 450000, "max_salary": 700000, "avg_bonus_pct": 6, "avg_equity_pct": 0},
    {"role": "Mobile Developer", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 2, "max_exp": 4, "min_salary": 900000, "max_salary": 1500000, "avg_bonus_pct": 9, "avg_equity_pct": 5},

    # QA Lead - Bengaluru
    {"role": "QA Lead", "seniority": "Lead", "location": "Bengaluru, India", "min_exp": 6, "max_exp": 10, "min_salary": 1200000, "max_salary": 2000000, "avg_bonus_pct": 10, "avg_equity_pct": 5},

    # Technical Architect - Mumbai
    {"role": "Technical Architect", "seniority": "Senior", "location": "Mumbai, India", "min_exp": 10, "max_exp": 99, "min_salary": 3000000, "max_salary": 5500000, "avg_bonus_pct": 18, "avg_equity_pct": 20},

    # Data Engineer Lead - Bengaluru
    {"role": "Data Engineer Lead", "seniority": "Lead", "location": "Bengaluru, India", "min_exp": 8, "max_exp": 12, "min_salary": 2500000, "max_salary": 4000000, "avg_bonus_pct": 15, "avg_equity_pct": 12},

    # Cloud Security Engineer - Hyderabad
    {"role": "Cloud Security Engineer", "seniority": "Mid", "location": "Hyderabad, India", "min_exp": 3, "max_exp": 7, "min_salary": 1100000, "max_salary": 2000000, "avg_bonus_pct": 10, "avg_equity_pct": 7},

    # ERP Consultant - Delhi
    {"role": "ERP Consultant", "seniority": "Mid", "location": "Delhi, India", "min_exp": 4, "max_exp": 8, "min_salary": 900000, "max_salary": 1600000, "avg_bonus_pct": 8, "avg_equity_pct": 0},

    # Financial Controller - Bengaluru
    {"role": "Financial Controller", "seniority": "Senior", "location": "Bengaluru, India", "min_exp": 10, "max_exp": 99, "min_salary": 2500000, "max_salary": 4000000, "avg_bonus_pct": 15, "avg_equity_pct": 8},

    # Digital Marketing Analyst - Bengaluru
    {"role": "Digital Marketing Analyst", "seniority": "Junior", "location": "Bengaluru, India", "min_exp": 0, "max_exp": 2, "min_salary": 350000, "max_salary": 550000, "avg_bonus_pct": 4, "avg_equity_pct": 0},
    {"role": "Digital Marketing Analyst", "seniority": "Mid", "location": "Bengaluru, India", "min_exp": 3, "max_exp": 6, "min_salary": 600000, "max_salary": 1000000, "avg_bonus_pct": 7, "avg_equity_pct": 0},
]

def save_to_firestore_production(data):
    data["user_uid"] = st.session_state.user_uid

    # Check login
    if "id_token" not in st.session_state:
        return False, "User not authenticated. Login required before saving."

    try:
        payload = to_firestore_format(data)

        url = (
            f"https://firestore.googleapis.com/v1/projects/"
            f"{FIREBASE_PROJECT_ID}/databases/(default)/documents/hr_role_matches"
        )

        headers = {
            "Authorization": f"Bearer {st.session_state['id_token']}",
            "Content-Type": "application/json",
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=15)

        if resp.status_code in (200, 201):
            return True, "Saved to Firebase successfully."

        return False, f"API Error: {resp.status_code} - {resp.text}"

    except Exception as e:
        return False, f"Network/Connection Error: {e}"
def make_pdf_bytes(result, title="Role Match Report"):
    """Generate BEAUTIFUL, modern HR report PDF."""
    buf = io.BytesIO()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    if REPORTLAB_AVAILABLE:
        # --------------------------
        # Base doc + styles
        # --------------------------
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=30
        )

        styles = getSampleStyleSheet()
        normal = styles["Normal"]
        normal.fontSize = 10
        normal.leading = 14

        heading = ParagraphStyle(
            "Heading",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#2F3B6E"),
            spaceAfter=10
        )

        sub = ParagraphStyle(
            "sub",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#4A6CFF"),
            spaceBefore=10,
            spaceAfter=4
        )

        label = ParagraphStyle(
            "label",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#1A1A1A"),
            spaceAfter=4,
        )

        info = ParagraphStyle(
            "info",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#333333"),
        )

        story = []

        # --------------------------
        # BEAUTIFUL HEADER SECTION
        # --------------------------
        banner = Paragraph(
            f"""
            <para alignment='center'>
            <font size=20 color='#ffffff'><b>{title}</b></font><br/>
            <font size=10 color='#f0f0f0'>{now}</font>
            </para>
            """,
            ParagraphStyle(
                "banner",
                parent=styles["Normal"],
                backColor=colors.HexColor("#4A6CFF"),
                leading=26,
                spaceAfter=18,
                borderRadius=6,
                alignment=1,
                textColor=colors.white,
                leftIndent=0,
                rightIndent=0,
                spaceBefore=0,
            )
        )
        story.append(banner)
        story.append(Spacer(1, 14))

        # --------------------------
        # TOP ROLE SUMMARY CARD
        # --------------------------
        top_role = result.get("top_role", "N/A")
        top_conf = int(result.get("top_prob", 0.0) * 100)

        summary_card = Paragraph(
            f"""
            <para>
            <font size=13><b>🎯 Top Predicted Role:</b> {top_role}</font><br/>
            <font size=11 color='#555555'>Confidence Score: {top_conf}%</font>
            </para>
            """,
            ParagraphStyle(
                "card",
                parent=normal,
                backColor=colors.HexColor("#F4F7FF"),
                borderColor=colors.HexColor("#4A6CFF"),
                borderWidth=1,
                borderPadding=10,
                borderRadius=8,
                leading=18,
                spaceAfter=18,
            )
        )
        story.append(summary_card)

        # --------------------------
        # TABLE FOR TOP ROLES
        # --------------------------
        story.append(Paragraph(" Top Role Predictions", sub))

        tdata = [["Role", "Confidence (%))"]]
        for r, p in result.get("top_roles", []):
            tdata.append([r, f"{int(p * 100)}%"])

        table = Table(tdata, colWidths=[280, 120])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A6CFF")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ]))
        story.append(table)
        story.append(Spacer(1, 20))

        # --------------------------
        # SKILLS SECTION
        # --------------------------
        story.append(Paragraph("🛠 Detected Skills", sub))

        skills = ", ".join(result.get("skills", [])) or "No skills detected"
        story.append(Paragraph(skills, info))

        story.append(Spacer(1, 12))
        story.append(Paragraph("⚠ Missing Core Skills", sub))

        missing = ", ".join(result.get("missing_skills", [])) or "No missing skills"
        story.append(Paragraph(missing, info))

        story.append(Spacer(1, 20))

        # --------------------------
        # SENIORITY & JD MATCH
        # --------------------------
        story.append(Paragraph("📌 Additional Insights", sub))

        sen = result.get("seniority", "N/A")
        jd = result.get("jd_score")

        story.append(Paragraph(f"<b>Seniority Detected:</b> {sen}", info))
        if jd is not None:
            story.append(Paragraph(f"<b>JD Match Score:</b> {round(jd * 100, 1)}%", info))

        story.append(Spacer(1, 20))

        # --------------------------
        # RESUME EXCERPT
        # --------------------------
        story.append(Paragraph("📝 Resume Excerpt", sub))

        excerpt = result.get("resume_excerpt", "N/A").replace("\n", "<br/>")
        excerpt_box = Paragraph(
            f"<font color='#444444'>{excerpt}</font>",
            ParagraphStyle(
                "excerpt",
                parent=info,
                backColor=colors.HexColor("#fafafa"),
                borderPadding=10,
                borderRadius=6,
                borderColor=colors.HexColor("#DDDDDD"),
                borderWidth=0.5,
                leading=14,
            )
        )
        story.append(excerpt_box)

        doc.build(story)
        buf.seek(0)
        return buf.read()

    # --------------------------
    # FALLBACK (No reportlab)
    # --------------------------
    text_lines = []
    text_lines.append(f"{title} — {now}")
    text_lines.append(f"Top role: {result.get('top_role', 'N/A')} ({int(result.get('top_prob', 0.0)*100)}%)")
    text_lines.append("Top roles:")
    for r, p in result.get("top_roles", []):
        text_lines.append(f" - {r}: {int(p*100)}%")
    text_lines.append("")
    text_lines.append("Detected skills: " + (", ".join(result.get("skills", [])) or "None"))
    text_lines.append("Missing skills: " + (", ".join(result.get("missing_skills", [])) or "None"))
    if result.get("jd_score") is not None:
        text_lines.append("JD match: " + f"{round(result['jd_score']*100,1)}%")
    text_lines.append("")
    text_lines.append("Resume excerpt:")
    text_lines.append(result.get("resume_excerpt", "N/A"))

    buf.write("\n".join(text_lines).encode("utf-8"))
    buf.seek(0)
    return buf.read()


# Convert to DataFrame for easier querying
MOCK_SALARY_DF = pd.DataFrame(MOCK_SALARY_DATA)

# --- Advanced Tools Page Function ---
def advanced_tools_page():
    FIREBASE_PROJECT_ID = "screenerproapp"
    FIREBASE_WEB_API_KEY = "AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw"
    FIRESTORE_BASE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)"

    user_email = st.session_state.get('username', 'anonymous')
    user_company = st.session_state.get('user_company', 'default_company').replace(' ', '_').lower()

    dark_mode = st.session_state.get('dark_mode_main', False)


    st.markdown(f"""
    <style>
    .advanced-tools-container {{
        background-color: {'#2D2D2D' if dark_mode else 'rgba(255, 255, 255, 0.96)'};
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0px 8px 20px rgba(0,0,0,{'0.2' if dark_mode else '0.1'});
        animation: fadeIn 0.8s ease-in-out;
        color: {'#E0E0E0' if dark_mode else '#333333'};
        margin-bottom: 2rem;
    }}
    .advanced-tools-header {{
        font-size: 2.2rem;
        font-weight: 700;
        color: {'#00cec9' if dark_mode else '#00cec9'};
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #00cec9;
        display: inline-block;
        margin-bottom: 1.5rem;
    }}
    .advanced-tools-caption {{
        font-size: 1.1em;
        color: {'#BBBBBB' if dark_mode else '#555555'};
        margin-bottom: 2rem;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 24px;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 50px;
        white-space: nowrap;
        border-radius: 8px 8px 0 0;
        gap: 10px;
        padding-top: 10px;
        padding-bottom: 10px;
        background-color: {'#3A3A3A' if dark_mode else '#f0f2f6'};
        color: {'#BBBBBB' if dark_mode else '#555555'};
        font-weight: 600;
        transition: all 0.2s ease;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {'#00cec9' if dark_mode else '#00cec9'};
        color: white;
        border-bottom: 4px solid {'#00cec9' if dark_mode else '#00cec9'};
    }}
    .stTabs [aria-selected="true"] > div {{
        color: white !important;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        background-color: {'#4A4A4A' if dark_mode else '#e0e2e6'};
    }}
    .stExpander {{
        background-color: {'#3A3A3A' if dark_mode else '#f0f2f6'};
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 12px rgba(0,0,0,{'0.2' if dark_mode else '0.05'});
    }}
    .stExpander > div > div > div > p {{
        color: {'#E0E0E0' if dark_mode else '#333333'};
    }}
    .stExpander > div[data-testid="stExpanderToggle"] {{
        color: {'#00cec9' if dark_mode else '#00cec9'};
    }}
    .stExpander > div[data-testid="stExpanderToggle"] svg {{
        fill: {'#00cec9' if dark_mode else '#00cec9'};
    }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="advanced-tools-container">', unsafe_allow_html=True)
    st.markdown('<div class="advanced-tools-header">📈 Advanced Tools</div>', unsafe_allow_html=True)
    st.markdown('<p class="advanced-tools-caption">Explore powerful HR analytics and automation tools to gain deeper insights and streamline your processes.</p>', unsafe_allow_html=True)

    tab_predictive, tab_skill_gap, tab_compensation, tab_dei, tab_scheduling, tab_interview_templates, tab_role_matcher  = st.tabs([
        " Predictive Analytics", " Skill Gap Analysis", " Compensation Benchmarking", " DEI Analytics", " Interview Scheduling", " Interview Templates"," Role Matcher AI"
    ])

    # --- Load existing interviews, feedback, interviewers, and templates from Firebase ---
    if 'user_interviews' not in st.session_state:
        st.session_state.user_interviews = []
    if 'user_feedback' not in st.session_state:
        st.session_state.user_feedback = []
    if 'user_interviewers' not in st.session_state:
        st.session_state.user_interviewers = []
    if 'interview_templates' not in st.session_state:
        st.session_state.interview_templates = []
    
    if st.session_state.get('refresh_advanced_data', True):
        with st.spinner("Loading advanced tools data..."):
            success_interviews, loaded_interviews = load_collection_from_firestore(
                f"artifacts/{FIREBASE_PROJECT_ID}/companies/{user_company}/interviews", FIREBASE_WEB_API_KEY, FIRESTORE_BASE_URL
            )
            if success_interviews:
                st.session_state.user_interviews = loaded_interviews

            success_feedback, loaded_feedback = load_collection_from_firestore(
                f"artifacts/{FIREBASE_PROJECT_ID}/companies/{user_company}/interview_feedback", FIREBASE_WEB_API_KEY, FIRESTORE_BASE_URL
            )
            if success_feedback:
                st.session_state.user_feedback = loaded_feedback
            
            success_interviewers, loaded_interviewers = load_collection_from_firestore(
                f"artifacts/{FIREBASE_PROJECT_ID}/companies/{user_company}/interviewers", FIREBASE_WEB_API_KEY, FIRESTORE_BASE_URL
            )
            if success_interviewers:
                st.session_state.user_interviewers = loaded_interviewers

            success_templates, loaded_templates = load_collection_from_firestore(
                f"artifacts/{FIREBASE_PROJECT_ID}/companies/{user_company}/interview_templates", FIREBASE_WEB_API_KEY, FIRESTORE_BASE_URL
            )
            if success_templates:
                st.session_state.interview_templates = loaded_templates
            
            st.session_state.refresh_advanced_data = False
        
    with tab_predictive:
        st.subheader("Candidate Success Prediction")
        st.info("This tool predicts the likelihood of a candidate succeeding in a role based on various factors.")

        with st.form("predictive_form", clear_on_submit=False):
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                candidate_score = st.slider("Candidate Score (%)", 0, 100, 75, key="pred_score")
                years_experience = st.slider("Years of Experience", 0.0, 30.0, 5.0, step=0.5, key="pred_exp")
                skills_match_score = st.slider("Specific Skills Match (0-100%)", 0, 100, 70, key="pred_skills_match")
            with col_p2:
                education_level = st.selectbox("Highest Education Level", ["High School", "Associate's", "Bachelor's", "Master's", "PhD"], key="pred_edu")
                interview_feedback = st.slider("Interview Feedback (1-5, 5=Excellent)", 1, 5, 3, key="pred_feedback")
                past_company_tier = st.selectbox("Past Company Tier", ["Tier 1 (FAANG/Unicorn)", "Tier 2 (Large Enterprise)", "Tier 3 (Mid-size)", "Tier 4 (Startup/Small)"], key="pred_company_tier")
            
            predict_button = st.form_submit_button("Predict Success")

            if predict_button:
                # More complex mock prediction logic
                likelihood_score = 0
                if candidate_score >= 80: likelihood_score += 3
                elif candidate_score >= 60: likelihood_score += 2
                else: likelihood_score += 1

                if years_experience >= 5: likelihood_score += 3
                elif years_experience >= 2: likelihood_score += 2
                else: likelihood_score += 1

                if skills_match_score >= 80: likelihood_score += 2
                elif skills_match_score >= 50: likelihood_score += 1

                if interview_feedback >= 4: likelihood_score += 2
                elif interview_feedback >= 3: likelihood_score += 1

                if past_company_tier == "Tier 1 (FAANG/Unicorn)": likelihood_score += 2
                elif past_company_tier == "Tier 2 (Large Enterprise)": likelihood_score += 1

                probability = min(100, max(0, int(likelihood_score / 13 * 100) + np.random.randint(-10, 10)))
                
                likelihood = "Low"
                confidence = "Low"
                if probability >= 80:
                    likelihood = "High"
                    confidence = "High"
                elif probability >= 50:
                    likelihood = "Moderate"
                    confidence = "Medium"
                else:
                    likelihood = "Low"
                    confidence = "Low"
                
                st.success(f"**Prediction:** The candidate has a **{likelihood}** likelihood of success in this role (Probability: **{probability}%**).")
                st.info(f"Confidence in this prediction: **{confidence}**.")

        st.markdown("---")
        st.subheader("Employee Churn Prediction")
        st.info("Predict which existing employees might be at risk of leaving the company.")

        with st.form("churn_prediction_form", clear_on_submit=False):
            col_ch1, col_ch2 = st.columns(2)
            with col_ch1:
                employee_tenure = st.slider("Employee Tenure (Years)", 0, 20, 3, key="churn_tenure")
                performance_rating = st.slider("Last Performance Rating (1-5)", 1, 5, 3, key="churn_perf")
            with col_ch2:
                compensation_satisfaction = st.slider("Compensation Satisfaction (1-5)", 1, 5, 3, key="churn_comp_sat")
                work_life_balance = st.slider("Work-Life Balance (1-5)", 1, 5, 3, key="churn_wlb")
            
            predict_churn_button = st.form_submit_button("Predict Churn Risk")

            if predict_churn_button:
                churn_risk_score = 0
                if employee_tenure <= 2: churn_risk_score += 2
                elif employee_tenure >= 7: churn_risk_score += 1

                if performance_rating <= 2: churn_risk_score += 3
                
                if compensation_satisfaction <= 2: churn_risk_score += 3
                elif compensation_satisfaction == 3: churn_risk_score += 1

                if work_life_balance <= 2: churn_risk_score += 2

                risk_level = "Low"
                if churn_risk_score >= 6:
                    risk_level = "High"
                elif churn_risk_score >= 3:
                    risk_level = "Moderate"
                
                st.warning(f"**Churn Risk Prediction:** This employee has a **{risk_level}** risk of leaving.")
                st.write("*(Factors considered: Tenure, Performance, Compensation Satisfaction, Work-Life Balance)*")

        with tab_skill_gap:
            st.subheader("Skill Gap Analysis")
            st.info(
                "Identify common and missing skills by comparing required skills for a role against a candidate's profile.")

            # --- Skill Gap Form ---
            with st.form("skill_gap_form", clear_on_submit=False):
                required_skills_input = st.text_area(
                    "Required Skills (comma-separated)",
                    "Python, SQL, Machine Learning, Communication, Problem Solving",
                    height=100,
                    key="req_skills"
                )
                candidate_skills_input = st.text_area(
                    "Candidate's Skills (comma-separated)",
                    "Python, SQL, Data Analysis, Teamwork",
                    height=100,
                    key="cand_skills"
                )

                analyze_button = st.form_submit_button("Analyze Skill Gap")

                if analyze_button:
                    req_skills = set([s.strip().lower() for s in required_skills_input.split(',') if s.strip()])
                    cand_skills = set([s.strip().lower() for s in candidate_skills_input.split(',') if s.strip()])

                    matched_skills = req_skills.intersection(cand_skills)
                    missing_skills = req_skills.difference(cand_skills)
                    additional_skills = cand_skills.difference(req_skills)

                    st.markdown("#### Analysis Results:")
                    if matched_skills:
                        st.success(f"✅ **Matched Skills:** {', '.join(matched_skills).title()}")
                    else:
                        st.warning("No direct skill matches found.")

                    if missing_skills:
                        st.error(f"❌ **Missing Skills:** {', '.join(missing_skills).title()}")
                        st.markdown("##### Suggested Learning Resources for Missing Skills:")
                        for skill in missing_skills:
                            st.write(
                                f"- For **{skill.title()}**: [Coursera Course](https://www.coursera.org/courses?query={skill.replace(' ', '%20')}), [Udemy Course](https://www.udemy.com/courses/search/?src=ukw&q={skill.replace(' ', '%20')}) (Mock Links)")
                    else:
                        st.info("Candidate possesses all required skills!")

                    if additional_skills:
                        st.info(
                            f"💡 **Additional Skills (not required but present):** {', '.join(additional_skills).title()}")

            st.markdown("---")
            st.subheader("Role Skill Requirements Builder")
            st.info("Define and categorize skills required for a new role.")

            new_role_name = st.text_input("New Role Name", "Senior AI Engineer", key="new_role_skill_builder")
            core_skills = st.text_area("Core Skills (comma-separated)", "Deep Learning, Python, TensorFlow, PyTorch",
                                       key="core_skills_builder")
            soft_skills = st.text_area("Soft Skills (comma-separated)", "Communication, Teamwork, Problem Solving",
                                       key="soft_skills_builder")

            if st.button("Build Skill Profile", key="build_skill_profile_button"):
                st.success(f"Skill profile built for **{new_role_name}**!")
                st.write(f"**Core Skills:** {core_skills}")
                st.write(f"**Soft Skills:** {soft_skills}")
                st.info("This profile can be saved and used for future candidate matching.")

            st.markdown("---")
            st.subheader("Team Skill Inventory & Heatmap")
            st.info("Visualize the distribution and proficiency of key skills across your current team.")

            use_sample_skill_data = st.checkbox("Use Sample Skill Data", value=True, key="use_sample_skill_data")

            if use_sample_skill_data:
                team_skills_data = {
                    'Skill': ['Python', 'SQL', 'Cloud Computing', 'Project Management', 'Data Analysis',
                              'Communication', 'Leadership'],
                    'Proficiency (Avg)': [4.2, 3.8, 3.0, 4.5, 3.5, 4.8, 4.0],
                    'Team Members': [15, 12, 8, 10, 14, 20, 7]
                }
                team_skills_df = pd.DataFrame(team_skills_data)

                fig_team_skills = px.bar(
                    team_skills_df.sort_values('Proficiency (Avg)', ascending=False),
                    x='Proficiency (Avg)',
                    y='Skill',
                    orientation='h',
                    title='Average Team Proficiency by Skill',
                    labels={'Proficiency (Avg)': 'Average Proficiency (1-5)', 'Skill': 'Skill'},
                    color='Proficiency (Avg)',
                    color_continuous_scale=px.colors.sequential.Teal if not dark_mode else px.colors.sequential.Plasma
                )
                st.plotly_chart(fig_team_skills, use_container_width=True)
                st.caption(
                    "This chart shows average self-reported or assessed proficiency for key skills across the team.")

                st.markdown("##### Team Skill Heatmap")
                skills_for_heatmap = ['Python', 'SQL', 'Cloud Computing', 'Communication', 'Leadership']
                team_members_for_heatmap = [f"Team Member {i + 1}" for i in range(10)]

                heatmap_data = pd.DataFrame(
                    np.random.randint(1, 6, size=(len(team_members_for_heatmap), len(skills_for_heatmap))),
                    index=team_members_for_heatmap,
                    columns=skills_for_heatmap
                )

                fig_heatmap = px.imshow(
                    heatmap_data,
                    text_auto=True,
                    aspect="auto",
                    color_continuous_scale=px.colors.sequential.Greens if not dark_mode else px.colors.sequential.Viridis,
                    title="Team Skill Proficiency Heatmap (1=Low, 5=High)"
                )
                fig_heatmap.update_xaxes(side="top")
                st.plotly_chart(fig_heatmap, use_container_width=True)
                st.caption("A visual representation of individual skill strengths across the team.")
            else:
                st.info("Upload or auto-load your team skill data.")
                collection_path = f"artifacts/{FIREBASE_PROJECT_ID}/companies/{user_company}/uploads"
                doc_id = f"{user_email}_skills"

                uploaded_skill_file = st.file_uploader("Upload Skill Data (CSV/Excel)", type=["csv", "xlsx"],
                                                       key="upload_skill_data")

                if uploaded_skill_file is not None:
                    try:
                        if uploaded_skill_file.name.endswith(".csv"):
                            df_skills = pd.read_csv(uploaded_skill_file)
                        else:
                            df_skills = pd.read_excel(uploaded_skill_file, engine="openpyxl")

                        st.session_state['skill_data'] = df_skills
                        st.success(f"✅ File '{uploaded_skill_file.name}' uploaded successfully.")
                        save_dataframe_to_firestore(collection_path, doc_id, df_skills, FIREBASE_WEB_API_KEY,
                                                    FIRESTORE_BASE_URL)
                    except Exception as e:
                        st.error(f"Error reading file: {e}")

                if 'skill_data' not in st.session_state:
                    saved_df = load_dataframe_from_firestore(collection_path, doc_id, FIREBASE_WEB_API_KEY,
                                                             FIRESTORE_BASE_URL)
                    if saved_df is not None:
                        st.session_state['skill_data'] = saved_df
                        st.info("📂 Loaded your previously uploaded skill data.")
                
        with tab_compensation:
            st.subheader(" Compensation Benchmarking")
            st.info("Get estimated salary ranges based on role, experience, seniority, and location.")

            # --- File uploader (always visible) ---
            st.markdown("### Upload Compensation Data")
            collection_path = f"artifacts/{FIREBASE_PROJECT_ID}/companies/{user_company}/uploads"
            doc_id = f"{user_email}_compensation"

            new_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx", "xls"], key="upload_comp_data")

            if new_file is not None:
                try:
                    if new_file.name.endswith(".csv"):
                        df_comp = pd.read_csv(new_file)
                    elif new_file.name.endswith(".xlsx"):
                        df_comp = pd.read_excel(new_file, engine="openpyxl")
                    else:
                        df_comp = pd.read_excel(new_file, engine="xlrd")

                    st.session_state['compensation_data'] = df_comp
                    st.success(f"✅ File '{new_file.name}' uploaded successfully.")

                    # 🔹 Save to Firestore under user ID
                    save_dataframe_to_firestore(collection_path, doc_id, df_comp, FIREBASE_WEB_API_KEY,
                                                FIRESTORE_BASE_URL)

                except Exception as e:
                    st.error(f"Error reading file: {e}")

            # 🔹 Auto-load previous file if exists
            if 'compensation_data' not in st.session_state:
                saved_df = load_dataframe_from_firestore(collection_path, doc_id, FIREBASE_WEB_API_KEY,
                                                         FIRESTORE_BASE_URL)
                if saved_df is not None:
                    st.session_state['compensation_data'] = saved_df
                    st.info("📂 Loaded your previously uploaded compensation data.")

            # --- Option to remove uploaded file ---
            if 'compensation_data' in st.session_state:
                if st.button("🗑️ Remove uploaded Compensation file", key="remove_comp_file"):
                    del st.session_state['compensation_data']
                    # clear from Firestore as well
                    url = f"{FIRESTORE_BASE_URL}/documents/{collection_path}/{doc_id}?key={FIREBASE_WEB_API_KEY}"
                    try:
                        requests.delete(url)
                        st.success("✅ Compensation file removed .")
                    except:
                        st.warning("⚠️ File removed from session but Firestore cleanup may have failed.")

            # --- Decide which dataset to use ---
            use_sample_comp_data = st.checkbox("Use Sample Compensation Data", value=True, key="use_sample_comp_data")

            if not use_sample_comp_data and 'compensation_data' in st.session_state and not st.session_state[
                'compensation_data'].empty:
                comp_df = st.session_state['compensation_data']
                st.caption("📂 Using uploaded compensation data for benchmarking.")
            else:
                comp_df = MOCK_SALARY_DF
                st.caption("📂 Using built-in sample compensation data for benchmarking.")

            # --- Role, Seniority, Location options ---
            if 'Role' in comp_df.columns:
                all_roles = sorted(comp_df['Role'].dropna().unique().tolist())
                all_seniorities = sorted(comp_df['Seniority'].dropna().unique().tolist())
                all_locations = sorted(comp_df['Location'].dropna().unique().tolist())
            else:
                seniority_order = [
                    'Junior', 'Mid', 'Senior', 'Lead', 'Principal', 'Staff', 'Director',
                    'UI/UX Lead', 'QA Lead', 'Data Engineer Lead', 'Technical Architect'
                ]
                all_roles = sorted(comp_df['role'].unique().tolist())
                all_seniorities = sorted(
                    comp_df['seniority'].unique().tolist(),
                    key=lambda x: seniority_order.index(x) if x in seniority_order else len(seniority_order)
                )
                all_locations = sorted(comp_df['location'].unique().tolist())

            # --- Benchmarking form ---
            with st.form("compensation_form", clear_on_submit=False):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    selected_role = st.selectbox("Role Title", all_roles, key="comp_role")
                    selected_seniority = st.selectbox("Seniority Level", all_seniorities, key="comp_seniority")
                with col_c2:
                    years_exp_comp = st.slider("Years of Experience", 0, 20, 5, key="comp_exp")
                    selected_location = st.selectbox("Location", all_locations, key="comp_loc")

                benchmark_button = st.form_submit_button("Get Benchmark")

                if benchmark_button:
                    if 'Role' in comp_df.columns:  # uploaded dataset
                        # Flexible exp column detection
                        min_exp_col = next(
                            (c for c in comp_df.columns if c.lower() in ["min_exp", "minexp", "experience_min"]), None)
                        max_exp_col = next(
                            (c for c in comp_df.columns if c.lower() in ["max_exp", "maxexp", "experience_max"]), None)

                        if min_exp_col and max_exp_col:
                            filtered = comp_df[
                                (comp_df['Role'] == selected_role) &
                                (comp_df['Seniority'] == selected_seniority) &
                                (comp_df['Location'] == selected_location) &
                                (comp_df[min_exp_col] <= years_exp_comp) &
                                (comp_df[max_exp_col] >= years_exp_comp)
                                ]
                        else:
                            filtered = comp_df[
                                (comp_df['Role'] == selected_role) &
                                (comp_df['Seniority'] == selected_seniority) &
                                (comp_df['Location'] == selected_location)
                                ]
                    else:  # fallback to mock data
                        filtered = comp_df[
                            (comp_df['role'] == selected_role) &
                            (comp_df['seniority'] == selected_seniority) &
                            (comp_df['location'] == selected_location) &
                            (comp_df['min_exp'] <= years_exp_comp) &
                            (comp_df['max_exp'] >= years_exp_comp)
                            ]

                    if not filtered.empty:
                        st.success("✅ Benchmark data found")

                        if 'min_salary' in filtered.columns and 'max_salary' in filtered.columns:
                            benchmark_row = filtered.iloc[0]
                            base_min_orig = benchmark_row['min_salary']
                            base_max_orig = benchmark_row['max_salary']
                            avg_bonus_pct = benchmark_row.get('avg_bonus_pct', 10)
                            avg_equity_pct = benchmark_row.get('avg_equity_pct', 5)

                            avg_base_salary_orig = (base_min_orig + base_max_orig) / 2
                            total_comp_min_orig = base_min_orig + (base_min_orig * avg_bonus_pct / 100) + (
                                        base_min_orig * avg_equity_pct / 100)
                            total_comp_max_orig = base_max_orig + (base_max_orig * avg_bonus_pct / 100) + (
                                        base_max_orig * avg_equity_pct / 100)

                            st.markdown("#### Benchmark Results:")
                            st.success(
                                f"**Estimated Compensation Range for '{selected_seniority} {selected_role}' in '{selected_location}' ({years_exp_comp} yrs exp):**")
                            st.write(f"**Base Salary: ₹{base_min_orig:,.0f} - ₹{base_max_orig:,.0f} per annum**")
                            st.write(
                                f"**Total Compensation (incl. Bonus/Equity): ₹{total_comp_min_orig:,.0f} - ₹{total_comp_max_orig:,.0f} per annum (approx.)**")

                            salary_range_df = pd.DataFrame({
                                'Component': ['Base Min', 'Base Max', 'Total Comp Min', 'Total Comp Max'],
                                'Salary': [base_min_orig, base_max_orig, total_comp_min_orig, total_comp_max_orig]
                            })
                            fig_salary_range = px.bar(
                                salary_range_df,
                                x='Component',
                                y='Salary',
                                title='Estimated Compensation Breakdown',
                                labels={'Salary': 'Annual Salary (₹)'}
                            )
                            st.plotly_chart(fig_salary_range, use_container_width=True)
                        else:
                            st.dataframe(filtered)
                    else:
                        st.warning("⚠️ No match found for the selected criteria.")

        with tab_dei:
            st.subheader("Diversity, Equity, and Inclusion (DEI) Analytics")
            st.info("Visualize and analyze diversity metrics within your candidate pipeline or workforce.")

            # --- File uploader (always visible) ---
            st.markdown("### Upload DEI Data")
            collection_path = f"artifacts/{FIREBASE_PROJECT_ID}/companies/{user_company}/uploads"
            doc_id = f"{user_email}_dei"

            new_dei_file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx", "xls"], key="upload_dei_data")

            if new_dei_file is not None:
                try:
                    if new_dei_file.name.endswith(".csv"):
                        df_dei = pd.read_csv(new_dei_file)
                    elif new_dei_file.name.endswith(".xlsx"):
                        df_dei = pd.read_excel(new_dei_file, engine="openpyxl")
                    else:
                        df_dei = pd.read_excel(new_dei_file, engine="xlrd")

                    st.session_state['dei_data'] = df_dei
                    st.success(f"✅ File '{new_dei_file.name}' uploaded successfully.")

                    # 🔹 Save to Firestore
                    save_dataframe_to_firestore(collection_path, doc_id, df_dei, FIREBASE_WEB_API_KEY,
                                                FIRESTORE_BASE_URL)
                except Exception as e:
                    st.error(f"Error reading file: {e}")

            # 🔹 Auto-load previous DEI file if exists
            if 'dei_data' not in st.session_state:
                saved_dei_df = load_dataframe_from_firestore(collection_path, doc_id, FIREBASE_WEB_API_KEY,
                                                             FIRESTORE_BASE_URL)
                if saved_dei_df is not None:
                    st.session_state['dei_data'] = saved_dei_df
                    st.info("📂 Loaded your previously uploaded DEI data.")

            # --- Option to remove uploaded DEI file ---
            if 'dei_data' in st.session_state:
                if st.button("🗑️ Remove uploaded DEI file", key="remove_dei_file"):
                    del st.session_state['dei_data']
                    # clear from Firestore as well
                    url = f"{FIRESTORE_BASE_URL}/documents/{collection_path}/{doc_id}?key={FIREBASE_WEB_API_KEY}"
                    try:
                        requests.delete(url)
                        st.success("✅ DEI file removed .")
                    except:
                        st.warning("⚠️ File removed from session but Firestore cleanup may have failed.")

            # --- Use DEI DataFrame if available ---
            dei_df = st.session_state.get('dei_data')

            # --- Gender Distribution ---
            st.write("#### Candidate Gender Distribution")
            if dei_df is not None and 'Gender' in dei_df.columns:
                gender_counts = dei_df['Gender'].value_counts().reset_index()
                gender_counts.columns = ['Gender', 'Count']
                fig_gender = px.pie(
                    gender_counts,
                    values='Count',
                    names='Gender',
                    title='Applicant Gender Breakdown'
                )
            else:
                gender_data = pd.DataFrame({
                    'Gender': ['Male', 'Female', 'Non-binary', 'Prefer not to say'],
                    'Count': [np.random.randint(50, 150), np.random.randint(40, 120),
                              np.random.randint(5, 20), np.random.randint(10, 30)]
                })
                fig_gender = px.pie(
                    gender_data,
                    values='Count',
                    names='Gender',
                    title='Applicant Gender Breakdown',
                    color_discrete_sequence=px.colors.qualitative.Pastel if not dark_mode else px.colors.qualitative.Dark2
                )
            st.plotly_chart(fig_gender, use_container_width=True)

            # --- Age Distribution ---
            st.write("#### Candidate Age Group Distribution")
            if dei_df is not None and 'Age Group' in dei_df.columns:
                age_counts = dei_df['Age Group'].value_counts().reset_index()
                age_counts.columns = ['Age Group', 'Count']
                fig_age = px.bar(
                    age_counts,
                    x='Age Group',
                    y='Count',
                    title='Applicant Age Group Distribution',
                    color='Count',
                    color_continuous_scale=px.colors.sequential.Viridis if not dark_mode else px.colors.sequential.Cividis
                )
            else:
                age_data = pd.DataFrame({
                    'Age Group': ['18-24', '25-34', '35-44', '45-54', '55+'],
                    'Count': [np.random.randint(30, 80), np.random.randint(70, 180),
                              np.random.randint(50, 100), np.random.randint(20, 60),
                              np.random.randint(10, 30)]
                })
                fig_age = px.bar(
                    age_data,
                    x='Age Group',
                    y='Count',
                    title='Applicant Age Group Distribution',
                    color='Count',
                    color_continuous_scale=px.colors.sequential.Viridis if not dark_mode else px.colors.sequential.Cividis
                )
            st.plotly_chart(fig_age, use_container_width=True)

            # --- Department Diversity ---
            st.write("#### Diversity by Department")
            if dei_df is not None and 'Department' in dei_df.columns:
                dept_grouped = dei_df.groupby('Department').size().reset_index(name='Count')
                fig_dept_diversity = px.bar(
                    dept_grouped,
                    x='Department',
                    y='Count',
                    title='Candidate Distribution by Department',
                    color='Count',
                    color_continuous_scale=px.colors.sequential.Viridis if not dark_mode else px.colors.sequential.Cividis
                )
            else:
                department_diversity_data = pd.DataFrame({
                    'Department': ['Engineering', 'Sales', 'HR', 'Marketing', 'Product'],
                    'Female Representation (%)': [np.random.uniform(20, 40), np.random.uniform(30, 50),
                                                  np.random.uniform(50, 70), np.random.uniform(40, 60),
                                                  np.random.uniform(25, 45)],
                    'Underrepresented Groups (%)': [np.random.uniform(10, 25), np.random.uniform(15, 30),
                                                    np.random.uniform(10, 20), np.random.uniform(12, 28),
                                                    np.random.uniform(8, 22)],
                })
                fig_dept_diversity = px.bar(
                    department_diversity_data,
                    x='Department',
                    y=['Female Representation (%)', 'Underrepresented Groups (%)'],
                    barmode='group',
                    title='Diversity Metrics by Department',
                    labels={'value': 'Percentage', 'variable': 'Diversity Metric'},
                    
                )
            st.plotly_chart(fig_dept_diversity, use_container_width=True)

            # --- Hiring Funnel Diversity ---
            st.markdown("---")
            st.subheader("Hiring Funnel Diversity Breakdown")
            if dei_df is not None and {'Stage', 'Total', 'Female', 'Underrepresented Groups'}.issubset(dei_df.columns):
                funnel_data = dei_df.copy()
                funnel_data['Female %'] = (funnel_data['Female'] / funnel_data['Total'] * 100).round(1)
                funnel_data['URG %'] = (funnel_data['Underrepresented Groups'] / funnel_data['Total'] * 100).round(1)
            else:
                funnel_data = pd.DataFrame({
                    'Stage': ['Applicants', 'Screened', 'Interviewed', 'Offered', 'Hired'],
                    'Total': [1000, 500, 100, 20, 10],
                    'Female': [400, 200, 40, 8, 4],
                    'Underrepresented Groups': [150, 70, 15, 3, 2]
                })
                funnel_data['Female %'] = (funnel_data['Female'] / funnel_data['Total'] * 100).round(1)
                funnel_data['URG %'] = (funnel_data['Underrepresented Groups'] / funnel_data['Total'] * 100).round(1)

            fig_funnel = px.line(
                funnel_data,
                x='Stage',
                y=['Female %', 'URG %'],
                title='Diversity Percentage Across Hiring Funnel',
                labels={'value': 'Percentage (%)', 'variable': 'Diversity Group'},
                markers=True,
                
            )
            st.plotly_chart(fig_funnel, use_container_width=True)
            st.dataframe(funnel_data[['Stage', 'Total', 'Female %', 'URG %']], use_container_width=True,
                         hide_index=True)

            # --- Pay Equity ---
            st.markdown("---")
            st.subheader("Pay Equity Analysis")
            st.info("Analyze pay differences across demographic groups for similar roles.")

            if dei_df is not None and {'Gender', 'Salary'}.issubset(dei_df.columns):
                if st.button("Run Pay Equity Analysis", key="run_pay_equity_button"):
                    avg_salary = dei_df.groupby('Gender')['Salary'].mean().reset_index()
                    st.dataframe(avg_salary)
                    st.success("✅ Pay equity analysis generated from uploaded data.")
            else:
                gender_pay_gap = np.random.uniform(-5, 5)
                urg_pay_gap = np.random.uniform(-3, 3)

                if st.button("Run Pay Equity Analysis", key="run_pay_equity_button"):
                    st.markdown("##### Pay Equity Report:")
                    st.write(
                        f"- **Gender Pay Gap (Female vs. Male):** **{gender_pay_gap:.2f}%** (positive means male earns more)")
                    st.write(
                        f"- **Underrepresented Groups Pay Gap:** **{urg_pay_gap:.2f}%** (positive means non-URG earns more)")

                    if abs(gender_pay_gap) > 2 or abs(urg_pay_gap) > 2:
                        st.warning(
                            "⚠️ **Action Recommended:** Data indicates potential pay disparities. Further investigation is advised.")
                    else:
                        st.success("✅ Pay appears generally equitable based on available data.")
                    st.caption("_This analysis does not account for all complex factors in real pay equity analysis._")

            st.markdown("---")
            st.write(
                "More DEI metrics (e.g., ethnicity, disability status) and bias detection features could be added here.")

            # --- JD Bias Detection ---
            st.subheader("Job Description Bias Detection")
            st.info("Analyze your job description for potentially biased language.")
            jd_text_for_bias = st.text_area(
                "Paste Job Description Text for Bias Check:",
                "We are seeking a highly motivated and aggressive individual to lead our sales team. Must be a rockstar with a proven track record.",
                height=150,
                key="jd_bias_check"
            )

            if st.button("Check for Bias", key="check_bias_button"):
                biased_terms = []
                bias_score = 0

                gender_coded = {
                    "aggressive": "masculine", "dominant": "masculine", "leader": "masculine",
                    "competitive": "masculine",
                    "nurturing": "feminine", "supportive": "feminine", "collaborative": "feminine",
                    "assertive": "masculine",
                    "independent": "masculine", "analytical": "masculine", "compassionate": "feminine",
                    "cooperative": "feminine"
                }
                for term, gender in gender_coded.items():
                    if term in jd_text_for_bias.lower():
                        biased_terms.append(f"{term} ({gender}-coded)")
                        bias_score += 1

                other_biased = {
                    "rockstar": "can imply age/culture bias", "ninja": "can imply culture bias",
                    "guru": "can imply age bias",
                    "digital native": "age bias", "young": "age bias", "energetic": "age bias",
                    "millennial": "age bias",
                    "fresh graduate": "age bias",
                    "cultural fit": "can lead to homogeneity, consider 'values alignment'",
                    "native speaker": "ethnicity/origin bias",
                    "global mindset": "can be used neutrally, but check context"
                }
                for term, reason in other_biased.items():
                    if term in jd_text_for_bias.lower():
                        biased_terms.append(f"{term} ({reason})")
                        bias_score += 1

                if biased_terms:
                    st.warning("⚠️ Potential biased language detected:")
                    for term in biased_terms:
                        st.write(f"- `{term}`: Consider using more neutral alternatives.")
                    st.markdown(
                        "Suggested alternatives: 'driven', 'high-achieving', 'expert', 'specialist', 'innovative', 'team-oriented', 'values alignment', 'proficient', 'experienced'.")
                    st.error(f"**Overall Bias Score:** {bias_score} (Higher score indicates more bias)")
                else:
                    st.success("✅ No obvious biased language detected in this text. Great job!")
                    st.info(f"**Overall Bias Score:** {bias_score}")

    with tab_scheduling:
        st.subheader("Automated Interview Scheduling")
        st.info("Streamline your interview process by automating scheduling, reminders, and feedback collection. .")
        
        st.markdown("---")
        st.subheader("📧 Email Configuration")
        
        
        # --- HARDCODED GMAIL CREDENTIALS (REPLACE THESE PLACEHOLDERS) ---
        gmail_address = "screenerpro.ai@gmail.com"
        gmail_app_password = "udwi life nbdv kgdt"
        # --- END HARDCODED GMAIL CREDENTIALS ---

        st.session_state.gmail_address = gmail_address
        st.session_state.gmail_app_password = gmail_app_password
        
        # --- Manage Interviewers Section ---
        st.markdown("---")
        with st.expander("👤 Manage Interviewers"):
            st.markdown("##### Add New Interviewer")
            with st.form("add_interviewer_form", clear_on_submit=True):
                new_interviewer_name = st.text_input("Interviewer Name", key="new_interviewer_name_input")
                new_interviewer_email = st.text_input("Interviewer Email", help="This email will receive interview invites.", key="new_interviewer_email_input")
                new_interviewer_general_availability = st.text_input("General Availability (e.g., Mon-Fri 9 AM - 5 PM)", key="new_interviewer_availability_input")
                
                add_interviewer_button = st.form_submit_button("Add Interviewer")

                if add_interviewer_button:
                    if new_interviewer_name and new_interviewer_email:
                        interviewer_data = {
                            "name": new_interviewer_name,
                            "email": new_interviewer_email,
                            "general_availability": new_interviewer_general_availability,
                            "timestamp": datetime.now()
                        }
                        doc_id = new_interviewer_email.replace('.', '_').replace('@', '_') 
                        success, response = save_document_to_firestore(
                            f"artifacts/{FIREBASE_PROJECT_ID}/companies/{user_company}/interviewers", 
                            doc_id,
                            interviewer_data, FIREBASE_WEB_API_KEY, FIRESTORE_BASE_URL
                        )
                        if success:
                            st.success(f"Interviewer '{new_interviewer_name}' added successfully to Firebase!")
                            st.session_state.refresh_advanced_data = True
                            st.rerun() 
                        else:
                            st.error(f"Failed to add interviewer: {response}")
                    else:
                        st.warning("Please provide interviewer name and email.")
            
            st.markdown("##### Existing Interviewers")
            if st.session_state.user_interviewers:
                interviewer_df = pd.DataFrame(st.session_state.user_interviewers)
                st.dataframe(interviewer_df[['name', 'email', 'general_availability']], use_container_width=True, hide_index=True)
            else:
                st.info("No interviewers added yet.")

        # --- Schedule a New Interview Form ---
        st.markdown("---")
        with st.form("interview_scheduling_form", clear_on_submit=True):
            st.markdown("##### Schedule a New Interview")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                candidate_name = st.text_input("Candidate Name", key="sched_cand_name")
                candidate_email = st.text_input("Candidate Email", key="sched_cand_email")
                interview_type = st.selectbox("Interview Type", ["Initial Screen", "Technical Interview (Round 1)", "Technical Interview (Round 2)", "Hiring Manager Interview", "Final Round"], key="sched_interview_type")
            
            with col_s2:
                interviewer_options = ["Select Interviewer"] + [i['name'] for i in st.session_state.user_interviewers]
                selected_interviewer_name = st.selectbox("Select Interviewer", interviewer_options, key="sched_interviewer_name_select")

                selected_interviewer_email = ""
                if selected_interviewer_name != "Select Interviewer":
                    for interviewer in st.session_state.user_interviewers:
                        if interviewer['name'] == selected_interviewer_name:
                            selected_interviewer_email = interviewer['email']
                            break
                    st.text_input("Interviewer Email (Auto-filled)", value=selected_interviewer_email, disabled=True, key="sched_interviewer_email_display")
                else:
                    st.text_input("Interviewer Email (Auto-filled)", value="", disabled=True, key="sched_interviewer_email_display_empty")

                interview_date = st.date_input("Preferred Date", min_value=datetime.now().date(), key="sched_date")
                interview_time = st.time_input("Preferred Time", value=datetime.now().time(), step=timedelta(minutes=30), key="sched_time")
            
            interview_duration = st.slider("Interview Duration (minutes)", 30, 120, 60, step=15, key="sched_duration")
            interview_notes = st.text_area("Internal Notes for Interviewers", height=80, key="sched_notes")

            schedule_button = st.form_submit_button("Schedule Interview")

            if schedule_button:
                if not candidate_name or not candidate_email or selected_interviewer_name == "Select Interviewer" or not selected_interviewer_email:
                    st.error("Please fill in all required fields (Candidate Name/Email, and select/add an Interviewer).")
                else:
                    interview_data = {
                        "candidate_name": candidate_name,
                        "candidate_email": candidate_email,
                        "interview_type": interview_type,
                        "interviewer_name": selected_interviewer_name,
                        "interviewer_email": selected_interviewer_email,
                        "interview_datetime": datetime.combine(interview_date, interview_time),
                        "duration_minutes": interview_duration,
                        "notes": interview_notes,
                        "scheduled_by": user_email,
                        "timestamp": datetime.now()
                    }
                    
                    success, response = add_document_to_firestore_collection(
                        f"artifacts/{FIREBASE_PROJECT_ID}/companies/{user_company}/interviews", interview_data, FIREBASE_WEB_API_KEY, FIRESTORE_BASE_URL
                    )

                    if success:
                        st.success(f"✅ Interview scheduled for {candidate_name} with {selected_interviewer_name} on {interview_date} at {interview_time} for {interview_duration} minutes ({interview_type}). (Data saved to Firebase)")
                        st.write("---")
                        st.markdown("##### Notification Status:")
                        
                        candidate_subject = f"Interview Invitation: {interview_type} with {selected_interviewer_name}"
                        candidate_body = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 10px; padding: 20px; background-color: #f9f9f9;">
      <h2 style="color: #2c3e50; text-align: center;">Interview Invitation</h2>
      <p>Dear <strong>{candidate_name}</strong>,</p>

      <p>We are pleased to invite you to the <strong>{interview_type}</strong> round of our hiring process.</p>

      <div style="background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 20px 0;">
        <p><strong>Interviewer:</strong> {selected_interviewer_name}</p>
        <p><strong>Date:</strong> {interview_date.strftime('%A, %B %d, %Y')}</p>
        <p><strong>Time:</strong> {interview_time.strftime('%I:%M %p')}</p>
        <p><strong>Duration:</strong> {interview_duration} minutes</p>
      </div>

      <p>We look forward to speaking with you and learning more about your skills and experience.</p>

      <p style="margin-top: 30px;">Best regards,<br>
      <strong>The HR Team</strong></p>

      <hr style="margin: 30px 0;">
      <p style="font-size: 12px; color: #888; text-align: center;">
        This is an automated email. Please do not reply directly to this message.
      </p>
    </div>
  </body>
</html>

"""
                        interviewer_subject = f"Interview Scheduled: {candidate_name} ({interview_type})"
                        interviewer_body = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 10px; padding: 20px; background-color: #f9f9f9;">
      <h2 style="color: #2c3e50; text-align: center;">New Interview Scheduled</h2>
      <p>Dear <strong>{selected_interviewer_name}</strong>,</p>

      <p>An interview has been scheduled for you. Please review the details below:</p>

      <div style="background-color: #ffffff; border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 20px 0;">
        <p><strong> Candidate:</strong> {candidate_name}</p>
        <p><strong> Candidate Email:</strong> {candidate_email}</p>
        <p><strong> Interview Type:</strong> {interview_type}</p>
        <p><strong> Date:</strong> {interview_date.strftime('%A, %B %d, %Y')}</p>
        <p><strong> Time:</strong> {interview_time.strftime('%I:%M %p')}</p>
        <p><strong> Duration:</strong> {interview_duration} minutes</p>
        <p><strong> Internal Notes:</strong> {interview_notes if interview_notes else 'N/A'}</p>
      </div>

      <p>Please make sure to add this event to your calendar.</p>

      <p style="margin-top: 30px;">Best regards,<br>
      <strong>The HR Team</strong></p>

      <hr style="margin: 30px 0;">
      <p style="font-size: 12px; color: #888; text-align: center;">
        This is an automated email. Please do not reply directly to this message.
      </p>
    </div>
  </body>
</html>
"""

                        if st.session_state.gmail_address and st.session_state.gmail_app_password:
                            try:
                                st.info("📨 Sending real interview emails via Gmail...")

                                send_actual_email(
                                    candidate_email,
                                    candidate_subject,
                                    candidate_body,
                                    st.session_state.gmail_address,
                                    st.session_state.gmail_app_password
                                )

                                send_actual_email(
                                    selected_interviewer_email,
                                    interviewer_subject,
                                    interviewer_body,
                                    st.session_state.gmail_address,
                                    st.session_state.gmail_app_password
                                )

                                st.success("✅ Emails sent successfully to candidate and interviewer!")
                            except Exception as e:
                                st.error(f"❌ Failed to send emails: {str(e)}")
                        else:
                            st.info("Emails will be simulated. To send real emails, please configure valid Gmail credentials in the code.")
                            st.info(f"📧 **Simulated Email to Candidate ({candidate_email}):** Your interview for {interview_type} is scheduled for {interview_date.strftime('%Y-%m-%d')} at {interview_time.strftime('%I:%M %p')}.")
                            st.info(f"📧 **Simulated Calendar Invite to Interviewer ({selected_interviewer_email}):** Interview for {candidate_name} on {interview_date.strftime('%Y-%m-%d')} at {interview_time.strftime('%I:%M %p')}.")

                        st.success("Reminders will be sent automatically 24 hours prior.")
                        st.session_state.refresh_advanced_data = True
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to save interview to Firebase: {response}")


        st.markdown("---")
        st.subheader("Interviewer Availability")
        st.info("View availability for interviewers to help with manual scheduling.")
        
        interviewer_avail_options = ["Select Interviewer"] + [i['name'] for i in st.session_state.user_interviewers]
        selected_avail_interviewer = st.selectbox("Select Interviewer", interviewer_avail_options, key="interviewer_avail_select")
        check_date = st.date_input("Check Availability for Date", min_value=datetime.now().date(), key="avail_check_date")

        if st.button("Check Availability", key="check_avail_button"):
            if selected_avail_interviewer == "Select Interviewer":
                st.warning("Please select an interviewer to check availability.")
            else:
                interviewer_general_avail = "N/A"
                selected_interviewer_email_for_avail = ""
                for interviewer in st.session_state.user_interviewers:
                    if interviewer['name'] == selected_avail_interviewer:
                        interviewer_general_avail = interviewer.get('general_availability', 'N/A')
                        selected_interviewer_email_for_avail = interviewer['email']
                        break

                st.markdown(f"##### Availability for {selected_avail_interviewer} on {check_date}:")
                st.write(f"**General Availability:** {interviewer_general_avail}")
                
                conflicting_interviews = []
                for interview in st.session_state.user_interviews:
                    if interview.get('interviewer_email') == selected_interviewer_email_for_avail and \
                       interview.get('interview_datetime').date() == check_date:
                        conflicting_interviews.append(interview)
                
                if conflicting_interviews:
                    st.warning("⚠️ **Conflicts Found!** The interviewer has the following interviews scheduled on this date:")
                    for conflict in conflicting_interviews:
                        st.write(f"- {conflict['interview_datetime'].strftime('%I:%M %p')} for {conflict['candidate_name']} ({conflict['interview_type']})")
                else:
                    st.success("✅ No direct conflicts found with scheduled interviews on this date.")

                if "Mon-Fri 9 AM - 5 PM" in interviewer_general_avail:
                    st.success("✅ Available: 10:00 AM - 12:00 PM, 02:00 PM - 04:00 PM (based on general availability, check conflicts above)")
                elif "Flexible" in interviewer_general_avail:
                    st.info("⚠️ Flexible availability, please confirm directly with interviewer.")
                else:
                    st.warning("⚠️ Limited Availability: Please contact directly for specific times.")

        st.markdown("---")
        st.subheader("Automated Reminders Configuration")
        st.info("Configure automated email reminders for candidates and interviewers.")
        
        reminder_candidate_days = st.slider("Send Candidate Reminder (days before interview)", 0, 3, 1, key="rem_cand_days")
        reminder_interviewer_hours = st.slider("Send Interviewer Reminder (hours before interview)", 0, 48, 24, key="rem_int_hours")
        
        if st.button("Save Reminder Settings", key="save_reminders_button"):
            st.success(f"Reminder settings saved: Candidate {reminder_candidate_days} day(s) before, Interviewer {reminder_interviewer_hours} hour(s) before.")


        st.markdown("---")
        st.subheader("🗓️ Interview Calendar View")
        st.info("View all scheduled interviews in a calendar-like format.")

        if st.session_state.user_interviews:
            interviews_df = pd.DataFrame(st.session_state.user_interviews)
            
            interviews_df['interview_datetime'] = pd.to_datetime(interviews_df['interview_datetime'])
            interviews_df['interview_date'] = interviews_df['interview_datetime'].dt.date

            col_cal1, col_cal2 = st.columns(2)
            with col_cal1:
                start_date = st.date_input("Start Date", value=date.today(), key="calendar_start_date")
            with col_cal2:
                end_date = st.date_input("End Date", value=date.today() + timedelta(days=30), key="calendar_end_date")

            filtered_interviews = interviews_df[
                (interviews_df['interview_date'] >= start_date) &
                (interviews_df['interview_date'] <= end_date)
            ].sort_values(by='interview_datetime')

            if not filtered_interviews.empty:
                st.markdown("---")
                st.markdown("##### Scheduled Interviews:")
                
                for interview_date, group in filtered_interviews.groupby('interview_date'):
                    st.markdown(f"** {interview_date.strftime('%A, %B %d, %Y')}**")
                    for _, row in group.iterrows():
                        interview_time_str = row['interview_datetime'].strftime('%I:%M %p')
                        st.markdown(f"- **{interview_time_str}** - **{row['candidate_name']}** ({row['interview_type']}) with {row['interviewer_name']}")
                        if row['notes']:
                            st.caption(f"    _Notes: {row['notes']}_")
                    st.markdown("---")
            else:
                st.info(f"No interviews scheduled between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}.")
        else:
            st.info("No interviews scheduled yet. Schedule one above to see it here!")

        st.markdown("---")
        st.subheader("Upcoming Interviews (List View)")
        st.info("View your upcoming interview schedule from Firebase.")

        if st.session_state.user_interviews:
            upcoming_interviews = [
                i for i in st.session_state.user_interviews
                if i.get('interview_datetime', datetime.min).date() >= date.today()
            ]
            sorted_interviews = sorted(upcoming_interviews, key=lambda x: x.get('interview_datetime', datetime.min))
            
            if sorted_interviews:
                display_interviews = []
                for interview in sorted_interviews:
                    display_interviews.append({
                        "Candidate": interview.get('candidate_name', 'N/A'),
                        "Role": interview.get('interview_type', 'N/A'),
                        "Interviewer": interview.get('interviewer_name', 'N/A'),
                        "Date": interview.get('interview_datetime', datetime.min).strftime("%Y-%m-%d"),
                        "Time": interview.get('interview_datetime', datetime.min).strftime("%I:%M %p")
                    })
                st.dataframe(pd.DataFrame(display_interviews), use_container_width=True, hide_index=True)
            else:
                st.info("No upcoming interviews found.")
        else:
            st.info("No upcoming interviews scheduled yet.")

        st.markdown("---")
        st.subheader("Interview Feedback Collection & Trends")
        st.info("Submit and review interview feedback easily, and see overall trends. .")

        candidate_options = ["New Candidate..."]
        if st.session_state.user_interviews:
            candidate_options.extend(sorted(list(set([i.get('candidate_name') for i in st.session_state.user_interviews if i.get('candidate_name')]))))

        feedback_candidate = st.selectbox("Select Candidate for Feedback", candidate_options, key="feedback_cand_select")
        if feedback_candidate == "New Candidate...":
            feedback_candidate_name = st.text_input("Enter Candidate Name", key="new_feedback_cand_name")
        else:
            feedback_candidate_name = feedback_candidate

        feedback_interviewer = st.text_input("Your Name (Interviewer)", value=st.session_state.get('username', 'Anonymous'), key="feedback_interviewer_name")
        feedback_rating = st.slider("Overall Rating (1-5, 5=Strong Hire)", 1, 5, 3, key="feedback_rating")
        
        template_options = ["None (Free Text Feedback)"] + [t['name'] for t in st.session_state.interview_templates]
        selected_feedback_template_name = st.selectbox("Select Interview Template (Optional)", options=template_options, key="feedback_template_select")

        feedback_comments = ""
        structured_responses_list = []
        selected_template_id = None

        if selected_feedback_template_name != "None (Free Text Feedback)":
            selected_template = next((t for t in st.session_state.interview_templates if t['name'] == selected_feedback_template_name), None)
            if selected_template:
                selected_template_id = selected_template['id']
                st.markdown("---")
                st.markdown("##### Structured Feedback Questions:")
                for section in selected_template.get('sections', []):
                    st.markdown(f"**{section.get('section_title', 'N/A')}**")
                    for question in section.get('questions', []):
                        question_hash = hashlib.md5(f"{selected_template_id}_{question}".encode()).hexdigest()
                        
                        col_q_rating, col_q_comment = st.columns([0.3, 0.7])
                        with col_q_rating:
                            q_rating = st.slider(f"Rating for: {question}", 1, 5, 3, key=f"rating_{question_hash}")
                        with col_q_comment:
                            q_comment = st.text_area(f"Comments for: {question}", height=50, key=f"comment_{question_hash}")
                        
                        structured_responses_list.append({
                            "question": question,
                            "rating": q_rating,
                            "comment": q_comment
                        })
                st.markdown("---")
            else:
                st.warning("Selected template not found.")
                feedback_comments = st.text_area("Comments (Free Text)", height=100, key="feedback_comments_freetext")
        else:
            feedback_comments = st.text_area("Comments (Free Text)", height=100, key="feedback_comments_freetext")


        if st.button("Submit Feedback", key="submit_feedback_button"):
            if feedback_candidate_name and feedback_interviewer:
                feedback_data = {
                    "candidate_name": feedback_candidate_name,
                    "interviewer_name": feedback_interviewer,
                    "rating": feedback_rating,
                    "timestamp": datetime.now()
                }
                if selected_template_id:
                    feedback_data["template_id"] = selected_template_id
                    feedback_data["structured_responses"] = structured_responses_list
                else:
                    feedback_data["comments"] = feedback_comments

                success, response = add_document_to_firestore_collection(
                    f"artifacts/{FIREBASE_PROJECT_ID}/companies/{user_company}/interview_feedback", feedback_data, FIREBASE_WEB_API_KEY, FIRESTORE_BASE_URL
                )
                if success:
                    st.success(f"Feedback submitted for {feedback_candidate_name} by {feedback_interviewer} with rating {feedback_rating}. (Data saved to Firebase)")
                    st.session_state.refresh_advanced_data = True
                    st.rerun()
                else:
                    st.error(f"❌ Failed to save feedback to Firebase: {response}")
            else:
                st.warning("Please fill in Candidate Name and Interviewer Name.")

        st.markdown("---")
        st.subheader("Overall Interview Feedback Trends")
        if st.session_state.user_feedback:
            feedback_ratings = [f.get('rating') for f in st.session_state.user_feedback if f.get('rating') is not None]
            if feedback_ratings:
                feedback_trend_data = pd.DataFrame({'Rating': feedback_ratings})
                feedback_counts = feedback_trend_data['Rating'].value_counts().sort_index().reset_index()
                feedback_counts.columns = ['Rating', 'Count']

                fig_feedback_trend = px.bar(
                    feedback_counts,
                    x='Rating',
                    y='Count',
                    title='Distribution of Interview Ratings',
                    labels={'Count': 'Number of Ratings', 'Rating': 'Rating (1-5)'},
                    color='Count',
                    color_continuous_scale=px.colors.sequential.Plasma if dark_mode else px.colors.sequential.Viridis
                )
                st.plotly_chart(fig_feedback_trend, use_container_width=True)
                st.caption("This chart shows the aggregated distribution of interview ratings from Firebase.")
            else:
                st.info("No feedback ratings available to display trends.")
        else:
            st.info("No interview feedback data available in Firebase yet.")

        st.markdown("---")
        st.subheader("Interviewer Performance Analysis (Simulated)")
        st.info("Analyze average ratings given by each interviewer and identify potential training needs.")

        if st.session_state.user_feedback:
            feedback_df = pd.DataFrame(st.session_state.user_feedback)
            if 'interviewer_name' in feedback_df.columns and 'rating' in feedback_df.columns:
                interviewer_avg_ratings = feedback_df.groupby('interviewer_name')['rating'].mean().reset_index()
                interviewer_avg_ratings.columns = ['Interviewer', 'Average Rating']
                interviewer_avg_ratings = interviewer_avg_ratings.sort_values(by='Average Rating', ascending=False)

                st.dataframe(interviewer_avg_ratings, use_container_width=True, hide_index=True)

                st.markdown("##### Potential Training Needs / Bias Flags:")
                flagged_interviewers = []
                for _, row in interviewer_avg_ratings.iterrows():
                    if row['Average Rating'] >= 4.5:
                        flagged_interviewers.append(f"- **{row['Interviewer']}**: Consistently high ratings. Consider calibration training or reviewing their rubric interpretation.")
                    elif row['Average Rating'] <= 2.0:
                        flagged_interviewers.append(f"- **{row['Interviewer']}**: Consistently low ratings. Consider training on positive feedback, constructive criticism, or role alignment.")
                
                if flagged_interviewers:
                    for flag in flagged_interviewers:
                        st.warning(flag)
                else:
                    st.success("✅ Interviewer ratings appear well-calibrated (based on simple rules).")
            else:
                st.info("Interviewer name or rating data not available in feedback.")
        else:
            st.info("No interview feedback data available for interviewer analysis.")
        
        st.markdown("---")
        st.subheader("Feedback Consistency Analysis (Simulated)")
        st.info("Analyze the consistency of feedback for a candidate when reviewed by multiple interviewers using the same template.")

        candidates_with_multi_template_feedback = []
        if st.session_state.user_feedback:
            feedback_df = pd.DataFrame(st.session_state.user_feedback)
            
            if 'template_id' not in feedback_df.columns:
                feedback_df['template_id'] = None
            if 'structured_responses' not in feedback_df.columns:
                feedback_df['structured_responses'] = None

            templated_feedback_df = feedback_df[(feedback_df['template_id'].notna()) & (feedback_df['rating'].notna()) & (feedback_df['structured_responses'].notna())]
            
            grouped_feedback = templated_feedback_df.groupby(['candidate_name', 'template_id'])
            
            for (candidate, template_id), group in grouped_feedback:
                if len(group) > 1:
                    candidates_with_multi_template_feedback.append({
                        'candidate_name': candidate,
                        'template_id': template_id,
                        'overall_ratings': group['rating'].tolist(),
                        'interviewer_names': group['interviewer_name'].tolist(),
                        'structured_responses_per_interviewer': group['structured_responses'].tolist()
                    })
        
        if candidates_with_multi_template_feedback:
            consistency_options = [f"{c['candidate_name']} (Template: {next((t['name'] for t in st.session_state.interview_templates if t['id'] == c['template_id']), 'Unknown')})" for c in candidates_with_multi_template_feedback]
            selected_consistency_candidate = st.selectbox("Select Candidate for Consistency Analysis", consistency_options, key="consistency_cand_select")

            if selected_consistency_candidate:
                selected_data = next((c for c in candidates_with_multi_template_feedback if f"{c['candidate_name']} (Template: {next((t['name'] for t in st.session_state.interview_templates if t['id'] == c['template_id']), 'Unknown')})" == selected_consistency_candidate), None)
                
                if selected_data:
                    overall_ratings = selected_data['overall_ratings']
                    interviewer_names = selected_data['interviewer_names']
                    structured_responses_per_interviewer = selected_data['structured_responses_per_interviewer']
                    
                    st.markdown(f"##### Overall Ratings for {selected_data['candidate_name']} by multiple interviewers:")
                    for i, rating in enumerate(overall_ratings):
                        st.write(f"- **{interviewer_names[i]}**: Overall Rating {rating}")
                    
                    std_dev_overall = np.std(overall_ratings)
                    st.write(f"**Standard Deviation of Overall Ratings:** {std_dev_overall:.2f}")

                    if std_dev_overall > 0.8:
                        st.warning("⚠️ **Overall Inconsistency Detected!** The standard deviation of overall ratings is high. Consider reviewing feedback with interviewers for calibration.")
                    else:
                        st.success("✅ Overall feedback ratings appear consistent for this candidate.")

                    st.markdown("---")
                    st.markdown("##### Per-Question Consistency:")
                    all_questions = set()
                    for responses_list in structured_responses_per_interviewer:
                        for item in responses_list:
                            all_questions.add(item['question'])
                    
                    if all_questions:
                        for q in sorted(list(all_questions)):
                            question_ratings = []
                            for responses_list in structured_responses_per_interviewer:
                                for item in responses_list:
                                    if item['question'] == q and item['rating'] is not None:
                                        question_ratings.append(item['rating'])
                            
                            if len(question_ratings) > 1:
                                std_dev_q = np.std(question_ratings)
                                st.write(f"**'{q}' Ratings:** {question_ratings} (Std Dev: {std_dev_q:.2f})")
                                if std_dev_q > 0.8:
                                    st.warning(f"  ⚠️ Inconsistency for '{q}': High standard deviation.")
                                else:
                                    st.success(f"  ✅ Consistent for '{q}'.")
                            elif len(question_ratings) == 1:
                                st.info(f"  Single rating for '{q}': {question_ratings[0]}. Cannot calculate consistency.")
                            else:
                                st.info(f"  No ratings recorded for '{q}'.")
                    else:
                        st.info("No structured questions found in feedback for detailed consistency analysis.")

                else:
                    st.info("No consistency data for selected candidate.")
        else:
            st.info("No candidates with multiple structured feedback entries found for consistency analysis. To enable this feature, ensure you submit feedback for the same candidate using the same interview template multiple times (e.g., by different interviewers or in different rounds).")

        st.markdown("---")
        st.subheader("Feedback Text Bias Analysis (Simulated)")
        st.info("Analyze interview feedback comments for potentially biased language. **Note:** This is a simulated analysis. A production-ready solution would involve advanced Natural Language Processing (NLP) models or dedicated bias detection APIs.")
        feedback_text_for_bias = st.text_area("Paste Interview Feedback Text for Bias Check:", "The candidate was very aggressive in their responses, lacking a nurturing approach.", height=150, key="feedback_bias_check")
        
        if st.button("Check Feedback for Bias", key="check_feedback_bias_button"):
            biased_terms = []
            bias_score = 0
            
            # Gender-coded words (reusing from JD bias)
            gender_coded = {"aggressive": "masculine", "dominant": "masculine", "leader": "masculine", "competitive": "masculine",
                            "nurturing": "feminine", "supportive": "feminine", "collaborative": "feminine", "assertive": "masculine",
                            "independent": "masculine", "analytical": "masculine", "compassionate": "feminine", "cooperative": "feminine",
                            "strong": "masculine", "determined": "masculine", "sensitive": "feminine", "understanding": "feminine"}
            for term, gender in gender_coded.items():
                if term in feedback_text_for_bias.lower():
                    biased_terms.append(f"{term} ({gender}-coded)")
                    bias_score += 1

            # Age/culture/other words (reusing from JD bias)
            other_biased = {"rockstar": "can imply age/culture bias", "ninja": "can imply culture bias", "guru": "can imply age bias",
                            "digital native": "age bias", "young": "age bias", "energetic": "age bias", "millennial": "age bias",
                            "fresh graduate": "age bias", "cultural fit": "can lead to homogeneity, consider 'values alignment'",
                            "native speaker": "ethnicity/origin bias", "global mindset": "can be used neutrally, but check context",
                            "gregarious": "can imply extroversion bias", "introvert": "can imply personality bias", "extrovert": "can imply personality bias"}
            for term, reason in other_biased.items():
                if term in feedback_text_for_bias.lower():
                    biased_terms.append(f"{term} ({reason})")
                    bias_score += 1

            if biased_terms:
                st.warning("⚠️ Potential biased language detected in feedback:")
                for term in biased_terms:
                    st.write(f"- `{term}`: Consider using more neutral alternatives.")
                st.markdown("Suggested alternatives: 'driven', 'high-achieving', 'expert', 'specialist', 'innovative', 'team-oriented', 'values alignment', 'proficient', 'experienced', 'adaptable', 'empathetic', 'analytical', 'results-oriented'.")
                st.error(f"**Overall Bias Score:** {bias_score} (Higher score indicates more bias)")
            else:
                st.success("✅ No obvious biased language detected in this feedback text. Great job!")
                st.info(f"**Overall Bias Score:** {bias_score}")

        st.markdown("---")
        st.subheader("Correlation with Hiring Outcomes")
        st.info("This feature would analyze the correlation between interview scores and actual successful hiring outcomes (e.g., employee performance, retention).")
       
    with tab_interview_templates:

        # ---------- HEADER ----------
        st.markdown("""
            <div style="padding:15px; border-radius:15px;
                        background:linear-gradient(135deg,#eef2ff,#f8fafc);
                        box-shadow:0 4px 12px rgba(0,0,0,0.08);">
                <h2 style="color:#1e3a8a;">📝 Interview Template Management</h2>
                <p style="color:#475569;">Create, generate and reuse structured interview templates.</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # =======================================================
        #          ADD NEW INTERVIEW TEMPLATE
        # =======================================================
        st.markdown("""
            <div style="padding:12px; border-radius:10px;
                background:#e0f2fe; border-left:5px solid #0284c7;">
                <h4 style="color:#075985;">➕ Add New Interview Template</h4>
            </div>
        """, unsafe_allow_html=True)

        with st.form("add_interview_template_form", clear_on_submit=True):

            template_name = st.text_input(
                "Template Name",
                placeholder="e.g., Senior Software Engineer"
            )

            st.markdown("**Format (strict):**")
            st.code("Technical: Data Structures; Algorithms; System Design")

            template_sections_input = st.text_area(
                "Template Content",
                height=160,
                placeholder="Technical Skills: Python; APIs; Databases\nBehavioral: Teamwork; Ownership"
            )

            col_ai, col_save = st.columns(2)

            ai_generate = col_ai.form_submit_button(
                "✨ Generate with AI",
                use_container_width=True
            )

            save_template = col_save.form_submit_button(
                "💾 Save Template",
                use_container_width=True
            )

            # =======================================================
            #               AI GENERATION (SAFE)
            # =======================================================
            if ai_generate:
                if not template_name:
                    st.warning("Please enter a Template Name.")
                else:
                    with st.spinner("🤖 Generating interview template..."):
                        ai_output = generate_interview_template_safe(template_name)

                    st.session_state.generated_template_sections = ai_output
                    st.success("✨ Template generated successfully!")

            # =======================================================
            #               SAVE TEMPLATE
            # =======================================================
            if save_template:
                if not template_name or not template_sections_input:
                    st.warning("Template Name and Content are required.")
                else:
                    sections = []
                    valid = True

                    for line in template_sections_input.split("\n"):
                        if ":" not in line:
                            valid = False
                            break

                        sec_title, q_block = line.split(":", 1)
                        questions = [q.strip() for q in q_block.split(";") if q.strip()]

                        sections.append({
                            "section_title": sec_title.strip(),
                            "questions": questions
                        })

                    if not valid:
                        st.error("Invalid format detected. Use: Section: Q1; Q2; Q3")
                    else:
                        data = {
                            "name": template_name,
                            "sections": sections,
                            "created_at": datetime.now().isoformat()
                        }

                        doc_id = template_name.lower().replace(" ", "_")

                        success, response = save_document_to_firestore(
                            f"artifacts/{FIREBASE_PROJECT_ID}/companies/{user_company}/interview_templates",
                            doc_id,
                            data,
                            FIREBASE_WEB_API_KEY,
                            FIRESTORE_BASE_URL
                        )

                        if success:
                            st.success("Template saved successfully!")
                            st.session_state.refresh_advanced_data = True
                            st.rerun()
                        else:
                            st.error("Failed to save template.")

        # =======================================================
        #          AI GENERATED PREVIEW
        # =======================================================
        if st.session_state.get("generated_template_sections"):
            st.markdown("""
                <div style="padding:12px; border-radius:10px;
                    background:#fef9c3; border-left:5px solid #ca8a04;">
                    <h4 style="color:#854d0e;">✨ AI-Generated Template Preview</h4>
                </div>
            """, unsafe_allow_html=True)

            st.text_area(
                "Generated Template (copy & save if needed)",
                value=st.session_state.generated_template_sections,
                height=200
            )

        st.markdown("<hr>", unsafe_allow_html=True)

        # =======================================================
        #          EXISTING TEMPLATES
        # =======================================================
        st.markdown("### 📂 Your Interview Templates")

        if st.session_state.interview_templates:
            for template in st.session_state.interview_templates:

                st.markdown(f"""
                    <div style="padding:15px; margin-bottom:15px;
                                border-radius:15px; background:white;
                                border:1px solid #e2e8f0;
                                box-shadow:0 4px 10px rgba(0,0,0,0.06);">
                        <h4 style="color:#1e40af;">📘 {template.get('name')}</h4>
                """, unsafe_allow_html=True)

                for sec in template["sections"]:
                    st.markdown(f"**{sec['section_title']}**")
                    for q in sec["questions"]:
                        st.markdown(f"- {q}")

                if st.button("🗑️ Delete", key=f"delete_{template['id']}"):
                    delete_document_from_firestore(
                        f"artifacts/{FIREBASE_PROJECT_ID}/companies/{user_company}/interview_templates",
                        template["id"],
                        FIREBASE_WEB_API_KEY,
                        FIRESTORE_BASE_URL
                    )
                    st.success("Template deleted.")
                    st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

        else:
            st.info("You have no interview templates yet. Create one above!")



    tab_role_matcher, tab_batch, tab_ranking, tab_history = st.tabs([" Single Analysis", " Batch Analysis", " JD Ranking", " Data History"])

    with tab_role_matcher:

        # Optional: ReportLab for rich PDF formatting (preferred). If missing, fallback to simple PDF.
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
            REPORTLAB_AVAILABLE = True
        except Exception:
            REPORTLAB_AVAILABLE = False

        # -------------------- CONFIG & FILE PATHS --------------------
        MODEL_PATH = "role_model.pkl"
        VECTORIZER_PATH = "role_vectorizer.pkl"
        PROJECT_FILE_PATH = "/mnt/data/advanced (5).py"

        # Mock Firebase Config (Set these in a real app/Streamlit secrets)
        # Assuming a user identifier (like a UID) is available in session state for scoping.
        if 'user_uid' not in st.session_state:
            st.session_state.user_uid = "MOCK_USER_HR_123" # Use a mock UID for demonstration

        FIREBASE_PROJECT_ID = "screenerproapp" # REPLACE WITH YOUR PROJECT ID
        FIREBASE_WEB_API_KEY = "AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw" # REPLACE WITH YOUR API KEY

        # Dummy/Mock Firebase Functions
        def to_firestore_format(data):
            fields = {}
            for k, v in data.items():
                if isinstance(v, float): fields[k] = {"doubleValue": v}
                elif isinstance(v, int): fields[k] = {"integerValue": v}
                elif isinstance(v, bool): fields[k] = {"booleanValue": v}
                elif isinstance(v, str): fields[k] = {"stringValue": v}
                elif isinstance(v, list) or isinstance(v, dict): fields[k] = {"stringValue": json.dumps(v)} 
                else: fields[k] = {"stringValue": str(v)}
            return {"fields": fields}




                
            
            # Real Firebase fetch logic would go here, likely involving Firestore's query API, 
            # filtering by a 'user_uid' field.
            return pd.DataFrame()

        # Load model & vectorizer (cache in session_state)
        if "role_model" not in st.session_state:
            try:
                st.session_state.role_model = pickle.load(open(MODEL_PATH, "rb"))
                st.session_state.role_vectorizer = pickle.load(open(VECTORIZER_PATH, "rb"))
            except Exception as e:
                st.error("Failed to load model/vectorizer. Put role_model.pkl and role_vectorizer.pkl in your app folder.")
                st.write("Tried paths:", MODEL_PATH, VECTORIZER_PATH)
                st.write("Error:", e)
                st.stop()

        model = st.session_state.role_model
        vectorizer = st.session_state.role_vectorizer

        # -------------------- CSS STYLES (ENHANCED) --------------------
        st.markdown("""
            <style>
            .main-header {
                padding: 18px;
                background: linear-gradient(135deg, #4A6CFF, #8C9EFF);
                color: white;
                border-radius: 12px;
                box-shadow: 0 6px 20px rgba(74, 108, 255, 0.5); 
                margin-bottom: 25px;
                animation: slideIn 0.5s ease-out;
            }
            .result-card {
                padding: 25px;
                border: 1px solid #e0e0e0;
                border-radius: 16px; 
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1); 
                margin-top: 15px;
                background-color: #ffffff;
                transition: box-shadow 0.3s ease-in-out;
            }
            .result-card:hover {
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15); 
            }
            .skill-chip {
                display: inline-block;
                background: #eef7ff;
                color: #4A6CFF;
                padding: 4px 8px;
                border-radius: 12px;
                margin: 3px;
                font-size: 0.85em;
                font-weight: 600;
            }
            .warning-box {
                background: #fff3cd;
                color: #856404;
                border: 1px solid #ffeeba;
                padding: 12px;
                border-radius: 10px;
                margin-top: 10px;
            }
            .duplicate-box, .unreadable-box {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
                padding: 15px;
                border-radius: 10px;
                margin-top: 15px;
            }
            .unreadable-box {
                background: #e9e9e9;
                color: #333333;
                border: 1px solid #d0d0d0;
            }
            .data-history-table {
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
                border-radius: 8px;
            }
            @keyframes slideIn {
                from {opacity: 0; transform: translateY(-20px);}
                to {opacity: 1; transform: translateY(0);}
            }
            </style>
        """, unsafe_allow_html=True)
        
        # -------------------- UI HEADER --------------------
        st.markdown("<div class='main-header'><h2>🧠 Role Matcher — Premium HR Toolkit</h2><p>Upload PDF(s), paste resume/JD, get top role matches, skill-gap radar, duplicate detection, PDF report, batch export, and Firebase save.</p></div>", unsafe_allow_html=True)

        # -------------------- UTILITIES (Functionality kept same) --------------------
        def extract_text_from_pdf_bytes(pdf_bytes):
            txt = ""
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                for p in doc:
                    txt += p.get_text()
            except Exception:
                txt = ""
            return txt

        skill_bank = {
            "python","java","c++","sql","html","css","javascript","react","node",
            "excel","tableau","powerbi","analysis","reporting","statistics",
            "machine","learning","ml","ai","cloud","aws","azure","gcp",
            "docker","kubernetes","tensorflow","pytorch","nlp","spark",
            "etl","airflow","testing","selenium","recruitment","communication",
            "marketing","sales","management","strategy","design","figma"
        }

        def extract_skills_and_seniority(text):
            t = text.lower().replace("\n", " ")
            tokens = [w.strip(",.();:") for w in t.split() if len(w) > 2]
            detected_skills = sorted(list({tok for tok in tokens if tok in skill_bank}))
            seniority_map = {
                "intern": "Intern", "fresher": "Intern",
                "junior": "Junior", "entry": "Junior",
                "mid": "Mid-Level", "intermediate": "Mid-Level",
                "senior": "Senior", "lead": "Lead", "manager": "Manager",
                "principal": "Principal", "director": "Director"
            }
            detected_sen = [seniority_map[tok] for tok in tokens if tok in seniority_map]
            seniority_label = detected_sen[0] if detected_sen else "Not detected"
            return detected_skills, seniority_label

        top_k = 5 # Set default for analysis
        def analyze_resume_text(resume_text, jd_text=None, top_k=5):
            resume_text = resume_text or ""
            if not resume_text or len(resume_text.strip()) < 50: 
                return {} 

            # model prediction
            vec = vectorizer.transform([resume_text])
            probs = model.predict_proba(vec)[0]
            classes = model.classes_
            sorted_roles = sorted(zip(classes, probs), key=lambda x: x[1], reverse=True)
            top_roles = [(r, float(p)) for r, p in sorted_roles[:top_k]]
            
            # skills and seniority
            skills, seniority = extract_skills_and_seniority(resume_text)
            
            # JD match score
            jd_score = None
            if jd_text and jd_text.strip():
                jd_vec = vectorizer.transform([jd_text])
                sim = cosine_similarity(vec, jd_vec)[0][0]
                jd_score = float(sim)
                
            # missing skills
            role_skills_map = {
                "Software Engineer": ["python","java","sql","docker","kubernetes"],
                "Frontend Developer": ["html","css","javascript","react"],
                "Data Analyst": ["excel","sql","tableau","powerbi"],
                "Data Scientist": ["python","machine","learning","pandas"],
                "Recruiter": ["recruitment","communication","sourcing"]
            }
            top_role = top_roles[0][0] if top_roles else "N/A"
            missing = [s for s in role_skills_map.get(top_role, []) if s not in skills]
            
            return {
                "top_role": top_role,
                "top_prob": float(top_roles[0][1]) if top_roles else 0.0,
                "top_roles": top_roles,
                "skills": skills,
                "missing_skills": missing,
                "seniority": seniority,
                "jd_score": jd_score,
                "resume_excerpt": resume_text[:3000]
            }


        def make_skill_radar(result):
            # Radar chart for skill coverage (kept same)
            skills = result.get("skills", [])
            radar_skills = ["python","sql","ml","cloud","docker","react","excel","testing"]
            values = []
            for s in radar_skills: values.append(1.0 if s in skills else 0.0)
            values += values[:1]
            angles = np.linspace(0, 2*np.pi, len(radar_skills)+1, endpoint=True)
            fig = plt.figure(figsize=(4,4))
            ax = fig.add_subplot(111, polar=True)
            ax.plot(angles, values, linewidth=2, color="#4A6CFF")
            ax.fill(angles, values, color="#4A6CFF", alpha=0.35)
            ax.set_thetagrids(angles[:-1] * 180/np.pi, radar_skills)
            ax.set_ylim(0,1)
            buf = io.BytesIO()
            plt.tight_layout()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            return buf

        def find_duplicates(resume_texts, threshold=0.85):
            # Duplicate detection (kept same as fixed version)
            if not resume_texts: return []
            
            temp_vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
            valid_texts = [t for t in resume_texts if t and len(t.strip()) > 50]
            if not valid_texts: return []

            valid_indices = [i for i, t in enumerate(resume_texts) if t and len(t.strip()) > 50]
            vecs = temp_vectorizer.fit_transform(valid_texts)
            sims = cosine_similarity(vecs)
            
            pairs = []
            n = len(valid_texts)
            for i in range(n):
                for j in range(i+1, n):
                    sim = sims[i,j]
                    if sim >= threshold:
                        original_i = valid_indices[i]
                        original_j = valid_indices[j]
                        pairs.append((original_i, original_j, float(sim)))
            return pairs

        # --- LIVE RESULT CARD UI (with error handling) ---
        def render_result_ui(result, label="Resume"):
            if not result:
                st.error(f"❌ Analysis Failed: Could not process text from **{label}** (File may be unreadable or empty).")
                return

            st.markdown(f"###  {label} — Top match: **{result.get('top_role', 'N/A')}** ({int(result.get('top_prob', 0.0)*100)}%)")
            with st.container():
                st.markdown("<div class='result-card'>", unsafe_allow_html=True)
                col_main, col_chart = st.columns([2, 1])

                with col_main:
                    jd_score_val = result.get('jd_score')
                    if jd_score_val is not None:
                        jd_score_percent = int(jd_score_val * 100)
                        if jd_score_percent >= 70:
                            st.success(f"✅ Excellent JD Match: **{jd_score_percent}%**")
                        elif jd_score_percent >= 40:
                            st.info(f"💡 Fair JD Match: **{jd_score_percent}%**")
                        else:
                            st.error(f"❌ Poor JD Match: **{jd_score_percent}%**")
                    else:
                        st.info("No Job Description provided for matching score.")

                    st.write(f"**Seniority:** `{result.get('seniority', 'N/A')}`")

                    with st.expander(" **Role Prediction Details**", expanded=True):
                        for r,p in result.get("top_roles", []):
                            st.write(f"**{r}** — {int(p*100)}%")
                            st.progress(int(p*100))
                    
                with col_chart:
                    radar_buf = make_skill_radar(result)
                    st.image(radar_buf, caption="Core Skill Coverage", use_column_width=True)

                st.markdown("---")
                st.markdown("#### 🛠️ Skills & Gaps")
                
                skills = result.get("skills", [])
                missing_skills = result.get("missing_skills", [])
                top_role = result.get('top_role', 'N/A')

                if skills:
                    chips = "".join([f"<span class='skill-chip'>{s}</span>" for s in skills])
                    st.markdown(f"**Detected Skills:** {chips}", unsafe_allow_html=True)
                else:
                    st.write("_No technical or functional skills detected._")
                    
                if missing_skills:
                    st.markdown(f"<div class='warning-box'>⚠️ **Missing Core Skills (for {top_role}):** {', '.join(missing_skills)}</div>", unsafe_allow_html=True)
                else:
                    st.success(f"✅ Core skills covered for **{top_role}**.")

                st.markdown("---")
                
                pdf_bytes = make_pdf_bytes(result, title=f"Role Report — {label}")
                st.download_button("📥 Download Rich PDF Report", pdf_bytes, file_name=f"role_report_{top_role}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf", mime="application/pdf")
                
                st.markdown("</div>", unsafe_allow_html=True)
            
        # -------------------- LAYOUT: INPUTS --------------------
        left, mid, right = st.columns([1.1, 1, 0.9])
        with left:
            single_pdf = st.file_uploader("Upload single PDF resume", type=["pdf"], key="rm_single_pdf")
            multi_pdf = st.file_uploader("Upload multiple PDFs (batch)", type=["pdf"], accept_multiple_files=True, key="rm_multi_pdf")
        with mid:
            paste_resume = st.text_area("Or paste resume text (single)", height=200, key="rm_paste")
            st.write("")
            paste_jd = st.text_area("Paste Job Description (optional) to compute JD-match score", height=120, key="rm_jd")
        with right:
            st.markdown("**⚙️ Options**")
            top_k = st.number_input("Top K roles", min_value=1, max_value=10, value=5, key="top_k")
            similar_threshold = st.slider("Duplicate similarity threshold (%)", min_value=60, max_value=95, value=85, key="dup_thresh")
            show_prob_bar = st.checkbox("Show probability bars", value=True, key="show_prob")
            enable_firebase = st.checkbox("☁️ Enable Firebase Sync", value=False, help="Requires Firebase project ID and API key to be set.", key="enable_fb")

        st.markdown("---")

        # -------------------- HANDLERS (Simplified) --------------------
        
        # --- Tabs for Analysis Flows ---
        

        with tab_role_matcher:
            # Single Analysis Logic (unchanged from previous fix)
            
            # --- Check if we need to set top_k based on user input for this tab ---
            current_top_k = int(top_k) if 'top_k' in st.session_state else 5
            
            if single_pdf and not multi_pdf:
                if st.button(" Analyze uploaded PDF", key="btn_single_pdf"):
                    with st.spinner("Extracting and Analyzing..."):
                        extracted = extract_text_from_pdf_bytes(single_pdf.read())
                        res = analyze_resume_text(extracted, jd_text=paste_jd, top_k=current_top_k)
                        st.session_state.last_result = res
                        render_result_ui(res, label=getattr(single_pdf, "name", "Uploaded PDF"))
            
            if st.button("🔎 Analyze pasted resume text", key="btn_paste"):
                if not paste_resume or len(paste_resume.strip()) < 50:
                    st.warning("Paste a longer resume or upload a PDF.")
                else:
                    with st.spinner("Analyzing pasted text..."):
                        res = analyze_resume_text(paste_resume, jd_text=paste_jd, top_k=current_top_k)
                        st.session_state.last_result = res
                        render_result_ui(res, label="Pasted Resume")

            # --- FIREBASE PRODUCTION FEATURE ---
            if enable_firebase:
                st.markdown("---")
                st.markdown(f"###  Production Data Sync (User: `{st.session_state.user_uid}`)")
                if 'last_result' in st.session_state and st.session_state.last_result:
                    if st.button("💾 Save **Last Analyzed Result** to Firebase", key="save_fb_btn"):
                        res = st.session_state.last_result
                        data = {
                            "cv_file_name": getattr(single_pdf, "name", "Pasted_Text"),
                            "predicted_role": res.get("top_role"), 
                            "confidence": res.get("top_prob"), 
                            "role_probs": {r: p for r,p in res.get("top_roles",[])}, 
                            "skills": res.get("skills", []),
                            "seniority": res.get("seniority"), 
                            "jd_match": res.get("jd_score"),
                            "source_type": "Single/Paste",
                            "created_at": datetime.utcnow().isoformat()
                        }
                        success, message = save_to_firestore_production(data)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                else:
                    st.info("Analyze a resume first (Single/Paste flow) to enable Firebase sync.")


        # -------------------- BATCH ANALYSIS TAB --------------------

        with tab_batch:
            current_top_k = int(top_k) if 'top_k' in st.session_state else 5
            
            if multi_pdf:
                if st.button(" Analyze uploaded PDFs (batch)", key="btn_batch_pdf"):
                    
                    st.markdown("---")
                    st.subheader(" Batch Analysis Report")
                    
                    progress = st.progress(0, "Starting batch analysis...")
                    results_rows = []
                    resume_texts = []
                    names = []
                    unreadable_files = []
                    
                    for idx, f in enumerate(multi_pdf, start=1):
                        progress.progress(int(idx/len(multi_pdf)*30), f"Extracting text from {f.name}...")
                        txt = extract_text_from_pdf_bytes(f.read())
                        resume_texts.append(txt)
                        names.append(getattr(f, "name", f"file_{idx}"))
                        
                        progress.progress(int(30 + idx/len(multi_pdf)*40), f"Analyzing {f.name}...")
                        res = analyze_resume_text(txt, jd_text=paste_jd, top_k=current_top_k)
                        
                        if not res:
                            # Record unreadable file and use placeholder
                            unreadable_files.append(names[-1])
                            res = {
                                "top_role": "Unreadable/Empty", "top_prob": 0.0, "jd_score": None, 
                                "seniority": "N/A", "skills": [], "missing_skills": []
                            }

                        results_rows.append({
                            "filename": names[-1],
                            "predicted_role": res["top_role"],
                            "confidence": res["top_prob"],
                            "jd_score": res["jd_score"],
                            "seniority": res["seniority"],
                            "detected_skills": ";".join(res["skills"]),
                            "missing_skills": ";".join(res["missing_skills"])
                        })
                        progress.progress(int(70 + (idx/len(multi_pdf)*30)), f"Processing {f.name} data...")

                    df_results = pd.DataFrame(results_rows)
                    
                    # --- BATCH FEATURE 1: DISPLAY UNREADABLE FILES ---
                    if unreadable_files:
                        st.markdown(f"<div class='unreadable-box'>🗃️ **Could not read {len(unreadable_files)} file(s):** {', '.join(unreadable_files)}</div>", unsafe_allow_html=True)
                    else:
                        st.success("✅ All files processed successfully.")

                    # --- NEW FEATURE: BATCH ANALYTICS VIOLIN PLOT ---
                    st.markdown("---")
                    st.markdown("###  Confidence Score Distribution by Predicted Role")
                    st.info("The Violin Plot shows how confident the model was for each predicted role. Wider sections indicate a higher concentration of resumes at that confidence level.")
                    
                    # Filter out unreadable files and those with low confidence (0.0)
                    df_chart = df_results[
                        (df_results['predicted_role'] != 'Unreadable/Empty') & 
                        (df_results['confidence'] > 0.0)
                    ].copy()
                    
                    if not df_chart.empty:
                        # Create the Violin Plot
                        try:
                            fig, ax = plt.subplots(figsize=(10, 5))
                            sns.violinplot(
                                x='predicted_role', 
                                y='confidence', 
                                data=df_chart, 
                                inner='quartile', 
                                palette='coolwarm',
                                ax=ax
                            )
                            ax.set_ylim(0, 1) # Set y-axis limit for confidence (0 to 1)
                            ax.set_title('Model Confidence Distribution per Predicted Role')
                            ax.set_xlabel('Predicted Role')
                            ax.set_ylabel('Confidence Score (0.0 to 1.0)')
                            plt.xticks(rotation=45, ha='right')
                            plt.tight_layout()
                            
                            st.pyplot(fig)
                            plt.close(fig)
                            
                        except Exception as e:
                            st.error(f"Failed to generate Violin Plot. Error: {e}")
                            st.info("This can happen if you have too few roles or only one resume.")

                        st.markdown(f"**Total Plottable Candidates:** `{len(df_chart)}`")
                    else:
                        st.info("Not enough data to generate the Confidence Distribution Violin Plot.")
                        
                    # --- BATCH FEATURE 2: VISUAL RESULTS TABLE ---
                    st.markdown("---")
                    st.markdown("#### Top Role & JD Match Overview")
                    st.dataframe(df_results[["filename", "predicted_role", "confidence", "jd_score", "seniority"]].style.format({
                        'confidence': '{:.1%}',
                        'jd_score': lambda x: f'{x:.1%}' if x is not None and not np.isnan(x) else 'N/A'
                    }).bar(subset=['confidence'], color='#A7C7E7', vmin=0, vmax=1), use_container_width=True)

                    # --- BATCH FEATURE 3: DUPLICATE DETECTION ---
                    duplicate_pairs = find_duplicates(resume_texts, threshold=similar_threshold/100)
                    st.markdown("---")
                    st.markdown(f"####  Duplicate File Detection (Similarity > {similar_threshold}%)")
                    
                    if duplicate_pairs:
                        st.markdown(f"<div class='duplicate-box'>🚨 **{len(duplicate_pairs)} Potential Duplicate Pair(s) Detected!**</div>", unsafe_allow_html=True)
                        for i, j, sim in duplicate_pairs:
                            st.warning(f"**{names[i]}** and **{names[j]}** are **{int(sim*100)}%** similar.")
                    else:
                        st.success("✅ No potential duplicates found above the threshold.")

                    progress.empty()
                    
                    # --- BATCH FEATURE 4: PRODUCTION-READY BATCH FIREBASE SAVE ---
                    st.markdown("---")
                    if enable_firebase:
                        st.markdown("#### 💾 Production Batch Data Save")
                        if st.button("🚀 Save ALL Batch Results to Firebase", key="save_batch_fb_btn"):
                            if FIREBASE_PROJECT_ID == "mock-project-id":
                                st.warning("Cannot save to production: Replace `mock-project-id` and `mock-api-key` with your real Firebase credentials in the config section of the script.")
                            else:
                                with st.spinner("Saving batch results..."):
                                    successful_saves = 0
                                    for row in results_rows:
                                        # Skip unreadable/empty files from saving to the database
                                        if row["predicted_role"] == "Unreadable/Empty":
                                            continue
                                            
                                        data = {
                                            "cv_file_name": row["filename"],
                                            "predicted_role": row["predicted_role"],
                                            "confidence": row["confidence"], 
                                            "seniority": row["seniority"], 
                                            "jd_match": row["jd_score"],
                                            "source_type": "Batch Upload",
                                            "created_at": datetime.utcnow().isoformat()
                                        }
                                        success, message = save_to_firestore_production(data)
                                        if success:
                                            successful_saves += 1
                                    
                                    if successful_saves == len(results_rows) - len(unreadable_files):
                                        st.success(f"✅ Successfully stored {successful_saves} valid results to Firebase.")
                                    elif successful_saves > 0:
                                        st.warning(f"⚠️ Stored {successful_saves} results. {len(results_rows) - successful_saves - len(unreadable_files)} failed or were unreadable.")
                                    else:
                                        st.error("❌ Failed to save any valid results. Check logs/credentials.")
                    
                    st.markdown("---")
                    
                    # --- CSV/JSON Download ---
                    @st.cache_data
                    def convert_df_to_csv(df):
                        # Convert float confidence/jd_score back to percentages for display
                        df_d = df.copy()
                        df_d['confidence'] = (df_d['confidence'] * 100).round(1).astype(str) + '%'
                        df_d['jd_score'] = df_d['jd_score'].apply(lambda x: f"{round(x * 100, 1)}%" if pd.notna(x) else 'N/A')
                        df_d = df_d.rename(columns={'confidence': 'confidence (%)', 'jd_score': 'jd_score (%)'})
                        return df_d.to_csv(index=False).encode('utf-8')
                    
                    if not df_results.empty:
                        csv_data = convert_df_to_csv(df_results)
                        st.download_button(
                            label="⬇️ Download Batch Results (CSV)",
                            data=csv_data,
                            file_name=f"batch_results_{datetime.utcnow().strftime('%Y%m%d')}.csv",
                            mime='text/csv',
                            key="batch_csv_download"
                        )
                    
            else:
                st.info("Upload multiple PDF resumes in the sidebar to enable batch analysis.")


        # -------------------- JD RANKING TAB --------------------

        with tab_ranking:
            st.header("🏷️ JD Ranking Tool")
            st.write("Upload a Job Description and multiple CVs to rank candidates solely by JD Match Score.")

            ranking_jd = st.text_area("Paste **Target Job Description (JD)** here", height=200, key="ranking_jd")
            ranking_cvs = st.file_uploader("Upload CVs to rank (PDFs)", type=["pdf"], accept_multiple_files=True, key="ranking_cvs")
            
            if st.button("🏆 Rank Candidates by JD Match Score", key="btn_ranking_run"):
                if not ranking_jd or not ranking_cvs:
                    st.warning("Please provide a JD and upload at least one CV.")
                else:
                    ranking_results = []
                    progress = st.progress(0, "Starting JD Match Ranking...")
                    
                    for idx, cv_file in enumerate(ranking_cvs):
                        progress.progress((idx + 1) / len(ranking_cvs), f"Calculating match for {cv_file.name}...")
                        cv_text = extract_text_from_pdf_bytes(cv_file.read())
                        
                        # Only calculate JD Match Score
                        jd_match_raw = None
                        if cv_text:
                            try:
                                # Need to re-vectorize since JD and CVs must be in the same space
                                temp_vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
                                texts = [ranking_jd, cv_text]
                                vectorized_texts = temp_vectorizer.fit_transform(texts)
                                
                                # Calculate cosine similarity: JD (0) vs CV (1)
                                jd_match_raw = cosine_similarity(vectorized_texts[0], vectorized_texts[1])[0][0]
                            except Exception:
                                jd_match_raw = None
                        
                        ranking_results.append({
                            "filename": cv_file.name,
                            "jd_match_score_raw": jd_match_raw
                        })

                    progress.empty()
                    
                    # Process and display results
                    df_ranking = pd.DataFrame(ranking_results)
                    df_ranking = df_ranking.dropna(subset=['jd_match_score_raw'])
                    df_ranking = df_ranking.sort_values(by='jd_match_score_raw', ascending=False).reset_index(drop=True)
                    df_ranking['Rank'] = df_ranking.index + 1
                    df_ranking['JD Match Score (%)'] = (df_ranking['jd_match_score_raw'] * 100).round(1).astype(str) + '%'
                    
                    st.subheader("✅ Candidate Ranking")
                    st.dataframe(df_ranking[['Rank', 'filename', 'JD Match Score (%)']].style.bar(subset=['JD Match Score (%)'], color='#8DCD72', vmin=0, vmax=100), use_container_width=True)

        # -------------------- DATA HISTORY TAB --------------------
        with tab_history:
                st.header("☁️ AI Screening History")
                st.write("Track, filter, analyze, and export your past resume screening results.")

                refresh_button = st.button("🔄 Reload History")

                if 'history_df' not in st.session_state or refresh_button:
                        with st.spinner("Fetching history from Firebase..."):
                                history_df = fetch_firebase_analytics_data(st.session_state.user_uid)
                                st.session_state.history_df = history_df

                df = st.session_state.history_df

                if df.empty:
                        st.info("No history found yet. Save an analysis to begin tracking.")
                        st.stop()

                # FILTERS
                st.markdown("### 🔎 Filters")
                col1, col2, col3 = st.columns(3)

                with col1:
                        search_role = st.text_input("Search Role")
                with col2:
                        date_range = st.date_input("Filter by Date Range (optional)", value=[])
                with col3:
                        source_filter = st.selectbox(
                                "Source Type",
                                ["All", "Single/Paste", "Batch Upload", "JD Ranking"]
                        )

                conf_min = st.slider("Minimum Confidence %", 0, 100, 0)
                jd_min = st.slider("Minimum JD Match %", 0, 100, 0)

                # Apply filters
                filtered = df.copy()

                if search_role:
                        filtered = filtered[filtered["Role"].str.contains(search_role, case=False)]

                if source_filter != "All":
                        filtered = filtered[filtered["source_type"] == source_filter]

                if len(date_range) == 2:
                        start, end = date_range
                        filtered = filtered[
                                (pd.to_datetime(filtered["Date"]) >= pd.to_datetime(start))
                                & (pd.to_datetime(filtered["Date"]) <= pd.to_datetime(end))
                        ]

                filtered["Conf_float"] = filtered["Confidence"].str.rstrip('%').astype(float)
                filtered["JD_float"] = filtered["JD Match Score"].str.rstrip('%').astype(float)

                filtered = filtered[
                        (filtered["Conf_float"] >= conf_min)
                        & (filtered["JD_float"] >= jd_min)
                ]

                st.success(f"Showing **{len(filtered)}** of {len(df)} results")

                # ANALYTICS
                st.markdown("## 📈 Insights & Analytics")

                # Trend
                st.markdown("### 📉 Confidence Trend Over Time")
                temp = filtered.copy()
                temp["Date_dt"] = pd.to_datetime(temp["Date"])

                fig_trend, ax = plt.subplots(figsize=(10, 4))
                ax.plot(temp["Date_dt"], temp["Conf_float"])
                ax.set_xlabel("Date")
                ax.set_ylabel("Confidence %")
                ax.set_title("Confidence Score Trend")
                plt.tight_layout()
                st.pyplot(fig_trend)

                # Role Distribution
                st.markdown("### 🧩 Role Distribution")
                role_counts = filtered["Role"].value_counts()

                fig_role, axr = plt.subplots(figsize=(8, 4))
                sns.barplot(x=role_counts.index, y=role_counts.values, ax=axr)
                plt.xticks(rotation=45)
                axr.set_title("Predicted Roles Frequency")
                st.pyplot(fig_role)

                # JD Histogram
                st.markdown("### 📊 JD Match Score Distribution")
                fig_jd, axjd = plt.subplots(figsize=(8, 4))
                sns.histplot(filtered["JD_float"], bins=10, ax=axjd)
                axjd.set_xlabel("JD Match %")
                axjd.set_title("JD Match Score Histogram")
                st.pyplot(fig_jd)

                # AI SUMMARY
                st.markdown("### 🤖 AI Summary of Your Hiring Patterns")
                summary_text = f"""
                • Most predicted role: **{role_counts.idxmax()}**  
                • Highest JD Match Average: **{filtered['JD_float'].mean():.1f}%**  
                • Average Confidence: **{filtered['Conf_float'].mean():.1f}%**  
                • Trend: Confidence score over time shows {'improvement' if filtered['Conf_float'].iloc[-1] > filtered['Conf_float'].iloc[0] else 'decline'}  
                """
                st.info(summary_text)

                # INTERACTIVE TABLE
                st.markdown("## 📑 Detailed History Table")
                for idx, row in filtered.iterrows():
                        with st.expander(f"📄 {row['Role']} — {row['Date']}"):
                                st.write(f"**Role:** {row['Role']}")
                                st.write(f"**Confidence:** {row['Confidence']}")
                                st.write(f"**JD Match Score:** {row['JD Match Score']}")
                                st.write(f"**Seniority:** {row['Seniority']}")
                                st.write(f"**Source:** {row['source_type']}")

                                pdf_btn = st.button(
                                        f"📥 Download PDF for {row['Role']} ({row['Date']})",
                                        key=f"pdf_{idx}"
                                )
                                if pdf_btn:
                                        pdf_data = {
                                                "top_role": row["Role"],
                                                "top_prob": float(row["Conf_float"]) / 100,
                                                "jd_score": float(row["JD_float"]) / 100,
                                                "skills": ["N/A"],
                                                "missing_skills": ["N/A"],
                                                "seniority": row["Seniority"],
                                                "top_roles": [],
                                                "resume_excerpt": "N/A"
                                        }
                                        pdf_bytes = make_pdf_bytes(pdf_data)
                                        st.download_button("📄 Save PDF", pdf_bytes, f"report_{idx}.pdf")

                # EXPORT
                st.markdown("## ⬇️ Export Data")
                colE1, colE2, colE3 = st.columns(3)
                with colE1:
                        st.download_button("⬇️ CSV", filtered.to_csv(index=False).encode(), "history.csv")
                with colE2:
                        st.download_button("⬇️ JSON", filtered.to_json().encode(), "history.json")
                with colE3:
                        st.download_button("⬇️ Excel", filtered.to_csv(index=False).encode(), "history.xlsx")

                # DELETE OPTIONS
                st.markdown("## 🗑 Delete History")
                delete_choice = st.selectbox(
                        "Choose delete mode:",
                        ["Select one", "Delete Single Entry", "Delete All My Entries", "Delete by Role", "Delete by Date Range"]
                )

                # --- DELETE SINGLE ENTRY ---
                if delete_choice == "Delete Single Entry":
                        single_list = filtered[["doc_id", "Role", "Date"]]

                        selected = st.selectbox(
                                "Select entry to delete",
                                [f"{row['doc_id']} — {row['Role']} — {row['Date']}" for _, row in single_list.iterrows()]
                        )

                        if st.button("🗑 Delete This Entry"):
                                doc_id = selected.split(" — ")[0]
                                success, msg = delete_firestore_document(doc_id)

                                if success:
                                        st.success("Deleted successfully.")
                                        st.session_state.pop("history_df", None)
                                        st.rerun()
                                else:
                                        st.error(msg)

                # --- DELETE ALL (ONLY USER'S OWN RECORDS) ---
                if delete_choice == "Delete All My Entries":
                        if st.button("⚠️ Confirm Delete ALL My History"):
                                user_uid = st.session_state.user_uid
                                count = 0
                                for _, row in filtered.iterrows():
                                        if row["user_uid"] == user_uid:
                                                success, _ = delete_firestore_document(row["doc_id"])
                                                if success:
                                                        count += 1

                                st.success(f"Deleted {count} entries.")
                                st.session_state.pop("history_df", None)
                                st.rerun()

                # --- DELETE BY ROLE ---
                if delete_choice == "Delete by Role":
                        roles = filtered["Role"].unique()
                        chosen_role = st.selectbox("Select Role", roles)

                        if st.button(f"🗑 Delete all entries for '{chosen_role}'"):
                                to_delete = filtered[filtered["Role"] == chosen_role]
                                count = 0

                                for _, row in to_delete.iterrows():
                                        success, _ = delete_firestore_document(row["doc_id"])
                                        if success:
                                                count += 1

                                st.success(f"Deleted {count} entries.")
                                st.session_state.pop("history_df", None)
                                st.rerun()

                # --- DELETE BY DATE RANGE ---
                if delete_choice == "Delete by Date Range":
                        del_range = st.date_input("Pick date range", [])

                        if len(del_range) == 2:
                                d1, d2 = del_range
                                to_delete = filtered[
                                        (pd.to_datetime(filtered["Date"]) >= pd.to_datetime(d1)) &
                                        (pd.to_datetime(filtered["Date"]) <= pd.to_datetime(d2))
                                ]

                                if st.button("🗑 Delete entries in this range"):
                                        count = 0
                                        for _, row in to_delete.iterrows():
                                                success, _ = delete_firestore_document(row["doc_id"])
                                                if success:
                                                        count += 1

                                        st.success(f"Deleted {count} entries.")
                                        st.session_state.pop("history_df", None)
                                        st.rerun()

                st.write("Delete options will appear only after delete function is added.")
