import streamlit as st
import sys
import os

# Add parent directory to path so we can import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from public_job_board import public_job_board_page

# Directly call the page logic
# The function handles st.set_page_config internally
if __name__ == "__main__":
    public_job_board_page()
