"""
app.py
------
Streamlit landing page for the AI Career Mentor System.
"""

import streamlit as st

from ui_shared import apply_style, load_env, render_hero


st.set_page_config(
    page_title="AI Career Mentor",
    page_icon="AI",
    layout="wide",
    initial_sidebar_state="collapsed",
)

load_env()
apply_style()
render_hero()

st.markdown(
    """
<div class='section-title'>Start Here</div>
<p style='color:#cbd5e1'>Pick a path: build your career snapshot or analyze a resume and chat with the mentor.</p>
""",
    unsafe_allow_html=True,
)

col_left, col_right = st.columns(2)
with col_left:
    st.markdown(
        """
<div class='phase-card'>
    <div class='phase-title'>Career Snapshot</div>
    <p style='color:#cbd5e1;margin:0'>Enter your skills, interests, education, and goal to get role matches, learning paths, live jobs, and interview prep.</p>
</div>
""",
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_Career_Snapshot.py", label="Open Career Snapshot", icon="🧭")

with col_right:
    st.markdown(
        """
<div class='phase-card'>
    <div class='phase-title'>Resume Analyzer & Chatbot</div>
    <p style='color:#cbd5e1;margin:0'>Upload a resume to extract skills, then ask targeted career questions with context.</p>
</div>
""",
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_Resume_Analyzer_Chatbot.py", label="Open Resume Tools", icon="🧠")

st.markdown(
    """
<div class='section-title'>API Keys</div>
<p style='color:#cbd5e1'>This app reads keys from the .env file in the project root. Add values there to enable live jobs and AI features.</p>
""",
    unsafe_allow_html=True,
)

st.markdown(
    "<div style='text-align:center;color:#4b5563;font-size:0.8rem;margin-top:3rem'>AI Career Mentor - Dynamic Career Intelligence Platform</div>",
    unsafe_allow_html=True,
)
