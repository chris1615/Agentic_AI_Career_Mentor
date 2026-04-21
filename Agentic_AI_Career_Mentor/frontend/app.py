"""
app.py
------
Streamlit frontend for the Agentic AI Career Mentor System.
Run with: streamlit run frontend/app.py
"""

import os
import sys
import time

import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from workflow import run_workflow


st.set_page_config(
    page_title="AI Career Mentor",
    page_icon="AI",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.hero-header {
    background: linear-gradient(135deg, #0f172a, #1e1b4b, #0f172a);
    border-radius: 20px;
    padding: 3rem 2rem;
    text-align: center;
    margin-bottom: 2rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.hero-header h1 {
    font-family: 'Syne', sans-serif;
    font-size: 2.8rem;
    font-weight: 800;
    color: #ffffff;
    margin: 0;
}
.hero-header p {
    color: #c4b5fd;
    font-size: 1.05rem;
    margin-top: 0.5rem;
}
.section-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.35rem;
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
    font-size: 1.15rem;
    font-weight: 700;
    color: #ffffff;
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
.chip-green {
    background: #064e3b;
    color: #6ee7b7;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.8rem;
    display: inline-block;
    margin: 2px;
}
.chip-red {
    background: #450a0a;
    color: #fca5a5;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.8rem;
    display: inline-block;
    margin: 2px;
}
.week-card {
    background: #1e293b;
    border-left: 4px solid #7c3aed;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
}
.week-number {
    font-family: 'Syne', sans-serif;
    font-size: 0.85rem;
    font-weight: 700;
    color: #a78bfa;
    text-transform: uppercase;
}
.week-skill {
    font-size: 1rem;
    font-weight: 600;
    color: #f8fafc;
    margin: 2px 0 8px 0;
}
.week-hint {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-top: 6px;
    font-style: italic;
}
.q-technical {
    background: #1a1035;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    border-left: 3px solid #7c3aed;
    color: #e2e8f0;
    font-size: 0.95rem;
}
.q-behavioral {
    background: #0d2137;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    border-left: 3px solid #0ea5e9;
    color: #e2e8f0;
    font-size: 0.95rem;
}
.agent-step {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0;
    color: #a78bfa;
    font-size: 0.9rem;
}
.agent-dot {
    width: 8px;
    height: 8px;
    background: #7c3aed;
    border-radius: 50%;
    flex-shrink: 0;
}
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #7c3aed, transparent);
    margin: 1.5rem 0;
}
.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.6rem 2rem !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    width: 100%;
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
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero-header">
    <h1>AI Career Mentor</h1>
    <p>Explainable multi-agent career intelligence with role fit, eligibility, and learning pathways</p>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Agent Pipeline")
    agents = [
        ("1", "Skill Agent", "Measures semantic skill fit"),
        ("2", "Career Agent", "Ranks roles with weighted explainable scoring"),
        ("3", "Learning Agent", "Builds a roadmap from missing skills"),
        ("4", "Interview Agent", "Generates targeted practice questions"),
    ]
    for num, name, desc in agents:
        st.markdown(
            f"<div class='agent-step'><div class='agent-dot'></div><div><strong>Agent {num} - {name}</strong><br><small style='color:#94a3b8'>{desc}</small></div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### Domains Covered")
    for domain in ["Technology", "Healthcare", "Finance", "Law", "Arts", "Engineering", "Business", "Education", "Marketing"]:
        st.markdown(f"- {domain}")

    st.markdown("---")
    openai_key = st.text_input(
        "OpenAI API Key (optional)",
        type="password",
        placeholder="sk-...",
        help="Optional. The ranking engine works locally; this key is only used by optional OpenAI-backed features.",
    )
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key


col_form, col_examples = st.columns([2, 1])

with col_form:
    st.markdown("<div class='section-title'>Your Profile</div>", unsafe_allow_html=True)
    skills_input = st.text_input(
        "Your Current Skills *",
        placeholder="e.g. Python, Communication, Excel, SQL",
        help="Separate multiple skills with commas.",
    )
    interests_input = st.text_input(
        "Your Interests",
        placeholder="e.g. Artificial Intelligence, Biology, Design",
    )
    col_a, col_b = st.columns(2)
    with col_a:
        education_input = st.text_input(
            "Education",
            placeholder="e.g. BCA, B.Tech Computer Science, MBBS",
        )
    with col_b:
        goal_input = st.text_input(
            "Career Goal",
            placeholder="e.g. Become a Data Scientist",
        )
    analyze_btn = st.button("Analyze My Career", use_container_width=True)

with col_examples:
    st.markdown("<div class='section-title'>Try an Example</div>", unsafe_allow_html=True)
    examples = {
        "Tech / AI": ("Python, Statistics, Excel", "Machine Learning, AI", "BCA", "Data Scientist"),
        "Healthcare": ("Biology, Communication", "Medicine, Patient Care", "BSc Biology", "Doctor"),
        "Business": ("Communication, Excel, Presentation", "Strategy, Finance", "BBA", "Product Manager"),
        "Design": ("Figma, Creativity, Typography", "UX, Visual Design", "BDes", "UX/UI Designer"),
    }
    for label, (skills, interests, education, goal) in examples.items():
        if st.button(label, key=f"example_{label}"):
            st.session_state["_skills"] = skills
            st.session_state["_interests"] = interests
            st.session_state["_education"] = education
            st.session_state["_goal"] = goal
            st.rerun()

if "_skills" in st.session_state:
    skills_input = st.session_state.pop("_skills")
    interests_input = st.session_state.pop("_interests", "")
    education_input = st.session_state.pop("_education", "")
    goal_input = st.session_state.pop("_goal", "")
    analyze_btn = True


def render_role_card(role: dict, rank_label: str) -> None:
    score = role.get("match_score", 0)
    eligibility = role.get("eligibility_status", "Unknown")
    if eligibility == "Eligible":
        eligibility_color = "#6ee7b7"
    elif eligibility == "Not Eligible":
        eligibility_color = "#fca5a5"
    else:
        eligibility_color = "#fcd34d"

    st.markdown(
        f"""
<div class='role-card'>
    <div class='role-card-domain'>{role.get('domain', 'Unknown')}</div>
    <div class='role-card-title'>{rank_label} {role.get('role', 'Unknown Role')}</div>
    <p style='color:#94a3b8;font-size:0.88rem;margin:4px 0 8px 0'>{role.get('description', '')}</p>
    <div style='font-size:0.83rem;color:{eligibility_color};margin-bottom:8px'><strong>Eligibility:</strong> {eligibility}</div>
    <div style='display:flex;justify-content:space-between;font-size:0.82rem;color:#a78bfa;margin-bottom:4px'>
        <span>Match Score</span><span><strong>{score}%</strong></span>
    </div>
    <div class='score-bar-bg'><div class='score-bar-fill' style='width:{min(score, 100)}%'></div></div>
</div>
""",
        unsafe_allow_html=True,
    )


if analyze_btn:
    if not skills_input.strip():
        st.error("Please enter at least one skill to get started.")
        st.stop()

    payload = {
        "skills": skills_input,
        "interests": interests_input,
        "education": education_input,
        "career_goal": goal_input,
    }

    progress_bar = st.progress(0)
    status_text = st.empty()
    steps = [
        (25, "Agent 1: Analyzing semantic skill fit"),
        (50, "Agent 2: Ranking roles with explainable scoring"),
        (75, "Agent 3: Building learning pathways"),
        (100, "Agent 4: Preparing interview guidance"),
    ]
    for pct, msg in steps:
        status_text.markdown(f"<p style='color:#a78bfa'>{msg}</p>", unsafe_allow_html=True)
        progress_bar.progress(pct)
        time.sleep(0.35)

    result = run_workflow(payload)
    progress_bar.empty()
    status_text.empty()

    if result.get("status") == "error":
        st.error(result["message"])
        st.stop()

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown(
        "<h2 style='font-family:Syne;color:#e2e8f0;text-align:center;'>Your Career Analysis</h2>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["Career Matches", "Skill Gap", "Learning Plan", "Interview Prep"])

    with tab1:
        st.markdown("<div class='section-title'>Top Career Recommendations</div>", unsafe_allow_html=True)
        rank_labels = ["1.", "2.", "3."]
        for index, role in enumerate(result.get("recommended_roles", [])):
            render_role_card(role, rank_labels[index] if index < len(rank_labels) else f"{index + 1}.")
            with st.expander(f"Role analysis - {role.get('role', 'Role')}"):
                col_left, col_right = st.columns(2)
                with col_left:
                    st.markdown("**Matched Skills**")
                    if role.get("matched_skills"):
                        chips = "".join(f"<span class='chip-green'>{skill}</span>" for skill in role["matched_skills"])
                        st.markdown(chips, unsafe_allow_html=True)
                    else:
                        st.caption("No strong matches yet.")
                with col_right:
                    st.markdown("**Missing Skills**")
                    if role.get("missing_skills"):
                        chips = "".join(f"<span class='chip-red'>{skill}</span>" for skill in role["missing_skills"])
                        st.markdown(chips, unsafe_allow_html=True)
                    else:
                        st.caption("No major skill gaps detected.")

                breakdown = role.get("score_breakdown", {})
                if breakdown:
                    st.markdown("**Score Breakdown**")
                    st.markdown(f"- Skill Score: {breakdown.get('skill_score', 0)}%")
                    st.markdown(f"- Domain Score: {breakdown.get('domain_score', 0)}%")
                    st.markdown(f"- Goal Score: {breakdown.get('goal_score', 0)}%")
                    st.markdown(f"- Education Score: {breakdown.get('education_score', 0)}%")

                if role.get("reasoning_explanation"):
                    st.markdown("**Reasoning Explanation**")
                    for line in role["reasoning_explanation"]:
                        st.markdown(f"- {line}")

                if role.get("suggested_learning_path"):
                    st.markdown("**Suggested Learning Path**")
                    for step_index, step in enumerate(role["suggested_learning_path"], 1):
                        st.markdown(f"{step_index}. {step}")

        if result.get("rejected_roles"):
            st.markdown("<div class='section-title'>Rejected or Low-Fit Roles</div>", unsafe_allow_html=True)
            for role in result["rejected_roles"]:
                with st.expander(f"{role.get('role', 'Role')} - {role.get('match_score', 0)}% match - {role.get('eligibility_status', 'Unknown')}"):
                    st.markdown(f"**Eligibility Status:** {role.get('eligibility_status', 'Unknown')}")
                    if role.get("reasoning_explanation"):
                        for line in role["reasoning_explanation"]:
                            st.markdown(f"- {line}")
                    if role.get("suggested_learning_path"):
                        st.markdown("**Suggested Path**")
                        for step_index, step in enumerate(role["suggested_learning_path"], 1):
                            st.markdown(f"{step_index}. {step}")

    with tab2:
        st.markdown("<div class='section-title'>Skill Gap Analysis</div>", unsafe_allow_html=True)
        col_have, col_need = st.columns(2)
        with col_have:
            st.markdown("#### Skills You Have")
            for skill in result.get("user_skills", []):
                st.markdown(f"<span class='chip-green'>{skill}</span>", unsafe_allow_html=True)
        with col_need:
            st.markdown("#### Skills to Acquire")
            missing_skills = result.get("missing_skills", [])
            if missing_skills:
                for skill in missing_skills:
                    st.markdown(f"<span class='chip-red'>{skill}</span>", unsafe_allow_html=True)
            else:
                st.success("You already cover the main skills for your top matches.")

        top_role = result.get("recommended_roles", [{}])[0]
        if top_role.get("reasoning_explanation"):
            st.markdown("#### Why the top role ranked highest")
            for line in top_role["reasoning_explanation"]:
                st.markdown(f"- {line}")

    with tab3:
        st.markdown("<div class='section-title'>Weekly Learning Roadmap</div>", unsafe_allow_html=True)
        learning_plan = result.get("learning_plan", [])
        if not learning_plan:
            st.success("No learning plan needed for the selected top matches.")
        else:
            for week in learning_plan:
                steps_html = "".join(f"<li style='margin:4px 0;color:#cbd5e1'>{step}</li>" for step in week.get("steps", []))
                st.markdown(
                    f"""
<div class='week-card'>
    <div class='week-number'>Week {week.get('week', '')}</div>
    <div class='week-skill'>{week.get('skill', '')}</div>
    <ul style='margin:0;padding-left:1.2rem'>{steps_html}</ul>
    <div class='week-hint'>{week.get('resource_hint', '')}</div>
</div>
""",
                    unsafe_allow_html=True,
                )

        top_role = result.get("recommended_roles", [{}])[0]
        if top_role.get("suggested_learning_path"):
            st.markdown("#### Suggested Career Path")
            for step_index, step in enumerate(top_role["suggested_learning_path"], 1):
                st.markdown(f"{step_index}. {step}")

    with tab4:
        iq = result.get("interview_questions", {})
        target_role = iq.get("role", "your target role")
        st.markdown(
            f"<div class='section-title'>Interview Prep - {target_role}</div>",
            unsafe_allow_html=True,
        )
        col_tech, col_beh = st.columns(2)
        with col_tech:
            st.markdown("<h4 style='color:#a78bfa'>Technical Questions</h4>", unsafe_allow_html=True)
            for index, question in enumerate(iq.get("technical", []), 1):
                st.markdown(f"<div class='q-technical'><strong>Q{index}.</strong> {question}</div>", unsafe_allow_html=True)
        with col_beh:
            st.markdown("<h4 style='color:#38bdf8'>Behavioral Questions</h4>", unsafe_allow_html=True)
            for index, question in enumerate(iq.get("behavioral", []), 1):
                st.markdown(f"<div class='q-behavioral'><strong>Q{index}.</strong> {question}</div>", unsafe_allow_html=True)

st.markdown(
    "<div style='text-align:center;color:#374151;font-size:0.8rem;margin-top:3rem'>Agentic AI Career Mentor - Built with Streamlit</div>",
    unsafe_allow_html=True,
)
