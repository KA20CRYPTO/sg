# =========================================================
# landing.py — ScreenerPro Landing Page (CLEAN & FAST)
# =========================================================

import json
import html
import requests
import streamlit as st
import streamlit.components.v1 as components

from firebase_config import (
    FIRESTORE_DOCUMENTS_URL,
    FIREBASE_WEB_API_KEY,
)

# =========================================================
# FIREBASE PROJECT ID
# =========================================================
PROJECT_ID = FIRESTORE_DOCUMENTS_URL.split("/projects/")[1].split("/")[0]

# =========================================================
# STREAMLIT CONFIG
# =========================================================
st.set_page_config(
    page_title="ScreenerPro • AI Talent Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# HIDE STREAMLIT UI
# =========================================================
try:
    from client_page import handle_activation
except ImportError:
    def handle_activation():
        return False

if handle_activation():
    st.success("🎉 Your account is now activated! You can now log in.")

st.markdown(
    """
    <style>
    [data-testid="stHeader"],
    [data-testid="stSidebar"],
    [data-testid="stSidebarNav"],
    #MainMenu { display:none; }
    .block-container { padding:0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# ROUTING (HR PORTAL)
# =========================================================
params = st.query_params
if params.get("action") == "hr_portal":
    st.switch_page("pages/main.py")
    st.stop()

if params.get("page") == "blog":
    st.switch_page("pages/blogs.py")
    st.stop()

# =========================================================
# HTTP SESSION (REUSED)
# =========================================================
SESSION = requests.Session()
SESSION.headers.update({"Content-Type": "application/json"})

# =========================================================
# FIRESTORE BATCH LOADER (FAST & CACHED)
# =========================================================
@st.cache_data(show_spinner=False, ttl=3600, persist=True)
def load_docs_batch(paths):
    url = (
        f"https://firestore.googleapis.com/v1/projects/"
        f"{PROJECT_ID}/databases/(default)/documents:batchGet"
        f"?key={FIREBASE_WEB_API_KEY}"
    )

    payload = {
        "documents": [
            f"projects/{PROJECT_ID}/databases/(default)/documents/{p}"
            for p in paths
        ]
    }

    r = SESSION.post(url, json=payload, timeout=6)
    if r.status_code != 200:
        return {}

    data = {}
    for item in r.json():
        if "found" not in item:
            continue

        doc = item["found"]
        doc_id = doc["name"].split("/")[-1]
        fields = doc.get("fields", {})

        data[doc_id] = {
            k: html.unescape(v.get("stringValue", ""))
            for k, v in fields.items()
        }

    return data

# =========================================================
# LOAD ALL FIREBASE CONTENT (ONE REQUEST)
# =========================================================
DOCS = load_docs_batch([
    "site_content/landing_content",
    "site_content/metrics",
    "site_content/announcement",
    "site_content/privacy_policy",
    "site_content/terms_conditions",
    "site_content/faqs",
])

# =========================================================
# FAQ PARSING (SAFE)
# =========================================================
faq_data = None
raw_faq = DOCS.get("faqs")

if raw_faq:
    try:
        faq_data = {
            "enabled": raw_faq.get("enabled") in ("true", "True", True),
            "title": raw_faq.get("title", ""),
            "subtitle": raw_faq.get("subtitle", ""),
            "items": json.loads(raw_faq.get("items", "[]")),
        }
    except Exception:
        faq_data = None

# =========================================================
# CACHE landing.html
# =========================================================
@st.cache_data(show_spinner=False, persist=True)
def load_landing_html():
    with open("landing.html", "r", encoding="utf-8") as f:
        return f.read()

# =========================================================
# RENDER LANDING
# =========================================================
page_html = load_landing_html()

inject_js = """
<script>
window.LANDING_DATA      = __LANDING__;
window.METRICS_DATA      = __METRICS__;
window.ANNOUNCEMENT_DATA = __ANNOUNCEMENT__;
window.PRIVACY_DATA      = __PRIVACY__;
window.TERMS_DATA        = __TERMS__;
window.FAQS_DATA         = __FAQS__;

function isExpired(data) {
  if (!data || !data.expiry) return false;
  const today = new Date().toISOString().split("T")[0];
  return data.expiry < today;
}

document.addEventListener("DOMContentLoaded", function () {

  window.LANDING_DATA && window.injectLandingContent?.(window.LANDING_DATA);
  window.METRICS_DATA && window.injectMetrics?.(window.METRICS_DATA);

  if (window.FAQS_DATA?.enabled && window.injectFAQs) {
    window.injectFAQs(window.FAQS_DATA);
  }

  if (window.ANNOUNCEMENT_DATA && !isExpired(window.ANNOUNCEMENT_DATA)) {
    window.injectAnnouncement?.(window.ANNOUNCEMENT_DATA);
  }

  if (
    window.ANNOUNCEMENT_DATA &&
    window.ANNOUNCEMENT_DATA.type === "first_open_banner" &&
    !isExpired(window.ANNOUNCEMENT_DATA)
  ) {
    window.showFirebaseBanner?.(window.ANNOUNCEMENT_DATA);
  }

  window.addEventListener("REQUEST_LEGAL", function (e) {
    if (e.detail === "privacy" && window.PRIVACY_DATA) {
      window.injectPrivacyPolicy?.(window.PRIVACY_DATA);
      window.openPrivacyModal?.();
    }
    if (e.detail === "terms" && window.TERMS_DATA) {
      window.injectTermsPolicy?.(window.TERMS_DATA);
      window.openTermsModal?.();
    }
  });
});
</script>
"""

inject_js = (
    inject_js
    .replace("__LANDING__", json.dumps(DOCS.get("landing_content")))
    .replace("__METRICS__", json.dumps(DOCS.get("metrics")))
    .replace("__ANNOUNCEMENT__", json.dumps(DOCS.get("announcement")))
    .replace("__PRIVACY__", json.dumps(DOCS.get("privacy_policy")))
    .replace("__TERMS__", json.dumps(DOCS.get("terms_conditions")))
    .replace("__FAQS__", json.dumps(faq_data))
)

components.html(
    page_html + inject_js,
    height=1200,
    scrolling=True,
)
