import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

PROJECT_ID = "screenerproapp"
FIREBASE_WEB_API_KEY = "AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw"
WEB_API_KEY = "AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw"
FIRESTORE_BASE_URL = (
    f"https://firestore.googleapis.com/v1/projects/"
    f"{PROJECT_ID}/databases/(default)/documents"
)

def _jd_collection(company: str) -> str:
    return f"companies/{company}/jds"

def _s_str(fields, key, default=""):
    return fields.get(key, {}).get("stringValue", default)

def fs_get_jds(company_name):
    url = (
        f"https://firestore.googleapis.com/v1/projects/"
        f"{PROJECT_ID}/databases/(default)/documents/"
        f"companies/{company_name}/jds?key={WEB_API_KEY}"
    )

    res = requests.get(url)
    if res.status_code != 200:
        return []

    jds = []
    for doc in res.json().get("documents", []):
        fields = doc.get("fields", {})

        title = fields.get("title", {}).get("stringValue", "")
        description = fields.get("description", {}).get("stringValue", "")

        # 🔍 DEBUG (keep once)
   #     print("DEBUG fs_get_jds:", title, "len =", len(description))

        jds.append({
            "title": title,
            "description": description   # ✅ ONLY THIS
        })

    return jds

