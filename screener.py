import streamlit as st
import pdfplumber
import re
import os
import sklearn
import joblib
import numpy as np
from datetime import datetime, date
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
from sentence_transformers import SentenceTransformer
import nltk
import collections
from sklearn.metrics.pairwise import cosine_similarity
import urllib.parse
import uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import tempfile
import shutil
from weasyprint import HTML
from concurrent.futures import ProcessPoolExecutor, as_completed
from io import BytesIO
import traceback
import time
import pandas as pd
import json
import os
import hashlib

from jd_store import fs_get_jds

import requests # Added for REST API calls
from difflib import SequenceMatcher # Added for Exact Match Score
import random # Added for LLM-style summary variability
import hashlib # For hashing uploaded files to detect changes
#from manage_jds import get_paths, read_jd_content  # Use your JD manager utilities
# CRITICAL: Disable Hugging Face tokenizers parallelism to avoid deadlocks with ProcessPoolExecutor
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import google.generativeai as genai
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)
# --- OCR Specific Imports ---
from PIL import Image
import pytesseract
import cv2
from pdf2image import convert_from_bytes
PROJECT_ID = "screenerproapp"
WEB_API_KEY = "AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw"
FIREBASE_WEB_API_KEY = "AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw"
def get_docs_from_firestore_rest(collection_path):
    """
    Fetches all documents from a Firestore collection using REST API.
    """

    url = (
        f"https://firestore.googleapis.com/v1/projects/"
        f"{PROJECT_ID}/databases/(default)/documents/"
        f"{collection_path}?key={WEB_API_KEY}"
    )

    try:
        res = requests.get(url)
        if res.status_code != 200:
            return []

        data = res.json()
        documents = []

        for doc in data.get("documents", []):
            doc_id = doc["name"].split("/")[-1]
            fields = doc.get("fields", {})

            parsed = {}
            for k, v in fields.items():
                if "stringValue" in v:
                    parsed[k] = v["stringValue"]
                elif "integerValue" in v:
                    parsed[k] = int(v["integerValue"])
                elif "doubleValue" in v:
                    parsed[k] = float(v["doubleValue"])
                elif "arrayValue" in v:
                    parsed[k] = [
                        list(x.values())[0]
                        for x in v["arrayValue"].get("values", [])
                    ]
                elif "mapValue" in v:
                    parsed[k] = {
                        mk: list(mv.values())[0]
                        for mk, mv in v["mapValue"]["fields"].items()
                    }

            parsed["id"] = doc_id
            documents.append(parsed)

        return documents

    except Exception as e:
        print("Firestore fetch error:", e)
        return []

# Global NLTK download check (should run once)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

# Define global constants
MASTER_CITIES = set([
    "Bengaluru", "Mumbai", "Delhi", "Chennai", "Hyderabad", "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    "Chandigarh", "Kochi", "Coimbatore", "Nagpur", "Bhopal", "Indore", "Gurgaon", "Noida", "Surat", "Visakhapatnam",
    "Patna", "Vadodara", "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Faridabad", "Meerut", "Rajkot", "Varanasi",
    "Srinagar", "Aurangabad", "Dhanbad", "Amritsar", "Allahabad", "Ranchi", "Jamshedpur", "Gwalior", "Jabalpur",
    "Vijayawada", "Jodhpur", "Raipur", "Kota", "Guwahati", "Thiruvananthapuram", "Mysuru", "Hubballi-Dharwad",
    "Mangaluru", "Belagavi", "Davangere", "Ballari", "Tumakuru", "Shivamogga", "Bidar", "Hassan", "Gadag-Betageri",
    "Chitradurga", "Udupi", "Kolar", "Mandya", "Chikkamagaluru", "Koppal", "Chamarajanagar", "Yadgir", "Raichur",
    "Kalaburagi", "Bengaluru Rural", "Dakshina Kannada", "Uttara Kannada", "Kodagu", "Chikkaballapur", "Ramanagara",
    "Bagalkot", "Gadag", "Haveri", "Vijayanagara", "Krishnagiri", "Vellore", "Salem", "Erode", "Tiruppur", "Madurai",
    "Tiruchirappalli", "Thanjavur", "Dindigad", "Kanyakumari", "Thoothukudi", "Tirunelveli", "Nagercoil", "Puducherry",
    "Panaji", "Margao", "Vasco da Gama", "Mapusa", "Ponda", "Bicholim", "Curchorem", "Sanquelim", "Valpoi", "Pernem",
    "Quepem", "Canacona", "Mormugao", "Sanguem", "Dharbandora", "Tiswadi", "Salcete", "Bardez",
    "London", "New York", "Paris", "Berlin", "Tokyo", "Sydney", "Toronto", "Vancouver", "Singapore", "Dubai",
    "San Francisco", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego",
    "Dallas", "San Jose", "Austin", "Jacksonville", "Fort Worth", "Columbus", "Charlotte", "Indianapolis",
    "Seattle", "Denver", "Washington D.C.", "Boston", "Nashville", "El Paso", "Detroit", "Oklahoma City",
    "Portland", "Las Vegas", "Memphis", "Louisville", "Baltimore", "Milwaukee", "Albuquerque", "Tucson",
    "Fresno", "Sacramento", "Mesa", "Atlanta", "Kansas City", "Colorado Springs", "Raleigh", "Miami", "Omaha",
    "Virginia Beach", "Long Beach", "Oakland", "Minneapolis", "Tulsa", "Wichita", "New Orleans", "Cleveland",
    "Tampa", "Honolulu", "Anaheim", "Santa Ana", "St. Louis", "Riverside", "Lexington", "Pittsburgh", "Cincinnati",
    "Anchorage", "Plano", "Newark", "Orlando", "Irvine", "Garland", "Hialeah", "Scottsdale", "North Las Vegas",
    "Chandler", "Laredo", "Chula Vista", "Madison", "Reno", "Buffalo", "Durham", "Rochester", "Winston-Salem",
    "St. Petersburg", "Jersey City", "Toledo", "Lincoln", "Greensboro", "Boise", "Richmond", "Stockton",
    "San Bernardino", "Des Moines", "Modesto", "Fayetteville", "Shreveport", "Akron", "Tacoma", "Aurora",
    "Oxnard", "Fontana", "Montgomery", "Little Rock", "Grand Rapids", "Springfield", "Yonkers", "Augusta",
    "Mobile", "Port St. Lucie", "Denton", "Spokane", "Chattanooga", "Worcester", "Providence", "Fort Lauderdale",
    "Chesapeake", "Fremont", "Baton Rouge", "Santa Clarita", "Birmingham", "Glendale", "Huntsville",
    "Salt Lake City", "Frisco", "McKinney", "Grand Prairie", "Overland Park", "Brownsville", "Killeen",
    "Pasadena", "Olathe", "Dayton", "Savannah", "Fort Collins", "Naples", "Gainesville", "Lakeland", "Sarasota",
    "Daytona Beach", "Melbourne", "Clearwater", "St. Augustine", "Key West", "Fort Myers", "Cape Coral",
    "Coral Springs", "Pompano Beach", "Miami Beach", "West Palm Beach", "Boca Raton", "Fort Pierce",
    "Port Orange", "Kissimmee", "Sanford", "Ocala", "Bradenton", "Palm Bay", "Deltona", "Largo",
    "Deerfield Beach", "Boynton Beach", "Coconut Creek", "Sunrise", "Plantation", "Davie", "Miramar",
    "Hollywood", "Pembroke Pines", "Coral Gables", "Doral", "Aventura", "Sunny Isles Beach", "North Miami",
    "Miami Gardens", "Homestead", "Cutler Bay", "Pinecrest", "Kendall", "Richmond Heights", "West Kendall",
    "East Kendall", "South Miami", "Sweetwater", "Opa-locka", "Florida City", "Golden Glades", "Leisure City",
    "Princeton", "West Perrine", "Naranja", "Goulds", "South Miami Heights", "Country Walk", "The Crossings",
    "Three Lakes", "Richmond West", "Palmetto Bay", "Palmetto Estates", "Perrine", "Cutler Ridge", "Westview",
    "Gladeview", "Brownsville", "Liberty City", "West Little River", "Pinewood", "Ojus", "Ives Estates",
    "Highland Lakes", "Sunny Isles Beach", "Golden Beach", "Bal Harbour", "Surfside", "Bay Harbor Islands",
    "Indian Creek", "North Bay Village", "Biscayne Park", "El Portal", "Miami Shores", "North Miami Beach",
    "Aventura"
])

# Removed NLTK_STOP_WORDS, CUSTOM_STOP_WORDS, STOP_WORDS as they are no longer used for skill extraction

# Removed SKILL_CATEGORIES and MASTER_SKILLS as they are replaced by skills_library.txt
# Removed CATEGORY_SHORTHAND_MAP and DOMAIN_SKILL_BUCKETS as they are no longer used for skill grouping
# =============================================
# Standalone Auto-Save Function (Fix for screener)
# =============================================
def auto_save_after_screening(username, df):
    try:
        # Firestore document path (same as main.py)
        doc_path = f"documents/user_data/{username}"
        url = f"{FIRESTORE_DATABASE_ROOT_URL}/{doc_path}?key={FIREBASE_WEB_API_KEY}"

        # Convert DataFrame to JSON string
        df_json = df.to_json(orient="records")

        payload = {
            "fields": {
                "comprehensive_df_json": {"stringValue": df_json},
                "screened_count": {"integerValue": str(len(df))},
                "timestamp": {"stringValue": str(datetime.now())}
            }
        }

        res = requests.patch(url, json=payload)
        return res.status_code == 200

    except Exception as e:
        st.warning(f"Auto-save internal error: {e}")
        return False

# Job domain classifier (still useful for HR summary, but not for skill grouping)
def detect_job_domain(jd_title, jd_text):
    text = (jd_title + " " + jd_text).lower()
    if any(k in text for k in ["accountant", "finance", "ca", "cpa", "audit", "tax", "financial"]):
        return "finance"
    elif any(k in text for k in ["data scientist", "analytics", "ml", "ai", "machine learning", "deep learning", "nlp", "computer vision"]):
        return "data_science"
    elif any(k in text for k in ["developer", "engineer", "react", "python", "java", "software", "web", "frontend", "backend", "fullstack"]):
        return "software"
    elif any(k in text for k in ["recruiter", "talent acquisition", "hr", "human resources", "people operations", "onboarding"]):
        return "hr"
    elif any(k in text for k in ["designer", "photoshop", "figma", "ux", "ui", "illustrator", "graphic"]):
        return "design"
    else:
        return "general"

# IMPORTANT: REPLACE THESE WITH YOUR ACTUAL DEPLOYMENT URLs
APP_BASE_URL = "https://screenerpro.streamlit.app/" # Updated as per user request
CERTIFICATE_HOSTING_URL = "https://screenerpro.streamlit.app/" # Updated as per user request


@st.cache_resource
def get_tesseract_cmd():
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        return tesseract_path
    return None

# Load ML models once using st.cache_resource
@st.cache_resource
def load_ml_model():
    """
    Safely loads the SentenceTransformer model with fallback.
    If Hugging Face download fails, switches to TF-IDF mode for limited scoring.
    """
    with st.spinner("Loading AI model... This may take a moment."):
        try:
            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            return model, "sentence-transformers/all-MiniLM-L6-v2"
        except Exception as e:
            
            
            return None, "tfidf_fallback"

# Load models globally (once per app run)
global_sentence_model, global_ml_model = load_ml_model()

# New function to load skill library
def load_skill_library(file_path="skills_library.txt"):
    """Loads a list of skills from a text file, one skill per line."""
    if not os.path.exists(file_path):
        st.error(f"Error: {file_path} not found. Please ensure the skills_library.txt file is in the correct directory.")
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]

# New skill extraction function
def extract_skills_from_text(text, skill_library):
    """
    Extracts skills from text by checking for their presence in the provided skill_library.
    This performs a simple substring check.
    """
    text = text.lower()
    found_skills = set()
    # Prioritize multi-word skills first to avoid partial matches
    sorted_skill_library = sorted(skill_library, key=len, reverse=True)
    for skill in sorted_skill_library:
        # Use regex with word boundaries to ensure whole word match
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text):
            found_skills.add(skill)
    return list(found_skills)


# Pre-compile regex patterns for efficiency
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.\w+')
PHONE_PATTERN = re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
CGPA_PATTERN = re.compile(r'(?:cgpa|gpa|grade point average)\s*[:\s]*(\d+\.\d+)(?:\s*[\/of]{1,4}\s*(\d+\.\d+|\d+))?|(\d+\.\d+)(?:\s*[\/of]{1,4}\s*(\d+\.\d+|\d+))?\s*(?:cgpa|gpa)')
EXP_DATE_PATTERNS = [
    re.compile(r'(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[,]*\s*\d{4})\s*(?:to|–|—|-)\s*(present|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[,]*\s*\d{4})', re.IGNORECASE),
    re.compile(r'(\b\d{4})\s*(?:to|–|—|-)\s*(present|\b\d{4})', re.IGNORECASE)
]
EXP_YEARS_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(\+)?\s*(year|yrs|years)\b')
EXP_FALLBACK_PATTERN = re.compile(r'experience[^\d]{0,10}(\d+(?:\.\d+)?)')
NAME_EXCLUDE_TERMS = {
    "linkedin", "github", "portfolio", "resume", "cv", "profile", "contact", "email", "phone",
    "mobile", "number", "tel", "telephone", "address", "website", "site", "social", "media",
    "url", "link", "blog", "personal", "summary", "about", "objective", "dob", "birth", "age",
    "nationality", "gender", "location", "city", "country", "pin", "zipcode", "state", "whatsapp",
    "skype", "telegram", "handle", "id", "details", "connection", "reach", "network", "www",
    "https", "http", "contactinfo", "connect", "reference", "references","fees","Bangalore, Karnataka",
    "resume", "cv", "curriculum vitae", "resume of", "cv of", "summary", "about",
    "objective", "declaration", "personal profile", "profile", "career objective",
    "introduction", "bio", "statement", "overview",

    # Education & academic
    "education", "qualifications", "academic", "certification", "certifications", "degree",
    "school", "college", "university", "diploma", "graduate", "graduation", "passed", "gpa",
    "cgpa", "marks", "percentage", "year", "pass", "exam", "results", "board",

    # Skills and tools
    "skills", "technical", "technologies", "tools", "software", "programming",
    "languages", "frameworks", "libraries", "databases", "methodologies", "platforms",
    "proficient", "knowledge", "experience", "exposure", "tools used", "framework",

    # Software/product/tool names (block spaCy NER mistakes)
    "zoom", "slack", "google", "microsoft", "excel", "word", "docs", "teams", "powerpoint",
    "notion", "jupyter", "linux", "windows", "android", "firebase", "oracle", "git", "github",
    "bitbucket", "jira", "confluence", "sheets", "trello", "figma", "canva", "sql", "mysql",
    "postgres", "mongodb", "hadoop", "spark", "kubernetes", "docker", "aws", "azure", "gcp",

    # Job/work section
    "experience", "internship", "work", "professional", "employment", "company",
    "role", "designation", "job", "project", "responsibilities", "position",
    "organization", "industry", "client", "team", "department",

    # Hobbies/extra
    "interests", "hobbies", "achievements", "awards", "activities", "extra curricular",
    "certified", "certificates", "participation", "strengths", "weaknesses", "languages known",

    # Location examples
    "bangalore", "delhi", "mumbai", "chennai", "hyderabad", "pune", "kolkata", "india",
    "remote", "new york", "california", "london", "tokyo", "berlin", "canada", "germany",

    # Misc
    "fees", "salary", "expected", "compensation", "passport", "visa", "availability",
    "notice period", "relocate", "relocation", "travel", "timing", "schedule", "full-time", "part-time",

    # Filler/common false-positive content
    "available", "required", "requested", "relevant", "coursework", "summary", "hello",
    "introduction", "dear", "regards", "thanks", "thank you", "please", "objective", "kindly"
}
# Re-enabled EDU_MATCH_PATTERN and EDU_FALLBACK_PATTERN for the new extract_education function
EDU_MATCH_PATTERN = re.compile(r'([A-Za-z0-9.,()&\-\s]+?(university|college|institute|school)[^–\n]{0,50}[–\-—]?\s*(expected\s*)?\d{4})', re.IGNORECASE)
EDU_FALLBACK_PATTERN = re.compile(r'([A-Za-z0-9.,()&\-\s]+?(b\.tech|m\.tech|b\.sc|m\.sc|bca|bba|mba|ph\.d)[^–\n]{0,50}\d{4})', re.IGNORECASE)

WORK_HISTORY_SECTION_PATTERN = re.compile(r'(?:experience|work history|employment history)\s*(\n|$)', re.IGNORECASE)
JOB_BLOCK_SPLIT_PATTERN = re.compile(r'\n(?=[A-Z][a-zA-Z\s,&\.]+(?:\s(?:at|@))?\s*[A-Z][a-zA-Z\s,&\.]*\s*(?:-|\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}))', re.IGNORECASE)
DATE_RANGE_MATCH_PATTERN = re.compile(r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}|\d{4})\s*[-–]\s*(present|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}|\d{4})', re.IGNORECASE)
TITLE_COMPANY_MATCH_PATTERN = re.compile(r'([A-Z][a-zA-Z\s,\-&.]+)\s+(?:at|@)\s+([A-Z][a-zA-Z\s,\-&.]+)')
COMPANY_TITLE_MATCH_PATTERN = re.compile(r'^([A-Z][a-zA-Z\s,\-&.]+),\s*([A-Z][a-zA-Z\s,\-&.]+)')
POTENTIAL_ORG_MATCH_PATTERN = re.compile(r'^[A-Z][a-zA-Z\s,\-&.]+')
PROJECT_SECTION_KEYWORDS = re.compile(r'(projects|personal projects|key projects|portfolio|selected projects|major projects|academic projects|relevant projects)\s*(\n|$)', re.IGNORECASE)
FORBIDDEN_TITLE_KEYWORDS = [
    'skills gained', 'responsibilities', 'reflection', 'summary',
    'achievements', 'capabilities', 'what i learned', 'tools used'
]
PROJECT_TITLE_START_PATTERN = re.compile(r'^[•*-]?\s*\d+[\).:-]?\s')
LANGUAGE_SECTION_PATTERN = re.compile(r'\b(languages|language skills|linguistic abilities|known languages)\s*[:\-]?\s*\n?', re.IGNORECASE)


# --- Firebase REST Setup (Moved from main.py) ---
FIREBASE_WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY', 'AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw')
FIREBASE_PROJECT_ID = globals().get('__app_id', 'screenerproapp')
FIRESTORE_DATABASE_ROOT_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)"

def log_activity_screener(message):
    """Logs an activity with a timestamp to the session state for screener.py's activities."""
    if 'activity_log_screener' not in st.session_state:
        st.session_state.activity_log_screener = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.activity_log_screener.insert(0, f"[{timestamp}] {message}") # Add to the beginning for most recent first
    st.session_state.activity_log_screener = st.session_state.activity_log_screener[:50]

def save_certificate_to_firestore_public(certificate_data):
    """
    Saves individual certificate data to a public Firestore collection for verification.
    This collection should have public read access and authenticated write access.
    """
    try:
        cert_id = certificate_data.get("Certificate ID")
        if not cert_id:
            cert_id = str(uuid.uuid4()) # Generate if missing, though it should be present
            certificate_data['Certificate ID'] = cert_id # Update data for consistency
            st.warning("Certificate ID was missing, generated a new one.")

        # Correct Firestore document path
        document_path = f"public_certificates/{cert_id}"
        url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents/{document_path}?key={FIREBASE_WEB_API_KEY}"

        # Prepare Firestore payload
        firestore_data = {
            "fields": {
                "candidate_name": {"stringValue": certificate_data.get("Candidate Name", "N/A")},
                "certificate_rank": {"stringValue": certificate_data.get("Certificate Rank", "Not Applicable")},
                "jd_used": {"stringValue": certificate_data.get("JD Used", "N/A")},
                "score": {"doubleValue": float(f"{certificate_data.get('Score (%)', 0.0):.2f}")}, # Use 'Score (%)' key
                "date_screened": {"stringValue": str(certificate_data.get("Date Screened", datetime.now().date()))}, # Use existing date format
                "certificate_id": {"stringValue": cert_id},
            }
        }

        # --- DEBUGGING OUTPUT ---
        print(f"DEBUG: Attempting to save certificate with URL: {url}")
        print(f"DEBUG: Payload: {json.dumps(firestore_data, indent=2)}")
        # --- END DEBUGGING OUTPUT ---

        res = requests.patch(url, json=firestore_data)
        if res.status_code == 200:
            st.toast(f"✅ Certificate ID '{cert_id}' saved for public verification.")
            log_activity_screener(f"Certificate ID '{cert_id}' saved to public collection.")
        else:
            st.error(f"❌ Failed to save certificate for public verification: {res.status_code}, {res.text}")
            log_activity_screener(f"Failed to save certificate '{cert_id}' to public collection: {res.status_code}, {res.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"🔥 Firestore connection error while saving certificate: {e}")
        log_activity_screener(f"Firestore connection error saving certificate '{cert_id}': {e}")
    except Exception as e:
        st.error(f"🔥 An unexpected error occurred saving certificate: {e}")
        log_activity_screener(f"Unexpected error saving certificate '{cert_id}': {e}")


def preprocess_image_for_ocr(image):
    img_cv = np.array(image)
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    img_processed = cv2.adaptiveThreshold(img_cv, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 11, 2)
    return Image.fromarray(img_processed)

def clean_text(text):
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return text.strip().lower()

# Removed old extract_relevant_keywords as it's replaced by extract_skills_from_text

def extract_text_from_file(file_bytes, file_name, file_type):
    full_text = ""
    # Tesseract configuration for speed and common resume layout
    tesseract_config = "--oem 1 --psm 3" 

    if "pdf" in file_type:
        try:
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                pdf_text = ''.join(page.extract_text() or '' for page in pdf.pages)
            
            if len(pdf_text.strip()) < 50: # Heuristic for potentially scanned PDF
                images = convert_from_bytes(file_bytes)
                for img in images:
                    processed_img = preprocess_image_for_ocr(img)
                    full_text += pytesseract.image_to_string(processed_img, lang='eng', config=tesseract_config) + "\n"
            else:
                full_text = pdf_text

        except Exception as e:
            # Fallback to OCR directly if pdfplumber fails or for any other PDF error
            try:
                images = convert_from_bytes(file_bytes)
                for img in images:
                    processed_img = preprocess_image_for_ocr(img)
                    full_text += pytesseract.image_to_string(processed_img, lang='eng', config=tesseract_config) + "\n"
            except Exception as e_ocr:
                print(f"ERROR: Failed to extract text from PDF via OCR for {file_name}: {str(e_ocr)}")
                return f"[ERROR] Failed to extract text from PDF via OCR: {str(e_ocr)}"

    elif "image" in file_type:
        try:
            img = Image.open(BytesIO(file_bytes)).convert("RGB")
            processed_img = preprocess_image_for_ocr(img)
            full_text = pytesseract.image_to_string(processed_img, lang='eng', config=tesseract_config)
        except Exception as e:
            print(f"ERROR: Failed to extract text from image for {file_name}: {str(e)}")
            return f"[ERROR] Failed to extract text from image: {str(e)}"
    else:
        print(f"ERROR: Unsupported file type for {file_name}: {file_type}")
        return f"[ERROR] Unsupported file type: {file_type}. Please upload a PDF or an image (JPG, PNG)."

    if not full_text.strip():
        print(f"ERROR: No readable text extracted from {file_name}. It might be a very low-quality scan or an empty document.")
        return "[ERROR] No readable text extracted from the file. It might be a very low-quality scan or an empty document."
    
    return full_text


# ⛔ Keywords to ignore (education, extra)
EDUCATION_TERMS = {
    'education', 'b.tech', 'b.e', 'bachelor', 'xii', '10th', '12th',
    'school', 'cgpa', 'percentage', 'intermediate', 'class x', 'class xii',
    'graduation', 'degree', 'college', 'university', 'high school', 'gpa'
}

# ✅ Keywords that indicate experience
WORK_TERMS = {
    'intern', 'engineer', 'developer', 'consultant', 'manager', 'data analyst',
    'researcher', 'scientist', 'assistant', 'officer', 'specialist', 'freelancer',
    'technician', 'trainer', 'administrator'
}

# 📅 Regex patterns for date ranges
EXP_DATE_PATTERNS = [
    re.compile(r'(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[,]*\s*\d{4})\s*(?:to|–|—|-)\s*(present|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[,]*\s*\d{4})', re.IGNORECASE),
    re.compile(r'(\b\d{4})\s*(?:to|–|—|-)\s*(present|\b\d{4})', re.IGNORECASE)
]

# 🧠 Additional fallback numeric patterns
EXP_YEARS_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(\+)?\s*(year|yrs|years)\b')
EXP_FALLBACK_PATTERN = re.compile(r'experience[^\d]{0,10}(\d+(?:\.\d+)?)')

def normalize_text(text):
    text = text.lower()
    text = text.replace('–', '-').replace('—', '-').replace(' to ', ' - ')
    text = re.sub(r'[,:\n]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def extract_years_of_experience(text):
    text = normalize_text(text)
    now = datetime.now()
    total_months = 0

    for pattern in EXP_DATE_PATTERNS:
        for match in pattern.finditer(text):
            start_str, end_str = match.groups()
            span_start = match.start()
            surrounding_text = text[max(0, span_start - 100):span_start + 100]

            # ✅ Count only if it's near a work term and NOT education
            if any(w in surrounding_text for w in WORK_TERMS) and not any(e in surrounding_text for e in EDUCATION_TERMS):
                try:
                    start_date = datetime.strptime(start_str.strip().replace(',', ''), '%B %Y')
                except:
                    try:
                        start_date = datetime.strptime(start_str.strip().replace(',', ''), '%b %Y')
                    except:
                        try:
                            start_date = datetime(int(start_str.strip()), 1, 1)
                        except:
                            continue

                if end_str.lower().strip() == 'present':
                    end_date = now
                else:
                    try:
                        end_date = datetime.strptime(end_str.strip().replace(',', ''), '%B %Y')
                    except:
                        try:
                            end_date = datetime.strptime(end_str.strip().replace(',', ''), '%b %Y')
                        except:
                            try:
                                end_date = datetime(int(end_str.strip()), 12, 31)
                            except:
                                continue

                if start_date > now:
                    continue
                if end_date > now:
                    end_date = now

                delta_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                total_months += max(delta_months, 0)

    # 🧠 If nothing found, try fallback numeric pattern
    if total_months > 0:
        return round(total_months / 12, 1)

    match = EXP_YEARS_PATTERN.search(text) or EXP_FALLBACK_PATTERN.search(text)
    if match:
        return float(match.group(1))

    return 0.0


def extract_email(text):
    text = text.lower()

    # Correct common typos in email domains
    text = text.replace("gmaill.com", "gmail.com").replace("gmai.com", "gmail.com")
    text = text.replace("yah00", "yahoo").replace("outiook", "outlook")
    text = text.replace("coim", "com").replace("hotmai", "hotmail")

    # Remove any characters not typically found in email addresses or whitespace
    text = re.sub(r'[^\w\s@._+-]', ' ', text)

    possible_emails = EMAIL_PATTERN.findall(text)

    if possible_emails:
        for email in possible_emails:
            # Prioritize common email providers or specific keywords if needed
            if "gmail" in email or "manav" in email:
                return email
        # If no specific priority match, return the first found email
        return possible_emails[0]
    
    return None

def extract_phone_number(text):
    match = PHONE_PATTERN.search(text)
    return match.group(0) if match else None

def extract_location(text):
    found_locations = set()
    text_lower = text.lower()

    sorted_cities = sorted(list(MASTER_CITIES), key=len, reverse=True)

    for city in sorted_cities:
        pattern = r'\b' + re.escape(city.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_locations.add(city)

    if found_locations:
        return ", ".join(sorted(list(found_locations)))
    return "Not Found"

def extract_name(text):
    lines = text.strip().splitlines()
    if not lines:
        return None

    # 🚫 Common noise terms and address words
    EXCLUDE_TERMS = {
        "email", "e-mail", "phone", "mobile", "contact", "linkedin", "github",
        "portfolio", "website", "profile", "summary", "objective", "education",
        "skills", "projects", "certifications", "achievements", "experience",
        "dob", "date of birth", "address", "resume", "cv", "career", "gender",
        "marital", "nationality", "languages", "language", "score", "cgpa",
        "bengaluru", "bangalore", "karnataka", "anekal", "india", "pin", "zipcode"
    }

    PREFIX_CLEANER = re.compile(r"^(name[\s:\-]*|mr\.?|ms\.?|mrs\.?)", re.IGNORECASE)

    potential_names = []

    for line in lines[:10]:
        original_line = line.strip()
        if not original_line:
            continue

        cleaned_line = PREFIX_CLEANER.sub('', original_line).strip()
        cleaned_line = re.sub(r'[^A-Za-z\s]', '', cleaned_line)

        if any(term in cleaned_line.lower() for term in EXCLUDE_TERMS):
            continue

        words = cleaned_line.split()

        if 1 < len(words) <= 4 and all(w.isalpha() for w in words):
            if all(w.istitle() or w.isupper() for w in words):
                potential_names.append(cleaned_line)

    if potential_names:
        return max(potential_names, key=len).title()

    return None

def extract_cgpa(text):
    text = text.lower()
    
    matches = CGPA_PATTERN.findall(text)

    for match in matches:
        if match[0] and match[0].strip():
            raw_cgpa = float(match[0])
            scale = float(match[1]) if match[1] else None
        elif match[2] and match[2].strip():
            raw_cgpa = float(match[2])
            scale = float(match[3]) if match[3] else None
        else:
            continue

        if scale and scale not in [0, 1]:
            normalized_cgpa = (raw_cgpa / scale) * 4.0
            return round(normalized_cgpa, 2)
        elif raw_cgpa <= 4.0:
            return round(raw_cgpa, 2)
        elif raw_cgpa <= 10.0:
            return round((raw_cgpa / 10.0) * 4.0, 2)
        
    return None

# Replaced the old extract_education with the user's provided extract_education_text
def extract_education(text):
    """
    Extract a clean single-line education summary from resume.
    E.g., "B.Tech in CSE, Alliance University, Bangalore – 2028"
    """
    text = text.replace('\r', '').replace('\t', ' ')
    lines = text.split('\n')
    lines = [line.strip() for line in lines if line.strip()]

    education_section = ''
    capture = False

    for line in lines:
        line_lower = line.lower()
        if any(h in line_lower for h in ['education', 'academic background', 'qualifications']):
            capture = True
            continue
        if capture and any(h in line_lower for h in ['experience', 'skills', 'certifications', 'projects', 'languages']):
            break
        if capture:
            education_section += line + ' '

    education_section = education_section.strip()

    # Try matching full pattern: degree + college + year
    edu_match = EDU_MATCH_PATTERN.search(education_section)
    if edu_match:
        # Convert all groups to string, handling None explicitly
        return ' '.join([g if g is not None else '' for g in edu_match.groups()]).strip()

    # Try fallback: degree + year
    fallback_match = EDU_FALLBACK_PATTERN.search(education_section)
    if fallback_match:
        # Convert all groups to string, handling None explicitly
        return ' '.join([g if g is not None else '' for g in fallback_match.groups()]).strip()

    # Fallback to first line in section
    fallback_line = education_section.split('.')[0].strip()
    return fallback_line if fallback_line else "Not Found" # Changed to Not Found for consistency
    

def extract_work_history(text):
    work_history_section_matches = WORK_HISTORY_SECTION_PATTERN.finditer(text)
    work_details = []
    
    start_index = -1
    for match in work_history_section_matches:
        start_index = match.end()
        break

    if start_index != -1:
        sections = ['education', 'skills', 'projects', 'certifications', 'awards', 'publications']
        end_index = len(text)
        for section in sections:
            section_match = re.search(r'\b' + re.escape(section) + r'\b', text[start_index:], re.IGNORECASE)
            if section_match:
                end_index = start_index + section_match.start()
                break
        
        work_text = text[start_index:end_index].strip()
        
        job_blocks = JOB_BLOCK_SPLIT_PATTERN.split(work_text)
        
        for block in job_blocks:
            block = block.strip()
            if not block:
                continue
            
            company = None
            title = None
            start_date = None
            end_date = None

            date_range_match = DATE_RANGE_MATCH_PATTERN.search(block)
            if date_range_match:
                start_date = date_range_match.group(1)
                end_date = date_range_match.group(2)
                block = block.replace(date_range_match.group(0), '').strip()

            lines = block.split('\n')
            for line in lines:
                line = line.strip()
                if not line: continue

                title_company_match = TITLE_COMPANY_MATCH_PATTERN.search(line)
                if title_company_match:
                    title = title_company_match.group(1).strip()
                    company = title_company_match.group(2).strip()
                    break
                
                company_title_match = COMPANY_TITLE_MATCH_PATTERN.search(line)
                if company_title_match:
                    company = company_title_match.group(1).strip()
                    title = company_title_match.group(2).strip()
                    break
                
                if not company and not title:
                    potential_org_match = POTENTIAL_ORG_MATCH_PATTERN.search(line)
                    if potential_org_match and len(potential_org_match.group(0).split()) > 1:
                        if not company: company = potential_org_match.group(0).strip()
                        elif not title: title = potential_org_match.group(0).strip()
                        break

            if company or title or start_date or end_date:
                work_details.append({
                    "Company": company,
                    "Title": title,
                    "Start Date": start_date,
                    "End Date": end_date
                })
    return work_details

def extract_project_details(text, skill_library): # Updated to use skill_library
    """
    Extracts real project entries from resume text.
    Returns a list of dicts: Title, Description, Technologies Used
    """

    project_details = []

    text = text.replace('\r', '').replace('\t', ' ')
    lines = text.split('\n')
    lines = [line.strip() for line in lines if line.strip()]

    # Step 1: Isolate project section
    project_section_match = PROJECT_SECTION_KEYWORDS.search(text)

    if not project_section_match:
        project_text = text[:1000]  # fallback to first 1000 chars
        start_index = 0
    else:
        start_index = project_section_match.end()
        sections = ['education', 'skills', 'certifications', 'awards', 'publications', 'interests', 'hobbies']
        end_index = len(text)
        for section in sections:
            m = re.search(r'\b' + re.escape(section) + r'\b', text[start_index:], re.IGNORECASE)
            if m:
                end_index = start_index + m.start()
                break
        project_text = text[start_index:end_index].strip()

    if not project_text:
        return []

    lines = [line.strip() for line in project_text.split('\n') if line.strip()]
    current_project = {"Project Title": None, "Description": [], "Technologies Used": set()}

    for i, line in enumerate(lines):
        line_lower = line.lower()
        words = line.split()
        num_words = len(words)

        # Skip all-uppercase names or headers (unless very short, e.g., for acronyms)
        if re.match(r'^[A-Z\s]{5,}$', line) and num_words <= 4:
            continue

        is_title = False
        # Condition 1: Starts with a bullet/number or "project" keyword
        if PROJECT_TITLE_START_PATTERN.match(line) or line_lower.startswith("project"):
            is_title = True
        # Condition 2: Title-case appearance, reasonable length, not all caps, not forbidden keyword
        elif (
            3 <= num_words <= 15 and
            not any(kw in line_lower for kw in FORBIDDEN_TITLE_KEYWORDS) and
            not line.isupper() and
            line.istitle() # Check if it's mostly Title Case
        ):
            is_title = True
            # Additional check: if it looks like a date range, it's probably a job title, not project
            if DATE_RANGE_MATCH_PATTERN.search(line):
                is_title = False

        is_url = re.match(r'https?://', line_lower)

        # New Project Begins
        if is_title or is_url:
            if current_project["Project Title"] or current_project["Description"]:
                full_desc = "\n".join(current_project["Description"])
                techs = extract_skills_from_text(full_desc, skill_library) # Changed to extract_skills_from_text
                current_project["Technologies Used"].update(techs)

                # If no title was explicitly set, try to infer from the first description line
                if not current_project["Project Title"] and current_project["Description"]:
                    first_desc_line = current_project["Description"][0]
                    if len(first_desc_line.split()) <= 10 and first_desc_line.istitle() and not any(kw in first_desc_line.lower() for kw in FORBIDDEN_TITLE_KEYWORDS):
                        current_project["Project Title"] = first_desc_line
                        current_project["Description"] = current_project["Description"][1:] # Remove it from description

                project_details.append({
                    "Project Title": current_project["Project Title"] if current_project["Project Title"] else "Unnamed Project",
                    "Description": full_desc.strip(),
                    "Technologies Used": ", ".join(sorted(current_project["Technologies Used"]))
                })

            current_project = {"Project Title": line, "Description": [], "Technologies Used": set()}
        else:
            current_project["Description"].append(line)

    # Add last project
    if current_project["Project Title"] or current_project["Description"]:
        full_desc = "\n".join(current_project["Description"])
        techs = extract_skills_from_text(full_desc, skill_library) # Changed to extract_skills_from_text
        current_project["Technologies Used"].update(techs)

        # If no title was explicitly set for the last project, try to infer
        if not current_project["Project Title"] and current_project["Description"]:
            first_desc_line = current_project["Description"][0]
            if len(first_desc_line.split()) <= 10 and first_desc_line.istitle() and not any(kw in first_desc_line.lower() for kw in FORBIDDEN_TITLE_KEYWORDS):
                current_project["Project Title"] = first_desc_line
                current_project["Description"] = current_project["Description"][1:] # Remove it from description

        project_details.append({
            "Project Title": current_project["Project Title"] if current_project["Project Title"] else "Unnamed Project",
            "Description": full_desc.strip(),
            "Technologies Used": ", ".join(sorted(current_project["Technologies Used"]))
        })

    return project_details


def extract_languages(text):
    """
    Extracts known languages from resume text.
    Returns a comma-separated string of detected languages or 'Not Found'.
    """
    languages_list = set()
    cleaned_full_text = clean_text(text)

    # De-duplicated, lowercase language set
    all_languages = list(set([
        "english", "hindi", "spanish", "french", "german", "mandarin", "japanese", "arabic",
        "russian", "portuguese", "italian", "korean", "bengali", "marathi", "telugu", "tamil",
        "gujarati", "urdu", "kannada", "odia", "malayalam", "punjabi", "assamese", "kashmiri",
        "sindhi", "sanskrit", "dutch", "swedish", "norwegian", "danish", "finnish", "greek",
        "turkish", "hebrew", "thai", "vietnamese", "indonesian", "malay", "filipino", "swahili",
        "farsi", "persian", "polish", "ukrainian", "romanian", "czech", "slovak", "hungarian",
        "chinese", "tagalog", "nepali", "sinhala", "burmese", "khmer", "lao", "pashto", "dari",
        "uzbek", "kazakh", "azerbaijani", "georgian", "armenian", "albanian", "serbian",
        "croatian", "bosnian", "bulgarian", "macedonian", "slovenian", "estonian", "latvian",
        "lithuanian", "icelandic", "irish", "welsh", "gaelic", "maltese", "esperanto", "latin",
        "ancient greek", "modern greek", "yiddish", "romani", "catalan", "galician", "basque",
        "breton", "cornish", "manx", "frisian", "luxembourgish", "sami", "romansh", "sardinian",
        "corsican", "occitan", "provencal", "walloon", "flemish", "afrikaans", "zulu", "xhosa",
        "sesotho", "setswana", "shona", "ndebele", "venda", "tsonga", "swati", "kikuyu",
        "luganda", "kinyarwanda", "kirundi", "lingala", "kongo", "yoruba", "igbo", "hausa"
    ]))

    sorted_all_languages = sorted(all_languages, key=len, reverse=True)

    # Step 1: Try to locate a language-specific section
    section_match = LANGUAGE_SECTION_PATTERN.search(cleaned_full_text)

    if section_match:
        start_index = section_match.end()
        # Optional: stop at next known section
        stop_words = ['education', 'experience', 'skills', 'certifications', 'awards', 'publications', 'interests', 'hobbies']
        end_index = len(cleaned_full_text)
        for stop in stop_words:
            m = re.search(r'\b' + re.escape(stop) + r'\b', cleaned_full_text[start_index:], re.IGNORECASE)
            if m:
                end_index = start_index + m.start()
                break

        language_chunk = cleaned_full_text[start_index:end_index]
    else:
        language_chunk = cleaned_full_text

    # Step 2: Match known languages
    for lang in sorted_all_languages:
        # Use word boundaries for exact matches and allow for common suffixes like " (fluent)"
        pattern = r'\b' + re.escape(lang) + r'(?:\s*\(?[a-z\s,-]+\)?)?\b'
        if re.search(pattern, language_chunk, re.IGNORECASE):
            if lang == "de":
                languages_list.add("German")
            else:
                languages_list.add(lang.title())

    return ", ".join(sorted(languages_list)) if languages_list else "Not Mentioned" # Changed to Not Mentioned


def format_work_history(work_list):
    if not work_list:
        return "Not Found"
    formatted_entries = []
    for entry in work_list:
        parts = []
        if entry.get("Title"):
            parts.append(f"• **{entry['Title']}**")
        if entry.get("Company"):
            # Removed "at" from here
            parts.append(f"{entry['Company']}")
        if entry.get("Start Date") and entry.get("End Date"):
            parts.append(f"({entry['Start Date']} - {entry['End Date']})")
        elif entry.get("Start Date"):
            parts.append(f"(Since {entry['Start Date']})")
        formatted_entries.append(" ".join(parts).strip())
    return "\n".join(formatted_entries) if formatted_entries else "Not Found"

def format_project_details(proj_list):
    if not proj_list:
        return "Not Found"
    formatted_entries = []
    for entry in proj_list:
        parts = []
        if entry.get("Project Title"):
            parts.append(f"• **{entry['Project Title']}**")
        if entry.get("Technologies Used"):
            parts.append(f"({entry['Technologies Used']})")
        if entry.get("Description") and entry["Description"].strip():
            desc_snippet = entry["Description"].split('\n')[0][:100] + "..." if len(entry["Description"]) > 100 else entry["Description"]
            parts.append(f'"{desc_snippet}"')
        formatted_entries.append(" ".join(parts).strip())
    return "\n".join(formatted_entries) if formatted_entries else "Not Found"

# REPLACED generate_concise_ai_suggestion and generate_detailed_hr_assessment
def generate_hr_summary(candidate_name, domain, final_score, semantic_score, experience):
    if final_score >= 70:
        return f"{candidate_name} shows a strong overall match. Highly recommended for interview."
    elif final_score >= 50:
        return f"{candidate_name} shows a reasonable match with the job requirements. Consider for interview after manual review."
    elif final_score >= 40 and semantic_score > 60 and experience >= 5:
        return (
            f"{candidate_name} brings senior-level experience and domain familiarity, "
            "though some JD-specific keywords may be missing. Recommend manual review for potential fit."
        )
    elif experience == 0:
        return (
            f"{candidate_name} is an early-career candidate with foundational skills. "
            "Not suitable for this senior role, but may fit entry-level openings."
        )
    else:
        return (
            f"{candidate_name} currently shows limited match with the requirements. "
            "Suggest holding for future or alternate roles aligned to their background."
        )

# New LLM-style HR summary generation function



def generate_llm_hr_summary(
    name,
    job_domain,
    score,
    experience,
    matched_skills,
    missing_skills,
    cgpa,
    jd_text,
    tone="professional"
):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime

    # -------------------------------
    # ADMIN EMAIL (ONLY ON FALLBACK)
    # -------------------------------
    def notify_admin(reason):
        try:
            gmail = st.secrets.get("GMAIL_ADDRESS")
            app_password = st.secrets.get("GMAIL_APP_PASSWORD")
            admin_email = "manav.nagpal2005@gmail.com"

            if not gmail or not app_password:
                return  # silently ignore

            msg = MIMEMultipart()
            msg["From"] = gmail
            msg["To"] = admin_email
            msg["Subject"] = "⚠️ ScreenerPro: Gemini Fallback Used"

            body = f"""
Gemini fallback was triggered.

Candidate: {name}
Job Domain: {job_domain}
Score: {score}%
Experience: {experience} years

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
            pass  # NEVER break app due to email failure

    # -------------------------------
    # SAFE HARD-CODED FALLBACK
    # -------------------------------
    def fallback_summary(reason):
        notify_admin(reason)
        return f"""
### Overall Fit
{name} shows **moderate alignment** with the {job_domain} role based on resume screening.

### Strengths
- Experience: {experience} years  
- Matched skills: {matched_skills or "Limited overlap"}  
- Academic performance: {cgpa or "Not specified"}

### Weak Areas / Risks
- Missing skills: {missing_skills or "No major gaps identified"}

### Role Alignment
Candidate aligns with **entry to mid-level expectations**.

### Final Recommendation
Recommended for further consideration with targeted upskilling.
"""

    # -------------------------------
    # TRY GEMINI FIRST
    # -------------------------------
    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")

        prompt = f"""
You are an HR professional writing an internal candidate assessment.

Rules:
- DO NOT mention AI, models, or automation
- Tone: {tone}

Candidate:
Name: {name}
Domain: {job_domain}
Score: {score}%
Experience: {experience} years
CGPA: {cgpa}
Matched Skills: {matched_skills}
Missing Skills: {missing_skills}

Write exactly:
Overall Fit
Strengths
Weak Areas / Risks
Role Alignment
Final Recommendation
"""

        response = model.generate_content(prompt)
        text = response.text if response and response.text else ""

        if not text.strip():
            return fallback_summary("Empty Gemini response")

        return text.strip()

    except Exception as e:
        return fallback_summary(str(e))


@st.cache_data(show_spinner="Calculating match score...")
@st.cache_data(show_spinner="Calculating match score...")
def compute_production_match_score(jd_text, resume_text, jd_skills, matched_skills, _model=None):
    """
    Computes final match score between JD and Resume using either SentenceTransformer embeddings
    or TF-IDF cosine similarity if the model fails to load.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer

    # Normalize and clean
    jd_clean = ' '.join(jd_text.lower().split())
    resume_clean = ' '.join(resume_text.lower().split())

    # Exact skill match score
    exact_score = round(len(matched_skills) / (len(jd_skills) + 1e-6) * 100, 2)

    semantic_score = 0.0
    if _model is not None:
        try:
            # Use SentenceTransformer embeddings
            emb1 = _model.encode(jd_clean, convert_to_numpy=True, show_progress_bar=False)
            emb2 = _model.encode(resume_clean, convert_to_numpy=True, show_progress_bar=False)
            from sklearn.metrics.pairwise import cosine_similarity
            semantic_score = float(cosine_similarity([emb1], [emb2])[0][0] * 100)
        except Exception as e:
            st.warning(f"⚠️ Semantic embedding failed, switching to TF-IDF fallback: {e}")
            _model = None  # Trigger fallback

    # Fallback: TF-IDF similarity
    if _model is None:
        vectorizer = TfidfVectorizer().fit([jd_clean, resume_clean])
        tfidf_vectors = vectorizer.transform([jd_clean, resume_clean])
        from sklearn.metrics.pairwise import cosine_similarity
        semantic_score = float(cosine_similarity(tfidf_vectors[0], tfidf_vectors[1])[0][0] * 100)

    # Weighted average
    final_score = round((0.6 * semantic_score) + (0.4 * exact_score), 2)
    return final_score, round(semantic_score, 2), round(exact_score, 2)



def create_mailto_link(recipient_email, candidate_name, job_title="Job Opportunity", sender_name="Recruiting Team"):
    subject = urllib.parse.quote(f"Invitation for Interview - {job_title} - {candidate_name}")
    body = urllib.parse.quote(f"""Dear {candidate_name},

We were very impressed with your profile and would like to invite you for an interview for the {job_title} position.

Best regards,

The {sender_name}""")
    return f"mailto:{recipient_email}?subject={subject}&body={body}"

@st.cache_data
def generate_certificate_pdf(html_content):
    """Converts HTML content to PDF bytes."""
    try:
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
    except Exception as e:
        st.error(f"❌ Failed to generate PDF certificate: {e}")
        return None

def send_certificate_email(recipient_email, candidate_name, score, certificate_pdf_content, gmail_address, gmail_app_password, company_name, certificate_id):
    """
    Sends an email with the candidate's certificate as a PDF attachment.
    Requires a valid Gmail address and a Gmail App Password for authentication.
    """
    if not gmail_address or not gmail_app_password:
        st.error("❌ Email sending is not configured. Please ensure your Gmail address and App Password secrets are set in Streamlit.")
        st.info("To set up Gmail App Password: Go to your Google Account -> Security -> 2-Step Verification (turn on if off) -> App passwords. Generate a new app password and use it here.")
        return False

    msg = MIMEMultipart('mixed')
    msg['Subject'] = f"🎉 You've Earned It! Here's Your Certification from ScreenerPro"
    msg['From'] = gmail_address
    msg['To'] = recipient_email

    plain_text_body = f"""Hi {candidate_name},

Congratulations on successfully clearing the ScreenerPro resume screening process with a score of {score:.1f}%!
Your resume was screened by {company_name}.

We’re proud to award you an official certificate recognizing your skills and employability.
Your unique Certificate ID is: {certificate_id}

You can add this to your resume, LinkedIn, or share it with employers to stand out.

Have questions? Contact us at screenerpro.ai@gmail.com

🚀 Keep striving. Keep growing.

– Team ScreenerPro
"""

    html_body = f"""
    <html>
        <body>
            <p>Hi {candidate_name},</p>
            <p>Congratulations on successfully clearing the ScreenerPro resume screening process with a score of <strong>{score:.1f}%</strong>!</p>
            <p>Your resume was screened by <strong>{company_name}</strong>.</p>
            <p>We’re proud to award you an official certificate recognizing your skills and employability.</p>
            <p>Your unique Certificate ID is: <strong>{certificate_id}</strong></p>
            <p>You can add this to your resume, LinkedIn, or share it with employers to stand out.</p>
            <p>Have questions? Contact us at screenerpro.ai@gmail.com</p>
            <p>🚀 Keep striving. Keep growing.</p>
            <p>– Team ScreenerPro</p>
        </body>
    </html>
    """

    msg_alternative = MIMEMultipart('alternative')
    msg_alternative.attach(MIMEText(plain_text_body, 'plain'))
    msg_alternative.attach(MIMEText(html_body, 'html'))
    
    msg.attach(msg_alternative)

    if certificate_pdf_content:
        try:
            attachment = MIMEBase('application', 'pdf')
            attachment.set_payload(certificate_pdf_content)
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', 'attachment', filename=f'ScreenerPro_Certificate_{candidate_name.replace(' ', '_')}.pdf')
            msg.attach(attachment)
            st.info(f"Attached certificate PDF to email for {candidate_name}.")
        except Exception as e:
            st.error(f"Failed to attach certificate PDF: {e}")
    else:
        st.warning("No PDF content generated to attach to email.")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(gmail_address, gmail_app_password)
            smtp.send_message(msg)
        st.success(f"✅ Certificate email sent to {recipient_email}!")
        return True
    except smtplib.SMTPAuthenticationError:
        st.error("❌ Failed to send email: Authentication error. Please check your Gmail address and App Password.")
        st.info("Ensure you have generated an App Password for your Gmail account and used it instead of your regular password.")
    except Exception as e:
        st.error(f"❌ Failed to send email: {e}")
    return False
# ------------------ NEW FUNCTION ------------------
def send_comprehensive_table_to_hr(comprehensive_df, session_username):
    gmail_address = "screenerpro.ai@gmail.com"
    gmail_app_password = "udwi life nbdv kgdt"

    try:
        from io import BytesIO
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email import encoders
        import smtplib

        # Create Excel attachment
        excel_buffer = BytesIO()
        comprehensive_df.to_excel(excel_buffer, index=False, engine="openpyxl")
        excel_buffer.seek(0)

        # ✅ Detect correct score column (handles "Score (%)" or similar)
        score_column = None
        for col in comprehensive_df.columns:
            if "score" in col.lower():
                score_column = col
                break

        if score_column:
            top_candidates = comprehensive_df.sort_values(by=score_column, ascending=False).head(5)
            avg_score = comprehensive_df[score_column].mean()
        else:
            top_candidates = comprehensive_df.head(5)
            avg_score = None

        # ✅ Safe average score formatting
        avg_score_str = f"{avg_score:.2f}" if avg_score is not None else "N/A"

        # Build HTML table for top candidates
        top_table_html = top_candidates.to_html(index=False, escape=False, border=0,
                                               classes='top-table',
                                               justify='center')

        # HTML body
        html_body = f"""
        <html>
        <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                color: #333333;
            }}
            .header {{
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                text-align: center;
                font-size: 20px;
                border-radius: 8px;
            }}
            .content {{
                margin: 20px;
            }}
            .top-table {{
                border-collapse: collapse;
                width: 100%;
            }}
            .top-table th, .top-table td {{
                border: 1px solid #dddddd;
                text-align: center;
                padding: 8px;
            }}
            .top-table th {{
                background-color: #f2f2f2;
            }}
            .summary {{
                margin-top: 20px;
                font-size: 16px;
            }}
        </style>
        </head>
        <body>
            <div class="header">📊 ScreenerPro - Candidate Results</div>
            <div class="content">
                <p>Dear HR,</p>
                <p>The comprehensive candidate screening is complete. Here are some quick insights:</p>
                <div class="summary">
                    <strong>Average Score:</strong> {avg_score_str}<br>
                    <strong>Top 5 Candidates:</strong>
                </div>
                {top_table_html}
                <p>The full detailed results are attached in the Excel file.</p>
                <p>Regards,<br>ScreenerPro System</p>
            </div>
        </body>
        </html>
        """

        # Build the email
        msg = MIMEMultipart()
        msg['From'] = gmail_address
        msg['To'] = session_username
        msg['Subject'] = "📊 ScreenerPro: Comprehensive Candidate Results"
        msg.attach(MIMEText(html_body, 'html'))

        # Attach Excel
        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(excel_buffer.read())
        encoders.encode_base64(attachment)
        attachment.add_header(
            'Content-Disposition',
            'attachment; filename="Comprehensive_Results.xlsx"'
        )
        msg.attach(attachment)

        # Send email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_address, gmail_app_password)
            server.send_message(msg)

        st.success(f"✅ Comprehensive table and insights sent to {session_username}")
        return True
    except Exception as e:
        st.error(f"❌ Failed to send email: {e}")
        return False


# Wrapper for extract_text_from_file to be used with ProcessPoolExecutor
def _extract_text_wrapper(file_info):
    file_data_bytes, file_name, file_type = file_info
    text = extract_text_from_file(file_data_bytes, file_name, file_type)
    return file_name, text

# Updated function to extract certifications as per user's request
def extract_certifications(text):
    """
    Extracts certification-related phrases from resume text.
    Returns a list of unique certifications found.
    """
    # Sample list of known certifications (extend this based on your app's database)
    KNOWN_CERTIFICATIONS = [
        "AWS Certified", "AWS Certified Solutions Architect", "AWS Certified Developer",
        "Google Professional Data Engineer", "Google Cloud Certified", "GCP Certified",
        "Certified Data Scientist", "Azure Fundamentals", "Microsoft Certified",
        "Certified Ethical Hacker", "CEH", "CISSP", "CompTIA Security+",
        "Certified Scrum Master", "CSM", "PMP", "Project Management Professional",
        "Six Sigma", "Lean Six Sigma", "TOGAF", "ITIL Foundation",
        "Certified Kubernetes Administrator", "CKA",
        "TensorFlow Developer", "DeepLearning.AI", "Machine Learning by Stanford",
        "CS50", "IBM Data Science", "Google ML Crash Course", "HackerRank Certified",
        "Udemy", "Coursera", "edX", "LinkedIn Learning", "NPTEL", "Scaler", "DataCamp",
        "Python for Everybody", "SQL for Data Science", "HarvardX", "MITx", "AI For Everyone"
    ]

    # Optional pattern for capturing general "Certification in XYZ"
    GENERIC_CERT_PATTERN = re.compile(r'\b(certification|certificate|certified)\s*(in|of)?\s*([\w\s\-\+&\.]{2,100})', re.IGNORECASE)


    found_certifications = set()
    text_clean = text.replace('\r', '').replace('\t', ' ')
    lower_text = text_clean.lower()

    # Match known certifications
    for cert in KNOWN_CERTIFICATIONS:
        if cert.lower() in lower_text:
            found_certifications.add(cert)

    # Match generic "Certification in XYZ"
    for match in GENERIC_CERT_PATTERN.finditer(text_clean):
        full_cert = match.group(0).strip()
        if 4 < len(full_cert) < 100:
            found_certifications.add(full_cert)

    return sorted(found_certifications) if found_certifications else ["Not Found"]

# New function to check timeline consistency - NO LONGER USED FOR CALCULATION
def check_timeline_consistency(work_history_raw):
    """
    Checks for significant gaps (more than 3 years) in the parsed work history.
    Returns True if no large gaps, False otherwise.
    """
    # This function is retained for logical completeness but its result is not used for scoring
    # to improve performance as per user request.
    if not work_history_raw or len(work_history_raw) < 2:
        return True # No gaps to check if less than 2 entries

    parsed_dates = []
    for entry in work_history_raw:
        start_str = entry.get("Start Date")
        end_str = entry.get("End Date")

        try:
            # Attempt to parse start date
            if start_str:
                try:
                    start_date = datetime.strptime(start_str.strip().replace(',', ''), '%B %Y')
                except ValueError:
                    try:
                        start_date = datetime.strptime(start_str.strip().replace(',', ''), '%b %Y')
                    except ValueError:
                        start_date = datetime(int(start_str.strip()), 1, 1) # Assume January for year-only
            else:
                start_date = None

            # Attempt to parse end date
            if end_str and end_str.lower() != 'present':
                try:
                    end_date = datetime.strptime(end_str.strip().replace(',', ''), '%B %Y')
                except ValueError:
                    try:
                        end_date = datetime.strptime(end_str.strip().replace(',', ''), '%b %Y')
                    except ValueError:
                        end_date = datetime(int(end_str.strip()), 12, 31) # Assume December for year-only
            else:
                end_date = datetime.now() # 'present' means current date

            if start_date and end_date:
                parsed_dates.append((start_date, end_date))
        except Exception:
            # Skip entries that cannot be parsed
            continue

    if not parsed_dates or len(parsed_dates) < 2:
        return True # Not enough valid entries to check for gaps

    # Sort entries by start date
    parsed_dates.sort(key=lambda x: x[0])

    for i in range(len(parsed_dates) - 1):
        current_end = parsed_dates[i][1]
        next_start = parsed_dates[i+1][0]

        # Calculate gap in months
        gap_months = (next_start.year - current_end.year) * 12 + (next_start.month - current_end.month)

        # Consider a gap significant if it's more than 36 months (3 years)
        if gap_months > 36:
            return False # Found a large gap
    return True # No large gaps found

# New function to verify claimed experience - NO LONGER USED FOR CALCULATION
def verify_experience(resume_text, extracted_years):
    """
    Compares explicitly stated experience (e.g., "10+ years") with extracted years.
    Returns True if consistent, False if a clear contradiction is found.
    """
    # This function is retained for logical completeness but its result is not used for scoring
    # to improve performance as per user request.
    text_lower = resume_text.lower()
    
    # Look for explicit "X+ years experience" claims
    match = re.search(r'(\d+)\+\s*(?:year|yrs|years)\s*(?:of)?\s*experience', text_lower)
    if match:
        claimed_years = int(match.group(1))
        # If claimed_years is significantly higher than extracted_years
        if claimed_years > extracted_years + 3: # Allow for some discrepancy
            return False
    
    # Look for "fresh graduate" or "entry-level" vs high extracted experience
    if ("fresh graduate" in text_lower or "entry-level" in text_lower) and extracted_years >= 2:
        return False

    return True

# New function to get consistency score - NO LONGER USED FOR CALCULATION
def get_consistency_score(resume_text, extracted_years, work_history_raw):
    """
    Calculates a consistency score based on timeline gaps and claimed vs extracted experience.
    Score starts at 100 and deductions are made for inconsistencies.
    """
    # This function is retained for logical completeness but its result is not used for scoring
    # to improve performance as per user request.
    score = 100

    if not check_timeline_consistency(work_history_raw):
        score -= 20 # Deduct for significant timeline gaps
    
    if not verify_experience(resume_text, extracted_years):
        score -= 30 # Deduct for contradiction in claimed vs extracted experience

    return max(0, score) # Ensure score doesn't go below 0

# Updated extract_resume_highlights as per user's latest prompt
# Modified to use existing extraction functions
def extract_resume_highlights(text, skill_library): # Added skill_library as argument
    highlights = {}
    text_lower = text.lower() # Convert to lowercase once for efficiency

    # 📘 Education - Use the dedicated extract_education function
    highlights["Education"] = extract_education(text)

    # 💼 Recent Role - Extract from work history
    work_history = extract_work_history(text)
    if work_history:
        highlights["Recent Role"] = work_history[0].get("Title", "Not Found")
    else:
        highlights["Recent Role"] = "Not Found"

    # 📊 Experience – Assume extracted earlier if you're using parser, or use the dedicated function
    highlights["Experience"] = extract_years_of_experience(text)

    # 🧠 Top Skills - Use the dedicated extract_skills_from_text function
    all_skills = extract_skills_from_text(text, skill_library) # Pass skill_library
    highlights["Skills"] = all_skills[:8] if all_skills else ["Not Found"]

    # 🏅 Certifications - Use the dedicated extract_certifications function
    highlights["Certifications"] = extract_certifications(text)

    # 🌐 Languages Known - Use the dedicated extract_languages function
    highlights["Languages"] = extract_languages(text)

    # 🕒 Availability
    highlights["Availability"] = "Immediate Joiner" if "immediate" in text_lower else "Not Mentioned"

    # 📍 Location - Use the dedicated extract_location function
    highlights["Location"] = extract_location(text)

    # 🛠 Tools Used
    ALL_TOOLS = [
        # Engineering/Dev
        "GitHub", "Bitbucket", "Jira", "Slack", "Postman", "Kubernetes", "Docker", "VSCode", "Eclipse", "Android Studio", "PyCharm",
        # Data / BI
        "Tableau", "Power BI", "MLflow", "Google Analytics", "BigQuery", "Looker", "Matplotlib", "Seaborn", "Snowflake",
        # Design / Creative
        "Figma", "Adobe XD", "Canva", "Photoshop", "Illustrator", "Premiere Pro",
        # Business / PM / Marketing
        "Salesforce", "Zoho CRM", "HubSpot", "MS Office", "Trello", "Asana", "ClickUp", "Notion", "SurveyMonkey",
        # Misc
        "Hadoop", "Spark", "Firebase", "Ansible", "Jupyter", "RStudio", "Notepad++"
    ]
    tools_found = set()
    for tool in ALL_TOOLS:
        if re.search(rf"\b{re.escape(tool.lower())}\b", text_lower): # Search in lowercased text
            tools_found.add(tool)
    highlights["Tools"] = ", ".join(sorted(tools_found)) if tools_found else "Not Found"

    # 🏆 Achievements
    ACHIEVEMENT_TERMS = [
        "published", "presented", "awarded", "recognized", "top performer",
        "achievement", "mentor", "volunteer", "scholarship", "winner", "gold medal",
        "rank holder", "speaker", "conference", "hackathon", "competition", "olympiad"
    ]
    achievements = [term for term in ACHIEVEMENT_TERMS if re.search(rf"\b{re.escape(term)}\b", text_lower)]
    # Ensure all found achievements are displayed, or "Not Found" if none
    highlights["Achievements"] = ", ".join(sorted(set(achievements))).title() if achievements else "Not Found"

    # 💻 Portfolio / GitHub / Personal Site
    portfolio_match = re.search(r"(https?://(?:www\.)?(?:github|linkedin|portfolio|personal|behance|dribbble|notion|medium)\.[^\s]+)", text, re.I)
    highlights["Portfolio"] = portfolio_match.group(0) if portfolio_match else "Not Found"

    # 🌟 Soft Skills (Smart Matching)
    SOFT_SKILLS = [
        "communication", "leadership", "teamwork", "adaptability", "problem solving", "time management",
        "critical thinking", "creativity", "collaboration", "negotiation", "empathy", "emotional intelligence"
    ]
    soft_found = [s for s in SOFT_SKILLS if re.search(rf"\b{re.escape(s)}\b", text_lower)]
    highlights["Soft Skills"] = ", ".join(sorted(set(soft_found))).title() if soft_found else "Not Found"

    # 💡 Notable Projects Highlight (Smart Summary Placeholder)
    highlights["Notable Projects Highlight"] = "Found" if "project" in text_lower else "Not Found"

    # 📚 Publications
    if re.search(r"\b(published|journal|conference|doi|research|arxiv|whitepaper)\b", text_lower):
        highlights["Publications"] = "Found"
    else:
        highlights["Publications"] = "Not Found"

    return highlights


# Modified _process_single_resume_for_screener_page
def _process_single_resume_for_screener_page(file_name, text, jd_text, 
                                             jd_name_for_results,
                                             skill_library, # Passed skill_library instead of priority skills
                                             max_experience,
                                             summary_tone): # Added summary_tone
    """
    Processes a single resume (pre-extracted text)
    for the main screener page and returns a dictionary of results.
    This function is designed to be run in a ProcessPoolExecutor.
    """
    try:
        if text.startswith("[ERROR]"):
            return {
                "File Name": file_name,
                "Candidate Name": file_name.replace('.pdf', '').replace('.jpg', '').replace('.jpeg', '').replace('.png', '').replace('_', ' ').title(),
                "Score (%)": 0, "Years Experience": 0, "CGPA (4.0 Scale)": None,
                "Email": "Not Found", "Phone Number": "Not Found", "Location": "Not Found",
                "Languages Known": "Not Found", 
                "Education Details": "Not Found",
                "Work History": "Not Found", "Project Details": "Not Found",
                "Latest Education": "Not Found", 
                "Most Recent Job": "Not Found",  
                "Certifications": "Not Found",   
                "Resume Consistency Score": 0, # Set to 0, not calculated
                "AI Suggestion": f"Error: {text.replace('[ERROR] ', '')}",
                "Detailed HR Assessment": f"Error processing resume: {text.replace('[ERROR] ', '')}",
                "Matched Keywords": "", "Missing Skills": "",
                "Semantic Similarity": 0.0,
                "Exact Match Score": 0.0,
                "Resume Raw Text": "",
                "Resume Word Count": 0, # Set to 0, not calculated
                "JD Used": jd_name_for_results, "Date Screened": datetime.now().date(),
                "Certificate ID": str(uuid.uuid4()), "Certificate Rank": "Not Applicable",
                "Tag": "❌ Text Extraction Error",
                # New highlight fields (initialized for error case)
                "Top Skills Highlight": "Not Found",
                "Availability": "Not Found",
                "Soft Skills": "Not Found",
                "Notable Projects Highlight": "Not Found",
                "Awards/Recognitions": "Not Found",
                "Tools Used Highlight": "Not Found",
                "Publications": "Not Found",
                "Portfolio/GitHub": "Not Found",
                "Manual Shortlist": False # Initialize manual shortlist
            }

        exp = extract_years_of_experience(text)
        email = extract_email(text)
        phone = extract_phone_number(text)
        
        work_history_raw = extract_work_history(text)
        project_details_raw = extract_project_details(text, skill_library) 
        
        education_details_formatted = extract_education(text) 
        work_history_formatted = format_work_history(work_history_raw)
        project_details_formatted = format_project_details(project_details_raw)

        candidate_name = extract_name(text) or file_name.replace('.pdf', '').replace('.jpg', '').replace('.jpeg', '').replace('.png', '').replace('_', ' ').title()
        cgpa = extract_cgpa(text)
        
        # Resume Word Count and Consistency Score are NOT calculated for performance
        resume_word_count = 0 
        resume_consistency_score = 0 

        # New: Extract all resume highlights using the combined function
        # Pass skill_library to extract_resume_highlights
        highlights = extract_resume_highlights(text, skill_library) 
        
        # Assign extracted highlights to their respective variables/keys, ensuring string conversion for lists
        latest_education = highlights.get("Education", "Not Found")
        most_recent_job = highlights.get("Recent Role", "Not Found")
        
        # Ensure Certifications is a string
        certifications = highlights.get("Certifications", ["Not Found"])
        if isinstance(certifications, list):
            certifications = ", ".join(certifications) if certifications != ["Not Found"] else "Not Found"

        # Ensure Top Skills Highlight is a string
        top_skills_highlight = highlights.get("Skills", ["Not Found"])
        if isinstance(top_skills_highlight, list):
            top_skills_highlight = ", ".join(top_skills_highlight) if top_skills_highlight != ["Not Found"] else "Not Found"
        
        availability = highlights.get("Availability", "Not Found")
        soft_skills = highlights.get("Soft Skills", "Not Found") # Now using the highlight output
        notable_projects_highlight = highlights.get("Notable Projects Highlight", "Not Found") # Now using the highlight output
        
        awards_recognitions = highlights.get("Achievements", "Not Found") # Corrected key to Achievements
        tools_used_highlight = highlights.get("Tools", "Not Found") # Corrected key
        publications = highlights.get("Publications", "Not Found") # Now using the highlight output
        portfolio_github = highlights.get("Portfolio", "Not Found") # Corrected key to Portfolio
        
        languages_known_highlight = highlights.get("Languages", "Not Found") # Corrected key
        location = highlights.get("Location", "Not Found") # Corrected key


        # Use the new extract_skills_from_text function
        resume_skills = extract_skills_from_text(text, skill_library)
        jd_skills_local = extract_skills_from_text(jd_text, skill_library) # Renamed to avoid conflict

        matched_keywords = list(set(resume_skills).intersection(set(jd_skills_local)))
        missing_skills = list(set(jd_skills_local).difference(set(resume_skills)))

        # No more weighted keyword overlap score with the new exact match logic
        
        # Use the new production match score function, passing jd_skills and matched_keywords
        final_score, semantic_similarity, exact_score = compute_production_match_score(
            jd_text, text, jd_skills_local, matched_keywords, global_sentence_model 
        )
        
        # Detect job domain for HR summary
        job_domain = detect_job_domain(jd_name_for_results, jd_text)
        
        # Generate HR summary using the new LLM-style function
        hr_summary = generate_llm_hr_summary(
    name=candidate_name,
    score=final_score,
    experience=exp,
    matched_skills=matched_keywords,
    missing_skills=missing_skills,
    cgpa=cgpa,
    job_domain=job_domain,
    jd_text=jd_text,
    tone=summary_tone

        )

        certificate_id = str(uuid.uuid4())
        # Default to a general rank if no higher rank is achieved
        certificate_rank = "⚪ Profile Reviewed" # New default rank for all processed resumes

        if final_score >= 90:
            certificate_rank = "🏅 Elite Match"
        elif final_score >= 80:
            certificate_rank = "⭐ Strong Match"
        elif final_score >= 75:
            certificate_rank = "✅ Good Fit"
        elif final_score >= 65:
            certificate_rank = "⚪ Low Fit"
        elif final_score >= 50:
            certificate_rank = "🟡 Basic Fit"
        # If score is below 50, it will remain "⚪ Profile Reviewed"
        
        # Determine Tag
        tag = "❌ Limited Match"
        if final_score >= 90 and exp >= 5 and exp <= max_experience and semantic_similarity >= 0.85 and (cgpa is None or cgpa >= 3.5):
            tag = "👑 Exceptional Match"
        elif final_score >= 80 and exp >= 3 and exp <= max_experience and semantic_similarity >= 0.7 and (cgpa is None or cgpa >= 3.0):
            tag = "🔥 Strong Candidate"
        elif final_score >= 60 and exp >= 1 and exp <= max_experience and (cgpa is None or cgpa >= 2.5):
            tag = "✨ Promising Fit"
        elif final_score >= 40:
            tag = "⚠️ Needs Review"

        return {
            "File Name": file_name,
            "Candidate Name": candidate_name,
            "Score (%)": final_score,
            "Years Experience": exp,
            "CGPA (4.0 Scale)": cgpa,
            "Email": email or "Not Found",
            "Phone Number": phone or "Not Found",
            "Location": location or "Not Found", 
            "Languages Known": languages_known_highlight, 
            "Education Details": education_details_formatted,
            "Work History": work_history_formatted,
            "Project Details": project_details_formatted,
            "Latest Education": latest_education, 
            "Most Recent Job": most_recent_job,  
            "Certifications": certifications,   
            "Resume Consistency Score": resume_consistency_score, # Now 0
            "AI Suggestion": hr_summary, 
            "Detailed HR Assessment": hr_summary, 
            "Matched Keywords": ", ".join(matched_keywords),
            "Missing Skills": ", ".join(missing_skills),
            "Semantic Similarity": semantic_similarity,
            "Exact Match Score": exact_score,
            "Resume Raw Text": text,
            "Resume Word Count": resume_word_count, # Now 0
            "JD Used": jd_name_for_results, "Date Screened": datetime.now().date(),
            "Certificate ID": certificate_id,
            "Certificate Rank": certificate_rank,
            "Tag": tag,
            # New highlight fields
            "Top Skills Highlight": top_skills_highlight,
            "Availability": availability,
            "Soft Skills": soft_skills,
            "Notable Projects Highlight": notable_projects_highlight,
            "Awards/Recognitions": awards_recognitions,
            "Tools Used Highlight": tools_used_highlight,
            "Publications": publications,
            "Portfolio/GitHub": portfolio_github,
            "Manual Shortlist": False # Initialize manual shortlist status
        }
    except Exception as e:
        print(f"CRITICAL ERROR: Unhandled exception processing {file_name}: {e}")
        traceback.print_exc()
        return {
            "File Name": file_name,
            "Candidate Name": file_name.replace('.pdf', '').replace('.jpg', '').replace('.jpeg', '').replace('.png', '').replace('_', ' ').title(),
            "Score (%)": 0, "Years Experience": 0, "CGPA (4.0 Scale)": None,
            "Email": "Not Found", "Phone Number": "Not Found", "Location": "Not Found",
            "Languages Known": "Not Found", 
            "Education Details": "Not Found",
            "Work History": "Not Found", "Project Details": "Not Found",
            "Latest Education": "Not Found", 
            "Most Recent Job": "Not Found",  
            "Certifications": "Not Found",   
            "Resume Consistency Score": 0, # Set to 0, not calculated
            "AI Suggestion": f"Critical Error: {e}",
            "Detailed HR Assessment": f"Critical Error processing resume: {e}",
            "Matched Keywords": "", "Missing Skills": "",
            "Semantic Similarity": 0.0,
            "Exact Match Score": 0.0,
            "Resume Raw Text": "",
            "Resume Word Count": 0, # Set to 0, not calculated
            "JD Used": jd_name_for_results, "Date Screened": datetime.now().date(),
            "Certificate ID": str(uuid.uuid4()), "Certificate Rank": "Not Applicable",
            "Tag": "❌ Critical Processing Error",
            # New highlight fields (initialized for error case)
            "Top Skills Highlight": "Not Found",
            "Availability": "Not Found",
            "Soft Skills": "Not Found",
            "Notable Projects Highlight": "Not Found",
            "Awards/Recognitions": "Not Found",
            "Tools Used Highlight": "Not Found",
            "Publications": "Not Found",
            "Portfolio/GitHub": "Not Found",
            "Manual Shortlist": False # Initialize manual shortlist status
        }


# Modified resume_screener_page to no longer accept save_certificate_to_firestore_public_func
# Modified resume_screener_page to no longer accept save_certificate_to_firestore_public_func
def resume_screener_page():
    st.title("🧠 ScreenerPro – AI-Powered Resume Screener")
    
    # =============================
    # INITIALIZATION (Only runs once on first load)
    # =============================
    if "screening_data" not in st.session_state:
        st.session_state.screening_data = []
    if "comprehensive_df" not in st.session_state:
        st.session_state.comprehensive_df = pd.DataFrame()

    # =============================
    # CLEAN RESET (Only runs when user clicks an explicit reset button)
    # 🔥 FIX: Replaced the redundant and unconditional wipe blocks with this clean, conditional block.
    # This prevents the page from resetting every time a widget is clicked.
    # =============================
    if st.session_state.get("reset_screener", False):
        st.session_state.screening_data = []
        st.session_state.comprehensive_df = pd.DataFrame()
        st.session_state['resume_raw_texts'] = {}
        st.session_state['processing_needed'] = True
        st.session_state['jd_text_global'] = ""
        st.session_state['jd_name_global'] = ""
        st.session_state.reset_screener = False  # turn flag OFF
    
    # Load the skill library once
    skill_library = load_skill_library()
    if not skill_library:
        st.error("Cannot proceed without a loaded skills_library.txt. Please ensure the file exists and is accessible.")
        st.stop() 

    if 'screening_cutoff_score' not in st.session_state:
        st.session_state['screening_cutoff_score'] = 75
    if 'screening_min_experience' not in st.session_state:
        st.session_state['screening_min_experience'] = 2
    if 'screening_max_experience' not in st.session_state:
        st.session_state['screening_max_experience'] = 10
    if 'screening_min_cgpa' not in st.session_state:
        st.session_state['screening_min_cgpa'] = 2.5
    
    # Define all required columns for the DataFrame
    REQUIRED_DF_COLUMNS = [
        "Manual Shortlist", # Moved to front
        "File Name", "Candidate Name", "Score (%)", "Years Experience", "CGPA (4.0 Scale)",
        "Email", "Phone Number", "Location", "Languages Known", 
        "Education Details",
        "Work History", "Project Details", "AI Suggestion", "Detailed HR Assessment",
        "Matched Keywords", "Missing Skills",
        "Semantic Similarity", 
        "Exact Match Score",
        "Resume Raw Text", "Resume Word Count", # Retained column name, but value will be 0
        "Latest Education", 
        "Most Recent Job",  
        "Certifications",   
        "Resume Consistency Score", # Retained column name, but value will be 0
        "JD Used", "Date Screened", "Certificate ID", "Certificate Rank", "Tag",
        
        # New highlight fields
        "Top Skills Highlight",
        "Availability",
        "Soft Skills",
        "Notable Projects Highlight",
        "Awards/Recognitions",
        "Tools Used Highlight",
        "Publications",
        "Portfolio/GitHub"
    ]

    # Initialize comprehensive_df if not present, ensuring all columns
    if 'comprehensive_df' not in st.session_state:
        st.session_state['comprehensive_df'] = pd.DataFrame(columns=REQUIRED_DF_COLUMNS)
    else:
        # Ensure existing DataFrame has all required columns, add missing ones
        current_cols = st.session_state['comprehensive_df'].columns.tolist()
        missing_cols = [col for col in REQUIRED_DF_COLUMNS if col not in current_cols]
        if missing_cols:
            for col in missing_cols:
                st.session_state['comprehensive_df'][col] = None # Add missing columns with None/NaN
            # Reorder columns to ensure "Manual Shortlist" is first and all others are in order
            st.session_state['comprehensive_df'] = st.session_state['comprehensive_df'].reindex(columns=REQUIRED_DF_COLUMNS, fill_value=None)
        # Ensure 'Manual Shortlist' is boolean for the checkbox
        if 'Manual Shortlist' in st.session_state['comprehensive_df'].columns:
            st.session_state['comprehensive_df']['Manual Shortlist'] = st.session_state['comprehensive_df']['Manual Shortlist'].astype(bool)

    if 'resume_raw_texts' not in st.session_state:
        st.session_state['resume_raw_texts'] = {}
    if 'certificate_html_content' not in st.session_state:
        st.session_state['certificate_html_content'] = ""
    if 'jd_skills_for_chart' not in st.session_state: 
        st.session_state['jd_skills_for_chart'] = []
    
    # 🔥 FIX: Optional Safety Patch for Certificate Generator (PART 3) - from previous turn
    if "jd_text_global" not in st.session_state:
        st.session_state['jd_text_global'] = ""
    if "jd_name_global" not in st.session_state:
        st.session_state['jd_name_global'] = ""
    # End PART 3 FIX
    
    # New state variable to track if processing is needed
    if 'processing_needed' not in st.session_state:
        st.session_state['processing_needed'] = True
    if 'last_uploaded_files_hash' not in st.session_state:
        st.session_state['last_uploaded_files_hash'] = None
    if 'last_jd_text_hash' not in st.session_state:
        st.session_state['last_jd_text_hash'] = None


    # Initial check for Tesseract (main process only)
    tesseract_cmd_path = get_tesseract_cmd()
    if not tesseract_cmd_path:
        st.error("Tesseract OCR engine not found. Please ensure it's installed and in your system's PATH.")
        st.info("On Streamlit Community Cloud, ensure you have a `packages.txt` file in your repository's root with `tesseract-ocr` and `tesseract-ocr-eng` listed.")
        st.stop()

    st.markdown("## ⚙️ Define Job Requirements & Screening Criteria")
    col1, col2 = st.columns([2, 1])

    with col1:
        jd_text = ""
        jd_name_for_results = ""

        # Ensure hash state exists
        if "last_jd_text_hash" not in st.session_state:
            st.session_state["last_jd_text_hash"] = None

        # JD options map
        job_roles = {
            "Upload my own": {
                "source": "upload"
            }
        }

        # --------------------------------------------------
        # 1️⃣ GLOBAL JDs (shared across platform)
        # --------------------------------------------------
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        global_jd_folder = os.path.join(BASE_DIR, "data")

        if os.path.exists(global_jd_folder):
            for fname in os.listdir(global_jd_folder):
                if fname.endswith(".txt"):
                    title = fname.replace(".txt", "").replace("_", " ").title()
                    job_roles[f"{title} (Global JD)"] = {
                        "source": "global",
                        "path": os.path.join(global_jd_folder, fname),
                        "title": title
                    }

        # --------------------------------------------------
        # 2️⃣ COMPANY-SPECIFIC JDs (Firestore)
        # --------------------------------------------------
        company_name = st.session_state.get("user_company")

        if company_name:
            company_jds = fs_get_jds(company_name)

            for jd in company_jds:
                job_roles[f"{jd['title']} (Company JD)"] = {
                    "source": "firestore",
                    "title": jd.get("title", "Company JD"),
                    # ✅ FIX: map Firestore `description` correctly
                    "content": jd.get("description", "")
                }

        # --------------------------------------------------
        # 3️⃣ JD SELECTION
        # --------------------------------------------------
        jd_option = st.selectbox(
            "📌 Select a Pre-Loaded Job Role or Upload Your Own Job Description",
            list(job_roles.keys())
        )

        selected_jd = job_roles.get(jd_option)

        # --------------------------------------------------
        # 4️⃣ HANDLE JD SOURCE
        # --------------------------------------------------
        if selected_jd["source"] == "upload":
            jd_file = st.file_uploader(
                "Upload Job Description (TXT, PDF)",
                type=["txt", "pdf"]
            )

            if jd_file:
                jd_text = extract_text_from_file(
                    jd_file.read(),
                    jd_file.name,
                    jd_file.type
                )
                jd_name_for_results = jd_file.name.replace(".pdf", "").replace(".txt", "")
            else:
                jd_name_for_results = "Uploaded JD"

        elif selected_jd["source"] == "global":
            with open(selected_jd["path"], "r", encoding="utf-8") as f:
                jd_text = f.read()
            jd_name_for_results = selected_jd["title"]

        elif selected_jd["source"] == "firestore":
            # ✅ CORRECT & SAFE JD TEXT EXTRACTION
            jd_text = (
                selected_jd.get("content")
                or selected_jd.get("description")
                or ""
            )

            jd_name_for_results = selected_jd.get("title", "Company JD")

            # ---------------- DEBUG ----------------
            # st.write("DEBUG Screener JD object:", selected_jd)
            # st.write("DEBUG JD text type:", type(jd_text))
            # st.write("DEBUG JD text length:", len(jd_text))
            # --------------------------------------

            if not jd_text.strip():
                st.warning("⚠️ Selected Company JD has no content.")
                st.stop()

        # --------------------------------------------------
        # 5️⃣ TRACK JD CHANGES
        # --------------------------------------------------
        if jd_text:
            current_hash = hashlib.md5(jd_text.encode("utf-8")).hexdigest()

            if current_hash != st.session_state.get("last_jd_text_hash"):
                st.session_state["processing_needed"] = True
                st.session_state["last_jd_text_hash"] = current_hash

            # Preserve globally (certificates + scoring)
            st.session_state["jd_text_global"] = jd_text
            st.session_state["jd_name_global"] = jd_name_for_results

            # --------------------------------------------------
            # 6️⃣ VIEW JD
            # --------------------------------------------------
            with st.expander("📝 View Loaded Job Description"):
                st.text_area(
                    "Job Description Content",
                    jd_text,
                    height=200,
                    disabled=True,
                    label_visibility="collapsed"
                )

            # --------------------------------------------------
            # 7️⃣ KEYWORD CLOUD
            # --------------------------------------------------
            st.markdown("---")
            st.markdown("## ☁️ Job Description Keyword Cloud")

            st.session_state["jd_skills_for_chart"] = extract_skills_from_text(
                jd_text,
                skill_library
            )

            jd_words = " ".join(st.session_state["jd_skills_for_chart"])

            if jd_words:
                wordcloud = WordCloud(
                    width=800,
                    height=400,
                    background_color="white",
                    collocations=False
                ).generate(jd_words)

                fig, ax = plt.subplots(figsize=(10, 5))
                ax.imshow(wordcloud, interpolation="bilinear")
                ax.axis("off")
                st.pyplot(fig)
                plt.close(fig)
            else:
                st.info("No significant keywords found in the Job Description.")

            st.markdown("---")


    with col2:
        cutoff = st.slider("📈 **Minimum Score Cutoff (%)**", 0, 100, 75, key="min_score_cutoff_slider", help="Candidates scoring below this percentage will be flagged for closer review or considered less suitable.")
        st.session_state['screening_cutoff_score'] = cutoff

        min_experience = st.slider("💼 **Minimum Experience Required (Years)**", 0, 15, 2, key="min_exp_slider", help="Candidates with less than this experience will be noted.")
        st.session_state['screening_min_experience'] = min_experience

        max_experience = st.slider("⬆️ **Maximum Experience Allowed (Years)**", 0, 20, 10, key="max_exp_slider", help="Candidates with more than this experience might be considered overqualified or outside the target range.")
        st.session_state['screening_max_experience'] = max_experience

        min_cgpa = st.slider("🎓 **Minimum CGPA Required (4.0 Scale)**", 0.0, 4.0, 2.5, 0.1, key="min_cgpa_slider", help="Candidates with CGPA below this value (normalized to 4.0) will be noted.")
        st.session_state['screening_min_cgpa'] = min_cgpa

        st.markdown("---")
        st.info("Once criteria are set, upload resumes below to begin screening.")

        # Optional Upgrade: “Smart Tone Selector”
        summary_tone = st.selectbox(
            "🗣️ **Choose HR Summary Tone**",
            ["Professional", "Friendly", "Critical"],
            index=0, # Default to Professional
            help="Select the desired tone for the AI-generated HR summaries."
        )

    # Removed Skill Prioritization section (High Priority Skills, Medium Priority Skills)

    uploaded_resume_files = st.file_uploader("📄 **Upload Resumes (PDF, JPG, PNG)**", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True, help="Upload one or more PDF or image resumes for screening. Each file must be less than 1MB.")

    resume_files_to_process = []
    if uploaded_resume_files:
        current_files_hash = hashlib.md5(str([f.name for f in uploaded_resume_files]).encode('utf-8')).hexdigest()
        if current_files_hash != st.session_state['last_uploaded_files_hash']:
            st.session_state['processing_needed'] = True
            st.session_state['last_uploaded_files_hash'] = current_files_hash
        
        for file in uploaded_resume_files:
            if file.size > 1 * 1024 * 1024: # 1MB limit
                st.error(f"❌ File '{file.name}' is too large ({file.size / (1024*1024):.2f} MB). Please upload files smaller than 1MB.")
            else:
                resume_files_to_process.append(file)
        
        if not resume_files_to_process:
            st.warning("No valid resume files to process (all were too large or none uploaded).")
            st.session_state['processing_needed'] = False # No files to process, so no processing needed

    # Only run processing if explicitly needed (new files or JD) or if df is empty
    if st.session_state['processing_needed'] and jd_text and resume_files_to_process:
        # Start overall timer
        total_screening_start_time = time.time()

        results = []

        total_resumes = len(resume_files_to_process)
        
        # --- PHASE 1: Parallel Text Extraction ---
        extracted_texts_info = [] # Stores (file_name, text) tuples
        file_infos_for_extraction = []
        for file in resume_files_to_process: # Corrected variable name here
            file_data_bytes = file.read() # Read file content into memory once
            file_infos_for_extraction.append((file_data_bytes, file.name, file.type))

        # Define a chunk size for processing (not directly used for batching here, but good practice for large lists)
        CHUNK_SIZE = 10 # Process 10 resumes at a time to manage memory and CPU usage

        # Use ProcessPoolExecutor for CPU-bound text extraction
        with st.spinner(f"Extracting text from {total_resumes} resumes..."):
            with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor: 
                text_futures = [executor.submit(_extract_text_wrapper, info) for info in file_infos_for_extraction]
                
                for future in as_completed(text_futures):
                    try:
                        extracted_texts_info.append(future.result())
                    except Exception as e:
                        st.error(f"Error extracting text for a resume: {e}")
                        # The error handling in _extract_text_wrapper already returns an error string
                
        # so this outer catch is more for unexpected executor issues.
        st.success("Text extraction complete.")

        # Separate successfully extracted texts from failed ones
        successfully_extracted_texts_map = {name: text for name, text in extracted_texts_info if not text.startswith("[ERROR]")}
        failed_extraction_results = [{
            "File Name": name,
            "Candidate Name": name.replace('.pdf', '').replace('.jpg', '').replace('.jpeg', '').replace('.png', '').replace('_', ' ').title(),
            "Score (%)": 0, "Years Experience": 0, "CGPA (4.0 Scale)": None,
            "Email": "Not Found", "Phone Number": "Not Found", "Location": "Not Found",
            "Languages Known": "Not Found", 
            "Education Details": "Not Found",
            "Work History": "Not Found", "Project Details": "Not Found",
            "Latest Education": "Not Found", 
            
            "Most Recent Job": "Not Found",  
            "Certifications": "Not Found",   
            "Resume Consistency Score": 0, # Set to 0, not calculated
            "AI Suggestion": f"Error: {text.replace('[ERROR] ', '')}",
            "Detailed HR Assessment": f"Error processing resume: {text.replace('[ERROR] ', '')}",
            "Matched Keywords": "", "Missing Skills": "",
            "Semantic Similarity": 0.0,
            "Exact Match Score": 0.0,
            "Resume Raw Text": "",
            "Resume Word Count": 0, # Set to 0, not calculated
            "JD Used": jd_name_for_results, "Date Screened": datetime.now().date(),
            "Certificate ID": str(uuid.uuid4()), "Certificate Rank": "Not Applicable",
            
            "Tag": "❌ Text Extraction Error",
            # New highlight fields (initialized for error case)
            "Top Skills Highlight": "Not Found",
            "Availability": "Not Found",
            "Soft Skills": "Not Found",
            "Notable Projects Highlight": "Not Found",
            
            "Awards/Recognitions": "Not Found",
            "Tools Used Highlight": "Not Found",
            "Publications": "Not Found",
            "Portfolio/GitHub": "Not Found",
            "Manual Shortlist": False # Initialize manual shortlist status
        } for name, text in extracted_texts_info if text.startswith("[ERROR]")]

        if not successfully_extracted_texts_map:
            st.warning("No resumes had readable text extracted. Please check the files and try again.")
            st.session_state['comprehensive_df'] = pd.DataFrame(columns=REQUIRED_DF_COLUMNS) # Clear the df if no successful extraction, re-init with all columns
            st.session_state['processing_needed'] = False # No more processing needed until new input
            return
        
        # --- PHASE 2: Parallel Individual Resume Analysis ---
        with st.spinner(f"Analyzing {len(successfully_extracted_texts_map)} resumes with AI models concurrently..."):
            processing_args = []
            for file_name in successfully_extracted_texts_map:
                text = successfully_extracted_texts_map[file_name]
                processing_args.append((
                    file_name, text, jd_text, 
                    jd_name_for_results, skill_library, st.session_state['screening_max_experience'], summary_tone 
                ))
            
            # Use ProcessPoolExecutor for CPU-bound analysis
            with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor: 
                analysis_futures = [executor.submit(_process_single_resume_for_screener_page, *args) for args in processing_args]
                
                for future in as_completed(analysis_futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as exc:
                        st.error(f"Resume processing generated an exception for one resume: {exc}")
            
        # Add results from failed extractions back to the list
        results.extend(failed_extraction_results)

        st.success("Resume analysis complete. Displaying results.")
        
        if not results:
            st.warning("No resumes were successfully processed. Please check the files and try again.")
            st.session_state['comprehensive_df'] = pd.DataFrame(columns=REQUIRED_DF_COLUMNS)  # Clear the df, re-init with all columns
            st.session_state['processing_needed'] = False  # No more processing needed until new input
            return

        # Create DataFrame from results and reindex to ensure all columns are present and in order
        temp_df = pd.DataFrame(results).sort_values(by="Score (%)", ascending=False).reset_index(drop=True)
        st.session_state['comprehensive_df'] = temp_df.reindex(columns=REQUIRED_DF_COLUMNS, fill_value=None)

        # Ensure 'Manual Shortlist' is boolean for the checkbox
        if 'Manual Shortlist' in st.session_state['comprehensive_df'].columns:
            st.session_state['comprehensive_df']['Manual Shortlist'] = st.session_state['comprehensive_df']['Manual Shortlist'].astype(bool)

        st.session_state['comprehensive_df'].to_csv("results.csv", index=False)

        # ============================
        # AUTO-SAVE AFTER SCREENING
        # ============================
        # ============================
        # AUTO-SAVE AFTER SCREENING
        # ============================
        try:
            auto_save_after_screening(st.session_state.get("username", "anonymous"), st.session_state['comprehensive_df'])
            st.toast("💾 Auto-saved to cloud")
        except Exception as e:
            st.warning(f"⚠️ Auto-save failed: {e}")

        # FIX 2 — Prevent history reload after save
        st.session_state.data_loaded_on_startup = True
        st.session_state.skip_history_reload = True


        total_screening_end_time = time.time()
        st.info(f"Total screening time: {total_screening_end_time - total_screening_start_time:.2f} seconds.")
        st.session_state['processing_needed'] = False  # Mark processing as complete


    # Only display the rest of the UI if there is data in the dataframe
    if not st.session_state['comprehensive_df'].empty:
        st.markdown("---")
        st.markdown("## 📊 Candidate Score Comparison")
        st.caption("Visual overview of how each candidate ranks against the job requirements.")
        dark_mode = st.session_state.get("dark_mode_main", False)

        # Only show graph if number of resumes is less than 25
        if not st.session_state['comprehensive_df'].empty and len(st.session_state['comprehensive_df']) <= 25:
            fig, ax = plt.subplots(figsize=(12, 7))
            colors = ['#4CAF50' if s >= cutoff else '#FFC107' if s >= (cutoff * 0.75) else '#F44346' for s in st.session_state['comprehensive_df']['Score (%)']]
            bars = ax.bar(st.session_state['comprehensive_df']['Candidate Name'], st.session_state['comprehensive_df']['Score (%)'], color=colors)
            ax.set_xlabel("Candidate", fontsize=14, color='white' if dark_mode else 'black')
            ax.set_ylabel("Score (%)", fontsize=14, color='white' if dark_mode else 'black')
            ax.set_title("Resume Screening Scores Across Candidates", fontsize=16, fontweight='bold', color='white' if dark_mode else 'black')
            ax.set_ylim(0, 100)
            plt.xticks(rotation=60, ha='right', fontsize=10, color='white' if dark_mode else 'black')
            plt.yticks(fontsize=10, color='white' if dark_mode else 'black')
            ax.tick_params(axis='x', colors='white' if dark_mode else 'black')
            ax.tick_params(axis='y', colors='white' if dark_mode else 'black')

            if dark_mode:
                fig.patch.set_facecolor('#1E1E1E')
                ax.set_facecolor('#2D2D2D')
                ax.spines['bottom'].set_color('white')
                ax.spines['top'].set_color('white')
                ax.spines['left'].set_color('white')
                ax.spines['right'].set_color('white')
            
            for bar in bars:
                yval = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, yval + 1, f"{yval:.1f}", ha='center', va='bottom', fontsize=9, color='white' if dark_mode else 'black')
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
        elif not st.session_state['comprehensive_df'].empty and len(st.session_state['comprehensive_df']) > 25:
            st.info(f"Skipping graph display for {len(st.session_state['comprehensive_df'])} resumes to optimize performance. Displaying results in table format below.")
        else:
            st.info("Upload resumes to see a comparison chart.")

        # START REPLACEMENT BLOCK
        st.markdown("## 👑 Top Candidate AI Assessment")
        
        if not st.session_state['comprehensive_df'].empty:
            top_candidate = st.session_state['comprehensive_df'].iloc[0]
            
            name = top_candidate['Candidate Name']
            experience = top_candidate['Years Experience']
            cgpa = top_candidate['CGPA (4.0 Scale)']
            semantic_score = top_candidate['Semantic Similarity']
            exact_score = top_candidate['Exact Match Score'] # Corrected variable name here
            final_score = top_candidate['Score (%)']
            email = top_candidate['Email']
            work_history = top_candidate['Work History']
            project_details = top_candidate['Project Details']
            
            # Retrieve all highlight fields
            latest_education = top_candidate['Latest Education']
            most_recent_job = top_candidate['Most Recent Job']
            certifications = top_candidate['Certifications']
            top_skills_highlight = top_candidate['Top Skills Highlight']
            availability = top_candidate['Availability']
            soft_skills = top_candidate['Soft Skills']
            notable_projects_highlight = top_candidate['Notable Projects Highlight']
            awards_recognitions = top_candidate['Awards/Recognitions']
            
            tools_used_highlight = top_candidate['Tools Used Highlight'] 
            publications = top_candidate['Publications']
            portfolio_github = top_candidate['Portfolio/GitHub']
            languages_known_highlight = top_candidate['Languages Known'] 
            location = top_candidate['Location'] 


            # Retrieve matched and missing skills as flat lists (comma-separated strings)
            matched_skills_str = top_candidate['Matched Keywords']
            missing_skills_str = top_candidate['Missing Skills']

            # Convert to lists for processing in display
            matched_skills = [s.strip() for s in matched_skills_str.split(',')] if matched_skills_str else []
            missing_skills = [s.strip() for s in missing_skills_str.split(',')] if missing_skills_str else []
            
            # Retrieve JD skills from session state for the chart
            jd_skills_for_chart = st.session_state.get('jd_skills_for_chart', [])

            # Badge Label
            badge = ""
            if experience > 10:
                badge = "👴 Overqualified"
            elif experience == 0:
                badge = "🧑‍🎓 Fresh Graduate"
            elif final_score >= 75:
                badge = "🔥 Top Match"

            # 🔹 Experience & Education Summary
            st.markdown(f"""
            ### 👤 {name if name else 'Candidate Name'} {badge}
            📅 **Experience**: {experience} years  
            🎓 **CGPA**: {cgpa if pd.notna(cgpa) else 'N/A'} (4.0 Scale)  
            """)
            
            # 8. Experience & Score Table
            st.markdown("### 🧮 Score & Experience Summary")
            st.table(pd.DataFrame({
                "Field": ["Final Score", "Experience", "Semantic Similarity", "Exact Match Score"],
                "Value": [f"{final_score:.2f}%", f"{experience} yrs", f"{semantic_score:.2f}%", f"{exact_score:.2f}%"]
            }))

            # 4. Add a “Score Tag” Badge
            score_tag = ""
            score_tag_color = ""
            if final_score >= 80:
                score_tag = "🟢 Top Match"
                score_tag_color = "green"
            elif 60 <= final_score < 80:
                score_tag = "🟡 Good Match"
                score_tag_color = "orange"
            else:
                score_tag = "🔴 Low Match"
                score_tag_color = "red"
            st.markdown(f"### 🏆 Score Tag: <span style='color:{score_tag_color}'>{score_tag}</span>", unsafe_allow_html=True)


            # 🔹 Decision Label (kept for consistency with existing logic)
            if final_score >= 75:
                decision = "✅ **Strong Match — Shortlist for Interview**"
                badge_decision = "🟢"
            elif final_score >= 60:
                decision = "🟡 **Good Match — Review for Interview**"
                badge_decision = "🟡"
            elif final_score >= 40:
                decision = "⚠️ **Partial Match — Needs Manual Review**"
                badge_decision = "🟠"
            else:
                decision = "❌ **Low Match — Not Recommended for This Role**"
                badge_decision = "🔴"

            st.markdown(f"""
            ### 🎯 Final Decision: {badge_decision} {decision}
            """)
            
            # 10. Red Flag Detector
            if experience > st.session_state['screening_max_experience'] and exact_score < 30: 
                st.error("⚠️ Red Flag: Candidate has high experience but a low exact skill match. This could indicate irrelevant experience for this specific role.")
            elif experience < st.session_state['screening_min_experience'] and final_score < 50:
                st.warning("⚠️ Red Flag: Candidate has low experience and a low overall score. Unlikely to be a good fit.")
            # Consistency score check is removed since it's no longer calculated.
            # if resume_consistency_score < 70: 
            #     st.error(f"⚠️ Red Flag: Low Resume Consistency Score ({resume_consistency_score}/100). This may indicate timeline gaps or inconsistent experience claims.")


            # 🔹 Skills Section (Visual Tags)
            st.markdown("### ✅ Matched Skills (from JD)")
            if matched_skills:
                st.markdown(" ".join([f"<span style='background:#e0f7fa; padding:4px 8px; margin:2px; border-radius:8px; display:inline-block;'>{skill}</span>" for skill in matched_skills]), unsafe_allow_html=True)
            else:
                st.write("None")

            st.markdown("### ❌ Missing Skills (from JD)")
            if missing_skills:
                st.markdown(" ".join([f"<span style='background:#ffe0e0; padding:4px 8px; margin:2px; border-radius:8px; display:inline-block;'>{skill}</span>" for skill in missing_skills]), unsafe_allow_html=True)
            else:
                st.write("None")

            # 2. Skill Gap Suggestions
            if missing_skills:
                top_gaps = ', '.join(sorted(missing_skills)[:3]) 
                st.info(f"🧠 *To improve fit for this role, candidate may focus on:* **{top_gaps}**")

            # 3. Donut Chart: JD vs Resume Skills
            st.markdown("### 📊 Skill Match Visualization")
            if jd_skills_for_chart:
                matched_count = len(matched_skills)
                unmatched_count = len(jd_skills_for_chart) - matched_count
                
                if matched_count + unmatched_count > 0:
                    labels = ['Matched Skills', 'Unmatched Skills']
                    sizes = [matched_count, unmatched_count]
                    colors = ['#4CAF50', '#F44346'] # Green for matched, Red for unmatched
                    explode = (0.05, 0) # Slightly explode the matched slice

                    fig, ax = plt.subplots(figsize=(8, 8))
                    wedges, texts, autotexts = ax.pie(
                        sizes, 
                        labels=labels, 
                        colors=colors, 
                        autopct='%1.1f%%', 
                        startangle=90, 
                        pctdistance=0.85, # Distance of percentage labels from center
                        wedgeprops=dict(width=0.3, edgecolor='w'), # Creates the donut hole
                        explode=explode
                    )
                    
                    # Draw a circle in the center to make it a donut chart
                    centre_circle = plt.Circle((0,0),0.70,fc='white')
                    fig.gca().add_artist(centre_circle)

                    # Add text in the center
                    total_jd_skills_count = len(jd_skills_for_chart)
                    ax.text(0, 0, f'Total JD Skills:\n{total_jd_skills_count}', 
                            horizontalalignment='center', verticalalignment='center', 
                            fontsize=14, color='black')

                    # Set text color for percentages
                    for autotext in autotexts:
                        autotext.set_color('white') # Make percentages white for better contrast

                    ax.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
                    ax.set_title("JD Skill Match Overview", fontsize=16, fontweight='bold', color='black')
                    
                    # Dark mode adjustments (if needed, though pie charts are often okay with white bg)
                    if dark_mode:
                        fig.patch.set_facecolor('#1E1E1E')
                        ax.set_facecolor('#2D2D2D')
                        ax.title.set_color('white')
                        for text_obj in texts:
                            text_obj.set_color('white')

                    st.pyplot(fig)
                    plt.close(fig)
                else:
                    st.info("No skills to visualize. Please ensure the Job Description has identifiable skills.")
            else:
                st.info("No JD skills available for visualization. Please ensure a Job Description is loaded and has identifiable skills.")


            # 🔹 Smart HR Summary (Now uses the LLM-style function)
            smart_summary = generate_llm_hr_summary(
    name=name,
    score=final_score,
    experience=experience,
    matched_skills=matched_skills,
    missing_skills=missing_skills,
    cgpa=cgpa,
    jd_text=jd_text,
    job_domain=detect_job_domain(jd_name_for_results, jd_text),
    tone=summary_tone
            )
            st.markdown("### 🧠 HR Summary")
            st.markdown(f"> {smart_summary}")


            # 6. Alternate Job Suggestion
            if final_score < 40:
                alt_roles = ["Junior Data Analyst", "Entry-Level Software Developer", "Marketing Intern", "Customer Support Specialist"]
                st.warning(f"🤔 Candidate may be better suited for for: {', '.join(alt_roles)}. Consider reviewing their profile for these roles.")

            # 7. Top Projects/Experience Highlight - Enhanced UI
            st.markdown("### 📌 Resume Highlights")
            
            # Using columns for better layout
            col_edu_cert, col_role_exp = st.columns(2)
            with col_edu_cert:
                st.markdown(f"**📘 Latest Education**: {latest_education}")
                st.markdown(f"**🏅 Certifications**: {certifications}")
            with col_role_exp:
                st.markdown(f"**💼 Recent Role**: {most_recent_job}")
                st.markdown(f"**📊 Experience**: {experience} years")
            
            st.markdown("---") # Separator for more clarity

            col_skills_lang, col_avail_loc = st.columns(2)
            with col_skills_lang:
                st.markdown(f"**🧠 Top Skills**: {top_skills_highlight}")
                st.markdown(f"**🌐 Languages Known**: {languages_known_highlight}")
            with col_avail_loc:
                st.markdown(f"**🕒 Availability**: {availability}")
                if location != "Not Found":
                    st.markdown(f"**📍 Location**: {location}")
            
            st.markdown("---") # Separator

            col_tools_achiev, col_portfolio_pub = st.columns(2)
            with col_tools_achiev:
                st.markdown(f"**🛠 Tools**: {tools_used_highlight}")
                st.markdown(f"**🏆 Achievements**: {awards_recognitions}")
            with col_portfolio_pub:
                if portfolio_github and portfolio_github != "Not Found" and re.match(r'https?://', portfolio_github):
                    st.markdown(f"**💻 Portfolio**: [{portfolio_github}]({portfolio_github})")
                else:
                    st.markdown(f"**💻 Portfolio**: {portfolio_github}")
                st.markdown(f"**📚 Publications**: {publications}")

            st.markdown("---") # Separator

            col_soft_proj = st.columns(2)
            with col_soft_proj[0]:
                st.markdown(f"**🌟 Soft Skills**: {soft_skills}")
            with col_soft_proj[1]:
                st.markdown(f"**💡 Notable Projects**: {notable_projects_highlight}")


            # 5. Auto Email (Preview Mode)
            if email and email != "Not Found":
                st.success(f"📧 Email found: `{email}`")
                st.markdown("---")
                st.markdown("#### 📤 Interview Invitation Email Preview")
                email_preview = f"""
Dear {name},

Thank you for your application for the position at {st.session_state.get('user_company', 'our company')}. We have carefully reviewed your profile using our AI-powered screening system.
Your Final Match Score for this role is: {final_score:.2f}%

Based on our assessment, your current status is: {'Shortlisted for Interview ✅' if final_score >= st.session_state['screening_cutoff_score'] else 'Not Shortlisted ❌'}

We appreciate your interest in {st.session_state.get('user_company', 'our company')}.
Best regards,

The {st.session_state.get('user_company', 'Hiring')} Team
"""
                st.text_area("Email Content", email_preview, height=250)
                if st.button("🚀 Send Interview Invite Email", key="send_interview_email_button"):
                    st.info(f"Email sending functionality would be triggered here for {email}. (Requires SMTP setup)")

            else:
                st.error("❌ Email address not found in resume. Please contact manually.")
            
            # 9. Download All Results as CSV (for bulk uploads) - Already exists, confirming placement
            st.markdown("---")
            st.info("For detailed analytics, matched keywords, and missing skills for ALL candidates, please navigate to the **Analytics Dashboard**.")

            # Download single candidate summary PDF
            summary_pdf_html = f"""
<html>
<head>
<title>Candidate Summary - {name}</title>
<style>
body {{ font-family: sans-serif; margin: 40px; }}
h1 {{ color: #003049; }}
h2 {{ color: #007c91; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 20px; }}
.score-box {{ border: 2px solid #003049; padding: 15px; border-radius: 8px; margin-bottom: 20px; background: #f9f9f9; }}
.highlight {{ background: #fff3cd; border: 1px solid #ffeeba; padding: 10px; border-radius: 5px; margin-bottom: 10px; }}
.tag {{ display: inline-block; background: #e0f7fa; padding: 3px 6px; border-radius: 4px; margin-right: 5px; margin-bottom: 5px; font-size: 0.9em; }}
</style>
</head>
<body>
<h1>Candidate Screening Summary</h1>
<div class="score-box">
    <h2>{name}</h2>
    <p><strong>Screening Score:</strong> {final_score:.2f}%</p>
    <p><strong>Final Decision:</strong> {decision}</p>
    <p><strong>Years Experience:</strong> {experience} years</p>
    <p><strong>CGPA (4.0 Scale):</strong> {cgpa if pd.notna(cgpa) else 'N/A'}</p>
    <p><strong>Email:</strong> {email if email != "Not Found" else 'N/A'}</p>
</div>
<h2>AI HR Summary</h2>
<p>{smart_summary}</p>
<h2>Skill Match Analysis</h2>
<p><strong>Matched Skills:</strong> {''.join([f'<span class="tag" style="background:#e8f5e9;">{s}</span>' for s in matched_skills]) if matched_skills else 'None'}</p>
<p><strong>Missing Skills:</strong> {''.join([f'<span class="tag" style="background:#ffebee;">{s}</span>' for s in missing_skills]) if missing_skills else 'None'}</p>
{f'<div class="highlight"><p><strong>Skill Gap Suggestion:</strong> To improve fit for this role, candidate may focus on: {", ".join(sorted(missing_skills)[:3])}</p></div>' if missing_skills else ''}
{f'<div class="highlight"><p><strong>Alternate Role Suggestion:</strong> Candidate may be better suited for for: {", ".join(alt_roles)}</p></div>' if final_score < 40 else ''}
{f'<div class="highlight"><p><strong>Red Flag:</strong> Experience high but skill match low. Possibly irrelevant experience.</p></div>' if experience > st.session_state['screening_max_experience'] and exact_score < 30 else ''}

<h2>Resume Highlights</h2>
<p><strong>Latest Education:</strong> {latest_education}</p>
<p><strong>Most Recent Job:</strong> {most_recent_job}</p>
<p><strong>Certifications:</strong> {certifications}</p>
<p><strong>Top Skills:</strong> {top_skills_highlight}</p>
<p><strong>Availability:</strong> {availability}</p>
<p><strong>Soft Skills:</strong> {soft_skills}</p>
<p><strong>Notable Projects:</strong> {notable_projects_highlight}</p>
<p><strong>Awards/Recognitions:</strong> {awards_recognitions}</p>
<p><strong>Tools Used:</strong> {tools_used_highlight}</p>
<p><strong>Publications:</strong> {publications}</p>
<p><strong>Portfolio/GitHub:</strong> {portfolio_github}</p>
<p><strong>Languages Known:</strong> {languages_known_highlight}</p>
<p><strong>Location:</strong> {location}</p>

<h2>Work History</h2>
<p>{work_history}</p>

<h2>Project Details</h2>
<p>{project_details}</p>
</body>
</html>
"""
            summary_pdf_bytes = generate_certificate_pdf(summary_pdf_html)

            if summary_pdf_bytes:
                st.download_button(
                    label="⬇️ Download Candidate Summary (PDF)",
                    data=summary_pdf_bytes,
                    file_name=f"Candidate_Summary_{name.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key="download_summary_pdf"
                )
            else:
                st.info("No candidates processed yet to determine the top candidate.")
        # END REPLACEMENT BLOCK

        st.markdown("---")
        st.markdown("## 🌟 Candidates Meeting Criteria Overview")
        st.caption("Candidates automatically identified as meeting your defined score, experience, and CGPA criteria.")

        # --- New Shortlisting Configuration (Moved to main screen) ---
        st.markdown("---")
        st.markdown("🎯 **Shortlisting Configuration**")
        col_shortlist_percent, col_min_score_shortlist = st.columns(2)
        with col_shortlist_percent:
            shortlist_percent = st.slider(
                "Select Shortlisting Percentage",
                min_value=5,
                max_value=100,
                value=15,
                step=5,
                help="Choose how many top candidates to shortlist based on AI score"
            )
        with col_min_score_shortlist:
            min_score_for_shortlist = st.number_input(
                "Minimum Score for Auto-Shortlist (%)",
                min_value=0,
                max_value=100,
                value=st.session_state['screening_cutoff_score'],
                step=1,
                help="Only candidates with scores above this value are considered for auto-shortlisting."
            )
        
        auto_shortlist_mode = st.checkbox("Toggle Auto-Shortlist Mode (Experimental)", help="In this mode, the system determines the cutoff based on the mean score plus 0.5 standard deviations (AI-powered dynamic cutoff). Otherwise, it uses the selected percentage.")

        # Filter the DataFrame based on criteria set in the sidebar
        filtered_by_min_score = st.session_state['comprehensive_df'][
            (st.session_state['comprehensive_df']['Score (%)'] >= min_score_for_shortlist) &
            (st.session_state['comprehensive_df']['Years Experience'] >= st.session_state['screening_min_experience']) &
            (st.session_state['comprehensive_df']['Years Experience'] <= st.session_state['screening_max_experience'])
        ].copy()

        # Filter by CGPA, handling NaN values (only filter non-NaN values)
        if 'CGPA (4.0 Scale)' in filtered_by_min_score.columns and filtered_by_min_score['CGPA (4.0 Scale)'].notnull().any():
            filtered_by_min_score = filtered_by_min_score[
                (filtered_by_min_score['CGPA (4.0 Scale)'].isnull()) |
                (filtered_by_min_score['CGPA (4.0 Scale)'] >= st.session_state['screening_min_cgpa'])
            ]
        
        # Sort by score
        sorted_for_shortlist = filtered_by_min_score.sort_values(by="Score (%)", ascending=False).reset_index(drop=True)

        # --- Decide shortlist ---
        if auto_shortlist_mode:
            # AI-based cutoff: mean + 0.5*std
            scores = sorted_for_shortlist["Score (%)"]
            if not scores.empty:
                cutoff = scores.mean() + 0.5 * scores.std()
                auto_shortlisted_candidates = sorted_for_shortlist[scores >= cutoff]
            else:
                auto_shortlisted_candidates = pd.DataFrame()
        else:
            # Slider-based shortlist
            num_candidates_to_shortlist = int(len(sorted_for_shortlist) * (shortlist_percent / 100))
            auto_shortlisted_candidates = sorted_for_shortlist.head(num_candidates_to_shortlist)

        # --- Display ---
        if not auto_shortlisted_candidates.empty:
            st.session_state['auto_shortlisted_candidates'] = auto_shortlisted_candidates.copy()

            st.success(
                f"**{len(auto_shortlisted_candidates)}** candidate(s) meet your specified criteria "
                f"(Score ≥ {min_score_for_shortlist}%, Experience {st.session_state['screening_min_experience']}-{st.session_state['screening_max_experience']} years, "
                f"minimum CGPA ≥ {st.session_state['screening_min_cgpa']} or N/A)."
            )

            # Add 'Overqualified' column based on max experience
            auto_shortlisted_candidates['Overqualified'] = auto_shortlisted_candidates['Years Experience'] > st.session_state['screening_max_experience']


            display_auto_shortlisted_cols = [ 
                'Candidate Name', 'Score (%)', 'Years Experience', 'CGPA (4.0 Scale)', 'Semantic Similarity', 'Exact Match Score', 'Email', 'AI Suggestion', 'Certificate Rank', 'Languages Known', 'Overqualified' 
            ]

            st.dataframe(
                auto_shortlisted_candidates[display_auto_shortlisted_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Score (%)": st.column_config.ProgressColumn("Score (%)", format="%.1f", min_value=0, max_value=100),
                    "Years Experience": st.column_config.NumberColumn("Years Experience", format="%.1f years"),
                    "CGPA (4.0 Scale)": st.column_config.NumberColumn("CGPA (4.0 Scale)", format="%.2f", min_value=0.0, max_value=4.0),
                    "Semantic Similarity": st.column_config.NumberColumn("Semantic Similarity", format="%.2f", min_value=0, max_value=1),
                    "Exact Match Score": st.column_config.NumberColumn("Exact Match Score", format="%.2f", min_value=0, max_value=1),
                    "Overqualified": st.column_config.Column("Overqualified", help="⚠️ Candidate has more experience than the maximum allowed, flagged as Overqualified")
                }
            )
        else:
            st.warning("No candidates meet the current stringent screening criteria. Try adjusting the score, experience, or CGPA cutoffs.")


        st.markdown("---")
        st.markdown("## 📚 Comprehensive Candidate Table")
        st.caption("Detailed view of all processed candidates with filtering options.")

        # --- Dynamic Filtering UI ---
        filter_cols_1 = st.columns(3)
        with filter_cols_1[0]:
            all_jd_skills = st.session_state.get('jd_skills_for_chart', [])
            selected_skills = st.multiselect(
                "**Filter Candidates by Skill (AND logic):**",
                options=all_jd_skills,
                help="Only candidates possessing ALL selected skills will be shown."
            )
        with filter_cols_1[1]:
            search_query = st.text_input(
                "**Keyword Search:**", 
                placeholder="Name, Email, Location, Raw Text...",
                help="Search for text across Candidate Name, Email, Location, and Resume Raw Text."
            )
        with filter_cols_1[2]:
            selected_tags = st.multiselect(
                "**AI Tag:**",
                options=["👑 Exceptional Match", "🔥 Strong Candidate", "✨ Promising Fit", "⚠️ Needs Review", "❌ Limited Match"],
                help="Filter by AI-generated assessment tags."
            )

        filter_cols_2 = st.columns(3)
        with filter_cols_2[0]:
            min_score_filter, max_score_filter = st.slider(
                "**Score Range (%):**",
                0, 100, (0, 100),
                key="score_range_filter",
                help="Filter candidates by their overall score range."
            )
        with filter_cols_2[1]:
            min_exp_filter, max_exp_filter = st.slider(
                "**Experience Range (Years):**",
                0, 20, (0, 20),
                key="exp_range_filter",
                help="Filter candidates by their years of experience range."
            )
        with filter_cols_2[2]:
            min_cgpa_filter, max_cgpa_filter = st.slider(
                "**CGPA Range (4.0 Scale):**",
                0.0, 4.0, (0.0, 4.0), 0.1,
                key="cgpa_range_filter",
                help="Filter candidates by their CGPA range (normalized to 4.0)."
            )

        filter_cols_3 = st.columns(3)
        with filter_cols_3[0]:
            all_locations = sorted(st.session_state['comprehensive_df']['Location'].unique())
            selected_locations = st.multiselect(
                "**Location:**",
                options=all_locations,
                help="Filter by candidate location."
            )
        with filter_cols_3[1]:
            all_languages_from_df = sorted(list(set(
                lang.strip() for langs_str in st.session_state['comprehensive_df']['Languages Known'] if langs_str != "Not Found" for lang in langs_str.split(',')
            )))
            selected_languages = st.multiselect(
                "**Languages:**",
                options=all_languages_from_df,
                help="Filter by languages spoken by the candidate."
            )
        with filter_cols_3[2]:
            manual_shortlist_only = st.checkbox(
                "**Manually Shortlisted Only**",
                help="Show only candidates that have been manually shortlisted."
            )
        
        filtered_display_df = st.session_state['comprehensive_df'].copy()

        # --- Apply Filters ---
        # 1. Skill Filter (AND logic)
        if selected_skills:
            for skill in selected_skills:
                # Filter rows where the 'Matched Keywords' string contains the skill (case-insensitive)
                filtered_display_df = filtered_display_df[
                    filtered_display_df['Matched Keywords'].str.contains(skill, case=False, na=False)
                ]

        # 2. Keyword Search
        if search_query:
            search_cols = ['Candidate Name', 'Email', 'Location', 'Resume Raw Text']
            # Create a boolean mask where at least one search column contains the query
            mask = filtered_display_df[search_cols].apply(
                lambda col: col.astype(str).str.contains(search_query, case=False, na=False)
            ).any(axis=1)
            filtered_display_df = filtered_display_df[mask]

        # 3. AI Tag Filter
        if selected_tags:
            tag_pattern = '|'.join([re.escape(tag) for tag in selected_tags])
            filtered_display_df = filtered_display_df[
                filtered_display_df['Tag'].str.contains(tag_pattern, case=False, na=False)
            ]

        # 4. Score Range Filter
        filtered_display_df = filtered_display_df[
            (filtered_display_df['Score (%)'] >= min_score_filter) &
            (filtered_display_df['Score (%)'] <= max_score_filter)
        ]

        # 5. Experience Range Filter
        filtered_display_df = filtered_display_df[
            (filtered_display_df['Years Experience'] >= min_exp_filter) &
            (filtered_display_df['Years Experience'] <= max_exp_filter)
        ]

        # 6. CGPA Range Filter (handle NaN)
        if not filtered_display_df.empty and 'CGPA (4.0 Scale)' in filtered_display_df.columns:
            if not (min_cgpa_filter == 0.0 and max_cgpa_filter == 4.0):
                filtered_display_df = filtered_display_df[
                    ((filtered_display_df['CGPA (4.0 Scale)'].notnull()) & 
                     (filtered_display_df['CGPA (4.0 Scale)'] >= min_cgpa_filter) & 
                     (filtered_display_df['CGPA (4.0 Scale)'] <= max_cgpa_filter))
                ]

        # 7. Location Filter
        if selected_locations:
            location_pattern = '|'.join([re.escape(loc) for loc in selected_locations])
            filtered_display_df = filtered_display_df[
                filtered_display_df['Location'].str.contains(location_pattern, case=False, na=False)
            ]

        # 8. Languages Filter
        if selected_languages:
            language_pattern = '|'.join([re.escape(lang) for lang in selected_languages])
            filtered_display_df = filtered_display_df[
                filtered_display_df['Languages Known'].str.contains(language_pattern, case=False, na=False)
            ]

        # 9. Manual Shortlist Only
        if manual_shortlist_only:
            filtered_display_df = filtered_display_df[filtered_display_df['Manual Shortlist'] == True]


        # Convert 'Date Screened' to datetime objects for st.column_config.DateColumn compatibility
        filtered_display_df['Date Screened'] = pd.to_datetime(
            filtered_display_df['Date Screened'], errors='coerce'
        )

        # Define the order of columns, with 'Manual Shortlist' first
        final_display_cols_order = [
            "Manual Shortlist", # Moved to the very first position
            'Candidate Name', 
            'Score (%)', 
            'Years Experience', 
            'CGPA (4.0 Scale)', 
            'Email', 
            'Phone Number', 
            'Location', 
            'Languages Known', 
            'Education Details', 
            'Work History', 
            'Project Details', 
            'Semantic Similarity', 
            'Exact Match Score', 
            'Tag', 
            'Certificate Rank', 
            'Matched Keywords', 
            'Missing Skills', 
            'JD Used', 
            'Date Screened', 
            'Certificate ID', # Hidden, but kept in order
            # New highlight fields
            "Top Skills Highlight",
            "Availability",
            "Soft Skills",
            "Notable Projects Highlight",
            "Awards/Recognitions",
            "Tools Used Highlight",
            "Publications",
            "Portfolio/GitHub"
        ]
        
        # Add 'Overqualified' column based on max experience
        if 'Overqualified' not in filtered_display_df.columns:
            filtered_display_df['Overqualified'] = filtered_display_df['Years Experience'] > st.session_state['screening_max_experience']

        # Ensure all required columns are present before reindexing
        current_cols = filtered_display_df.columns.tolist()
        missing_from_final = [col for col in final_display_cols_order if col not in current_cols]
        for col in missing_from_final:
            filtered_display_df[col] = None
        
        filtered_display_df = filtered_display_df.reindex(columns=final_display_cols_order)

        # Display the interactive data editor
        edited_df = st.data_editor(
            filtered_display_df,
            column_order=final_display_cols_order,
            hide_index=True,
            use_container_width=True,
            key="comprehensive_table_editor",
            column_config={
                # Editable checkbox for manual shortlist
                "Manual Shortlist": st.column_config.CheckboxColumn(
                    "Manually Shortlist",
                    default=False,
                    help="Click to manually shortlist a candidate."
                ),
                # Progress bar for scores
                "Score (%)": st.column_config.ProgressColumn(
                    "Score (%)",
                    format="%.1f",
                    min_value=0,
                    max_value=100,
                    help="Overall AI match score based on JD and resume."
                ),
                "Years Experience": st.column_config.NumberColumn(
                    "Years Experience",
                    format="%.1f years",
                    help="Total years of work experience extracted."
                ),
                "CGPA (4.0 Scale)": st.column_config.NumberColumn(
                    "CGPA (4.0 Scale)",
                    format="%.2f",
                    min_value=0.0,
                    max_value=4.0,
                    help="Candidate's CGPA, normalized to a 4.0 scale."
                ),
                "Semantic Similarity": st.column_config.NumberColumn(
                    "Semantic Similarity",
                    format="%.2f",
                    help="Score based on meaning and context match between JD and resume."
                ),
                "Exact Match Score": st.column_config.NumberColumn(
                    "Exact Match Score",
                    format="%.2f",
                    help="Score based on presence of exact keywords/skills from the JD."
                ),
                "Tag": st.column_config.Column(
                    "AI Tag",
                    help="AI's primary assessment tag."
                ),
                "Certificate Rank": st.column_config.Column(
                    "Certificate Rank",
                    help="The rank achieved by the candidate (e.g., Gold, Silver, Bronze)."
                ),
                "Matched Keywords": st.column_config.Column(
                    "Matched Keywords",
                    help="Keywords found in both JD and Resume"
                ),
                "Missing Skills": st.column_config.Column(
                    "Missing Skills",
                    help="Key skills from JD not found in Resume"
                ),
                "JD Used": st.column_config.Column(
                    "JD Used",
                    help="Job Description used for this screening"
                ),
                "Date Screened": st.column_config.DateColumn(
                    "Date Screened",
                    help="Date when the resume was screened",
                    format="YYYY-MM-DD"
                ),
                "Phone Number": st.column_config.Column(
                    "Phone Number",
                    help="Candidate's phone number extracted from resume"
                ),
                "Location": st.column_config.Column(
                    "Location",
                    help="Candidate's location extracted from resume"
                ),
                "Languages Known": st.column_config.Column(
                    "Languages Known",
                    help="Languages spoken by the candidate"
                ),
                "Overqualified": st.column_config.Column(
                    "Overqualified",
                    help="⚠️ Candidate has more experience than the maximum allowed, flagged as Overqualified"
                ),
                "Education Details": st.column_config.Column(
                    "Education Details",
                    help="Structured education history (University, Degree, Major, Year)"
                ),
                "Work History": st.column_config.Column(
                    "Work History",
                    help="Structured work experience (Company, Title, Dates)"
                ),
                "Project Details": st.column_config.Column(
                    "Project Details",
                    help="Structured project experience (Title, Description, Technologies)"
                ),
                "Certificate ID": st.column_config.Column(
                    "Certificate ID",
                    help="Unique ID for the certificate",
                    disabled=True, 
                    width="hidden"
                ),
                "Resume Word Count": st.column_config.NumberColumn(
                    "Resume Word Count",
                    help="Total number of words in the resume (Calculation Disabled for Speed)", 
                    format="%d words", 
                    disabled=True, 
                    # Keep it in the dataframe but hide from display if not needed
                    width="hidden"
                ),
                "Latest Education": st.column_config.Column(
                    "Latest Education",
                    help="Candidate's latest degree and institution"
                ),
                "Most Recent Job": st.column_config.Column(
                    "Most Recent Job",
                    help="Candidate's most recent job title and company"
                ),
                "Certifications": st.column_config.Column(
                    "Certifications",
                    help="Certifications found in the resume"
                ),
                "Resume Consistency Score": st.column_config.NumberColumn(
                    "Resume Consistency Score",
                    help="Score indicating consistency of resume timeline and claims (Calculation Disabled for Speed)", 
                    format="%d / 100", 
                    disabled=True, 
                    # Keep it in the dataframe but hide from display if not needed
                    width="hidden"
                ),
                "AI Suggestion": st.column_config.Column(
                    # Keep it in the dataframe but hide from display if not needed
                    "AI Suggestion", 
                    help="AI's concise overall assessment and recommendation", 
                    disabled=True, 
                    width="hidden"
                ),
                # New highlight fields
                "Top Skills Highlight": st.column_config.Column(
                    "Top Skills",
                    help="The most relevant skills extracted from the resume"
                ),
                "Availability": st.column_config.Column(
                    "Availability",
                    help="Candidate's availability status (e.g., immediate, 1 month notice)"
                ),
                "Soft Skills": st.column_config.Column(
                    "Soft Skills",
                    help="Soft skills extracted from the resume"
                ),
                "Notable Projects Highlight": st.column_config.Column(
                    "Notable Projects",
                    help="Key projects highlighted by the candidate"
                ),
                "Awards/Recognitions": st.column_config.Column(
                    "Awards/Recognitions",
                    help="Awards or special recognitions mentioned"
                ),
                "Tools Used Highlight": st.column_config.Column(
                    "Tools/Tech Stack",
                    help="Key tools and technologies mentioned in the resume"
                ),
                "Publications": st.column_config.Column(
                    "Publications",
                    help="Publications mentioned in the resume"
                ),
                "Portfolio/GitHub": st.column_config.Column(
                    "Portfolio/GitHub",
                    help="Link to candidate's portfolio or GitHub"
                )
            }
        )

        # 🚀 Auto-send results once to HR
        if (
            "username" in st.session_state 
            and isinstance(st.session_state.get("comprehensive_df"), pd.DataFrame)
            and not st.session_state.get("email_sent", False)
                ):
            if send_comprehensive_table_to_hr(st.session_state["comprehensive_df"], st.session_state["username"]):
                st.session_state["email_sent"] = True


        # Update the session state DataFrame with changes from st.data_editor
        st.session_state['comprehensive_df'] = edited_df.copy() # Use .copy() to ensure a new DataFrame object
        
        st.markdown("---")
        st.markdown("## 🏆 Generate Candidate Certificates")
        st.caption("Select a candidate to view or download their ScreenerPro Certification.")

        if not st.session_state['comprehensive_df'].empty:
            candidate_names_for_cert = st.session_state['comprehensive_df']['Candidate Name'].tolist()
            selected_candidate_names_for_cert = st.multiselect(
                "**Select Candidate(s) for Certificate:**",
                options=candidate_names_for_cert,
                key="certificate_candidate_select"
            )

            if selected_candidate_names_for_cert:
                for selected_name in selected_candidate_names_for_cert:
                    try:
                        candidate_rows = st.session_state['comprehensive_df'][
                            st.session_state['comprehensive_df']['Candidate Name'] == selected_name
                        ]
                        
                        if not candidate_rows.empty:
                            candidate_data_for_cert = candidate_rows.iloc[0].to_dict()

                            if candidate_data_for_cert.get('Certificate Rank') != "Not Applicable":
                                # Generate HTML content for the certificate (for preview and PDF conversion)
                                certificate_html_content = generate_certificate_html(candidate_data_for_cert, CERTIFICATE_HOSTING_URL)
                                st.session_state['certificate_html_content'] = certificate_html_content # Store for preview

                                # Generate PDF content
                                certificate_pdf_content = generate_certificate_pdf(certificate_html_content)

                                st.subheader(f"Certificate for {selected_name}")
                                col_cert_view, col_cert_download = st.columns(2)
                                with col_cert_view:
                                    if st.button(f"👁️ View Certificate (HTML Preview) for {selected_name}", key=f"view_cert_button_{selected_name}"):
                                        pass 
                                        
                                with col_cert_download:
                                    if certificate_pdf_content:
                                        st.download_button(
                                            label=f"⬇️ Download Certificate (PDF) for {selected_name}",
                                            data=certificate_pdf_content,
                                            file_name=f"ScreenerPro_Certificate_{candidate_data_for_cert['Candidate Name'].replace(' ', '_')}.pdf",
                                            mime="application/pdf",
                                            key=f"download_cert_pdf_button_{selected_name}"
                                        )
                                        # Send email only if PDF is successfully generated
                                        if candidate_data_for_cert.get('Email') and candidate_data_for_cert['Email'] != "Not Found":
                                            send_certificate_email(
                                                recipient_email=candidate_data_for_cert['Email'],
                                                candidate_name=candidate_data_for_cert['Candidate Name'],
                                                score=candidate_data_for_cert['Score (%)'],
                                                certificate_pdf_content=certificate_pdf_content,
                                                gmail_address="screenerpro.ai@gmail.com", # Using the hardcoded Gmail address
                                                gmail_app_password=st.secrets.get("udwi life nbdv kgdt"), # Getting app password from secrets
                                                company_name=st.session_state.get('user_company', 'ScreenerPro'),
                                                certificate_id=candidate_data_for_cert.get('Certificate ID', 'N/A')
                                            )
                                        else:
                                            st.info(f"No email address found for {candidate_data_for_cert['Candidate Name']}. Certificate could not be sent automatically.")
                                        
                                        # Call the function to save certificate data to public Firestore
                                        save_certificate_to_firestore_public(candidate_data_for_cert)
                                    else:
                                        st.warning(f"PDF generation failed for {selected_name}, cannot provide download.")
                                
                            else:
                                st.info(f"{selected_name} does not qualify for a ScreenerPro Certificate at this time.")
                        else:
                            st.warning(f"Selected candidate '{selected_name}' not found in the processed results. Please re-select or re-process resumes.")
                    except Exception as e:
                        st.error(f"An unexpected error occurred while processing certificate for {selected_name}: {e}")
                        traceback.print_exc()
                        st.info(f"Continuing to process other selected candidates...")
        else:
            st.info("No candidates available to generate certificates for. Please screen resumes first.")

    if st.session_state['certificate_html_content']:
        st.markdown("---")
        st.markdown("### Generated Certificate Preview (HTML)")
        st.components.v1.html(st.session_state['certificate_html_content'], height=850, scrolling=False)
        st.markdown("---")


    else:
        st.info("Please upload a Job Description and at least one Resume to begin the screening process.")

@st.cache_data
def generate_certificate_html(candidate_data, certificate_hosting_url):
    html_template = """

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>ScreenerPro Certificate (Landscape)</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;600&display=swap');

    body {
      margin: 0;
      padding: 0;
      background: #f4f6f8;
      font-family: 'Inter', sans-serif;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
    }

    .certificate {
      background-color: #ffffff;
      width: 1120px;
      height: 790px;
      padding: 50px 70px;
      border: 10px solid #00bcd4;
      box-shadow: 0 0 20px rgba(0,0,0,0.1);
      box-sizing: border-box;
      text-align: center;
      position: relative;
    }

    .certificate img.logo {
      width: 200px;
      margin-bottom: 20px;
    }

    h1 {
      font-family: 'Playfair Display', serif;
      font-size: 36px;
      color: #003049;
      margin: 10px 0;
    }

    h2 {
      font-size: 20px;
      margin-bottom: 25px;
      color: #007c91;
    }

    .subtext {
      font-size: 18px;
      color: #333;
      margin-bottom: 10px;
    }

    .candidate-name {
      font-family: 'Playfair Display', serif;
      font-size: 32px;
      color: #00bcd4;
      font-weight: bold;
      margin: 10px 0;
      text-decoration: underline;
    }

    .score-rank {
      display: inline-block;
      font-size: 18px;
      font-weight: 600;
      background: #e0f7fa;
      color: #2e7d32;
      padding: 8px 24px;
      border-radius: 8px;
      margin: 20px 0;
    }

    .description {
      font-size: 16px;
      color: #555;
      margin: 20px auto;
      line-height: 1.5;
      max-width: 900px;
    }

    .footer-details {
      font-size: 13px;
      color: #666;
      margin-top: 20px;
    }

    .signature-block {
      margin-top: 40px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .signature img {
      width: 150px;
      border-bottom: 1px solid #ccc;
      padding-bottom: 5px;
    }

    .signature .title {
      font-size: 13px;
      color: #777;
      margin-top: 5px;
      text-align: left;
    }

    .stamp {
      font-size: 42px;
      color: #4caf50;
      margin-right: 10px;
    }

    @media print {
      @page {
        size: landscape;
        margin: 0;
      }

      body {
        background: #ffffff;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }

      .certificate {
        box-shadow: none;
      }
    }
  </style>
</head>
<body>
  <div class="certificate">
    <img class="logo" src="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhhq_OCSv-QmuBjXeRQXr60EfsvVA4chRPCNslo3NhjVQkoKjUtiRfTPpGoQjyQXS7sMsJifQC6Yq34cAhNbq9lMwBXZqIIbCij1adyXSuNoyxuzOTDfrPU2dnna0baimldd7Y1KCkvaAfrWC1yLGxp25SJ9s4exJ-JAc8kNcTyUSgkLWbW2DdvhpWH4GlO/s578/logo.png" alt="ScreenerPro Logo" />


    <h1>CERTIFICATE OF EXCELLENCE</h1>
    <h2>Presented by ScreenerPro</h2>

    <div class="subtext">This is to certify that</div>
    <div class="candidate-name">{{CANDIDATE_NAME}}</div>

    <div class="subtext">has successfully completed the AI-powered resume screening process</div>

    <div class="score-rank">Score: {{SCORE}}% | Rank: {{CERTIFICATE_RANK}}</div>

    <div class="description">
      This certificate acknowledges the candidate’s exceptional qualifications, industry-aligned skills, and readiness to contribute effectively in challenging roles. Evaluated and validated by ScreenerPro’s advanced screening engine.
    </div>

    <div class="footer-details">
      Awarded on: {{DATE_SCREENED}}<br>
      Certificate ID: {{CERTIFICATE_ID}}
    </div>

    <div class="signature-block">
      <div class="signature">
        <img src="https://see.fontimg.com/api/rf5/DOLnW/ZTAyODAyZDM3MWUyNDVjNjg0ZWRmYTRjMjNlOTE3ODUub3Rm/U2NyZWVuZXJQcm8/autography.png?r=fs&h=81&w=1250&fg=000000&bg=FFFFFF&tb=1&s=65" alt="Signature" />
        <div class="title">Founder & Product Head, ScreenerPro</div>
      </div>
      <div class="stamp">✔️</div>
    </div>
  </div>
</body>
</html>



    """

    candidate_name = candidate_data.get('Candidate Name', 'Candidate Name')
    score = candidate_data.get('Score (%)', 0.0)
    certificate_rank = candidate_data.get('Certificate Rank', 'Not Applicable')
    date_screened = candidate_data.get('Date Screened', datetime.now().date()).strftime("%B %d, %Y")
    certificate_id = candidate_data.get('Certificate ID', 'N/A')
    
    html_content = html_template.replace("{{CANDIDATE_NAME}}", candidate_name)
    html_content = html_content.replace("{{SCORE}}", f"{score:.1f}")
    html_content = html_content.replace("{{CERTIFICATE_RANK}}", certificate_rank)
    html_content = html_content.replace("{{DATE_SCREENED}}", date_screened)
    html_content = html_content.replace("{{CERTIFICATE_ID}}", certificate_id)
    html_content = html_content.replace("{{CERTIFICATE_HOSTING_URL}}", certificate_hosting_url)

    return html_content

if __name__ == "__main__":
    # This block is for local testing of screener.py in isolation.
    # When run as part of main.py, this block will be skipped.
    st.set_page_config(page_title="ScreenerPro - Local Screener Test", layout="wide")
    st.write("This is a local test run of screener.py. For full functionality, run main.py.")
    
    # Mock the save_certificate_to_firestore_public_func for local testing
    def mock_save_certificate_to_firestore_public(cert_data):
        st.success(f"Mock: Certificate data for '{cert_data.get('Candidate Name')}' with ID '{cert_data.get('Certificate ID')}' would be saved publicly.")
        st.json(cert_data) # Show what would be saved

    resume_screener_page()



















