"""
1_Your_Profile.py
-----------------
Streamlit page for the user profile and career analysis flow.
"""

from __future__ import annotations

import os
import sys
import time

import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.workflow import run_workflow
from ui_shared import apply_style, load_env, render_agent_pipeline, render_hero, render_learning_plan, render_role_card


st.set_page_config(
    page_title="AI Career Mentor - Career Snapshot",
    page_icon="AI",
    layout="wide",
    initial_sidebar_state="collapsed",
)

load_env()
apply_style()
render_hero()

with st.sidebar:
    render_agent_pipeline()

st.markdown("<div class='section-title'>Career Snapshot</div>", unsafe_allow_html=True)
skills_input = st.text_input(
    "Your Current Skills *",
    placeholder="e.g. Python, Blender, Video Editing, SQL",
)
interests_input = st.text_input(
    "Your Interests",
    placeholder="e.g. Drawing, VFX, Animation, Game Design",
)
col_a, col_b = st.columns(2)
with col_a:
    education_input = st.text_input("Education", placeholder="e.g. BCA, B.Tech, MBBS")
with col_b:
    goal_input = st.text_input("Career Goal", placeholder="e.g. Become a Game Developer")

analyze_btn = st.button("Analyze My Career", use_container_width=True)

st.markdown("<div class='section-title'>Try an Example</div>", unsafe_allow_html=True)
example_cols = st.columns(4)
examples = [
    ("Creative Media", ("Blender, Video Editing, VFX", "Drawing, Video Editing, VFX", "BCA", "VFX Artist")),
    ("Game Dev", ("C++, Unity, Debugging", "Gaming, Animation, Interactive Design", "BSc", "Game Developer")),
    ("Cybersecurity", ("Linux, Python", "Cybersecurity, Networks", "BCA", "Cybersecurity Analyst")),
    ("Data", ("Python, Excel, SQL", "Analytics, Mathematics", "BCA", "Data Scientist")),
]
for index, (label, values) in enumerate(examples):
    if example_cols[index].button(label, key=f"ex_{label}"):
        st.session_state["_skills"] = values[0]
        st.session_state["_interests"] = values[1]
        st.session_state["_education"] = values[2]
        st.session_state["_goal"] = values[3]
        st.rerun()

if "_skills" in st.session_state:
    skills_input = st.session_state.pop("_skills")
    interests_input = st.session_state.pop("_interests")
    education_input = st.session_state.pop("_education")
    goal_input = st.session_state.pop("_goal")
    analyze_btn = True

if analyze_btn:
    if not skills_input.strip():
        st.error("Please enter at least one skill to get started.")
        st.stop()

    user_input = {
        "skills": skills_input,
        "interests": interests_input,
        "education": education_input,
        "career_goal": goal_input,
    }

    progress = st.progress(0)
    status_text = st.empty()
    for pct, msg in [
        (20, "Skill Analyzer is understanding your profile"),
        (45, "Career Recommender is ranking static and live roles"),
        (70, "Learning Planner is building role-specific roadmaps"),
        (100, "Interview Coach is preparing the best-fit role questions"),
    ]:
        status_text.markdown(f"<p style='color:#a78bfa'>{msg}</p>", unsafe_allow_html=True)
        progress.progress(pct)
        time.sleep(0.35)

    result = run_workflow(user_input)
    st.session_state["latest_workflow_result"] = result
    progress.empty()
    status_text.empty()

    if result.get("status") == "error":
        st.error(result["message"])
        st.stop()

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    tabs = st.tabs(["Career Matches", "Learning Paths", "Live Jobs", "Interview Prep"])

    with tabs[0]:
        st.markdown("<div class='section-title'>Top Career Recommendations</div>", unsafe_allow_html=True)
        for index, role in enumerate(result.get("recommended_roles", []), 1):
            render_role_card(role, f"{index}.")
            with st.expander(f"{role.get('role', 'Role')} - full explanation"):
                st.markdown("**Matched Skills**")
                if role.get("matched_skills"):
                    for skill in role["matched_skills"]:
                        st.markdown(f"<span class='chip-green'>{skill}</span>", unsafe_allow_html=True)
                else:
                    st.caption("No strong matched skills yet.")

                st.markdown("**Missing Skills**")
                if role.get("missing_skills"):
                    for skill in role["missing_skills"]:
                        st.markdown(f"<span class='chip-red'>{skill}</span>", unsafe_allow_html=True)
                else:
                    st.success("No major missing skills detected.")

                st.markdown("**Reasoning Explanation**")
                for line in role.get("reasoning_explanation", []):
                    st.markdown(f"- {line}")

                st.markdown("**Eligibility Reasoning**")
                for line in role.get("eligibility_reasoning", []):
                    st.markdown(f"- {line}")

                breakdown = role.get("score_breakdown", {})
                st.markdown("**Score Breakdown**")
                st.markdown(f"- Skills Match: {breakdown.get('skill_score', 0)}%")
                st.markdown(f"- Semantic Similarity: {breakdown.get('semantic_score', 0)}%")
                st.markdown(f"- Random Forest Probability: {breakdown.get('random_forest_score', 0)}%")
                st.markdown(f"- Existing Weighted Score: {breakdown.get('existing_weighted_score', 0)}%")
                st.markdown(f"- Interest Match: {breakdown.get('interest_score', 0)}%")
                st.markdown(f"- Domain Match: {breakdown.get('domain_score', 0)}%")
                st.markdown(f"- Career Goal: {breakdown.get('goal_score', 0)}%")
                st.markdown(f"- Eligibility: {breakdown.get('eligibility_score', 0)}%")

        model_metrics = result.get("ml_model_metrics", {})
        if model_metrics:
            st.markdown("<div class='section-title'>Hybrid AI Signals</div>", unsafe_allow_html=True)
            st.markdown(f"- Semantic Model: `{result.get('hybrid_components', {}).get('semantic_matching', 'enabled')}`")
            st.markdown(f"- Random Forest Status: `{model_metrics.get('status', 'unknown')}`")
            if model_metrics.get("accuracy") is not None:
                st.markdown(f"- Validation Accuracy: `{round(model_metrics.get('accuracy', 0.0) * 100, 2)}%`")
            if model_metrics.get("sample_count"):
                st.markdown(f"- Training Samples: `{model_metrics.get('sample_count')}`")

        if result.get("rejected_roles"):
            st.markdown("<div class='section-title'>Rejected or Low-Fit Roles</div>", unsafe_allow_html=True)
            for role in result["rejected_roles"]:
                with st.expander(f"{role.get('role', 'Role')} - why it ranked lower"):
                    for line in role.get("reasoning_explanation", []):
                        st.markdown(f"- {line}")

    with tabs[1]:
        st.markdown("<div class='section-title'>Role-Specific Learning Paths</div>", unsafe_allow_html=True)
        for role in result.get("recommended_roles", []):
            with st.expander(f"{role.get('role', 'Role')} - learning plan"):
                st.markdown(f"**Confidence Score:** {role.get('confidence_score', role.get('match_score', 0))}%")
                st.markdown(f"**Portfolio Required:** {'Yes' if role.get('portfolio_required') else 'No'}")
                render_learning_plan(role.get("learning_plan", []))

    with tabs[2]:
        st.markdown("<div class='section-title'>Live Job Listings</div>", unsafe_allow_html=True)
        job_listings = result.get("live_job_listings", [])
        if not job_listings:
            st.info("No live job listings were fetched. Add Adzuna or RapidAPI credentials to your .env file to enable live market results.")
        else:
            recommended_names = [role.get("role", "") for role in result.get("recommended_roles", [])]
            if recommended_names:
                st.caption(f"Live jobs matched for: {', '.join(name for name in recommended_names if name)}")
            for job in job_listings:
                job_title = job.get("role", "Role")
                company = job.get("company", "Unknown company")
                location = job.get("location", "Unknown location")
                source = job.get("source", "Live API")
                url = job.get("job_url", "")
                st.markdown(
                    f"""
<div class='job-card'>
    <strong style='color:#fff'>{job_title}</strong><br>
    <span style='color:#c4b5fd'>{company} • {location} • {source}</span>
    <p style='color:#d1d5db'>{job.get('description', '')}</p>
</div>
""",
                    unsafe_allow_html=True,
                )
                if url:
                    st.markdown(f"[Open job listing]({url})")

    with tabs[3]:
        iq = result.get("interview_questions", {})
        target_role = iq.get("role", "your target role")
        st.markdown(f"<div class='section-title'>Interview Prep - {target_role}</div>", unsafe_allow_html=True)
        col_tech, col_beh = st.columns(2)
        with col_tech:
            st.markdown("#### Technical Questions")
            for index, question in enumerate(iq.get("technical", []), 1):
                st.markdown(f"<div class='phase-card'><strong>Q{index}.</strong> {question}</div>", unsafe_allow_html=True)
        with col_beh:
            st.markdown("#### Behavioral Questions")
            for index, question in enumerate(iq.get("behavioral", []), 1):
                st.markdown(f"<div class='phase-card'><strong>Q{index}.</strong> {question}</div>", unsafe_allow_html=True)

st.markdown(
    "<div style='text-align:center;color:#4b5563;font-size:0.8rem;margin-top:3rem'>AI Career Mentor - Dynamic Career Intelligence Platform</div>",
    unsafe_allow_html=True,
)
