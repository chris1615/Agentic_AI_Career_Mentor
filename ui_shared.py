"""
ui_shared.py
------------
Shared UI helpers for the AI Career Mentor Streamlit pages.
"""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.abspath(__file__))

STYLE_BLOCK = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.hero-header {
    background: linear-gradient(135deg, #101827, #1e1b4b, #1f2937);
    border-radius: 20px;
    padding: 3rem 2rem;
    text-align: center;
    margin-bottom: 2rem;
}
.hero-header h1 {
    font-family: 'Syne', sans-serif;
    font-size: 2.8rem;
    color: #fff;
    margin: 0;
}
.hero-header p { color: #c4b5fd; margin-top: 0.6rem; }
.section-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: #c4b5fd;
    border-left: 4px solid #7c3aed;
    padding-left: 0.75rem;
    margin: 1rem 0;
}
.role-card {
    background: linear-gradient(135deg, #1e1b4b, #312e81);
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    border: 1px solid #4c1d95;
}
.role-card-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #fff;
}
.role-card-domain {
    font-size: 0.78rem;
    background: #7c3aed;
    color: #fff;
    border-radius: 20px;
    padding: 2px 10px;
    display: inline-block;
    margin-bottom: 0.5rem;
}
.score-bar-bg {
    background: #312e81;
    border-radius: 10px;
    height: 8px;
    margin-top: 6px;
}
.score-bar-fill {
    background: linear-gradient(90deg, #7c3aed, #a78bfa);
    border-radius: 10px;
    height: 8px;
}
.chip-green, .chip-red {
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.8rem;
    display: inline-block;
    margin: 2px;
}
.chip-green { background: #064e3b; color: #6ee7b7; }
.chip-red { background: #450a0a; color: #fca5a5; }
.phase-card, .job-card, .chat-card, .resume-card {
    background: #111827;
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.8rem;
    border: 1px solid #312e81;
}
.phase-title {
    font-family: 'Syne', sans-serif;
    color: #a78bfa;
    font-size: 0.95rem;
    margin-bottom: 0.45rem;
}
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #7c3aed, transparent);
    margin: 1.5rem 0;
}
.agent-step {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0;
    color: #c4b5fd;
}
.agent-dot {
    width: 8px;
    height: 8px;
    background: #7c3aed;
    border-radius: 50%;
}
.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
}
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #1e1b4b !important;
    color: #f1f5f9 !important;
    border: 1px solid #4c1d95 !important;
    border-radius: 10px !important;
}
footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
</style>
"""


def load_env() -> None:
    env_path = os.path.join(ROOT, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path, override=False)


def apply_style() -> None:
    st.markdown(STYLE_BLOCK, unsafe_allow_html=True)


def render_hero() -> None:
    st.markdown(
        """
<div class="hero-header">
    <h1>AI Career Mentor</h1>
    <p>Dynamic career intelligence with live roles, explainable matching, and career chat</p>
</div>
""",
        unsafe_allow_html=True,
    )


def render_agent_pipeline() -> None:
    st.markdown("### Agent Pipeline")
    for index, (name, desc) in enumerate([
        ("Skill Analyzer", "Understands semantic skill meaning"),
        ("Career Recommender", "Ranks static and dynamic roles"),
        ("Learning Planner", "Builds role-specific roadmaps"),
        ("Interview Coach", "Generates targeted practice questions"),
        ("Career Chatbot", "Answers role and skill questions"),
    ], 1):
        st.markdown(
            f"<div class='agent-step'><div class='agent-dot'></div><div><strong>Agent {index} - {name}</strong><br><small style='color:#94a3b8'>{desc}</small></div></div>",
            unsafe_allow_html=True,
        )


def render_compact_workflow() -> None:
    st.markdown("### Workflow")
    for index, (title, desc) in enumerate([
        ("Upload Resume", "Parse skills and experience"),
        ("Analyze Gaps", "Compare skills to target roles"),
        ("Ask Career Chat", "Get next-step guidance"),
    ], 1):
        st.markdown(
            f"<div class='agent-step'><div class='agent-dot'></div><div><strong>Step {index} - {title}</strong><br><small style='color:#94a3b8'>{desc}</small></div></div>",
            unsafe_allow_html=True,
        )


def render_role_card(role: dict, rank_label: str) -> None:
    confidence = role.get("confidence_score", role.get("match_score", 0))
    eligibility = role.get("eligibility_status", "Unknown")
    eligibility_color = "#6ee7b7" if eligibility == "Eligible" else "#fca5a5" if eligibility == "Not Eligible" else "#fcd34d"
    st.markdown(
        f"""
<div class='role-card'>
    <div class='role-card-domain'>{role.get('domain', 'Unknown')}</div>
    <div class='role-card-title'>{rank_label} {role.get('role', 'Unknown Role')}</div>
    <p style='color:#94a3b8;font-size:0.9rem'>{role.get('description', '')}</p>
    <div style='font-size:0.83rem;color:{eligibility_color};margin-bottom:8px'><strong>Eligibility:</strong> {eligibility}</div>
    <div style='display:flex;justify-content:space-between;font-size:0.82rem;color:#a78bfa;margin-bottom:4px'>
        <span>Confidence Score</span><span><strong>{confidence}%</strong></span>
    </div>
    <div class='score-bar-bg'><div class='score-bar-fill' style='width:{min(confidence, 100)}%'></div></div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_learning_plan(phases: list[dict]) -> None:
    if not phases:
        st.caption("No structured roadmap available.")
        return

    for phase in phases:
        topics_html = "".join(f"<li>{topic}</li>" for topic in phase.get("topics", []))
        st.markdown(
            f"""
<div class='phase-card'>
    <div class='phase-title'>{phase.get('phase', '')}</div>
    <ul style='color:#cbd5e1;padding-left:1.2rem;margin:0'>{topics_html}</ul>
    <p style='color:#94a3b8;margin-top:0.7rem'><em>{phase.get('resource_hint', '')}</em></p>
</div>
""",
            unsafe_allow_html=True,
        )
        for step in phase.get("steps", []):
            st.markdown(f"- {step}")
