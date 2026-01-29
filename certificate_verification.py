import streamlit as st
import requests
from datetime import datetime

def certificate_verification_page(app_id, FIREBASE_WEB_API_KEY):
    st.markdown("<h2 style='color:#00cec9; text-align: center; font-family: \"Playfair Display\", serif;'>🎓 ScreenerPro Certificate Verification</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-family: \"Inter\", sans-serif;'>Enter a <strong>Certificate ID</strong> to verify authenticity.</p>", unsafe_allow_html=True)

    # Initialize session state
    if 'verified' not in st.session_state:
        st.session_state.verified = False
    if 'cert_data' not in st.session_state:
        st.session_state.cert_data = {}
    if 'cert_id' not in st.session_state:
        st.session_state.cert_id = ''

    st.markdown("""
    <style>
    /* Input box styling */
    div.stTextInput > div > input {
        border-radius: 12px;
        padding: 12px;
        border: 2px solid #00bcd4;
        background: rgba(255, 255, 255, 0.1);
        color: #222;
        font-size: 16px;
        transition: all 0.3s ease;
    }
    div.stTextInput > div > input:focus {
        border-color: #00cec9;
        box-shadow: 0 0 10px rgba(0, 206, 201, 0.4);
    }

    /* Buttons */
    div.stButton > button {
        background: linear-gradient(90deg, #00bcd4, #00cec9);
        color: white;
        border-radius: 12px;
        padding: 10px 20px;
        font-weight: 600;
        font-size: 16px;
        transition: all 0.3s ease;
        box-shadow: 0 6px 18px rgba(0,0,0,0.2);
    }
    div.stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        background: linear-gradient(90deg, #00cec9, #00bcd4);
    }

    /* Verified certificate card */
    .cert-card {
        background: rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 30px 25px;
        margin: 25px 0;
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        font-family: 'Inter', sans-serif;
        transition: all 0.3s ease;
    }
    .cert-card h3 {
        color: #00bcd4;
        margin-bottom: 15px;
        font-family: 'Playfair Display', serif;
        font-weight: 700;
    }
    .cert-card div {
        line-height: 1.8;
        color: #333;
        font-size: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

    cert_id = st.text_input("🔑 Certificate ID", help="The unique ID printed on the certificate.", value=st.session_state.cert_id)

    col1, col2 = st.columns(2)
    with col1:
        verify_button = st.button("🔍 Verify Certificate", use_container_width=True)
    with col2:
        clear_button = st.button("🔄 Clear", use_container_width=True)

    if clear_button:
        st.session_state.verified = False
        st.session_state.cert_data = {}
        st.session_state.cert_id = ''
        st.rerun()

    FIRESTORE_DATABASE_ROOT_URL = f"https://firestore.googleapis.com/v1/projects/{app_id}/databases/(default)"

    def get_field_value(field, default="N/A"):
        if not field:
            return default
        return (
            field.get("stringValue")
            or field.get("integerValue")
            or field.get("doubleValue")
            or field.get("timestampValue")
            or default
        )

    if verify_button:
        st.session_state.cert_id = cert_id
        if not st.session_state.cert_id:
            st.session_state.verified = False
            st.warning("⚠️ Please enter a Certificate ID.")
        else:
            with st.spinner("Verifying certificate... 🔎"):
                try:
                    doc_path = f"public_certificates/{st.session_state.cert_id}"
                    url = f"{FIRESTORE_DATABASE_ROOT_URL}/documents/{doc_path}?key={FIREBASE_WEB_API_KEY}"

                    res = requests.get(url)

                    if res.status_code == 200:
                        firestore_data = res.json()
                        fields = firestore_data.get("fields", {})
                        st.session_state.verified = True
                        st.session_state.cert_data = fields
                    elif res.status_code == 404:
                        st.session_state.verified = False
                        st.session_state.cert_data = {}
                        st.error("❌ Certificate Not Found. Please double-check the ID.")
                    else:
                        st.session_state.verified = False
                        st.session_state.cert_data = {}
                        st.error(f"⚠️ Error during verification: {res.status_code}")

                except Exception as e:
                    st.session_state.verified = False
                    st.session_state.cert_data = {}
                    st.error(f"🔥 Unexpected error: {e}")

    if st.session_state.verified:
        fields = st.session_state.cert_data
        cert_id_display = st.session_state.cert_id

        candidate = get_field_value(fields.get("candidate_name"))
        score = get_field_value(fields.get("score"))
        rank = get_field_value(fields.get("certificate_rank"))
        jd_used = get_field_value(fields.get("jd_used"))
        date_awarded = get_field_value(fields.get("date_screened"))

        if date_awarded and date_awarded != "N/A":
            try:
                date_awarded = datetime.fromisoformat(date_awarded.replace("Z", "+00:00")).strftime("%B %d, %Y")
            except Exception:
                pass

        # Render certificate details card
        html_details = f"""
<div class="cert-card">
    <h3>✅ Certificate Verified</h3>
    <div style="text-align:left;">
        <strong>👤 Candidate:</strong> {candidate} <br>
        <strong>📊 Score:</strong> {score}% <br>
        <strong>🏅 Rank:</strong> {rank} <br>
        <strong>📝 Job Description:</strong> {jd_used} <br>
        <strong>📅 Date Awarded:</strong> {date_awarded or "N/A"} <br>
        <strong>🔑 Certificate ID:</strong> {cert_id_display}
    </div>
</div>
"""
        st.markdown(html_details, unsafe_allow_html=True)

        # Certificate HTML (unchanged)
        html_template = f"""
        <div style="margin-top:30px;">
            <iframe srcdoc='
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8" />
                <style>
                    @import url("https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;600&display=swap");
                    body {{
                        margin: 0;
                        font-family: "Inter", sans-serif;
                        background: #ffffff;
                        text-align: center;
                        padding: 40px;
                    }}
                    .certificate {{
                        border: 10px solid #00bcd4;
                        padding: 50px;
                        max-width: 900px;
                        margin: auto;
                        box-shadow: 0 0 20px rgba(0,0,0,0.1);
                        border-radius: 20px;
                    }}
                    h1 {{
                        font-family: "Playfair Display", serif;
                        font-size: 34px;
                        color: #003049;
                    }}
                    h2 {{
                        font-size: 20px;
                        color: #007c91;
                    }}
                    .candidate-name {{
                        font-family: "Playfair Display", serif;
                        font-size: 28px;
                        color: #00bcd4;
                        margin: 15px 0;
                        font-weight: bold;
                        text-decoration: underline;
                    }}
                    .score-rank {{
                        background: #e0f7fa;
                        display: inline-block;
                        padding: 8px 20px;
                        border-radius: 6px;
                        margin: 20px 0;
                        font-weight: 600;
                        color: #2e7d32;
                    }}
                    .footer-details {{
                        font-size: 14px;
                        color: #555;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="certificate">
                    <img src="https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhhq_OCSv-QmuBjXeRQXr60EfsvVA4chRPCNslo3NhjVQkoKjUtiRfTPpGoQjyQXS7sMsJifQC6Yq34cAhNbq9lMwBXZqIIbCij1adyXSuNoyxuzOTDfrPU2dnna0baimldd7Y1KCkvaAfrWC1yLGxp25SJ9s4exJ-JAc8kNcTyUSgkLWbW2DdvhpWH4GlO/s578/logo.png" width="150" />
                    <h1>CERTIFICATE OF EXCELLENCE</h1>
                    <h2>Presented by ScreenerPro</h2>
                    <p>This is to certify that</p>
                    <div class="candidate-name">{candidate}</div>
                    <p>has successfully completed the AI-powered resume screening process</p>
                    <div class="score-rank">Score: {score}% | Rank: {rank}</div>
                    <div class="footer-details">
                        Awarded on: {date_awarded or "N/A"} <br>
                        Certificate ID: {cert_id_display}
                    </div>
                </div>
            </body>
            </html>
            ' width="100%" height="700px" style="border:none;"></iframe>
        </div>
        """
        st.markdown(html_template, unsafe_allow_html=True)
