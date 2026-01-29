import streamlit as st
import requests
from datetime import datetime

FORMSPREE_ENDPOINT = "https://formspree.io/f/mwpqevno"

def partner_with_us_page():
    # --- Color Palette & Global Variables ---
    dark_mode = False # Enforcing SAAS Light Mode
    
    # Ethereal Light Mode Palette
    ACCENT_COLOR = '#8e2de2'        # Deep Purple/Violet
    ACCENT_HOVER = '#4a00e0'        
    BG_COLOR_LIGHT = '#f0f5ff'      # Very light blue-white background
    BG_GRADIENT = 'linear-gradient(180deg, #f0f5ff 0%, #ffffff 100%)'
    TEXT_COLOR_MAIN = '#1a202c'     # Dark Slate for high contrast
    TEXT_COLOR_LIGHT = '#6b7280'    # Muted Gray
    CARD_BG = 'rgba(255, 255, 255, 0.8)' # Semi-transparent white for glass effect
    
    # *** FIX: Defining BG_SECTION_CONTRAST to prevent NameError ***
    BG_SECTION_CONTRAST = '#ffffff' 
    
    # Glassmorphism/Neumorphism Shadows
    SHADOW_FROST = '0 10px 40px rgba(142, 45, 226, 0.1), 0 5px 15px rgba(0, 0, 0, 0.05)'
    SHADOW_HOVER = '0 20px 50px rgba(142, 45, 226, 0.25), 0 8px 20px rgba(0, 0, 0, 0.1)'
    
    # Transition setting for smoothness
    TRANSITION_SMOOTH = 'all 0.5s cubic-bezier(0.23, 1, 0.32, 1)'

    # --- CSS for animations & styles ---
    st.markdown(f"""
    <style>
    /* Global Styles & Font */
    .stApp {{
        background: {BG_GRADIENT};
        font-family: 'Poppins', 'Inter', sans-serif;
        color: {TEXT_COLOR_MAIN};
        transition: background-color 0.5s;
    }}
    
    /* Ensure all elements transition smoothly */
    *, *:before, *:after {{
        box-sizing: border-box;
        transition: {TRANSITION_SMOOTH};
    }}

    /* Hero Section - Maximum Visual Impact */
    .hero {{
        background: linear-gradient(45deg, #a779e9, {ACCENT_COLOR}); /* Purple to Lighter Purple */
        border-radius: 30px;
        padding: 100px 50px;
        text-align: center;
        color: white;
        box-shadow: 0 25px 50px rgba(142, 45, 226, 0.4);
        animation: fadeInScale 2s ease-out;
        position: relative; /* For the subtle background effect */
        overflow: hidden;
    }}
    /* Subtle Hero background pattern */
    .hero::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image: radial-gradient(circle at 10% 20%, rgba(255, 255, 255, 0.1) 0%, rgba(0, 0, 0, 0) 60%);
        z-index: 1;
    }}
    .hero * {{
        position: relative;
        z-index: 2;
    }}
    .hero h1 {{
        font-size: 5em;
        margin-bottom: 15px;
        font-weight: 900;
        letter-spacing: -3px;
        text-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        animation: slideInDown 1.5s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    }}
    .hero p {{
        font-size: 1.6em;
        max-width: 1000px;
        margin: auto;
        line-height: 1.6;
        opacity: 0.9;
    }}

    /* Section Headers - Clean and central */
    .section-header {{
        text-align: center;
        margin-top: 60px;
        margin-bottom: 60px;
    }}
    .section-header h2 {{
        font-size: 3.2em;
        font-weight: 800;
        color: {TEXT_COLOR_MAIN};
        position: relative;
    }}
    .section-header h2::first-letter {{
        color: {ACCENT_COLOR};
    }}

    /* Cards - The Glassmorphism Effect */
    .card {{
        background: {CARD_BG};
        backdrop-filter: blur(10px); /* The Glass effect */
        -webkit-backdrop-filter: blur(10px);
        border-radius: 25px;
        padding: 40px;
        box-shadow: {SHADOW_FROST};
        height: 100%;
        border: 1px solid rgba(255, 255, 255, 0.4); /* Light border for definition */
        transition: {TRANSITION_SMOOTH};
        animation: fadeInUp 1.5s ease-out;
        opacity: 0; /* Base state for staggered animation */
    }}
    .card:hover {{
        transform: translateY(-15px) scale(1.03);
        box-shadow: {SHADOW_HOVER};
        border-color: {ACCENT_COLOR}; 
    }}
    .card h3 {{
        color: {ACCENT_COLOR};
        margin-top: 10px;
        font-size: 1.8em;
        font-weight: 700;
    }}
    .card .icon {{
        font-size: 2.5em;
        color: {ACCENT_COLOR};
        display: inline-block;
        margin-bottom: 10px;
        transition: transform 0.5s;
    }}
    .card:hover .icon {{
        transform: rotate(10deg) scale(1.1);
    }}
    .card p {{
        color: {TEXT_COLOR_LIGHT};
        line-height: 1.7;
    }}

    /* Form card - Contained and contrasting */
    .form-card {{
        background: {BG_SECTION_CONTRAST}; /* Use pure white for form contrast */
        border-radius: 30px;
        padding: 70px;
        box-shadow: 0 15px 45px rgba(0, 0, 0, 0.15);
        border: 1px solid #e0e0e0;
        animation: fadeIn 2s ease-out;
    }}

    /* Buttons - Gradient CTA with 3D press effect */
    .stButton>button {{
        background: linear-gradient(90deg, #a779e9, {ACCENT_COLOR});
        color: white;
        border-radius: 40px; /* More pronounced pill shape */
        padding: 1em 3em;
        font-size: 1.25em;
        font-weight: 700;
        border: none;
        box-shadow: 0 10px 30px rgba(142, 45, 226, 0.4); 
        transition: {TRANSITION_SMOOTH};
    }}
    .stButton>button:hover {{
        transform: translateY(-5px) scale(1.02);
        box-shadow: 0 15px 40px rgba(142, 45, 226, 0.6);
    }}
    .stButton>button:active {{ /* 3D press effect */
        transform: translateY(2px);
        box-shadow: 0 5px 15px rgba(142, 45, 226, 0.4);
    }}

    /* Input Fields - Clean and professional */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {{
        border-radius: 12px;
        border: 1px solid #d1d5db;
        padding: 14px;
        font-size: 1em;
    }}
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {{
        border-color: {ACCENT_COLOR};
        box-shadow: 0 0 0 4px rgba(142, 45, 226, 0.15);
        outline: none;
    }}

    /* Animations (Retained and slightly faster) */
    @keyframes fadeIn {{ 0% {{opacity: 0;}} 100% {{opacity: 1;}} }}
    @keyframes fadeInScale {{ 0% {{opacity: 0; transform: scale(0.97);}} 100% {{opacity: 1; transform: scale(1);}} }}
    @keyframes slideInDown {{ 0% {{transform: translateY(-120px); opacity:0;}} 100% {{transform: translateY(0); opacity:1;}} }}
    @keyframes fadeInUp {{ 0% {{transform: translateY(60px); opacity:0;}} 100% {{transform: translateY(0); opacity:1;}} }}
    </style>
    """, unsafe_allow_html=True)

    # --- Hero Section ---
    st.markdown("""
    <div class="hero">
        <h1>🚀 Elevate Your Enterprise. Partner with ScreenerPro.</h1>
        <p>Become a strategic ally in the AI revolution. Integrate our proprietary talent intelligence engine to drive unmatched efficiency and growth.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- Partnership Avenues Section ---
    st.markdown('<div class="section-header"><h2>Our Partnership Ecosystem</h2></div>', unsafe_allow_html=True)
    cols = st.columns(3)
    cards = [
        ("Integration Partner", "Embed ScreenerPro's validated AI endpoints directly into your Applicant Tracking System (ATS) or HR platform.", "🔌"),
        ("Value-Added Reseller (VAR)", "License and distribute our specialized screening modules to your corporate clients under a mutual agreement.", "🤝"),
        ("Academic & Certification Body", "Collaborate on research and offer exclusive, AI-backed certifications to enhance student and alumni marketability.", "🎓")
    ]
    
    # Apply staggered animation delays
    for i, (title, desc, icon) in enumerate(cards):
        with cols[i]:
            animation_delay = f"{0.3 + i * 0.15}s"
            st.markdown(f"""
            <div class="card" style="animation-delay: {animation_delay}; animation-fill-mode: forwards;">
                <span class="icon">{icon}</span>
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- Key Benefits Section ---
    st.markdown('<div class="section-header"><h2>The Advantage of Alliance</h2></div>', unsafe_allow_html=True)
    benefit_cols = st.columns(2)
    benefits = [
        ("Massive Time Savings", "Cut down initial screening cycles by 90% using pre-vetted, objective AI models.", "⏱️"),
        ("Premium Differentiation", "Offer a cutting-edge, tech-forward solution that stands out in the crowded HR market.", "✨"),
        ("Co-Marketing & Leads", "Benefit from joint press releases, case studies, and partner-exclusive lead-sharing programs.", "📢"),
        ("Unmatched Scalability", "Our cloud-native infrastructure ensures seamless performance, regardless of your volume or growth rate.", "☁️")
    ]
    
    # Another set of cards with staggered animation
    for i, (title, desc, icon) in enumerate(benefits):
        col = benefit_cols[i % 2]
        with col:
            animation_delay = f"{0.2 + i * 0.1}s"
            st.markdown(f"""
            <div class="card" style="margin-bottom: 30px; animation-delay: {animation_delay}; animation-fill-mode: forwards;">
                <span class="icon">{icon}</span>
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- Form Section (The ultimate CTA) ---
    st.markdown('<div class="section-header"><h2>Let’s Build Something Great</h2></div>', unsafe_allow_html=True)
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    with st.form("partner_form", clear_on_submit=True):
        st.markdown(f"<p style='color:{TEXT_COLOR_LIGHT}; font-size:1.1em; text-align:center; margin-bottom: 30px;'>Submit your details below to schedule a 1:1 consultation with our executive partnership team.</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            organization_name = st.text_input("Organization Name *", help="Required field")
            contact_person = st.text_input("Contact Person Name *", help="Required field")
        with col2:
            contact_email = st.text_input("Work Email *", help="Required field")
            partner_type = st.selectbox("I represent a:", ["Technology Provider", "HR/Recruitment Agency", "Educational Institution", "Venture Capital/Investor", "Other"], index=0)

        partnership_interest = st.text_area("What is your primary partnership goal? (Be specific!) *", height=150, help="Required field")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Center the submit button
        col_empty_left, col_btn, col_empty_right = st.columns([1, 1, 1])
        with col_btn:
             submitted = st.form_submit_button("Launch Partnership Process")
        
        if submitted:
            data = {
                "Partner Type": partner_type,
                "Organization Name": organization_name,
                "Contact Person": contact_person,
                "Contact Email": contact_email,
                "Partnership Interest": partnership_interest,
                "Submission Timestamp": datetime.now().isoformat()
            }
            if not organization_name or not contact_email or not contact_person or not partnership_interest:
                st.error("❌ Please ensure all fields marked with * are completed.")
            else:
                try:
                    response = requests.post(FORMSPREE_ENDPOINT, data=data)
                    if response.status_code == 200:
                        st.balloons()
                        st.success("✨ **Success!** Your inquiry has been received. Expect a personalized response within 48 hours.")
                    else:
                        st.error(f"⚠️ Submission failed. Please try again. Status: {response.status_code}")
                except Exception as e:
                    st.error(f"🔴 An unexpected connection error occurred: {e}")
                    
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{TEXT_COLOR_LIGHT}; text-align:center; font-size:0.9em;'>ScreenerPro is a product of FLIP & CLIP. &copy; {datetime.now().year} All rights reserved. <br>Innovating the future of talent, together.</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    # Ensure you are not running this as a sub-module if this is intended as a full app/page file
    st.set_page_config(page_title="ScreenerPro - Partner With Us", layout="wide", page_icon="📣")
    partner_with_us_page()
