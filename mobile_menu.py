import streamlit as st

def render_mobile_menu(authenticated: bool):
    """
    Render a mobile-specific top menu.

    Parameters:
    - authenticated (bool): whether the user is authenticated or not
    """
    st.markdown("""
    <style>
    @media only screen and (max-width: 768px) {
        .mobile-toggle {
            display: block;
            background-color: #00cec9;
            color: white;
            border: none;
            padding: 10px 16px;
            font-size: 20px;
            border-radius: 6px;
            cursor: pointer;
            margin-bottom: 1rem;
        }
        .mobile-menu {
            background: #fff;
            border: 1px solid #ccc;
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 0px 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        .mobile-menu a {
            display: block;
            padding: 8px 0;
            color: #333;
            text-decoration: none;
            font-weight: 500;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    if "show_mobile_menu" not in st.session_state:
        st.session_state["show_mobile_menu"] = False

    if st.button("☰ Menu", key="toggle_menu", help="Open Navigation", use_container_width=True):
        st.session_state["show_mobile_menu"] = not st.session_state["show_mobile_menu"]

    if st.session_state["show_mobile_menu"]:
        st.markdown("<div class='mobile-menu'>", unsafe_allow_html=True)

        if authenticated:
            st.markdown("""
            <a href="?tab=🏠 Dashboard Home">🏠 Dashboard Home</a>
            <a href="?tab=📁 Manage JDs">📁 Manage JDs</a>
            <a href="?tab=📊 Screening Analytics">📊 Analytics</a>
            <a href="?tab=📈 Advanced Tools">📈 Advanced Tools</a>
            <a href="?tab=🤝 Collaboration Hub">🤝 Collaboration</a>
            <a href="?tab=🧑‍💼 Employee Management">🧑‍💼 Employee Management</a>
            <a href="?tab=🔍 Search Resumes">🔍 Search Resumes</a>
            <a href="?tab=📩 Email Candidates">📩 Email Candidates</a>
            <a href="?tab=📄 Candidate Notes">📄 Candidate Notes</a>
            <a href="?tab=📃 Certificate">📃 Certificate</a>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <a href="?tab=🏠 Public Home">🏠 Home</a>
            <a href="?tab=📝 Public Resume Form">📝 Resume Form</a>
            <a href="?tab=📬 View Submissions">📬 View Submissions</a>
            <a href="?tab=📢 Feedback">📢 Feedback</a>
            <a href="?tab=🛡️ Privacy Policy">🛡️ Privacy Policy</a>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
