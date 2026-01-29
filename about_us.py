import streamlit as st

def about_us_page():
    # 1. Page Configuration
    st.set_page_config(page_title="ScreenerPro - Corporate Overview", layout="wide", page_icon="🏢")

    # 2. Professional Custom CSS with Two-Tone Background and Enhanced Animations
    st.markdown("""
    <style>
    /* Global Styling */
    .stApp {
        background-color: #f8f9fa; /* Soft Light Gray */
        color: #212529; /* Deep Charcoal Text */
    }

    /* Hero Section Background */
    .hero-container {
        padding: 80px 0;
        background-color: #0d1e2d; /* Primary Corporate Navy */
        margin-bottom: 40px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4); /* Stronger Shadow for Premium Feel */
    }

    /* Hero Header Style */
    .hero-header {
        font-size: 68px; /* Slightly larger */
        font-weight: 900;
        letter-spacing: -2px;
        color: #ffffff; 
        margin-bottom: 10px;
    }
    .hero-tagline {
        font-size: 26px; /* Slightly larger */
        font-weight: 300;
        color: #c0dfe9; 
        margin-bottom: 40px;
    }

    /* Section Subheaders */
    .subheader {
        font-size: 42px; /* Slightly larger */
        font-weight: 700;
        margin-top: 40px;
        margin-bottom: 30px;
        text-align: center;
        color: #0d1e2d;
        border-bottom: 3px solid #e9ecef; 
        padding-bottom: 10px;
    }

    /* Card Section Containers - Two-Tone Effect */
    .section-light {
        background-color: #ffffff;
        padding: 30px 0 50px 0;
        margin: 20px 0;
    }
    .section-gray {
        background-color: #f8f9fa;
        padding: 30px 0 50px 0;
        margin: 20px 0;
    }

    /* Card Styling (Values & Offerings) */
    .pro-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 30px; 
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08); 
        border: 1px solid #dee2e6; 
        height: 100%; 
        transition: transform 0.3s ease, box-shadow 0.3s ease; 
    }
    .pro-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0,0,0,0.25); /* Stronger Hover Shadow */
        border-color: #008c99; 
    }
    .pro-card h3 {
        font-size: 24px; /* Slightly larger */
        margin-bottom: 10px;
        color: #0d1e2d; 
        font-weight: 700;
    }
    .pro-card p {
        font-size: 16px; 
        color: #6c757d; /* Softer text color for body copy */
    }
    
    /* Icon Styling - Accent Color with Lift */
    .icon-box {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 55px; /* Larger */
        height: 55px;
        border-radius: 50%;
        background-color: #008c99; /* Corporate Teal/Cyan Accent */
        color: white;
        font-size: 26px; 
        margin-bottom: 15px;
        font-style: normal;
        font-weight: bold;
        border: 3px solid #005f6b; /* Inner border for depth */
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.2); /* Shadow for lift */
    }
    
    /* Call to Action Button Style */
    .cta-button {
        background-color: #008c99; 
        color: white; 
        padding: 18px 45px; /* Larger padding */
        border: none; 
        border-radius: 10px; /* Softer corners */
        font-size: 22px; 
        font-weight: bold; 
        cursor: pointer;
        transition: background-color 0.3s ease, transform 0.3s ease; 
        box-shadow: 0 4px 15px rgba(0, 140, 153, 0.4);
    }
    .cta-button:hover {
        background-color: #006b74; 
        transform: scale(1.02); 
    }
    </style>
    """, unsafe_allow_html=True)

    # 3. Hero Section (Deep Navy Background)
    st.markdown("""
    <div class="hero-container">
        <div class="hero-header">ScreenerPro: Hiring Intelligence Redefined</div>
        <div class="hero-tagline">Leveraging advanced technology to ensure ethical, efficient, and data-driven candidate selection.</div>
    </div>
    """, unsafe_allow_html=True)

    # 4. Core Mission Statement (White Background)
    st.markdown('<div class="section-light">', unsafe_allow_html=True)
    st.markdown('<div class="subheader">Our Mission and Vision</div>', unsafe_allow_html=True)
    
    col_text, col_diagram = st.columns([2, 3])
    
    with col_text:
        st.markdown(f"""
        **ScreenerPro was founded to solve the core challenge in high-volume recruiting: achieving speed without sacrificing quality or fairness.** We believe that modern recruitment requires objective insights, freeing up human resources to focus on candidate engagement and final selection.

        Our vision is to provide a comprehensive, transparent platform that transforms raw applicant data into actionable hiring intelligence. We ensure our technology remains a supportive tool, empowering human judgment rather than replacing it.
        """)
    
    with col_diagram:
        # Strategic instructional diagram placement
        st.markdown("")
        
    st.markdown('</div>', unsafe_allow_html=True) 

    # 5. Core Values Section (Light Gray Background)
    st.markdown('<div class="section-gray">', unsafe_allow_html=True)
    st.markdown('<div class="subheader">Fundamental Values</div>', unsafe_allow_html=True)

    values = [
        ("Accountability", "Recruiters maintain complete authority. Our system provides objective data points for human decision-making."),
        ("Data Security", "Rigorous compliance and top-tier security ensure the confidential and ethical handling of all candidate information."),
        ("Usability", "Our platform is engineered for simplicity, providing sophisticated features accessible to all levels of technical proficiency."),
        ("Transparency", "Every score and insight is fully auditable, eliminating the 'black box' and building trust in the selection process."),
    ]

    cols = st.columns(4)
    icons = ["I", "II", "III", "IV"] # Roman Numerals for a formal, ordered look

    for idx, (title, desc) in enumerate(values):
        with cols[idx]:
            st.markdown(f"""
            <div class="pro-card">
                <div class="icon-box">{icons[idx]}</div>
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True) 

    # 6. Offerings Section (White Background)
    st.markdown('<div class="section-light">', unsafe_allow_html=True)
    st.markdown('<div class="subheader">Key Platform Offerings</div>', unsafe_allow_html=True)

    offerings = [
        ("Advanced Match Scoring", "Instantly analyze resumes against job criteria, delivering a precise match percentage based on contextual relevance."),
        ("Custom Screening Criteria", "Define objective thresholds for experience, required skills, and academic metrics for automated filtering."),
        ("In-Depth Analytics", "Access comprehensive reports detailing candidate skills, experience alignment, and comparative ranking visualizations."),
        ("Interactive Candidate Management", "Utilize a dynamic table interface for real-time sorting, filtering, and mass shortlisting of applicants."),
        ("Campaign Lifecycle Management", "Tools to create, launch, track, and manage the complete hiring lifecycle across multiple job campaigns."),
        ("Integrated Job Board", "Seamlessly post positions publicly and automatically feed applications directly into the screening pipeline."),
    ]

    # Display Offerings in 2 columns for larger, less cluttered cards
    num_cols = 2
    for i in range(0, len(offerings), num_cols):
        cols = st.columns(num_cols)
        for idx, col in enumerate(cols):
            if i + idx < len(offerings):
                title, desc = offerings[i + idx]
                with col:
                    st.markdown(f"""
                    <div class="pro-card">
                        <div class="icon-box">♦</div>
                        <h3>{title}</h3>
                        <p>{desc}</p>
                    </div>
                    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True) 

    # 7. Call-to-Action Footer (Professional and Animated)
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; padding: 50px; background-color: #e9ecef; border-radius: 8px; margin-top: 20px;">
            <h2 style="color: #0d1e2d; font-size: 36px; margin-bottom: 20px;">Schedule an Intelligence Briefing</h2>
            <p style="font-size: 20px; color: #495057;">Connect with our team to see how ScreenerPro can integrate seamlessly with your current recruitment infrastructure.</p>
            <br>
            <button class="cta-button">
            Request a Product Demonstration
            </button>
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    about_us_page()
