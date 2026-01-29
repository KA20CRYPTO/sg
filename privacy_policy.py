import streamlit as st
from datetime import datetime

def privacy_policy_page():
    """
    Hyper-Modern, Readable Privacy Policy & Terms page with premium SAAS design,
    enforcing Light Theme for high contrast and vibrancy.
    """
    # --- Color Palette (STRICTLY LIGHT MODE) ---
    
    # Modern Palette
    ACCENT_COLOR = '#ff6a00'        # Orange Accent
    ACCENT_GRADIENT = 'linear-gradient(45deg, #ff6a00, #ee0979)' 
    BG_COLOR = '#ffffff'            # Pure White Background
    TEXT_COLOR_MAIN = '#1a202c'     # Dark Slate for high contrast
    TEXT_COLOR_LIGHT = '#6b7280'    # Muted Gray
    CARD_BG = '#f8f8f8'             # Slightly off-white for card contrast
    
    # Glassmorphism/Neumorphism Shadows
    SHADOW_CARD = '0 8px 30px rgba(0, 0, 0, 0.05)' 
    SHADOW_HOVER = '0 18px 50px rgba(0, 0, 0, 0.15)'

    # Transition setting for smoothness
    TRANSITION_SMOOTH = 'all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)'

    # --- CSS for animations & styles ---
    st.markdown(f"""
    <style>
    /* Global Styles */
    .stApp {{
        background-color: {BG_COLOR};
        font-family: 'Poppins', 'Inter', sans-serif;
        color: {TEXT_COLOR_MAIN};
    }}

    /* Hero Banner - Focus on Gradient and Clarity */
    .hero {{
        background: {ACCENT_GRADIENT};
        border-radius: 20px;
        text-align: center;
        padding: 80px 40px;
        color: white;
        margin-bottom: 50px;
        box-shadow: 0 15px 50px rgba(255, 106, 0, 0.3);
        animation: fadeIn 1.5s ease-out;
    }}
    .hero h1 {{
        font-size: 3.8em;
        margin-bottom: 10px;
        font-weight: 900;
        letter-spacing: -1px;
        color: white; /* Title is pure white for maximum pop on gradient */
        text-shadow: 0 3px 6px rgba(0,0,0,0.15);
        animation: slideInDown 1s ease-out;
    }}
    .hero p {{
        font-size: 1.4em;
        color: rgba(255, 255, 255, 0.9);
        animation: fadeIn 2s ease-out;
        max-width: 800px;
        margin: auto;
    }}

    /* Main Content Headers */
    h2 {{
        font-size: 2.5em;
        font-weight: 800;
        color: {TEXT_COLOR_MAIN};
        padding-bottom: 10px;
        border-bottom: 3px solid {ACCENT_COLOR};
        margin-top: 40px;
        margin-bottom: 30px;
        display: inline-block;
    }}
    
    /* Policy Card with subtle contrast and strong hover */
    .policy-card {{
        background-color: {CARD_BG};
        border-radius: 15px;
        padding: 30px;
        margin-bottom: 25px;
        box-shadow: {SHADOW_CARD};
        transition: {TRANSITION_SMOOTH};
        height: 100%; /* Important for grid alignment */
        border-left: 5px solid {ACCENT_COLOR}; /* Accent Strip */
    }}
    .policy-card:hover {{
        transform: translateY(-8px);
        box-shadow: {SHADOW_HOVER};
        border-left: 5px solid #ee0979; /* Color change on hover */
    }}
    .policy-card h3 {{
        font-size: 1.6em;
        margin-bottom: 15px;
        font-weight: 700;
        color: {ACCENT_COLOR};
        display: flex;
        align-items: center;
    }}
    .policy-card li, .policy-card p {{
        color: {TEXT_COLOR_LIGHT};
        line-height: 1.7;
        font-size: 1.05em;
        margin-bottom: 10px;
    }}
    .policy-card strong {{
        color: {TEXT_COLOR_MAIN};
        font-weight: 600;
    }}

    /* Grid Layout */
    .row {{
        display: flex;
        flex-wrap: wrap;
        gap: 30px; /* Increased gap for visual breathing room */
        margin-bottom: 40px;
    }}
    .column {{
        flex: 1;
        min-width: 45%; /* Adjusted minimum width for better two-column layout */
    }}

    /* Footer Note */
    .footer-note {{
        text-align: center;
        padding: 30px 0;
        margin-top: 50px;
        border-top: 1px solid #eeeeee;
    }}

    /* Back to Top Button */
    .back-to-top {{
        position: fixed;
        bottom: 30px;
        right: 30px;
        background: {ACCENT_GRADIENT};
        color: white;
        border-radius: 50%;
        width: 60px;
        height: 60px;
        text-align: center;
        line-height: 60px;
        font-size: 28px;
        cursor: pointer;
        box-shadow: 0 12px 30px rgba(255, 106, 0, 0.4);
        transition: all 0.3s ease;
        z-index: 999;
    }}
    .back-to-top:hover {{
        transform: scale(1.1);
        box-shadow: 0 18px 40px rgba(255, 106, 0, 0.6);
    }}

    /* Animations */
    @keyframes fadeIn {{ 0% {{opacity:0;}} 100% {{opacity:1;}} }}
    @keyframes slideInDown {{ 0% {{transform: translateY(-80px); opacity:0;}} 100% {{transform: translateY(0); opacity:1;}} }}

    </style>

    <script>
    function scrollToTop() {{
        window.scrollTo({{top: 0, behavior: 'smooth'}});
    }}
    </script>
    """, unsafe_allow_html=True)

    # --- Page Content ---

    # Hero Banner
    current_year = datetime.now().year
    st.markdown(f"""
    <div class="hero">
        <h1>⚖️ Security, Transparency, Trust.</h1>
        <p>Your privacy is our priority. This document details how ScreenerPro collects, uses, and protects your data. Last updated: September 20, {current_year}.</p>
    </div>
    """, unsafe_allow_html=True)

    ## 🔒 Privacy Policy
    st.markdown("<h2>Privacy Policy</h2>", unsafe_allow_html=True)
    
    st.markdown('<div class="row">', unsafe_allow_html=True)

    # Privacy Policy Cards (Organized for better flow)
    privacy_data = [
        ("🔍 Information We Collect", "We only collect data necessary to provide and improve our service.", [
            "**Account Info:** Email, organization name, and billing details upon sign-up.",
            "**Uploaded Content:** Resumes and job descriptions submitted for analysis.",
            "**Usage Data:** Non-identifying operational metrics, page views, and error logs."
        ]),
        ("🛡️ Data Protection Principles", "We adhere to strict data principles to ensure your trust.", [
            "**No Third-Party Sharing:** We never sell or share your content with advertisers.",
            "**Content Isolation:** Uploaded documents are processed in isolated environments.",
            "**No Training:** Your content is explicitly **not** used for training our AI models."
        ]),
        ("✅ How We Use Your Data", "Data is used solely to deliver service value.", [
            "To provide **AI screening reports**, visualization dashboards, and comparisons.",
            "To **maintain and improve** platform security and feature performance.",
            "To communicate **critical updates**, billing, and technical support."
        ]),
        ("🔐 Security & Retention", "Your data security is managed with industry best practices.", [
            "**Encryption:** All data is transmitted via **end-to-end HTTPS** encryption.",
            "**Access Control:** Data access is strictly limited to authorized personnel.",
            "**Retention:** Uploaded content is retained only as long as your active subscription requires or per your explicit deletion request."
        ])
    ]

    for title, description, items in privacy_data:
        st.markdown(f'<div class="column"><div class="policy-card"><h3>{title}</h3><p><strong>{description}</strong></p><ul>', unsafe_allow_html=True)
        for item in items:
            st.markdown(f"<li>{item}</li>", unsafe_allow_html=True)
        st.markdown('</ul></div></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")

    ## 📜 Terms of Service
    st.markdown("<h2>Terms of Service</h2>", unsafe_allow_html=True)
    
    st.markdown('<div class="row">', unsafe_allow_html=True)

    # Terms of Service Cards
    terms_data = [
        ("1. Account Responsibility", "You are responsible for all activity under your account.", [
            "Ensure all account registration information is **accurate and current**.",
            "Maintain the confidentiality of your login credentials.",
            "Notify us immediately of any unauthorized use."
        ]),
        ("2. Permitted Usage", "The platform must be used lawfully and ethically.", [
            "Use ScreenerPro strictly for **legitimate talent acquisition** purposes.",
            "Do not upload malicious software or content.",
            "Do not attempt to disrupt or reverse-engineer the service."
        ]),
        ("3. Intellectual Property (IP)", "Respect for content and platform IP is mandatory.", [
            "You retain all ownership rights to your **uploaded content**.",
            "ScreenerPro retains all IP rights to its AI models, code, and visuals.",
            "You may not copy, modify, or redistribute any part of the platform without consent."
        ]),
        ("4. Limitation of Liability", "Understand the scope and limitation of our service.", [
            "ScreenerPro provides tools, but **hiring decisions remain solely yours**.",
            "We are not liable for any indirect, incidental, or consequential damages.",
            "Our total liability is limited to the amount paid by you for the service in the last twelve months."
        ])
    ]

    for title, description, items in terms_data:
        st.markdown(f'<div class="column"><div class="policy-card"><h3>{title}</h3><p><strong>{description}</strong></p><ul>', unsafe_allow_html=True)
        for item in items:
            st.markdown(f"<li>{item}</li>", unsafe_allow_html=True)
        st.markdown('</ul></div></div>', unsafe_allow_html=True)
        
    st.markdown('</div>', unsafe_allow_html=True)

    # Footer Note
    st.markdown('<div class="footer-note">', unsafe_allow_html=True)
    st.markdown(f"<p style='color:{TEXT_COLOR_MAIN}; font-size:16px;'>✅ By utilizing ScreenerPro, you formally acknowledge and agree to the terms outlined in both our **Privacy Policy** and **Terms of Service**.</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Back to top button
    st.markdown('<div class="back-to-top" onclick="scrollToTop()">⬆️</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    st.set_page_config(page_title="ScreenerPro - Privacy & Terms", layout="wide", page_icon="⚖️")
    privacy_policy_page()
