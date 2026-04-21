"""
app.py
------
Streamlit frontend for the AI Career Mentor System.
"""

import os
import sys
import time

import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from chatbot_agent import ask_career_chatbot
from data_loader import load_roles
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
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero-header">
    <h1>AI Career Mentor</h1>
    <p>Dynamic career intelligence with live roles, explainable matching, and career chat</p>
</div>
""",
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


with st.sidebar:
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

    st.markdown("---")
    openai_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key

    groq_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    if groq_key:
        os.environ["GROQ_API_KEY"] = groq_key

    openrouter_key = st.text_input("OpenRouter API Key", type="password", placeholder="sk-or-...")
    if openrouter_key:
        os.environ["OPENROUTER_API_KEY"] = openrouter_key

    adzuna_id = st.text_input("Adzuna App ID", type="password")
    if adzuna_id:
        os.environ["ADZUNA_APP_ID"] = adzuna_id

    adzuna_key = st.text_input("Adzuna App Key", type="password")
    if adzuna_key:
        os.environ["ADZUNA_APP_KEY"] = adzuna_key

    rapidapi_key = st.text_input("RapidAPI Key", type="password")
    if rapidapi_key:
        os.environ["RAPIDAPI_KEY"] = rapidapi_key

    rapidapi_host = st.text_input("RapidAPI Jobs Host", placeholder="example.p.rapidapi.com")
    if rapidapi_host:
        os.environ["RAPIDAPI_JOBS_HOST"] = rapidapi_host


col_profile, col_tools = st.columns([2, 1])

with col_profile:
    st.markdown("<div class='section-title'>Your Profile</div>", unsafe_allow_html=True)
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

with col_tools:
    tool_tab1, tool_tab2 = st.tabs(["Resume Analyzer", "Career Chatbot"])

    with tool_tab1:
        st.markdown("<div class='section-title'>Resume Analyzer</div>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload resume (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
            key="resume_uploader",
        )
        if uploaded_file is not None:
            if not groq_key:
                st.error("Enter a Groq API key in the sidebar to use the resume analyzer.")
            else:
                try:
                    from resume_analyzer import analyze_resume_with_groq, extract_resume_text

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
                        st.rerun()
                except Exception as exc:
                    st.error(f"Resume analysis failed: {exc}")

    with tool_tab2:
        st.markdown("<div class='section-title'>Career Chatbot</div>", unsafe_allow_html=True)
        chat_question = st.text_area(
            "Ask a career question",
            placeholder="What skills do I need to become a game developer?",
            height=140,
        )
        if st.button("Ask Career Chatbot", use_container_width=True):
            roles = load_roles()
            answer = ask_career_chatbot(chat_question, roles)
            st.session_state["career_chat_answer"] = answer

        if st.session_state.get("career_chat_answer"):
            st.markdown(
                f"<div class='chat-card' style='color:#e5e7eb'>{st.session_state['career_chat_answer']}</div>",
                unsafe_allow_html=True,
            )

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
                st.markdown(f"- Interest Match: {breakdown.get('interest_score', 0)}%")
                st.markdown(f"- Domain Match: {breakdown.get('domain_score', 0)}%")
                st.markdown(f"- Career Goal: {breakdown.get('goal_score', 0)}%")
                st.markdown(f"- Eligibility: {breakdown.get('eligibility_score', 0)}%")

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
            st.info("No live job listings were fetched. Add Adzuna or RapidAPI credentials in the sidebar to enable live market results.")
        else:
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
