# -----------------------------
# 🔥 CENTRAL SHARED FIREBASE CONFIG
# -----------------------------

import os

# API Key for Firebase Auth and Firestore
FIREBASE_WEB_API_KEY = os.environ.get(
    "FIREBASE_WEB_API_KEY",
    "AIzaSyDjC7tdmpEkpsipgf9r1c3HlTO7C7BZ6Mw"
)

# Project ID
FIREBASE_PROJECT_ID = "screenerproapp"

# Auth URLs
FIREBASE_AUTH_SIGNUP_URL = (
    f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_WEB_API_KEY}"
)

FIREBASE_AUTH_SIGNIN_URL = (
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
)

FIREBASE_AUTH_RESET_PASSWORD_URL = (
    f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_WEB_API_KEY}"
)

# Firestore Base URL
FIRESTORE_DOCUMENTS_URL = (
    f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents"
)
FIREBASE_AUTH_SIGNIN_IDP_URL = (
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={FIREBASE_WEB_API_KEY}"
)
# -----------------------------
