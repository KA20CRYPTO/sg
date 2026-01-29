import streamlit as st
import requests
from datetime import datetime

# --- Formspree Endpoint ---
# IMPORTANT: Replace this with your actual Formspree endpoint if different from the example
FORMSPREE_ENDPOINT = "https://formspree.io/f/mwpqevno"

# --- Logging Function ---
def log_user_action(user_email, action, details=None):
    """Logs user actions to the console for tracking purposes."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if details:
        print(f"[{timestamp}] User '{user_email}' performed '{action}' with details: {details}")
    else:
        print(f"[{timestamp}] User '{user_email}' performed '{action}'")

# --- Feedback & Help Page ---
def feedback_and_help_page():
    user_email = st.session_state.get('user_email', 'anonymous')
    log_user_action(user_email, "FEEDBACK_HELP_PAGE_ACCESSED")

    # --- Color Palette (STRICTLY LIGHT MODE) ---
    ACCENT_COLOR = '#00cec9'        # Primary Cyan/Aqua
    ACCENT_HOVER = '#00a39c'        
    BG_COLOR = '#f0f5ff'            # Very light blue-white background
    BG_GRADIENT = 'linear-gradient(180deg, #f0f5ff 0%, #ffffff 100%)'
    TEXT_COLOR_MAIN = '#1a202c'     # Dark Slate for high contrast
    TEXT_COLOR_LIGHT = '#6b7280'    # Muted Gray
    CARD_BG_FROSTY = 'rgba(255, 255, 255, 0.85)' # Semi-transparent for Glass effect
    
    SHADOW_FROST = '0 10px 40px rgba(0, 206, 201, 0.15), 0 5px 15px rgba(0, 0, 0, 0.05)'
    SHADOW_HOVER = '0 20px 50px rgba(0, 206, 201, 0.3), 0 8px 20px rgba(0, 0, 0, 0.1)'
    
    TRANSITION_SMOOTH = 'all 0.5s cubic-bezier(0.23, 1, 0.32, 1)'

    # --- CSS & Animations ---
    st.markdown(f"""
    <style>
    /* Global Styles */
    .stApp {{
        background: {BG_GRADIENT};
        font-family: 'Poppins', 'Inter', sans-serif;
        color: {TEXT_COLOR_MAIN};
    }}

    /* Hero Banner - Vibrant and Modern */
    .hero {{
        position: relative;
        border-radius: 25px;
        text-align: center;
        color: white;
        overflow: hidden;
        padding: 80px 40px;
        background: linear-gradient(135deg, {ACCENT_COLOR}, #81ecec);
        box-shadow: 0 15px 50px rgba(0, 206, 201, 0.4);
        animation: fadeInScale 1.5s ease-out;
    }}
    .hero h1 {{
        position: relative; z-index:1;
        font-size: 4em;
        margin-bottom: 10px;
        font-weight: 900;
        letter-spacing: -1px;
        animation: slideInDown 1s ease-out;
    }}
    .hero p {{
        position: relative; z-index:1;
        font-size: 1.4em;
        max-width: 900px;
        margin: auto;
        line-height: 1.6;
    }}

    /* Main Section Header */
    h2 {{
        font-size: 2.5em;
        font-weight: 800;
        color: {TEXT_COLOR_MAIN};
        margin-top: 50px;
        margin-bottom: 30px;
        text-align: center;
    }}
    h2::after {{
        content: '';
        display: block;
        width: 60px;
        height: 4px;
        background: {ACCENT_COLOR};
        margin: 10px auto 0;
        border-radius: 2px;
    }}
    
    /* Cards - Glassmorphism Effect */
    .card, .faq-card, .contact-card {{
        background: {CARD_BG_FROSTY};
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-radius: 20px;
        padding: 30px;
        box-shadow: {SHADOW_FROST};
        border: 1px solid rgba(255, 255, 255, 0.5); /* Light border */
        transition: {TRANSITION_SMOOTH};
        animation: fadeInUp 1s ease-out;
        margin-bottom: 25px;
        height: 100%;
    }}
    .card:hover {{
        transform: translateY(-8px);
        box-shadow: {SHADOW_HOVER};
        border-color: {ACCENT_COLOR}; 
    }}
    .card h3, .faq-card h3, .contact-card h3 {{
        color: {ACCENT_COLOR};
        margin-bottom: 8px;
        font-size: 1.5em;
        font-weight: 700;
        display: flex;
        align-items: center;
    }}
    .card p, .faq-card p, .contact-card p {{
        color: {TEXT_COLOR_LIGHT};
        line-height: 1.6;
    }}
    .faq-card, .contact-card {{
        border-left: 5px solid {ACCENT_COLOR}; /* Feature stripe */
        cursor: default;
    }}
    .faq-card:hover, .contact-card:hover {{
        transform: none;
    }}
    .contact-info p {{
        font-weight: 600;
        color: {TEXT_COLOR_MAIN};
        margin-bottom: 5px;
    }}
    .contact-info a {{
        color: {ACCENT_COLOR};
        text-decoration: none;
    }}

    /* Feedback Form - Contained Contrast */
    .form-card {{
        background: {CARD_BG_FROSTY};
        backdrop-filter: blur(10px);
        border-radius: 25px;
        padding: 40px;
        box-shadow: 0 15px 45px rgba(0,0,0,0.1);
    }}
    .stTextInput>div>div>input, .stTextArea>div>div, .stTextInput>label {{
        border-radius: 12px;
        border: 1px solid #d1d5db;
        padding: 10px;
        font-size: 1em;
        background-color: {BG_COLOR}; 
    }}
    .stButton>button {{
        background: linear-gradient(90deg, #00cec9, #81ecec);
        color: white;
        border-radius: 40px; 
        padding: 1em 2.5em;
        font-size: 1.1em;
        font-weight: 700;
        border: none;
        transition: {TRANSITION_SMOOTH};
        box-shadow: 0 8px 25px rgba(0, 206, 201, 0.4);
        margin-top: 1.5rem;
    }}
    .stButton>button:hover {{
        transform: translateY(-5px) scale(1.03);
        box-shadow: 0 12px 35px rgba(0, 206, 201, 0.6);
    }}

    /* Animations (Simplified) */
    @keyframes fadeInScale {{ 0% {{opacity: 0; transform: scale(0.97);}} 100% {{opacity: 1; transform: scale(1);}} }}
    @keyframes slideInDown {{ 0% {{transform: translateY(-80px); opacity:0;}} 100% {{transform: translateY(0); opacity:1;}} }}
    @keyframes fadeInUp {{ 0% {{transform: translateY(40px); opacity:0;}} 100% {{transform: translateY(0); opacity:1;}} }}
    </style>
    """, unsafe_allow_html=True)

    # --- Hero Section ---
    st.markdown("""
    <div class="hero">
        <h1>💬 We're Here to Help.</h1>
        <p>Your feedback fuels our innovation. Share your thoughts, report issues, or find quick answers to common questions below.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # --- Features: Categories, FAQ & Contact ---
    
    st.markdown("<h2>💡 Feedback Categories</h2>", unsafe_allow_html=True)
    categories = [
        ("Feature Request", "Suggest new features or enhancements to our screening models and UI.", "✨"),
        ("Bug Report / Issue", "Report unexpected behavior, errors, or performance issues.", "🐞"),
        ("General Inquiry / Help", "Ask questions about usage, billing, or request guidance.", "❓")
    ]
    cols = st.columns(3)
    for i, (title, desc, icon) in enumerate(categories):
        with cols[i]:
            st.markdown(f"""
            <div class="card">
                <h3>{icon} {title}</h3>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    
    st.markdown("<h2>🤝 Need Immediate Assistance?</h2>", unsafe_allow_html=True)
    
    faq_cols = st.columns([2, 1])
    
    with faq_cols[0]:
        # FAQ/Quick Answers
        st.subheader("📚 Quick Answers (FAQ)")
        faq_items = [
            ("How secure is my data?", "We use end-to-end encryption (HTTPS) and never use your uploaded resumes or job descriptions for AI training."),
            ("What does the AI score mean?", "The score is a quantified measure of alignment between the candidate's profile and the job description, using validated skill, experience, and keyword matches."),
            ("Can I integrate with my ATS?", "Yes, ScreenerPro offers a robust API for seamless integration with major Applicant Tracking Systems. Contact our support for setup guidance.")
        ]
        for question, answer in faq_items:
            st.markdown(f"""
            <div class="faq-card" style="margin-bottom: 20px;">
                <h3 style="font-size: 1.2em;">{question}</h3>
                <p>{answer}</p>
            </div>
            """, unsafe_allow_html=True)

    with faq_cols[1]:
        # Contact Box 
        st.subheader("📞 Direct Contact")
        st.markdown(f"""
        <div class="contact-card">
            <h3>Contact Sales & Support</h3>
            <div class="contact-info">
                <p>👤 **Manav Nagpal** (CEO)</p>
                <p>📧 <a href="mailto:SCREENERPRO.AI@GMAIL.COM">SCREENERPRO.AI@GMAIL.COM</a></p>
                <p>📱 <a href="tel:+919896817707">+91 98968 17707</a></p>
            </div>
            <p style='margin-top: 15px; font-size:0.9em;'>For immediate or executive-level inquiries regarding integration and enterprise access.</p>
        </div>
        """, unsafe_allow_html=True)


    st.markdown("---")

    # --- Feedback Form (FIXED LOGIC) ---
    st.markdown("<h2>📝 Send Us Your Feedback</h2>", unsafe_allow_html=True)
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    
    # All form elements MUST be inside the `with st.form` block
    with st.form("feedback_form", clear_on_submit=True):
        st.markdown(f'<p style="color:{TEXT_COLOR_LIGHT}; margin-bottom: 25px;">Please fill out the details below. We aim to respond to inquiries within 24 hours.</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            feedback_name = st.text_input("Your Name (Optional)", placeholder="e.g., Jane Doe")
        with col2:
            default_email = user_email if user_email != 'anonymous' else ""
            feedback_email = st.text_input("Your Email (Required for response) *", value=default_email, placeholder="e.g., you@example.com")
            
        feedback_category = st.selectbox("Topic Category *", options=[
            "Feature Request", "Bug Report / Issue", "General Inquiry / Help", "Billing / Account"
        ], index=0)
        
        feedback_message = st.text_area("Your Detailed Message *", height=180, placeholder=f"Describe your {feedback_category} here...")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Streamlit Submit Button MUST be the last widget in the form
        submit_button = st.form_submit_button(f"🚀 Send {feedback_category}")

        if submit_button:
            if not feedback_message.strip() or not feedback_email.strip():
                st.error("❌ Please ensure your message and email address are provided.")
                log_user_action(user_email, "FEEDBACK_SUBMIT_FAILED", {"reason": "Missing required fields"})
            else:
                payload = {
                    "name": feedback_name,
                    "email": feedback_email,
                    "category": feedback_category,
                    "message": feedback_message
                }
                try:
                    response = requests.post(FORMSPREE_ENDPOINT, data=payload)
                    if response.status_code == 200:
                        st.success("✅ Success! Your feedback has been submitted. We'll be in touch soon.")
                        st.balloons()
                        log_user_action(user_email, "FEEDBACK_SUBMITTED_FORMSPREE", {"category": feedback_category})
                    else:
                        st.error(f"⚠️ Submission failed. Status: {response.status_code}. Please try emailing support directly.")
                        log_user_action(user_email, "FEEDBACK_SUBMIT_FAILED", {"status": response.status_code})
                except Exception as e:
                    st.error(f"⚠️ An error occurred while sending feedback: {e}")
                    log_user_action(user_email, "FEEDBACK_SUBMIT_FAILED", {"error": str(e)})
                    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    st.set_page_config(page_title="ScreenerPro - Feedback & Help", layout="wide", page_icon="❓")
    # Initialize session state variables if running as a standalone script
    if 'user_email' not in st.session_state:
        st.session_state['user_email'] = 'guest@screenerpro.com'
    if 'dark_mode_main' not in st.session_state:
        st.session_state['dark_mode_main'] = False
        
    feedback_and_help_page()
