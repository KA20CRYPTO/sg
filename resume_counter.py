import streamlit as st
import os
# import json # Removed: not used in this file
# import time # Removed: not used in this file

# File to store the resume count
COUNT_FILE = "resume_count.txt"
INITIAL_COUNT = 231532 # Set the initial count here as requested

def get_current_count():
    """Reads the current resume count from a file."""
    if not os.path.exists(COUNT_FILE):
        # If file doesn't exist, create it with the specified initial count
        with open(COUNT_FILE, "w") as f:
            f.write(str(INITIAL_COUNT))
        return INITIAL_COUNT
    try:
        with open(COUNT_FILE, "r") as f:
            count_str = f.read().strip()
            return int(count_str)
    except ValueError:
        # Handle cases where file content is not a valid integer
        st.error(f"Error: '{COUNT_FILE}' contains invalid data. Resetting count to {INITIAL_COUNT}.")
        with open(COUNT_FILE, "w") as f:
            f.write(str(INITIAL_COUNT))
        return INITIAL_COUNT
    except Exception as e:
        st.error(f"Error reading count from '{COUNT_FILE}': {e}. Resetting count to {INITIAL_COUNT}.")
        with open(COUNT_FILE, "w") as f:
            f.write(str(INITIAL_COUNT))
        return INITIAL_COUNT

def increment_count(amount=1):
    """Increments the resume count and writes it back to the file."""
    current_count = get_current_count()
    new_count = current_count + amount
    try:
        with open(COUNT_FILE, "w") as f:
            f.write(str(new_count))
        return new_count
    except Exception as e:
        st.error(f"Error writing count to '{COUNT_FILE}': {e}. Count may not be persistent.")
        return current_count # Return old count if write fails

def live_resume_counter_page():
    st.title("📍 Live Resume Counter")
    st.markdown("A fun real-time metric showing the impact of ScreenerPro!")

    # Initialize session state for tracking resumes added from current session
    if 'resumes_added_to_global_count' not in st.session_state:
        st.session_state['resumes_added_to_global_count'] = 0

    # Get the number of resumes processed in the current session
    current_session_screened_count = 0
    if 'comprehensive_df' in st.session_state and not st.session_state['comprehensive_df'].empty:
        current_session_screened_count = len(st.session_state['comprehensive_df'])

    # Calculate how many *new* resumes from this session need to be added to the global count
    new_resumes_to_add = current_session_screened_count - st.session_state['resumes_added_to_global_count']

    # Increment the global count if there are new resumes from this session
    if new_resumes_to_add > 0:
        current_resumes_screened = increment_count(amount=new_resumes_to_add * 954) # Multiply by 954 here
        st.session_state['resumes_added_to_global_count'] += new_resumes_to_add
    else:
        # If no new resumes to add from this session, just fetch the current global count
        current_resumes_screened = get_current_count()

    # Access dark_mode from session state, defaulting to False if not set
    dark_mode = st.session_state.get('dark_mode_main', False)

    # Define colors based on dark mode for the counter box
    counter_bg_light = 'radial-gradient(circle at top left, #F0F2F6, #E0E5EC 80%)' # More subtle radial
    counter_bg_dark = 'radial-gradient(circle at top left, #2D2D2D, #1E1E1E 80%)' # More subtle radial
    counter_shadow_light = '0 12px 25px rgba(0, 0, 0, 0.2)'
    counter_shadow_dark = '0 12px 25px rgba(0, 0, 0, 0.6)'
    counter_border_light = '1px solid rgba(0, 0, 0, 0.15)'
    counter_border_dark = '1px solid rgba(255, 255, 255, 0.15)'

    counter_bg = counter_bg_dark if dark_mode else counter_bg_light
    counter_shadow = counter_shadow_dark if dark_mode else counter_shadow_light
    counter_border = counter_border_dark if dark_mode else counter_border_light

    counter_text_color = '#00cec9' # Keep teal for the icon
    counter_value_color = 'white' if dark_mode else '#333333'
    counter_caption_color = '#bbb' if dark_mode else '#666'

    # Inject custom CSS for the st.metric component
    st.markdown(
        f"""
        <style>
            @keyframes pulseEffect {{
                0% {{ transform: scale(1); opacity: 1; }}
                50% {{ transform: scale(1.03); opacity: 0.95; }}
                100% {{ transform: scale(1); opacity: 1; }}
            }}
            @keyframes fadeInScaleBounce {{
                0% {{ opacity: 0; transform: translateY(30px) scale(0.9); }}
                70% {{ opacity: 1; transform: translateY(-5px) scale(1.02); }}
                100% {{ opacity: 1; transform: translateY(0) scale(1); }}
            }}
            @keyframes iconFloat {{
                0% {{ transform: translateY(0) rotate(0deg); }}
                25% {{ transform: translateY(-3px) rotate(2deg); }}
                50% {{ transform: translateY(0) rotate(0deg); }}
                75% {{ transform: translateY(3px) rotate(-2deg); }}
                100% {{ transform: translateY(0) rotate(0deg); }}
            }}


            /* Targeting the stMetric component directly */
            .stMetric {{
                background: {counter_bg};
                padding: 40px 30px; /* Increased padding */
                border-radius: 30px; /* More rounded */
                text-align: center;
                margin: 50px auto; /* Increased margin */
                max-width: 500px; /* Slightly wider */
                box-shadow: {counter_shadow};
                border: {counter_border};
                animation: fadeInScaleBounce 1.2s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards; /* New animation */
                transition: all 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94); /* Smoother transition */
                overflow: hidden;
                position: relative;
            }}
            .stMetric:hover {{
                transform: translateY(-12px) scale(1.02); /* More pronounced hover effect */
                box-shadow: 0 20px 40px {'rgba(0, 0, 0, 0.55)' if dark_mode else 'rgba(0, 0, 0, 0.35)'}; /* Deeper shadow on hover */
                border-color: #00cec9; /* Teal border on hover */
            }}

            /* Styling the value within stMetric */
            .stMetric > div[data-testid="stMetricValue"] {{
                font-size: 5.5em; /* Even larger value font */
                color: {counter_value_color};
                font-weight: 900; /* Bolder */
                margin-top: 0;
                margin-bottom: 10px; /* More space below value */
                letter-spacing: -0.07em; /* Tighter spacing */
                text-shadow: 0 5px 15px rgba(0,0,0,0.4); /* More prominent shadow */
            }}

            /* Styling the label/caption within stMetric */
            .stMetric > div[data-testid="stMetricLabel"] {{
                font-size: 2em; /* Even larger caption font */
                color: {counter_caption_color};
                font-weight: 700; /* Bolder caption */
                opacity: 0.9; /* Slightly less opaque for subtle contrast */
                text-shadow: 0 1px 3px rgba(0,0,0,0.1); /* Subtle shadow for caption */
            }}

            /* Styling the icon within stMetric */
            .stMetric > div[data-testid="stMetricDelta"] {{ /* Streamlit uses stMetricDelta for the icon */
                font-size: 3.5em; /* Larger icon */
                color: {counter_text_color};
                margin-bottom: 15px; /* More space below icon */
                animation: pulseEffect 2s infinite ease-in-out, iconFloat 4s infinite ease-in-out 0.5s; /* Combined animations */
                display: block;
                width: fit-content;
                margin-left: auto;
                margin-right: auto;
            }}

            /* Responsive adjustments for smaller screens */
            @media (max-width: 600px) {{
                .stMetric {{
                    padding: 30px 20px;
                    margin: 30px auto;
                    border-radius: 20px;
                }}
                .stMetric > div[data-testid="stMetricDelta"] {{
                    font-size: 3em;
                    margin-bottom: 10px;
                }}
                .stMetric > div[data-testid="stMetricValue"] {{
                    font-size: 4.5em;
                }}
                .stMetric > div[data-testid="stMetricLabel"] {{
                    font-size: 1.6em;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True
    )

    # Use st.metric for the counter display
    # The label is the "resumes screened as of now!" part, value is the number, and delta is the icon
    st.metric(
        label="resumes screened as of now!",
        value=f"{current_resumes_screened:,}",
        delta="🚀", # Use the rocket emoji as the delta/icon
        delta_color="off" # Turn off default delta coloring as we control it with CSS
    )
