import requests
from datetime import datetime
import streamlit as st
import requests
from datetime import datetime

def save_certificate_to_firestore_public(app_id, api_key, cert_data):
    """
    Saves a certificate into Firestore under:
    public_certificates/{Certificate ID}
    """

    cert_id = cert_data.get("Certificate ID")
    if not cert_id:
        raise ValueError("Certificate ID missing in cert_data")

    url = f"https://firestore.googleapis.com/v1/projects/{app_id}/databases/(default)/documents/public_certificates/{cert_id}?key={api_key}"

    # Convert data to Firestore format
    firestore_payload = {
        "fields": {
            key.replace(" ", "_").lower(): (
                {"stringValue": str(value)}
            )
            for key, value in cert_data.items()
        }
    }

    res = requests.patch(url, json=firestore_payload)

    if res.status_code not in [200, 201]:
        raise Exception(f"Failed to save certificate: {res.status_code} -> {res.text}")

    return True

def to_firestore_format(data: dict) -> dict:
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
            fields[key] = {"timestampValue": value.isoformat() + "Z"}
        elif isinstance(value, dict):
            fields[key] = {"mapValue": {"fields": to_firestore_format(value)["fields"]}}
        elif isinstance(value, list):
            fields[key] = {"arrayValue": {"values": [to_firestore_format({"v": v})["fields"]["v"] for v in value]}}
        elif value is None:
            fields[key] = {"nullValue": None}
        else:
            fields[key] = {"stringValue": str(value)}
    return {"fields": fields}

def from_firestore_format(firestore_data: dict) -> dict:
    if "fields" not in firestore_data:
        return {}
    result = {}
    for k, v in firestore_data["fields"].items():
        if "stringValue" in v:
            result[k] = v["stringValue"]
        elif "integerValue" in v:
            result[k] = int(v["integerValue"])
        elif "doubleValue" in v:
            result[k] = float(v["doubleValue"])
        elif "booleanValue" in v:
            result[k] = v["booleanValue"]
        elif "timestampValue" in v:
            try:
                result[k] = datetime.fromisoformat(v["timestampValue"].replace("Z", ""))
            except:
                result[k] = v["timestampValue"]
        elif "mapValue" in v and "fields" in v["mapValue"]:
            result[k] = from_firestore_format(v["mapValue"])
        elif "arrayValue" in v and "values" in v["arrayValue"]:
            result[k] = [from_firestore_format({"fields": {"v": item}})["v"] for item in v["arrayValue"]["values"]]
        elif "nullValue" in v:
            result[k] = None
    return result

def add_document(collection_path, data, api_key, base_url):
    url = f"{base_url}/documents/{collection_path}?key={api_key}"
    try:
        res = requests.post(url, json=to_firestore_format(data))
        res.raise_for_status()
        return True, res.json()
    except Exception as e:
        st.error(f"Firestore add error: {e}")
        return False, str(e)

def update_document(collection_path, doc_id, data, api_key, base_url):
    url = f"{base_url}/documents/{collection_path}/{doc_id}?key={api_key}"
    try:
        res = requests.patch(url, json=to_firestore_format(data))
        res.raise_for_status()
        return True, res.json()
    except Exception as e:
        st.error(f"Firestore update error: {e}")
        return False, str(e)

def get_document(collection_path, doc_id, api_key, base_url):
    url = f"{base_url}/documents/{collection_path}/{doc_id}?key={api_key}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        return True, from_firestore_format(res.json())
    except Exception as e:
        return False, str(e)

def list_documents(collection_path, api_key, base_url):
    url = f"{base_url}/documents/{collection_path}?key={api_key}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        docs = []
        if "documents" in data:
            for doc in data["documents"]:
                d = from_firestore_format(doc)
                d["id"] = doc["name"].split("/")[-1]
                docs.append(d)
        return True, docs
    except Exception as e:
        return False, str(e)

def log_activity(message, user, app_id, company, api_key, base_url):
    collection_path = f"artifacts/{app_id}/companies/{company}/activity_feed"
    add_document(
        collection_path,
        {"message": message, "user": user, "timestamp": datetime.now()},
        api_key, base_url
    )
