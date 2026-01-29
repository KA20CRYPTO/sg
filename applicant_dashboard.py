import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd
import urllib.parse
import os

# Firebase Project ID and API Key from environment variables
FIREBASE_PROJECT_ID = globals().get('__app_id', 'screenerproapp')
FIREBASE_WEB_API_KEY = os.environ.get('FIREBASE_WEB_API_KEY', 'AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw')
FIRESTORE_DATABASE_ROOT_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)"

# --- Firebase Data Persistence Functions (Copied for self-containment) ---
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

@st.cache_data(ttl=1) # Cache for 1 second
def get_applications_for_campaign(campaign_id: str, user_uid: str, firebase_project_id: str, firestore_database_root_url: str, firebase_web_api_key: str):
    """Retrieves all applications for a specific job campaign."""
    if not campaign_id or not user_uid:
        return []
    
    collection_path = f"artifacts/{firebase_project_id}/users/{user_uid}/my_campaigns/{campaign_id}/applications"
    url = f"{firestore_database_root_url}/documents/{collection_path}?key={firebase_web_api_key}"

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

def applicant_dashboard_page():
    st.markdown('<div class="dashboard-header">👥 Applicant Dashboard</div>', unsafe_allow_html=True)

    # Get campaign_id and hr_user_uid from query parameters
    query_params = st.query_params
    campaign_id = query_params.get("campaign_id")
    hr_user_uid = query_params.get("hr_user_uid")

    if not campaign_id or not hr_user_uid:
        st.error("Campaign ID or HR User ID not provided. Please navigate from the HR Campaign Creator page.")
        st.stop()

    # Fetch campaign details to display job title and company
    campaign_path = f"artifacts/{FIREBASE_PROJECT_ID}/users/{hr_user_uid}/my_campaigns"
    campaign_details = get_single_doc_from_firestore_rest(campaign_path, campaign_id)

    if campaign_details:
        st.subheader(f"Applicants for: {campaign_details.get('job_title', 'N/A')} at {campaign_details.get('company_name', 'N/A')}")
        st.write(f"**Campaign ID:** `{campaign_id}`")
        st.write(f"**Posted On:** {campaign_details.get('posted_date', 'N/A')}")
        st.write(f"**Application Deadline:** {campaign_details.get('application_deadline', 'N/A')}")
        st.write(f"**Status:** {campaign_details.get('status', 'N/A').capitalize()}")
        st.markdown("---")
    else:
        st.warning("Could not retrieve campaign details.")
        st.markdown("---")

    # Fetch applications for the campaign
    applications = get_applications_for_campaign(
        campaign_id,
        hr_user_uid,
        FIREBASE_PROJECT_ID,
        FIRESTORE_DATABASE_ROOT_URL,
        FIREBASE_WEB_API_KEY
    )

    if not applications:
        st.info("No applications found for this campaign yet.")
        return

    df_applications = pd.DataFrame(applications)

    # Ensure all expected columns exist, fill missing ones
    expected_cols = [
        "applicant_name", "applicant_email", "applied_at", "status", "AI_Decision",
        "ai_score", "years_experience", "cgpa", "matched_skills", "missing_skills",
        "ai_suggestion", "resume_filename", "certificate_id", "certificate_rank",
        "Manual Shortlist" # Added for potential future manual override
    ]
    for col in expected_cols:
        if col not in df_applications.columns:
            df_applications[col] = None

    # Convert applied_at to datetime for sorting
    df_applications['applied_at'] = pd.to_datetime(df_applications['applied_at'], errors='coerce')
    df_applications = df_applications.sort_values(by='applied_at', ascending=False)

    st.subheader("All Applicants")

    # Filters
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        search_query = st.text_input("Search Applicant (Name/Email/Resume Filename):", "")
    with col_filter2:
        filter_status = st.selectbox("Filter by Status:", ["All", "shortlisted", "submitted"], index=0)

    filtered_df = df_applications.copy()
    if search_query:
        search_query_lower = search_query.lower()
        filtered_df = filtered_df[
            filtered_df['applicant_name'].str.lower().str.contains(search_query_lower, na=False) |
            filtered_df['applicant_email'].str.lower().str.contains(search_query_lower, na=False) |
            filtered_df['resume_filename'].str.lower().str.contains(search_query_lower, na=False)
        ]
    if filter_status != "All":
        filtered_df = filtered_df[filtered_df['status'] == filter_status]

    if not filtered_df.empty:
        # Columns to display in the main table
        display_cols = [
            "applicant_name", "applicant_email", "applied_at", "status", "AI_Decision",
            "ai_score", "years_experience", "cgpa", "resume_filename"
        ]
        
        # Ensure 'Manual Shortlist' is boolean for the checkbox
        if 'Manual Shortlist' in filtered_df.columns:
            filtered_df['Manual Shortlist'] = filtered_df['Manual Shortlist'].astype(bool)

        edited_df = st.data_editor(
            filtered_df[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "applicant_name": st.column_config.TextColumn("Applicant Name"),
                "applicant_email": st.column_config.TextColumn("Email"),
                "applied_at": st.column_config.DatetimeColumn("Applied At", format="YYYY-MM-DD HH:mm"),
                "status": st.column_config.TextColumn("Application Status"),
                "AI_Decision": st.column_config.TextColumn("AI Decision"),
                "ai_score": st.column_config.ProgressColumn(
                    "AI Score (%)",
                    help="AI Match Score against job requirements",
                    format="%.1f", 
                    min_value=0,
                    max_value=100,
                ),
                "years_experience": st.column_config.NumberColumn("Years Exp."),
                "cgpa": st.column_config.NumberColumn("CGPA (4.0)"),
                "resume_filename": st.column_config.TextColumn("Resume File"),
            }
        )
        # For now, we don't save changes from data_editor back to Firestore
        # This would require a more complex update mechanism for subcollections.
        # st.session_state['current_campaign_applicants_df'] = edited_df.copy()

        st.markdown("---")
        st.subheader("Applicant Details and Collaboration (Future Features)")
        st.info("Click on an applicant's row in the table above to view their detailed profile, add notes, and manage their status. This interactive feature is under development.")

        # Placeholder for detailed applicant view and collaboration features
        st.markdown("##### Placeholder: Selected Applicant Details")
        st.write("Select an applicant from the table above to see their detailed screening results, full resume text, and to add collaborative notes.")

        # Example of how to get selected row (requires user to select a row in data_editor)
        # This is a conceptual example, as data_editor doesn't directly expose selected row index easily for this use case.
        # A workaround would involve adding a unique key to each row and using a separate button/select box.
        # For now, this section is purely illustrative.
        
        with st.expander("Shared Notes & Feedback (Coming Soon)"):
            st.write("This section will allow HR team members to add shared notes and feedback on the selected applicant.")
            st.text_area("Add a new note:", height=100, key="new_note_placeholder", disabled=True)
            st.button("Save Note", key="save_note_placeholder", disabled=True)
            st.markdown("---")
            st.write("##### Existing Notes:")
            st.info("No notes yet. (Notes will appear here once implemented.)")

        with st.expander("Applicant Status & Workflow (Coming Soon)"):
            st.write("Track the applicant's progress through the hiring pipeline.")
            st.selectbox("Current Status:", ["Applied", "Screened", "Interview Scheduled", "Interviewed", "Offer Extended", "Hired", "Rejected"], key="applicant_status_placeholder", disabled=True)
            st.button("Update Status", key="update_status_placeholder", disabled=True)
            st.info("Status updates will be visible to all assigned HR team members.")

    else:
        st.info("No applicants found matching your search and filter criteria.")

# This ensures the page runs when accessed directly or via navigation
if __name__ == "__main__":
    st.set_page_config(page_title="ScreenerPro - Applicant Dashboard", layout="wide", page_icon="👥")
    applicant_dashboard_page()
