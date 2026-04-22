"""
2_Resume_Analyzer_Chatbot.py
----------------------------
Streamlit page for resume analysis and career chatbot.
"""

from __future__ import annotations

import os
import sys

import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.chatbot_agent import ask_career_chatbot
from backend.data_loader import load_roles
from ui_shared import apply_style, load_env, render_compact_workflow, render_hero


st.set_page_config(
    page_title="AI Career Mentor - Resume & Chat",
    page_icon="AI",
    layout="wide",
    initial_sidebar_state="collapsed",
)

load_env()
apply_style()
render_hero()

with st.sidebar:
    render_compact_workflow()

st.markdown("<div class='section-title'>Resume Analyzer</div>", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Upload resume (PDF, DOCX, TXT)",
    type=["pdf", "docx", "txt"],
    key="resume_uploader",
)

if uploaded_file is not None:
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_key:
        st.error("Add `GROQ_API_KEY` to your .env file to use the resume analyzer.")
    else:
        try:
            from backend.resume_analyzer import analyze_resume_with_groq, extract_resume_text

            file_bytes = uploaded_file.read()
            file_type = uploaded_file.name.split(".")[-1].lower()
            with st.spinner("Analyzing resume..."):
                resume_text = extract_resume_text(file_bytes, file_type)
                resume_result = analyze_resume_with_groq(resume_text, groq_key)

            st.markdown("<div class='resume-card'>", unsafe_allow_html=True)
            st.markdown("**Extracted Skills**")
            skills_list = resume_result.get("skills", [])
            if skills_list:
                for skill in skills_list:
                    st.markdown(f"<span class='chip-green'>{skill}</span>", unsafe_allow_html=True)
            else:
                st.caption("No skills detected.")

            st.markdown("**Education**")
            st.write(resume_result.get("education", "Not detected"))

            st.markdown("**Years of Experience**")
            st.write(f"{resume_result.get('experience_years', 0)} years")

            st.markdown("**Suggested Missing Skills**")
            for skill in resume_result.get("missing_skills_suggestion", []):
                st.markdown(f"<span class='chip-red'>{skill}</span>", unsafe_allow_html=True)

            st.markdown("**Professional Summary**")
            st.info(resume_result.get("summary", "No summary generated."))
            st.markdown("</div>", unsafe_allow_html=True)

            if skills_list and st.button("Import Resume Skills", key="import_resume_skills", use_container_width=True):
                st.session_state["_skills"] = ", ".join(skills_list)
                st.success("Skills imported. Open the Your Profile page to run analysis.")
        except Exception as exc:
            st.error(f"Resume analysis failed: {exc}")

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

st.markdown("<div class='section-title'>Career Chatbot</div>", unsafe_allow_html=True)
chat_question = st.text_area(
    "Ask a career question",
    placeholder="What skills do I need to become a game developer?",
    height=140,
)

if st.button("Ask Career Chatbot", use_container_width=True):
    roles = load_roles()
    latest_result = st.session_state.get("latest_workflow_result", {})
    user_profile = {
        "skills": latest_result.get("user_skills", []),
        "education": latest_result.get("education", ""),
        "interests": latest_result.get("interests", ""),
        "career_goal": latest_result.get("career_goal", ""),
    }
    answer = ask_career_chatbot(
        chat_question,
        roles,
        user_profile=user_profile,
        recommended_roles=latest_result.get("recommended_roles", []),
    )
    st.session_state["career_chat_answer"] = answer

if st.session_state.get("career_chat_answer"):
    st.markdown(
        f"<div class='chat-card' style='color:#e5e7eb'>{st.session_state['career_chat_answer']}</div>",
        unsafe_allow_html=True,
    )

st.markdown(
    "<div style='text-align:center;color:#4b5563;font-size:0.8rem;margin-top:3rem'>AI Career Mentor - Dynamic Career Intelligence Platform</div>",
    unsafe_allow_html=True,
)
