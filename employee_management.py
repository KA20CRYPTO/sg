import streamlit as st
from firebase_admin import credentials, firestore, initialize_app
import os
import json
from datetime import datetime, date, timedelta
import pandas as pd
import requests

def safe_date_convert(date_val, default=None):
    if not date_val or pd.isna(date_val):
        return default
    try:
        ts = pd.to_datetime(date_val)
        if pd.isna(ts):
            return default
        return ts.date()
    except:
        return default
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import base64
from collections import Counter

# Initialize Firebase (if not already initialized)
try:
    app_id = globals().get('__app_id', 'default-screenerpro-app')
    firebase_config_str = globals().get('__firebase_config', '{}')
    firebase_config = json.loads(firebase_config_str)

    if not st.session_state.get('firebase_initialized'):
        st.session_state['firebase_initialized'] = True
        
except Exception as e:
    st.error(f"Error initializing Firebase context: {e}. Please ensure Firebase environment variables are correctly set up.")

FIREBASE_WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY', 'AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw')
FIREBASE_PROJECT_ID = globals().get('__app_id', 'screenerproapp')
FIRESTORE_BASE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"


def convert_to_firestore_fields(data):
    """Converts a Python dictionary to Firestore's required field format."""
    firestore_fields = {}
    for key, value in data.items():
        if isinstance(value, str):
            firestore_fields[key] = {"stringValue": value}
        elif isinstance(value, bool):
            firestore_fields[key] = {"booleanValue": value}
        elif isinstance(value, int):
            firestore_fields[key] = {"integerValue": str(value)}
        elif isinstance(value, float):
            firestore_fields[key] = {"doubleValue": value}
        elif isinstance(value, datetime):
            firestore_fields[key] = {"timestampValue": value.isoformat() + "Z"}
        elif isinstance(value, list):
            firestore_fields[key] = {"arrayValue": {"values": [convert_to_firestore_fields_single(item) for item in value]}}
        elif isinstance(value, dict):
            firestore_fields[key] = {"mapValue": {"fields": convert_to_firestore_fields(value)}}
        elif value is None:
            firestore_fields[key] = {"nullValue": None}
        else:
            firestore_fields[key] = {"stringValue": str(value)}
    return firestore_fields

def convert_to_firestore_fields_single(value):
    """Converts a single Python value to Firestore's required field format."""
    if isinstance(value, str):
        return {"stringValue": value}
    elif isinstance(value, bool):
        return {"booleanValue": value}
    elif isinstance(value, int):
        return {"integerValue": str(value)}
    elif isinstance(value, float):
        return {"doubleValue": value}
    elif isinstance(value, datetime):
        return {"timestampValue": value.isoformat() + "Z"}
    elif isinstance(value, list):
        return {"arrayValue": {"values": [convert_to_firestore_fields_single(item) for item in value]}}
    elif isinstance(value, dict):
        return {"mapValue": {"fields": convert_to_firestore_fields(value)}}
    elif value is None:
        return {"nullValue": None}
    else:
        return {"stringValue": str(value)}


def parse_firestore_document(doc_data):
    """Parses Firestore document data into a Python dictionary."""
    parsed_data = {}
    if "fields" in doc_data:
        for key, value_obj in doc_data["fields"].items():
            if "stringValue" in value_obj:
                parsed_data[key] = value_obj["stringValue"]
            elif "integerValue" in value_obj:
                parsed_data[key] = int(value_obj["integerValue"])
            elif "doubleValue" in value_obj:
                parsed_data[key] = float(value_obj["doubleValue"])
            elif "booleanValue" in value_obj:
                parsed_data[key] = value_obj["booleanValue"]
            elif "timestampValue" in value_obj:
                parsed_data[key] = datetime.fromisoformat(value_obj["timestampValue"].replace('Z', '+00:00'))
            elif "arrayValue" in value_obj and "values" in value_obj["arrayValue"]:
                parsed_data[key] = [parse_firestore_document_single(item) for item in value_obj["arrayValue"]["values"]]
            elif "mapValue" in value_obj and "fields" in value_obj["mapValue"]:
                parsed_data[key] = parse_firestore_document({"fields": value_obj["mapValue"]["fields"]})
            elif "nullValue" in value_obj:
                parsed_data[key] = None
    if "name" in doc_data:
        parsed_data["id"] = doc_data["name"].split("/")[-1]
    return parsed_data

def parse_firestore_document_single(value_obj):
    """Parses a single Firestore value object."""
    if "stringValue" in value_obj:
        return value_obj["stringValue"]
    elif "integerValue" in value_obj:
        return int(value_obj["integerValue"])
    elif "doubleValue" in value_obj:
        return float(value_obj["doubleValue"])
    elif "booleanValue" in value_obj:
        return value_obj["booleanValue"]
    elif "timestampValue" in value_obj:
        return datetime.fromisoformat(value_obj["timestampValue"].replace('Z', '+00:00'))
    elif "arrayValue" in value_obj and "values" in value_obj["arrayValue"]:
        return [parse_firestore_document_single(item) for item in value_obj["arrayValue"]["values"]]
    elif "mapValue" in value_obj and "fields" in value_obj["mapValue"]:
        return parse_firestore_document({"fields": value_obj["mapValue"]["fields"]})
    elif "nullValue" in value_obj:
        return None
    return None


def get_employee_collection_path(user_company):
    """
    Constructs the Firestore collection path for company-specific employee data.
    This uses a NEW, distinct top-level collection for employee management.
    """
    sanitized_company = user_company.replace(' ', '_').lower()
    return f"artifacts/{FIREBASE_PROJECT_ID}/employee_management_data/{sanitized_company}/employees"

def get_template_collection_path(template_type):
    """Constructs the Firestore collection path for company-wide templates."""
    return f"artifacts/{FIREBASE_PROJECT_ID}/public/data/{template_type}_templates"

def get_payroll_collection_path(user_company):
    """Constructs the Firestore collection path for payroll records."""
    sanitized_company = user_company.replace(' ', '_').lower()
    return f"artifacts/{FIREBASE_PROJECT_ID}/employee_management_data/{sanitized_company}/payroll"


def add_document_to_firestore(collection_path, doc_data):
    """Adds a new document to a specified Firestore collection."""
    try:
        add_url = f"{FIRESTORE_BASE_URL}/{collection_path}?key={FIREBASE_WEB_API_KEY}"
        doc_data["created_at"] = datetime.now()
        response = requests.post(add_url, json={"fields": convert_to_firestore_fields(doc_data)})
        response.raise_for_status()
        return response.json().get('name', '').split('/')[-1]
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to add document to {collection_path}: {e.response.text if e.response else e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred while adding document to {collection_path}: {e}")
        return None

def get_documents_from_firestore(collection_path):
    """Retrieves all documents from a specified Firestore collection."""
    try:
        list_url = f"{FIRESTORE_BASE_URL}/{collection_path}?key={FIREBASE_WEB_API_KEY}"
        response = requests.get(list_url)
        response.raise_for_status()
        
        docs = response.json().get("documents", [])
        parsed_docs = []
        for doc in docs:
            doc_data = parse_firestore_document(doc)
            doc_data['id'] = doc['name'].split('/')[-1]
            parsed_docs.append(doc_data)
        return parsed_docs
    except requests.exceptions.RequestException as e:
        if e.response and e.response.status_code == 404:
            return []
        st.error(f"Failed to fetch documents from {collection_path}: {e.response.text if e.response else e}")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching documents from {collection_path}: {e}")
        return []

def update_document_in_firestore(collection_path, doc_id, updated_data):
    """Updates an existing document in Firestore with correct updateMask handling."""
    try:
        # Correctly format the update mask for the REST API
        mask = "&updateMask.fieldPaths=".join(updated_data.keys())
        update_url = f"{FIRESTORE_BASE_URL}/{collection_path}/{doc_id}?key={FIREBASE_WEB_API_KEY}&updateMask.fieldPaths={mask}"
        
        updated_data["updated_at"] = datetime.now()
        payload = {"fields": convert_to_firestore_fields(updated_data)}
        
        response = requests.patch(update_url, json=payload)
        response.raise_for_status()
        
        st.success("Employee updated successfully!")
        st.session_state['refresh_employees'] = True
    except requests.exceptions.RequestException as e:
        error_msg = e.response.text if e.response else str(e)
        st.error(f"Update failed: {error_msg}")
    except Exception as e:
        st.error(f"An unexpected error occurred during update: {e}")

def delete_document_from_firestore(collection_path, doc_id):
    """Deletes a document from Firestore."""
    try:
        delete_url = f"{FIRESTORE_BASE_URL}/{collection_path}/{doc_id}?key={FIREBASE_WEB_API_KEY}"
        response = requests.delete(delete_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to delete document from {collection_path}: {e.response.text if e.response else e}")
    except Exception as e:
        st.error(f"An unexpected error occurred while deleting document from {collection_path}: {e}")


def add_employee_to_firestore(employee_data, user_company):
    """Adds a new employee document to Firestore for a specific company."""
    try:
        collection_path = get_employee_collection_path(user_company)
        add_url = f"{FIRESTORE_BASE_URL}/{collection_path}?key={FIREBASE_WEB_API_KEY}"
        
        employee_data["created_at"] = datetime.now()
        
        response = requests.post(add_url, json={"fields": convert_to_firestore_fields(employee_data)})
        response.raise_for_status()
        st.success("Employee added successfully!")
        st.session_state['refresh_employees'] = True
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to add employee: {e.response.text if e.response else e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

def get_employees_from_firestore(user_company):
    """Retrieves all employee documents from Firestore for a specific company."""
    return get_documents_from_firestore(get_employee_collection_path(user_company))

def update_employee_in_firestore(employee_id, updated_data, user_company):
    """Updates an existing employee document in Firestore for a specific company."""
    update_document_in_firestore(get_employee_collection_path(user_company), employee_id, updated_data)
    st.session_state['refresh_employees'] = True

def delete_employee_from_firestore(employee_id, user_company):
    """Deletes an employee document from Firestore for a specific company."""
    delete_document_from_firestore(get_employee_collection_path(user_company), employee_id)
    st.session_state['refresh_employees'] = True

def get_payroll_records_for_employee(employee_id, user_company):
    """Fetches all payroll records for a specific employee."""
    all_payroll = get_documents_from_firestore(get_payroll_collection_path(user_company))
    return [r for r in all_payroll if r.get('employee_id') == employee_id]

def generate_avatar_svg(name):
    initials = "".join([n[0] for n in name.split() if n]).upper()[:2]
    colors = ["#FF5733", "#33FF57", "#3357FF", "#FF33F7", "#F7FF33", "#33FFF7"]
    color_index = sum(ord(char) for char in initials) % len(colors)
    bg_color = colors[color_index]
    text_color = "white"

    svg = f"""
    <svg width="100" height="100" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="50" cy="50" r="50" fill="{bg_color}"/>
        <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="{text_color}" font-family="Inter, sans-serif" font-size="40" font-weight="bold">{initials}</text>
    </svg>
    """
    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode('utf-8')).decode('utf-8')}"


def template_management_page():
    st.title("Template Management")
    st.markdown("Define reusable templates for Onboarding and Performance Reviews.")

    dark_mode = st.session_state.get('dark_mode_main', False)
    primary_color = '#00cec9'
    form_container_bg_light = 'linear-gradient(135deg, #E8F5E9, #D4EDDA)'
    form_container_bg_dark = 'linear-gradient(135deg, #2A3B3A, #1F2D2C)'
    form_container_border_light = '1px solid #4CAF50'
    form_container_border_dark = '1px solid #00cec9'
    form_container_shadow = '0 6px 15px rgba(0, 0, 0, 0.15)' if not dark_mode else '0 6px 15px rgba(0, 0, 0, 0.4)'
    text_color_main = '#f0f2f6' if dark_mode else '#333333'

    st.markdown(f"""
        <style>
            .template-form-container {{
                background: {form_container_bg_light if not dark_mode else form_container_bg_dark};
                border-radius: 20px;
                padding: 30px;
                margin-bottom: 40px;
                box-shadow: {form_container_shadow};
                border: {form_container_border_light if not dark_mode else form_container_border_dark};
                transition: all 0.3s ease;
            }}
            .template-form-container:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25) !important;
            }}
            .template-form-container h3 {{
                color: {text_color_main};
                border-bottom: 1px solid {primary_color};
                padding-bottom: 10px;
                margin-bottom: 25px;
            }}
            .template-card {{
                background-color: {'#3A3A3A' if dark_mode else '#FFFFFF'};
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 15px;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
                border: 1px solid {'rgba(255,255,255,0.1)' if dark_mode else 'rgba(0,0,0,0.1)'};
            }}
            .template-card h4 {{
                color: {primary_color};
                margin-top: 0;
                margin-bottom: 10px;
            }}
            .template-card p {{
                color: {text_color_main};
                margin-bottom: 5px;
            }}
        </style>
    """, unsafe_allow_html=True)

    st.subheader("Onboarding Templates")
    st.markdown('<div class="template-form-container">', unsafe_allow_html=True)
    with st.form("add_onboarding_template_form"):
        template_name = st.text_input("Template Name", key="onboarding_template_name_add")
        st.markdown("#### Tasks (one per line: `Task Name, Responsible Role, Due Days After Hire`)")
        tasks_input = st.text_area("Tasks", key="onboarding_tasks_input_add", 
                                   placeholder="e.g., 'Complete HR paperwork, HR, 5'\n'Setup IT equipment, IT, 10'\n'Meet team, Employee, 30'")
        add_template_submitted = st.form_submit_button("Add Onboarding Template")

        if add_template_submitted:
            if template_name and tasks_input:
                tasks = []
                for line in tasks_input.split('\n'):
                    if line.strip():
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 3:
                            try:
                                tasks.append({
                                    "task_name": parts[0],
                                    "responsible_role": parts[1],
                                    "due_days_after_hire": int(parts[2])
                                })
                            except ValueError:
                                st.error(f"Invalid 'Due Days After Hire' for task: {parts[0]}. Please enter a number.")
                                tasks = []
                                break
                        else:
                            st.error(f"Invalid format for task: '{line}'. Expected 'Task Name, Responsible Role, Due Days After Hire'.")
                            tasks = []
                            break
                if tasks:
                    template_data = {"name": template_name, "tasks": tasks}
                    add_document_to_firestore(get_template_collection_path("onboarding"), template_data)
                    st.success("Onboarding Template added!")
                    st.session_state['refresh_templates'] = True
                    st.experimental_rerun()
            else:
                st.error("Template Name and Tasks are required.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Existing Onboarding Templates")
    if 'refresh_templates' not in st.session_state:
        st.session_state['refresh_templates'] = True
    
    if st.session_state['refresh_templates']:
        st.session_state['onboarding_templates'] = get_documents_from_firestore(get_template_collection_path("onboarding"))
        st.session_state['refresh_templates'] = False

    if st.session_state['onboarding_templates']:
        for template in st.session_state['onboarding_templates']:
            st.markdown(f'<div class="template-card">', unsafe_allow_html=True)
            st.markdown(f"<h4>{template.get('name', 'N/A')}</h4>")
            st.markdown("<h5>Tasks:</h5>")
            for task in template.get('tasks', []):
                st.markdown(f"- {task.get('task_name', 'N/A')} (Responsible: {task.get('responsible_role', 'N/A')}, Due: {task.get('due_days_after_hire', 'N/A')} days)")
            delete_col = st.columns(1)[0]
            if delete_col.button(f"Delete {template.get('name', 'Template')}", key=f"del_onboard_temp_{template['id']}"):
                delete_document_from_firestore(get_template_collection_path("onboarding"), template['id'])
                st.success("Onboarding Template deleted.")
                st.session_state['refresh_templates'] = True
                st.experimental_rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No onboarding templates defined yet.")

    st.markdown("---")
    st.subheader("Offboarding Templates")
    st.markdown('<div class="template-form-container">', unsafe_allow_html=True)
    with st.form("add_offboarding_template_form"):
        template_name = st.text_input("Template Name", key="offboarding_template_name_add")
        st.markdown("#### Tasks (one per line: `Task Name, Responsible Role, Due Days Before Offboarding`)")
        tasks_input = st.text_area("Tasks", key="offboarding_tasks_input_add", 
                                   placeholder="e.g., 'Collect company laptop, IT, 7'\n'Final paycheck processing, HR, 0'\n'Exit interview, Manager, 3'")
        add_template_submitted = st.form_submit_button("Add Offboarding Template")

        if add_template_submitted:
            if template_name and tasks_input:
                tasks = []
                for line in tasks_input.split('\n'):
                    if line.strip():
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 3:
                            try:
                                tasks.append({
                                    "task_name": parts[0],
                                    "responsible_role": parts[1],
                                    "due_days_before_offboarding": int(parts[2])
                                })
                            except ValueError:
                                st.error(f"Invalid 'Due Days Before Offboarding' for task: {parts[0]}. Please enter a number.")
                                tasks = []
                                break
                        else:
                            st.error(f"Invalid format for task: '{line}'. Expected 'Task Name, Responsible Role, Due Days Before Offboarding'.")
                            tasks = []
                            break
                if tasks:
                    template_data = {"name": template_name, "tasks": tasks}
                    add_document_to_firestore(get_template_collection_path("offboarding"), template_data)
                    st.success("Offboarding Template added!")
                    st.session_state['refresh_templates'] = True
                    st.experimental_rerun()
            else:
                st.error("Template Name and Tasks are required.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Existing Offboarding Templates")
    if st.session_state['refresh_templates']:
        st.session_state['offboarding_templates'] = get_documents_from_firestore(get_template_collection_path("offboarding"))
        st.session_state['refresh_templates'] = False

    if st.session_state['offboarding_templates']:
        for template in st.session_state['offboarding_templates']:
            st.markdown(f'<div class="template-card">', unsafe_allow_html=True)
            st.markdown(f"<h4>{template.get('name', 'N/A')}</h4>")
            st.markdown("<h5>Tasks:</h5>")
            for task in template.get('tasks', []):
                st.markdown(f"- {task.get('task_name', 'N/A')} (Responsible: {task.get('responsible_role', 'N/A')}, Due: {task.get('due_days_before_offboarding', 'N/A')} days before)")
            delete_col = st.columns(1)[0]
            if delete_col.button(f"Delete {template.get('name', 'Template')}", key=f"del_offboard_temp_{template['id']}"):
                delete_document_from_firestore(get_template_collection_path("offboarding"), template['id'])
                st.success("Offboarding Template deleted.")
                st.session_state['refresh_templates'] = True
                st.experimental_rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No offboarding templates defined yet.")


    st.markdown("---")
    st.subheader("Performance Review Templates")
    st.markdown('<div class="template-form-container">', unsafe_allow_html=True)
    with st.form("add_performance_template_form"):
        template_name = st.text_input("Template Name", key="perf_template_name_add")
        st.markdown("#### Sections/Questions (one per line: `Section Title: Question 1; Question 2`)")
        sections_input = st.text_area("Sections/Questions", key="perf_sections_input_add", 
                                      placeholder="e.g., 'Overall Performance: Rate overall performance (1-5); Provide comments'\n'Strengths: List key strengths'\n'Areas for Development: Identify areas for growth'")
        add_perf_template_submitted = st.form_submit_button("Add Performance Review Template")

        if add_perf_template_submitted:
            if template_name and sections_input:
                sections = []
                for line in sections_input.split('\n'):
                    if line.strip():
                        parts = line.split(':')
                        if len(parts) >= 2:
                            section_title = parts[0].strip()
                            questions = [q.strip() for q in parts[1].split(';') if q.strip()]
                            sections.append({"section_title": section_title, "questions": questions})
                        else:
                            st.error(f"Invalid format for section: '{line}'. Expected 'Section Title: Question1; Question2'.")
                            sections = []
                            break
                if sections:
                    template_data = {"name": template_name, "sections": sections}
                    add_document_to_firestore(get_template_collection_path("performance_review"), template_data)
                    st.success("Performance Review Template added!")
                    st.session_state['refresh_templates'] = True
                    st.experimental_rerun()
            else:
                st.error("Template Name and Sections/Questions are required.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Existing Performance Review Templates")
    if st.session_state['refresh_templates']:
        st.session_state['performance_review_templates'] = get_documents_from_firestore(get_template_collection_path("performance_review"))
        st.session_state['refresh_templates'] = False

    if st.session_state['performance_review_templates']:
        for template in st.session_state['performance_review_templates']:
            st.markdown(f'<div class="template-card">', unsafe_allow_html=True)
            st.markdown(f"<h4>{template.get('name', 'N/A')}</h4>")
            st.markdown("<h5>Sections:</h5>")
            for section in template.get('sections', []):
                st.markdown(f"- **{section.get('section_title', 'N/A')}**")
                for question in section.get('questions', []):
                    st.markdown(f"  - {question}")
            delete_col = st.columns(1)[0]
            if delete_col.button(f"Delete {template.get('name', 'Template')}", key=f"del_perf_temp_{template['id']}"):
                delete_document_from_firestore(get_template_collection_path("performance_review"), template['id'])
                st.success("Performance Review Template deleted.")
                st.session_state['refresh_templates'] = True
                st.experimental_rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No performance review templates defined yet.")


def employee_management_page():
    st.title("Employee Management")
    st.markdown("Manage your team's employee records.")

    user_company = st.session_state.get('user_company', 'default_company')
    if not user_company:
        user_company = 'default_company'
    
    sanitized_user_company = str(user_company).replace(' ', '_').lower()

    if user_company == 'default_company':
        st.error(
            "**CRITICAL WARNING: Data Isolation Compromised!**\n\n"
            "Your company information (`st.session_state['user_company']`) is currently set to "
            "**'default_company'**. This means **all users sharing this default** will see and "
            "manage the **same employee data**. \n\n"
            "**To ensure data isolation and security:**\n"
            "1.  **Ensure users log in** and their `st.session_state['user_company']` is set to a **unique company ID**.\n"
            "2.  **Strongly consider updating your Firebase Firestore Security Rules** to enforce "
            "company-specific access, even if you rely on app-side filtering for now. "
            "The current rules (if 'allow read, write: if true;') offer no protection."
        )
    else:
        st.info(f"Managing employees for company: **{user_company}**")

    # --- Setup & Styling ---
    dark_mode = st.session_state.get('dark_mode_main', False)
    text_color_main = '#f0f2f6' if dark_mode else '#333333'
    text_color_light = '#BBBBBB' if dark_mode else '#555555'
    primary_color = '#00cec9'
    secondary_bg = '#262730' if dark_mode else '#F0F2F6'
    card_bg = '#3A3A3A' if dark_mode else '#FFFFFF'
    card_shadow = '0 8px 20px rgba(0, 0, 0, 0.2)' if dark_mode else '0 8px 20px rgba(0, 0, 0, 0.1)'
    card_border = '1px solid rgba(255, 255, 255, 0.1)' if dark_mode else '1px solid rgba(0, 0, 0, 0.1)'
    form_container_bg_light = 'linear-gradient(135deg, #E8F5E9, #D4EDDA)'
    form_container_bg_dark = 'linear-gradient(135deg, #2A3B3A, #1F2D2C)'
    form_container_border_light = '1px solid #4CAF50'
    form_container_border_dark = '1px solid #00cec9'
    form_container_shadow = '0 6px 15px rgba(0, 0, 0, 0.15)' if not dark_mode else '0 6px 15px rgba(0, 0, 0, 0.4)'

    st.markdown(f"""
        <style>
            /* Greeting message styling */
            .greeting-container {{
                background: linear-gradient(45deg, {primary_color}, #00b0a8);
                color: white;
                padding: 20px 30px;
                border-radius: 15px;
                margin-bottom: 30px;
                box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
                text-align: center;
                animation: fadeInScale 0.8s ease-out forwards;
                font-size: 1.2em;
                font-weight: 600;
                letter-spacing: 0.05em;
            }}
            .greeting-container strong {{
                font-size: 1.5em;
                display: block;
                margin-bottom: 5px;
            }}
            @keyframes fadeInScale {{
                0% {{ opacity: 0; transform: scale(0.9); }}
                100% {{ opacity: 1; transform: scale(1); }}
            }}
            .stTextInput label, .stSelectbox label, .stDateInput label, .stNumberInput label, .stTextArea label {{
                font-weight: 600;
                color: {text_color_main};
                margin-bottom: 0.5rem;
                display: block;
            }}
            .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] {{
                border-radius: 10px;
                border: 1px solid {primary_color};
                padding: 0.75rem 1rem;
                background-color: {secondary_bg};
                color: {text_color_main};
                box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
                transition: all 0.3s ease;
            }}
            .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox [data-baseweb="select"]:focus-within {{
                border-color: {primary_color};
                box-shadow: 0 0 0 3px rgba(0, 206, 201, 0.4);
                outline: none;
            }}
            .stButton > button {{
                background-color: {primary_color};
                color: white;
                border-radius: 10px;
                padding: 0.75rem 1.5rem;
                font-weight: 600;
                border: none;
                transition: all 0.3s ease;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                cursor: pointer;
            }}
            .stButton > button:hover {{
                background-color: #00b0a8;
                transform: translateY(-2px);
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3);
            }}
            .stDataFrame {{
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
                border: 1px solid {'rgba(255,255,255,0.1)' if dark_mode else 'rgba(0,0,0,0.1)'};
            }}
            .stDataFrame th {{
                background-color: {primary_color};
                color: white;
                font-weight: 700;
                padding: 1rem;
            }}
            .stDataFrame td {{
                background-color: {'#2D2D2D' if dark_mode else '#FFFFFF'};
                color: {text_color_main};
                padding: 0.8rem 1rem;
                border-bottom: 1px solid {'rgba(255,255,255,0.05)' if dark_mode else 'rgba(0,0,0,0.05)'};
            }}
            .stDataFrame tbody tr:nth-child(odd) td {{
                background-color: {'#262730' if dark_mode else '#F8F8F8'};
            }}
            .stDataFrame tbody tr:hover td {{
                background-color: {'rgba(0, 206, 201, 0.15)' if dark_mode else 'rgba(0, 206, 201, 0.08)'} !important;
            }}
            .stMetric {{
                background-color: {secondary_bg};
                border-radius: 15px;
                padding: 1.5rem;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
                border: 1px solid {'rgba(255,255,255,0.08)' if dark_mode else 'rgba(0,0,0,0.08)'};
            }}
            .stMetric > div[data-testid="stMetricValue"] {{
                color: {primary_color};
                font-size: 2.2em;
                font-weight: 700;
            }}
            .stMetric > div[data-testid="stMetricLabel"] {{
                color: {text_color_light};
                font-size: 1em;
            }}
            .stMetric > div[data-testid="stMetricDelta"] {{
                color: {primary_color};
                font-size: 1.5em;
            }}
            .employee-profile-card {{
                background-color: {card_bg};
                border-radius: 20px;
                padding: 25px;
                margin-top: 30px;
                margin-bottom: 30px;
                box-shadow: {card_shadow};
                border: {card_border};
                transition: all 0.3s ease;
            }}
            .employee-profile-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 12px 25px rgba(0, 0, 0, 0.3);
            }}
            .employee-profile-card h3 {{
                color: {primary_color};
                margin-bottom: 15px;
                font-size: 1.8em;
                border-bottom: 2px solid {primary_color};
                padding-bottom: 10px;
            }}
            .employee-profile-card p {{
                color: {text_color_main};
                font-size: 1.05em;
                margin-bottom: 8px;
            }}
            .employee-profile-card p strong {{
                color: {primary_color};
            }}
            .employee-profile-card .detail-section {{
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 1px dashed {text_color_light};
            }}
            .employee-profile-card .detail-section:last-child {{
                border-bottom: none;
            }}
            .employee-profile-card .avatar-placeholder {{
                width: 100px;
                height: 100px;
                border-radius: 50%;
                background-color: #ccc;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 2.5em;
                font-weight: bold;
                color: white;
                margin: 0 auto 20px auto;
                overflow: hidden;
            }}
            .employee-profile-card .avatar-placeholder img {{
                width: 100%;
                height: 100%;
                object-fit: cover;
            }}
            .form-container {{
                background: {form_container_bg_light if not dark_mode else form_container_bg_dark};
                border-radius: 20px;
                padding: 30px;
                margin-bottom: 40px;
                box-shadow: {form_container_shadow};
                border: {form_container_border_light if not dark_mode else form_container_border_dark};
                transition: all 0.3s ease;
            }}
            .form-container:hover {{
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25) !important;
            }}
            .form-container h3 {{
                color: {text_color_main};
                border-bottom: 1px solid {primary_color};
                padding-bottom: 10px;
                margin-bottom: 25px;
            }}
            .form-container .stButton > button {{
                width: 100%;
            }}
        </style>
    """, unsafe_allow_html=True)

    # --- Session State Management ---
    if 'employees_df' not in st.session_state:
        st.session_state['employees_df'] = pd.DataFrame()
    if 'refresh_employees' not in st.session_state:
        st.session_state['refresh_employees'] = True
    if 'update_success_msg' not in st.session_state:
        st.session_state['update_success_msg'] = None
    if 'edit_employee_id' not in st.session_state:
        st.session_state['edit_employee_id'] = None
    if 'edit_employee_data' not in st.session_state:
        st.session_state['edit_employee_data'] = {}
    if 'show_delete_confirm' not in st.session_state:
        st.session_state['show_delete_confirm'] = False
    if 'employee_to_delete_id' not in st.session_state:
        st.session_state['employee_to_delete_id'] = None
    if 'employee_to_delete_name' not in st.session_state:
        st.session_state['employee_to_delete_name'] = None
    if 'selected_employee_for_view' not in st.session_state:
        st.session_state['selected_employee_for_view'] = None
    if 'onboarding_templates' not in st.session_state:
        st.session_state['onboarding_templates'] = []
    if 'offboarding_templates' not in st.session_state:
        st.session_state['offboarding_templates'] = []
    if 'performance_review_templates' not in st.session_state:
        st.session_state['performance_review_templates'] = []
    if 'refresh_templates' not in st.session_state:
        st.session_state['refresh_templates'] = True

    # --- Data Fetching ---
    if st.session_state['refresh_employees']:
        with st.spinner("Loading employees..."):
            employees_list = get_employees_from_firestore(sanitized_user_company)
            st.session_state['employees_df'] = pd.DataFrame(employees_list)
            st.session_state['refresh_employees'] = False
            if not st.session_state['employees_df'].empty:
                st.session_state['employees_df'] = st.session_state['employees_df'].set_index('id')

    if st.session_state['refresh_templates']:
        st.session_state['onboarding_templates'] = get_documents_from_firestore(get_template_collection_path("onboarding"))
        st.session_state['offboarding_templates'] = get_documents_from_firestore(get_template_collection_path("offboarding"))
        st.session_state['performance_review_templates'] = get_documents_from_firestore(get_template_collection_path("performance_review"))
        st.session_state['refresh_templates'] = False

    if st.session_state['update_success_msg']:
        st.success(st.session_state['update_success_msg'])
        if st.button("Dismiss Message"):
            st.session_state['update_success_msg'] = None
            st.rerun()

    # --- TABBED INTERFACE ---
    tab_titles = ["Dashboard", "Directory", "Onboarding Tracker", "Manage Employees", "Templates", "Bulk Actions"]
    
    # We use st.tabs but since we can't programmatically select easily in standard Streamlit,
    # we'll ensure our logic respects the selected tab and avoids unnecessary jumping.
    emp_tabs = st.tabs(tab_titles)


    with emp_tabs[3]: # Manage Employees
        st.subheader("Manage Your Team")
        
        # --- Split View Layout ---
        manage_col_list, manage_col_form = st.columns([1, 2.5])
        
        with manage_col_list:
            st.markdown("### Employees")
            search_emp = st.text_input("Search employees...", key="manage_search_input", placeholder="Name or Role")
            
            # Action: Reset to "Add New"
            if st.button("➕ Add New Employee", use_container_width=True):
                st.session_state['edit_employee_id'] = None
                st.session_state['edit_employee_data'] = {}
                st.rerun()

            st.markdown("---")
            # List of employees
            if not st.session_state['employees_df'].empty:
                temp_df = st.session_state['employees_df'].copy()
                if search_emp:
                    temp_df = temp_df[
                        temp_df['name'].str.contains(search_emp, case=False, na=False) |
                        temp_df['role'].str.contains(search_emp, case=False, na=False)
                    ]
                
                # Use a scrollable container for the list
                st.markdown('<div style="max-height: 600px; overflow-y: auto;">', unsafe_allow_html=True)
                for emp_id, row in temp_df.iterrows():
                    is_editing = (st.session_state['edit_employee_id'] == emp_id)
                    btn_label = f"**{row['name']}**\n{row['role']}"
                    if st.button(btn_label, key=f"select_emp_{emp_id}", use_container_width=True, type="secondary" if not is_editing else "primary"):
                        st.session_state['edit_employee_id'] = emp_id
                        # Fetch full data to ensure we have everything
                        st.session_state['edit_employee_data'] = row.to_dict()
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No employees found.")

        with manage_col_form:
            is_edit_mode = st.session_state.get('edit_employee_id') is not None
            current_data = st.session_state.get('edit_employee_data', {}) if is_edit_mode else {}
            
            if is_edit_mode:
                st.markdown(f"### Management: {current_data.get('name', 'N/A')}")
                m_tabs = st.tabs(["Edit Details", "View Profile", "Lifecycle Tasks"])
                
                with m_tabs[0]: # Edit Details
                    st.markdown('<div class="form-container">', unsafe_allow_html=True)
                    with st.form("manage_employee_form_edit", clear_on_submit=False):
                        st.markdown("#### Core Information")
                        c1, c2 = st.columns(2)
                        with c1:
                            m_name = st.text_input("Full Name", value=current_data.get('name', ''), key="m_name_e")
                            m_email = st.text_input("Email", value=current_data.get('email', ''), key="m_email_e")
                            m_phone = st.text_input("Phone", value=current_data.get('phone', ''), key="m_phone_e")
                        with c2:
                            m_role = st.text_input("Role", value=current_data.get('role', ''), key="m_role_e")
                            m_dept = st.text_input("Department", value=current_data.get('department', ''), key="m_dept_e")
                            m_manager = st.text_input("Manager", value=current_data.get('manager', ''), key="m_manager_e")
                        
                        c3, c4 = st.columns(2)
                        with c3:
                            m_hire_date = st.date_input("Hire Date", value=safe_date_convert(current_data.get('hire_date'), datetime.now().date()), key="m_hire_date_e")
                        with c4:
                            m_dob = st.date_input("Date of Birth", value=safe_date_convert(current_data.get('date_of_birth'), datetime(2000,1,1).date()), key="m_dob_e")
                        
                        st.markdown("---")
                        st.markdown("#### Emergency Contact")
                        ec_data = current_data.get('emergency_contact', {})
                        if not isinstance(ec_data, dict): ec_data = {}
                        ec1, ec2, ec3 = st.columns(3)
                        with ec1:
                            m_ec_name = st.text_input("Contact Name", value=ec_data.get('name', ''), key="m_ec_name_e")
                        with ec2:
                            m_ec_rel = st.text_input("Relationship", value=ec_data.get('relationship', ''), key="m_ec_rel_e")
                        with ec3:
                            m_ec_phone = st.text_input("Contact Phone", value=ec_data.get('phone', ''), key="m_ec_phone_e")

                        st.markdown("---")
                        st.markdown("#### Professional Details")
                        pd1, pd2 = st.columns(2)
                        with pd1:
                            # Safely handle list inputs
                            current_skills = current_data.get('skills', [])
                            if current_skills is None: current_skills = []
                            skills_val = ", ".join(map(str, current_skills)) if isinstance(current_skills, list) else str(current_skills)
                            m_skills = st.text_area("Skills (comma-separated)", value=skills_val, key="m_skills_e", height=68)
                        with pd2:
                            current_certs = current_data.get('certifications', [])
                            if current_certs is None: current_certs = []
                            certs_val = ", ".join(map(str, current_certs)) if isinstance(current_certs, list) else str(current_certs)
                            m_certs = st.text_area("Certifications (comma-separated)", value=certs_val, key="m_certs_e", height=68)

                        st.markdown("---")
                        st.markdown("#### Salary & Payout")
                        breakdown = current_data.get('salary_breakdown', {})
                        if not isinstance(breakdown, dict): breakdown = {}
                        sc1, sc2, sc3 = st.columns(3)
                        with sc1:
                            m_base = st.number_input("Base Salary", value=float(breakdown.get('base', 0.0)), key="m_base_e")
                            m_hra = st.number_input("HRA", value=float(breakdown.get('hra', 0.0)), key="m_hra_e")
                        with sc2:
                            m_allow = st.number_input("Allowances", value=float(breakdown.get('allowances', 0.0)), key="m_allow_e")
                            m_bonus = st.number_input("Bonus", value=float(breakdown.get('bonus', 0.0)), key="m_bonus_e")
                        with sc3:
                            m_deduct = st.number_input("Deductions", value=float(breakdown.get('deductions', 0.0)), key="m_deduct_e")
                            m_status = st.selectbox("Status", ["Active", "On Leave", "Terminated"], 
                                                 index=["Active", "On Leave", "Terminated"].index(current_data.get('status', 'Active')), key="m_status_e")

                        st.markdown("---")
                        st.markdown("#### Banking")
                        bc1, bc2 = st.columns(2)
                        with bc1:
                            m_bank_acc = st.text_input("Account Number", value=current_data.get('bank_account', ''), key="m_bank_acc_e")
                        with bc2:
                            m_ifsc = st.text_input("IFSC Code", value=current_data.get('ifsc_code', ''), key="m_ifsc_e")

                        st.markdown("---")
                        st.markdown("#### Lifecycle & Templates")
                        ltc1, ltc2 = st.columns(2)
                        with ltc1:
                            m_offboarding_date = st.date_input("Offboarding Date", value=safe_date_convert(current_data.get('offboarding_date')), key="m_offboarding_date_e")
                        with ltc2:
                            offboard_temp_options = ["None"] + [t['name'] for t in st.session_state['offboarding_templates']]
                            m_offboard_temp = st.selectbox("Apply Offboarding Template", options=offboard_temp_options, key="m_offboard_temp_e")

                        m_submitted = st.form_submit_button("Update Employee", use_container_width=True)
                        
                        if m_submitted:
                            if m_name and m_email and m_role:
                                skills_list = [s.strip() for s in m_skills.split(',') if s.strip()]
                                certs_list = [c.strip() for c in m_certs.split(',') if c.strip()]

                                updated_data = {
                                    "name": m_name,
                                    "email": m_email,
                                    "phone": m_phone,
                                    "role": m_role,
                                    "department": m_dept,
                                    "manager": m_manager,
                                    "hire_date": m_hire_date.isoformat(),
                                    "date_of_birth": m_dob.isoformat(),
                                    "status": m_status,
                                    "emergency_contact": {"name": m_ec_name, "relationship": m_ec_rel, "phone": m_ec_phone},
                                    "skills": skills_list,
                                    "certifications": certs_list,
                                    "salary_breakdown": {
                                        "base": m_base, "hra": m_hra, "allowances": m_allow,
                                        "bonus": m_bonus, "deductions": m_deduct
                                    },
                                    "salary": m_base + m_hra + m_allow + m_bonus - m_deduct,
                                    "bank_account": m_bank_acc,
                                    "ifsc_code": m_ifsc,
                                    "offboarding_date": m_offboarding_date.isoformat() if m_offboarding_date else None
                                }
                                
                                if m_offboard_temp != "None" and m_offboarding_date:
                                    selected_temp = next((t for t in st.session_state['offboarding_templates'] if t['name'] == m_offboard_temp), None)
                                    if selected_temp:
                                        off_tasks = []
                                        off_date_obj = pd.to_datetime(m_offboarding_date)
                                        for t in selected_temp.get('tasks', []):
                                            due_days = t.get('due_days_before_offboarding', 0)
                                            task_due = (off_date_obj - timedelta(days=due_days)).date()
                                            off_tasks.append({
                                                "task_name": t.get('task_name'),
                                                "responsible_role": t.get('responsible_role'),
                                                "status": "Pending",
                                                "due_date": task_due.isoformat()
                                            })
                                        updated_data["offboarding_tasks"] = off_tasks
                                
                                update_document_in_firestore(get_employee_collection_path(sanitized_user_company), st.session_state['edit_employee_id'], updated_data)
                                st.session_state['update_success_msg'] = f"Employee **{m_name}** updated successfully!"
                                st.session_state['refresh_employees'] = True
                                st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    if st.button("Delete Employee", use_container_width=True, type="secondary"):
                        st.session_state['show_delete_confirm'] = True
                        st.session_state['employee_to_delete_id'] = st.session_state['edit_employee_id']
                        st.session_state['employee_to_delete_name'] = current_data['name']
                        st.rerun()

                with m_tabs[1]: # View Profile
                    avatar_svg_data = generate_avatar_svg(current_data.get('name', 'N/A'))
                    st.markdown(f"""
                    <div class="employee-profile-card">
                        <div class="avatar-placeholder">
                            <img src="{avatar_svg_data}" alt="Avatar"/>
                        </div>
                        <h3>{current_data.get('name', 'N/A')}</h3>
                        <div class="detail-section">
                            <p><strong>Email:</strong> {current_data.get('email', 'N/A')}</p>
                            <p><strong>Phone:</strong> {current_data.get('phone', 'N/A')}</p>
                            <p><strong>Role:</strong> {current_data.get('role', 'N/A')}</p>
                            <p><strong>Department:</strong> {current_data.get('department', 'N/A')}</p>
                            <p><strong>Status:</strong> {current_data.get('status', 'N/A')}</p>
                        </div>
                        <div class="detail-section">
                            <p><strong>Hire Date:</strong> {current_data.get('hire_date', 'N/A')}</p>
                            <p><strong>Salary (Total):</strong> ₹{current_data.get('salary', 0.0):,.2f}</p>
                            <p><strong>Leave Balance:</strong> {current_data.get('leave_balance', 0)} days</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("#### Performance Trend")
                    perf_history = current_data.get('performance_history')
                    
                    if perf_history and isinstance(perf_history, list) and len(perf_history) > 0:
                        try:
                            perf_df = pd.DataFrame(perf_history)
                            if 'date' in perf_df.columns and 'score' in perf_df.columns:
                                perf_df['date'] = pd.to_datetime(perf_df['date'])
                                
                                # Calculate Company Average
                                all_emps = st.session_state.get('employees_data', [])
                                all_perf_scores = []
                                for e in all_emps:
                                    ph = e.get('performance_history')
                                    if ph and isinstance(ph, list):
                                        for p in ph:
                                            if isinstance(p, dict) and p.get('score'):
                                                all_perf_scores.append({'date': p.get('date'), 'score': p.get('score')})
                                
                                fig = px.line(perf_df, x='date', y='score', markers=True, title="Score over time")
                                fig.update_traces(name='Employee', showlegend=True)

                                if all_perf_scores:
                                    avg_df = pd.DataFrame(all_perf_scores)
                                    avg_df['date'] = pd.to_datetime(avg_df['date'])
                                    avg_score = avg_df['score'].mean()
                                    fig.add_hline(y=avg_score, line_dash="dash", annotation_text=f"Company Avg: {avg_score:.1f}", annotation_position="top right", line_color="gray")
                                
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("Performance history missing required 'date' or 'score' fields.")
                        except Exception as e:
                             st.error(f"Error displaying performance chart: {e}")
                    else:
                        st.info("No performance history available.")

                with m_tabs[2]: # Lifecycle Tasks
                    st.markdown("#### Onboarding Progress")
                    tasks = current_data.get('onboarding_tasks', [])
                    if tasks is None: tasks = []
                    updated_on_tasks = []
                    
                    # Using a form for task updates to prevent excessive reruns
                    with st.form("lifecycle_tasks_form"):
                        st.markdown("CHECK to mark as Completed, UNCHECK for Pending.")
                        
                        # ROBOTIC VALIDATION: Ensure tasks is a LIST before iterating
                        if isinstance(tasks, list) and len(tasks) > 0:
                            for t in tasks:
                                if isinstance(t, dict): # Ensure t is a dict
                                    is_done = st.checkbox(f"{t.get('task_name')} ({t.get('responsible_role')})", 
                                                value=(t.get('status') == 'Completed'), key=f"otask_{t.get('task_name')}_{current_data.get('name')}")
                                    updated_on_tasks.append({**t, "status": "Completed" if is_done else "Pending"})
                        else:
                            st.info("No onboarding tasks assigned.")
                        
                        st.markdown("---")
                        st.markdown("#### Offboarding Progress")
                        off_tasks = current_data.get('offboarding_tasks', [])
                        updated_off_tasks = []
                        
                        # ROBOTIC VALIDATION: Ensure off_tasks is a LIST before iterating
                        if isinstance(off_tasks, list) and len(off_tasks) > 0:
                            for t in off_tasks:
                                if isinstance(t, dict):
                                    is_done = st.checkbox(f"{t.get('task_name')} ({t.get('responsible_role')})", 
                                                value=(t.get('status') == 'Completed'), key=f"ftask_{t.get('task_name')}_{current_data.get('name')}")
                                    updated_off_tasks.append({**t, "status": "Completed" if is_done else "Pending"})
                        else:
                            st.info("No offboarding tasks assigned.")
                            
                        save_tasks = st.form_submit_button("Save Task Progress", use_container_width=True)
                        if save_tasks:
                            # Update only the task lists in Firestore
                            update_payload = {}
                            if updated_on_tasks:
                                update_payload['onboarding_tasks'] = updated_on_tasks
                            if updated_off_tasks:
                                update_payload['offboarding_tasks'] = updated_off_tasks
                            
                            if update_payload:
                                update_document_in_firestore(get_employee_collection_path(sanitized_user_company), st.session_state['edit_employee_id'], update_payload)
                                st.success("Task progress saved successfully!")
                                st.session_state['refresh_employees'] = True
                                # Slight delay to show success message before rerun or just let it persist
                                st.rerun()

            else: # Add mode
                st.markdown("### Add New Employee")
                st.markdown('<div class="form-container">', unsafe_allow_html=True)
                with st.form("manage_employee_form_add", clear_on_submit=False):
                    st.markdown("#### Core Information")
                    c1, c2 = st.columns(2)
                    with c1:
                        m_name = st.text_input("Full Name", key="m_name_a")
                        m_email = st.text_input("Email", key="m_email_a")
                        m_phone = st.text_input("Phone", key="m_phone_a")
                    with c2:
                        m_role = st.text_input("Role", key="m_role_a")
                        m_dept = st.text_input("Department", key="m_dept_a")
                        m_manager = st.text_input("Manager", key="m_manager_a")
                    
                    c3, c4 = st.columns(2)
                    with c3:
                        m_hire_date = st.date_input("Hire Date", value=datetime.now().date(), key="m_hire_date_a")
                    with c4:
                        m_dob = st.date_input("Date of Birth", value=date(2000, 1, 1), key="m_dob_a")
                    
                    st.markdown("#### Emergency Contact")
                    ec1, ec2, ec3 = st.columns(3)
                    with ec1:
                        m_ec_name = st.text_input("Contact Name", key="m_ec_name_a")
                    with ec2:
                        m_ec_rel = st.text_input("Relationship", key="m_ec_rel_a")
                    with ec3:
                        m_ec_phone = st.text_input("Contact Phone", key="m_ec_phone_a")

                    st.markdown("#### Professional Details")
                    pd1, pd2 = st.columns(2)
                    with pd1:
                        m_skills = st.text_area("Skills (comma-separated)", key="m_skills_a", height=68, help="E.g., Python, Management, Sales")
                    with pd2:
                        m_certs = st.text_area("Certifications (comma-separated)", key="m_certs_a", height=68, help="E.g., PMP, AWS Certified")

                    st.markdown("#### Salary")
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        m_base = st.number_input("Base Salary", value=0.0, key="m_base_a")
                        m_hra = st.number_input("HRA", value=0.0, key="m_hra_a")
                    with sc2:
                        m_allow = st.number_input("Allowances", value=0.0, key="m_allow_a")
                        m_status = st.selectbox("Status", ["Active", "On Leave", "Terminated"], key="m_status_a")
                    
                    st.markdown("#### Lifecycle")
                    onboard_temp_options = ["None"] + [t['name'] for t in st.session_state['onboarding_templates']]
                    m_onboard_temp = st.selectbox("Apply Onboarding Template", options=onboard_temp_options, key="m_onboard_temp_a")

                    m_submitted = st.form_submit_button("Add Employee", use_container_width=True)
                    if m_submitted:
                        if m_name and m_email and m_role:
                            onboard_tasks = []
                            if m_onboard_temp != "None":
                                selected_temp = next((t for t in st.session_state['onboarding_templates'] if t['name'] == m_onboard_temp), None)
                                if selected_temp:
                                    hire_date_obj = pd.to_datetime(m_hire_date)
                                    for t in selected_temp.get('tasks', []):
                                        due_days = t.get('due_days_after_hire', 0)
                                        task_due = (hire_date_obj + timedelta(days=due_days)).date()
                                        onboard_tasks.append({
                                            "task_name": t.get('task_name'),
                                            "responsible_role": t.get('responsible_role'),
                                            "status": "Pending",
                                            "due_date": task_due.isoformat()
                                        })
                            
                            skills_list = [s.strip() for s in m_skills.split(',') if s.strip()]
                            certs_list = [c.strip() for c in m_certs.split(',') if c.strip()]

                            new_emp = {
                                "name": m_name, "email": m_email, "phone": m_phone,
                                "role": m_role, "department": m_dept, "manager": m_manager,
                                "hire_date": m_hire_date.isoformat(), "date_of_birth": m_dob.isoformat(),
                                "status": m_status,
                                "salary_breakdown": {"base": m_base, "hra": m_hra, "allowances": m_allow, "bonus": 0, "deductions": 0},
                                "salary": m_base + m_hra + m_allow,
                                "onboarding_tasks": onboard_tasks,
                                "onboarding_status": "Pending",
                                "performance_history": [],
                                "emergency_contact": {"name": m_ec_name, "relationship": m_ec_rel, "phone": m_ec_phone},
                                "skills": skills_list,
                                "certifications": certs_list,
                                "goals": [], "development_plans": [], "documents": []
                            }
                            add_employee_to_firestore(new_emp, sanitized_user_company)
                            st.session_state['update_success_msg'] = f"Employee **{m_name}** added!"
                            st.session_state['refresh_employees'] = True
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    with emp_tabs[0]: # Dashboard Tab
        st.subheader("Employee Overview and Statistics")

        if not st.session_state['employees_df'].empty:
            total_employees = len(st.session_state['employees_df'])
            avg_salary = st.session_state['employees_df']['salary'].mean()
            
            department_counts = st.session_state['employees_df']['department'].value_counts().to_dict()
            
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                st.metric(label="Total Employees", value=total_employees)
            with col_stats2:
                st.metric(label="Average Salary", value=f"₹{avg_salary:,.2f}")
            with col_stats3:
                st.metric(label="Departments", value=len(department_counts))
            
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.markdown("##### Department Distribution")
                dept_df = st.session_state['employees_df']['department'].value_counts().reset_index()
                dept_df.columns = ['Department', 'Count']
                fig_dept = px.bar(dept_df, x='Department', y='Count', 
                                  title='Employees by Department',
                                  color='Department',
                                  color_discrete_sequence=px.colors.qualitative.Pastel,
                                  template="plotly_white" if not dark_mode else "plotly_dark")
                st.plotly_chart(fig_dept, use_container_width=True)

            with chart_col2:
                st.markdown("##### Employment Status")
                status_df = st.session_state['employees_df']['status'].value_counts().reset_index()
                status_df.columns = ['Status', 'Count']
                fig_status = px.pie(status_df, names='Status', values='Count', 
                                    title='Employees by Status',
                                    template="plotly_white" if not dark_mode else "plotly_dark")
                st.plotly_chart(fig_status, use_container_width=True)

            st.markdown("##### Collective Skills Insight")
            if 'skills' in st.session_state['employees_df'].columns and not st.session_state['employees_df']['skills'].empty:
                all_skills = [skill for sublist in st.session_state['employees_df']['skills'].tolist() if isinstance(sublist, list) for skill in sublist]
                if all_skills:
                    skills_text = " ".join(all_skills)
                    wordcloud = WordCloud(width=800, height=200, background_color="white" if not dark_mode else "#1E1E1E").generate(skills_text)
                    fig, ax = plt.subplots(figsize=(10, 3))
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis('off')
                    st.pyplot(fig)
                    plt.close(fig)
        else:
            st.info("No employee data available for dashboard.")

    with emp_tabs[2]: # Onboarding Tracker Tab
        st.subheader("Active Onboarding and Offboarding Processes")
        
        if not st.session_state['employees_df'].empty:
            # Active Onboarding
            onboarding_df = st.session_state['employees_df'][
                st.session_state['employees_df']['onboarding_status'].isin(["Pending", "In Progress"])
            ]
            
            if not onboarding_df.empty:
                st.markdown("### Active Onboarding")
                for idx, emp in onboarding_df.iterrows():
                    tasks = emp.get('onboarding_tasks', [])
                    if not isinstance(tasks, list): tasks = []
                    completed = len([t for t in tasks if isinstance(t, dict) and t.get('status') == 'Completed'])
                    total = len(tasks)
                    progress = (completed / total) if total > 0 else 0
                    
                    with st.expander(f"{emp['name']} - {emp['role']} ({int(progress*100)}%)"):
                        st.progress(progress)
                        st.markdown(f"**Department:** {emp['department']} | **Hire Date:** {emp['hire_date']}")
                        if tasks:
                            cols = st.columns([2, 1, 1])
                            cols[0].markdown("**Task**")
                            cols[1].markdown("**Responsible**")
                            cols[2].markdown("**Status**")
                            for task in tasks:
                                t_cols = st.columns([2, 1, 1])
                                t_cols[0].write(task.get('task_name'))
                                t_cols[1].write(task.get('responsible_role'))
                                t_cols[2].write(task.get('status'))
                        else:
                            st.info("No tasks assigned.")
            else:
                st.info("No active onboarding processes.")

            st.markdown("---")
            
            # Active Offboarding
            if 'offboarding_date' in st.session_state['employees_df'].columns:
                offboarding_df = st.session_state['employees_df'][
                    st.session_state['employees_df']['offboarding_date'].notnull()
                ]
            else:
                offboarding_df = pd.DataFrame()
            
            if not offboarding_df.empty:
                st.markdown("### Active Offboarding")
                for idx, emp in offboarding_df.iterrows():
                    tasks = emp.get('offboarding_tasks', [])
                    if not isinstance(tasks, list): tasks = []
                    completed = len([t for t in tasks if isinstance(t, dict) and t.get('status') == 'Completed'])
                    total = len(tasks)
                    progress = (completed / total) if total > 0 else 0
                    
                    with st.expander(f"{emp['name']} - {emp['role']} (Offboarding: {emp['offboarding_date']})"):
                        st.progress(progress)
                        if tasks:
                            cols = st.columns([2, 1, 1])
                            cols[0].markdown("**Task**")
                            cols[1].markdown("**Responsible**")
                            cols[2].markdown("**Status**")
                            for task in tasks:
                                t_cols = st.columns([2, 1, 1])
                                t_cols[0].write(task.get('task_name'))
                                t_cols[1].write(task.get('responsible_role'))
                                t_cols[2].write(task.get('status'))
                        else:
                            st.info("No tasks assigned.")
            else:
                st.info("No active offboarding processes.")
        else:
            st.info("No employee data available.")

    with emp_tabs[4]: # Templates Tab
        template_management_page()

    with emp_tabs[5]: # Bulk Actions Tab
        st.subheader("Bulk Employee Import")
        st.markdown("""
        Upload a CSV file to add multiple employees at once. 
        Ensure your CSV follows the required format.
        """)
        
        # Download Template
        template_data = {
            'name': ['John Doe'],
            'email': ['john@example.com'],
            'phone': ['555-0101'],
            'role': ['Software Engineer'],
            'department': ['Engineering'],
            'manager': ['Jane Smith'],
            'hire_date': ['2024-01-01'],
            'salary': [80000],
            'status': ['Active']
        }
        template_df = pd.DataFrame(template_data)
        st.download_button(
            label="Example CSV Template",
            data=template_df.to_csv(index=False),
            file_name="employee_import_template.csv",
            mime="text/csv"
        )
        
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        if uploaded_file is not None:
            try:
                import_df = pd.read_csv(uploaded_file)
                st.write("Preview of Uploaded Data:")
                st.dataframe(import_df.head(), use_container_width=True)
                
                if st.button("Confirm and Import Employees"):
                    progress_bar = st.progress(0)
                    success_count = 0
                    for i, row in import_df.iterrows():
                        # Basic data construction
                        new_emp = {
                            "name": str(row.get('name', 'N/A')),
                            "email": str(row.get('email', 'N/A')),
                            "phone": str(row.get('phone', '')),
                            "role": str(row.get('role', 'N/A')),
                            "department": str(row.get('department', 'N/A')),
                            "manager": str(row.get('manager', '')),
                            "hire_date": str(row.get('hire_date', datetime.now().isoformat())),
                            "salary": float(row.get('salary', 0)),
                            "status": str(row.get('status', 'Active')),
                            "onboarding_status": "Pending",
                            "onboarding_tasks": [],
                            "offboarding_date": None,
                            "offboarding_tasks": [],
                            "performance_review_date": None,
                            "performance_score": 0,
                            "performance_history": [],
                            "goals": [],
                            "certifications": [],
                            "development_plans": [],
                            "documents": [],
                            "address": "",
                            "skills": [],
                            "notes": "Bulk Imported",
                            "emergency_contact": {"name": "", "relationship": "", "phone": ""}
                        }
                        add_document_to_firestore(get_employee_collection_path(sanitized_user_company), new_emp)
                        success_count += 1
                        progress_bar.progress(success_count / len(import_df))
                    
                    st.success(f"Successfully imported {success_count} employees!")
                    st.session_state['refresh_employees'] = True
                    st.rerun()
            except Exception as e:
                st.error(f"Error processing file: {e}")



    with emp_tabs[1]: # Directory Tab
        st.subheader("Current Employees")

        if st.session_state['employees_df'].empty:
            st.info("No employees added yet. Use the 'Manage Employees' tab to add your first employee!")
        else:
            st.markdown("### Search and Filter Employees")
            search_col, status_filter_col, dept_filter_col = st.columns(3)
            # ... (Search/Filter logic) ...
            with search_col:
                search_query = st.text_input("Search by Name, Email, Role, or Phone", key="employee_search_query", placeholder="e.g., John Doe, HR, 555-1234")
            with status_filter_col:
                all_statuses = ["All"] + list(st.session_state['employees_df']['status'].unique())
                selected_status = st.selectbox("Filter by Employment Status", options=all_statuses, key="employee_status_filter")
            with dept_filter_col:
                all_departments = ["All"] + list(st.session_state['employees_df']['department'].unique())
                selected_department = st.selectbox("Filter by Department", options=all_departments, key="employee_department_filter")

            filtered_display_df = st.session_state['employees_df'].copy()
            # ... (Rest of filtering and table display) ...
            
            # (I'll keep the full logic here in the actual tool call)

        filtered_display_df = st.session_state['employees_df'].copy()

        if search_query:
            search_query_lower = search_query.lower()
            filtered_display_df = filtered_display_df[
                filtered_display_df['name'].str.lower().str.contains(search_query_lower, na=False) |
                filtered_display_df['email'].str.lower().str.contains(search_query_lower, na=False) |
                filtered_display_df['role'].str.lower().str.contains(search_query_lower, na=False) |
                filtered_display_df['department'].str.lower().str.contains(search_query_lower, na=False) |
                filtered_display_df['phone'].str.lower().str.contains(search_query_lower, na=False)
            ]
        
        if selected_status != "All":
            filtered_display_df = filtered_display_df[filtered_display_df['employment_status'] == selected_status]

        if selected_department != "All":
            filtered_display_df = filtered_display_df[filtered_display_df['department'] == selected_department]


        for col in ['hire_date', 'date_of_birth', 'performance_review_date', 'last_promotion_date', 'offboarding_date']:
            if col in filtered_display_df.columns:
                filtered_display_df[col] = pd.to_datetime(filtered_display_df[col], errors='coerce').dt.date
        
        if 'skills' in filtered_display_df.columns:
            filtered_display_df['skills'] = filtered_display_df['skills'].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)

        if 'training_courses' in filtered_display_df.columns:
            filtered_display_df['training_courses'] = filtered_display_df['training_courses'].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)

        if 'performance_history' in filtered_display_df.columns:
            filtered_display_df['performance_history_display'] = filtered_display_df['performance_history'].apply(
                lambda history: "; ".join([f"{entry.get('date', 'N/A')}: {entry.get('score', 'N/A')}" for entry in history]) if isinstance(history, list) else "N/A"
            )
        
        if 'onboarding_tasks' in filtered_display_df.columns:
            filtered_display_df['onboarding_tasks_display'] = filtered_display_df['onboarding_tasks'].apply(
                lambda tasks: "; ".join([f"{t.get('task_name', 'N/A')} ({t.get('status', 'N/A')})" for t in tasks]) if isinstance(tasks, list) else "N/A"
            )

        if 'offboarding_tasks' in filtered_display_df.columns:
            filtered_display_df['offboarding_tasks_display'] = filtered_display_df['offboarding_tasks'].apply(
                lambda tasks: "; ".join([f"{t.get('task_name', 'N/A')} ({t.get('status', 'N/A')})" for t in tasks]) if isinstance(tasks, list) else "N/A"
            )

        if 'goals' in filtered_display_df.columns:
            filtered_display_df['goals_display'] = filtered_display_df['goals'].apply(
                lambda goals: "; ".join([f"{g.get('goal_name', 'N/A')} ({g.get('current_progress', 'N/A')}, {g.get('status', 'N/A')})" for g in goals]) if isinstance(goals, list) else "N/A"
            )

        if 'certifications' in filtered_display_df.columns:
            filtered_display_df['certifications_display'] = filtered_display_df['certifications'].apply(
                lambda certs: "; ".join([
                    f"{c.get('name', 'N/A')} (Expires: {c.get('expiry_date', 'N/A')})" if isinstance(c, dict) else str(c)
                    for c in certs
                ]) if isinstance(certs, list) else "N/A"
            )

        if 'development_plans' in filtered_display_df.columns:
            filtered_display_df['development_plans_display'] = filtered_display_df['development_plans'].apply(
                lambda plans: "; ".join([f"{p.get('plan_name', 'N/A')} ({p.get('status', 'N/A')})" for p in plans]) if isinstance(plans, list) else "N/A"
            )
        
        if 'documents' in filtered_display_df.columns:
            filtered_display_df['documents_display'] = filtered_display_df['documents'].apply(
                lambda docs: "; ".join([f"{d.get('name', 'N/A')} ({d.get('type', 'N/A')})" for d in docs]) if isinstance(docs, list) else "N/A"
            )

        if 'external_feedback' in filtered_display_df.columns:
            filtered_display_df['external_feedback_display'] = filtered_display_df['external_feedback'].apply(
                lambda feedback_list: "; ".join([
                    f"{f.get('reviewer_name', 'N/A')} ({f.get('relationship', 'N/A')})"
                    for f in feedback_list if isinstance(f, dict)
                ]) if isinstance(feedback_list, list) else "N/A"
            )


        if 'emergency_contact' in filtered_display_df.columns:
            filtered_display_df['Emergency Contact Name'] = filtered_display_df['emergency_contact'].apply(lambda x: x.get('name') if isinstance(x, dict) else '')
            filtered_display_df['Emergency Contact Phone'] = filtered_display_df['emergency_contact'].apply(lambda x: x.get('phone') if isinstance(x, dict) else '')
            filtered_display_df['Emergency Contact Rel'] = filtered_display_df['emergency_contact'].apply(lambda x: x.get('relationship') if isinstance(x, dict) else '')

        display_cols = [
            'name', 'email', 'phone', 'role', 'department', 'manager', 'employment_status', 'onboarding_status',
            'onboarding_tasks_display',
            'offboarding_date',
            'offboarding_tasks_display',
            'hire_date', 'date_of_birth', 'performance_review_date', 'performance_score', 'performance_history_display', 
            'goals_display',
            'certifications_display',
            'development_plans_display',
            'documents_display',
            'external_feedback_display',
            'last_promotion_date', 
            'salary', 'leave_balance', 'training_courses', 'address', 'skills', 'notes', 
            'Emergency Contact Name', 'Emergency Contact Phone', 'Emergency Contact Rel'
        ]
        display_cols = [col for col in display_cols if col in filtered_display_df.columns]

        st.dataframe(
            filtered_display_df[display_cols],
            use_container_width=True,
            column_config={
                "name": "Employee Name",
                "email": "Email",
                "phone": "Phone",
                "role": "Role",
                "department": "Department",
                "manager": "Manager",
                "employment_status": "Status",
                "onboarding_status": "Onboarding",
                "onboarding_tasks_display": st.column_config.Column("Onboarding Tasks", help="Current Onboarding Tasks"),
                "offboarding_date": st.column_config.DateColumn("Offboarding Date", format="YYYY-MM-DD"),
                "offboarding_tasks_display": st.column_config.Column("Offboarding Tasks", help="Current Offboarding Tasks"),
                "hire_date": st.column_config.DateColumn("Hire Date", format="YYYY-MM-DD"),
                "date_of_birth": st.column_config.DateColumn("Date of Birth", format="YYYY-MM-DD"),
                "performance_review_date": st.column_config.DateColumn("Latest Review Date", format="YYYY-MM-DD"),
                "performance_score": st.column_config.NumberColumn("Latest Perf. Score", format="%d", help="Latest Performance Score (1-5)"),
                "performance_history_display": st.column_config.Column("Performance History", help="Historical Performance Reviews (Date: Score)"),
                "goals_display": st.column_config.Column("Goals", help="Employee Goals"),
                "certifications_display": st.column_config.Column("Certifications", help="Employee Certifications"),
                "development_plans_display": st.column_config.Column("Dev Plans", help="Employee Development Plans"),
                "documents_display": st.column_config.Column("Documents", help="Links to Employee Documents"),
                "external_feedback_display": st.column_config.Column("External Feedback", help="Summarized External Feedback"),
                "last_promotion_date": st.column_config.DateColumn("Last Promo", format="YYYY-MM-DD"),
                "salary": st.column_config.NumberColumn("Salary", format="$%.2f"),
                "leave_balance": st.column_config.NumberColumn("Leave (Days)", format="%d", help="Available Leave Balance in Days"),
                "training_courses": st.column_config.Column("Training", help="Completed Training Courses"),
                "address": "Address",
                "skills": "Skills",
                "notes": "Notes",
                "Emergency Contact Name": "EC Name",
                "Emergency Contact Phone": "EC Phone",
                "Emergency Contact Rel": "EC Rel"
            }
        )

        @st.cache_data
        def convert_df_to_csv(df):
            return df.to_csv().encode('utf-8')

        csv_data = convert_df_to_csv(filtered_display_df)
        st.download_button(
            label="Export Employee Data to CSV",
            data=csv_data,
            file_name="employee_data.csv",
            mime="text/csv",
            key="export_csv_button"
        )

    return True

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    employee_management_page()
