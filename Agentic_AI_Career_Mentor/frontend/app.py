"""
app.py
------
Streamlit frontend for the Agentic AI Career Mentor System.
Run with:  streamlit run frontend/app.py
"""

import sys
import os

# ── path setup ─────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

import streamlit as st
from workflow import run_workflow

# ── page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Career Mentor",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── custom CSS ─────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* ---- hero header ---- */
.hero-header {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
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
    letter-spacing: -1px;
    margin: 0;
}
.hero-header p {
    color: #a78bfa;
    font-size: 1.1rem;
    margin-top: 0.5rem;
    font-weight: 300;
}

/* ---- input card ---- */
.input-card {
    background: #1e1b4b;
    border-radius: 16px;
    padding: 1.5rem;
    border: 1px solid #312e81;
}

/* ---- section headings ---- */
.section-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: #c4b5fd;
    border-left: 4px solid #7c3aed;
    padding-left: 0.75rem;
    margin-bottom: 1rem;
}

/* ---- role cards ---- */
.role-card {
    background: linear-gradient(135deg, #1e1b4b, #312e81);
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    border: 1px solid #4c1d95;
    transition: transform .2s;
}
.role-card:hover { transform: translateY(-2px); }
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

/* ---- skill chips ---- */
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

/* ---- week cards ---- */
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
    letter-spacing: 1px;
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

/* ---- interview questions ---- */
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

/* ---- agent progress steps ---- */
.agent-step {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0;
    color: #a78bfa;
    font-size: 0.9rem;
}
.agent-dot {
    width: 8px; height: 8px;
    background: #7c3aed;
    border-radius: 50%;
    flex-shrink: 0;
}

/* ---- resume analyzer button & container ---- */
.resume-analyzer-btn {
    background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.6rem 1.5rem !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    width: 100%;
    transition: opacity .2s !important;
}
.resume-analyzer-btn:hover { opacity: 0.88; }

.resume-container {
    background: #1e1b4b;
    border-radius: 16px;
    padding: 1.5rem;
    margin-top: 1rem;
    border: 1px solid #312e81;
}

/* ---- misc ---- */
.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.6rem 2rem !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    width: 100%;
    transition: opacity .2s !important;
}
.stButton > button:hover { opacity: 0.88 !important; }

.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #1e1b4b !important;
    color: #f1f5f9 !important;
    border: 1px solid #4c1d95 !important;
    border-radius: 10px !important;
}

label { color: #c4b5fd !important; font-weight: 500; }

.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #7c3aed, transparent);
    margin: 1.5rem 0;
}

footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

# ── hero ─────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="hero-header">
    <h1>🧭 AI Career Mentor</h1>
    <p>Multi-agent system · Skill Gap Analysis · Personalized Roadmap · Interview Prep</p>
</div>
""",
    unsafe_allow_html=True,
)

# ── sidebar: agent pipeline info ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🤖 Agent Pipeline")
    agents = [
        ("1", "Skill Analyzer", "Compares your skills vs. role requirements"),
        ("2", "Career Advisor", "Recommends best-fit career paths"),
        ("3", "Learning Planner", "Builds your weekly roadmap"),
        ("4", "Interview Coach", "Generates interview questions"),
    ]
    for num, name, desc in agents:
        st.markdown(
            f"<div class='agent-step'><div class='agent-dot'></div><div>"
            f"<strong>Agent {num} — {name}</strong><br>"
            f"<small style='color:#64748b'>{desc}</small></div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### 🌐 Domains Covered")
    domains = ["Technology", "Business", "Marketing", "Design",
               "Healthcare", "Finance", "Education", "Creative"]
    for d in domains:
        st.markdown(f"• {d}")

    st.markdown("---")
    openai_key = st.text_input(
        "🔑 OpenAI API Key (optional)",
        type="password",
        placeholder="sk-...",
        help="If provided, uses GPT for richer plans & questions. Otherwise uses templates.",
    )
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key

    # Groq API key for resume analyzer (reused)
    st.markdown("---")
    groq_api_key = st.text_input(
        "🧠 Groq API Key (for Resume Analyzer)",
        type="password",
        placeholder="gsk_...",
        help="Free key from console.groq.com. Used to extract info from your resume."
    )
    if groq_api_key:
        os.environ["GROQ_API_KEY"] = groq_api_key


# ── main layout: two columns ─────────────────────────────────────────────────
col_form, col_resume = st.columns([2, 1])

# ── left column: user profile form ──────────────────────────────────────────
with col_form:
    st.markdown("<div class='section-title'>📝 Your Profile</div>", unsafe_allow_html=True)

    skills_input = st.text_input(
        "🛠️ Your Current Skills *",
        placeholder="e.g. Python, Communication, Excel, SQL",
        help="Separate multiple skills with commas.",
    )

    interests_input = st.text_input(
        "💡 Your Interests",
        placeholder="e.g. Artificial Intelligence, Data, Design",
        help="What topics excite you?",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        education_input = st.text_input(
            "🎓 Education (optional)",
            placeholder="e.g. B.Tech Computer Science",
        )
    with col_b:
        goal_input = st.text_input(
            "🎯 Career Goal (optional)",
            placeholder="e.g. Become a Data Scientist",
        )

    analyze_btn = st.button("🚀  Analyze My Career", use_container_width=True)

# ── right column: Resume Analyzer button (seamless) ─────────────────────────
with col_resume:
    st.markdown("<div class='section-title'>📄 Resume Analyzer</div>", unsafe_allow_html=True)
    if st.button("📂 Upload & Analyze Resume", key="resume_btn", use_container_width=True):
        st.session_state.show_resume_upload = True
    else:
        if "show_resume_upload" not in st.session_state:
            st.session_state.show_resume_upload = False

    if st.session_state.show_resume_upload:
        with st.container():
            st.markdown("<div class='resume-container'>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "Choose your resume (PDF, DOCX, or TXT)",
                type=["pdf", "docx", "txt"],
                key="resume_uploader"
            )
            if uploaded_file is not None:
                if not groq_api_key:
                    st.error("❌ Please enter your Groq API key in the sidebar first.")
                else:
                    file_bytes = uploaded_file.read()
                    file_type = uploaded_file.name.split(".")[-1].lower()
                    with st.spinner("🔍 Extracting text and analyzing with Groq AI..."):
                        try:
                            from resume_analyzer import extract_resume_text, analyze_resume_with_groq
                            resume_text = extract_resume_text(file_bytes, file_type)
                            if not resume_text:
                                st.error("Could not extract text from the file. Try a different file.")
                            else:
                                result = analyze_resume_with_groq(resume_text, groq_api_key)
                                st.success("✅ Analysis complete!")

                                # Display extracted info
                                st.markdown("**🛠️ Extracted Skills**")
                                skills_list = result.get("skills", [])
                                if skills_list:
                                    for s in skills_list:
                                        st.markdown(f"<span class='chip-green'>{s}</span>", unsafe_allow_html=True)
                                else:
                                    st.info("No skills detected.")

                                st.markdown("**🎓 Education**")
                                st.write(result.get("education", "Not detected"))

                                st.markdown("**📅 Years of Experience**")
                                st.write(f"{result.get('experience_years', 0)} years")

                                st.markdown("**🚀 Suggested Missing Skills**")
                                missing_sug = result.get("missing_skills_suggestion", [])
                                if missing_sug:
                                    for s in missing_sug:
                                        st.markdown(f"<span class='chip-red'>{s}</span>", unsafe_allow_html=True)
                                else:
                                    st.write("No suggestions.")

                                st.markdown("**📝 Professional Summary**")
                                st.info(result.get("summary", "No summary generated."))

                                # Import skills button
                                if skills_list and st.button("📋 Import these skills into your profile", key="import_skills"):
                                    existing = set(st.session_state.get("user_skills", []))
                                    new_skills = existing.union(set(skills_list))
                                    st.session_state.user_skills = list(new_skills)
                                    st.success(f"Added {len(skills_list)} skills! Refresh the page to see them in the skills input.")
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
            st.markdown("</div>", unsafe_allow_html=True)


# ── run workflow (if Analyze button clicked) ─────────────────────────────────
if analyze_btn:
    if not skills_input.strip():
        st.error("⚠️  Please enter at least one skill to get started.")
        st.stop()

    user_input = {
        "skills": skills_input,
        "interests": interests_input,
        "education": education_input if "education_input" in dir() else "",
        "career_goal": goal_input,
    }

    # Progress animation
    progress_bar = st.progress(0)
    status_text = st.empty()
    steps = [
        (25, "🔍 Agent 1: Analyzing your skill profile…"),
        (50, "🎯 Agent 2: Identifying best career matches…"),
        (75, "📚 Agent 3: Building your learning roadmap…"),
        (100, "💬 Agent 4: Generating interview questions…"),
    ]

    import time
    for pct, msg in steps:
        status_text.markdown(f"<p style='color:#a78bfa'>{msg}</p>", unsafe_allow_html=True)
        progress_bar.progress(pct)
        time.sleep(0.4)

    result = run_workflow(user_input)
    progress_bar.empty()
    status_text.empty()

    # ── error handling ─────────────────────────────────────────────────────
    if result.get("status") == "error":
        st.error(f"❌ {result['message']}")
        st.stop()

    # ─────────────────────────────────────────────────────────────────────
    # RESULTS
    # ─────────────────────────────────────────────────────────────────────
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown(
        "<h2 style='font-family:Syne;color:#e2e8f0;text-align:center;'>✨ Your Career Analysis</h2>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🏆 Career Matches", "🧩 Skill Gap", "📅 Learning Plan", "🎤 Interview Prep"]
    )

    # ─── TAB 1 — Career Matches ───────────────────────────────────────────
    with tab1:
        st.markdown("<div class='section-title'>Top Career Recommendations</div>", unsafe_allow_html=True)

        for i, role in enumerate(result["recommended_roles"]):
            rank_emoji = ["🥇", "🥈", "🥉"][i]
            score = role["match_score"]

            st.markdown(
                f"""
<div class='role-card'>
    <div class='role-card-domain'>{role['domain']}</div>
    <div class='role-card-title'>{rank_emoji} {role['role']}</div>
    <p style='color:#94a3b8;font-size:0.88rem;margin:4px 0 8px 0'>{role['description']}</p>
    <div style='display:flex;justify-content:space-between;font-size:0.82rem;color:#a78bfa;margin-bottom:4px'>
        <span>Match Score</span><span><strong>{score}%</strong></span>
    </div>
    <div class='score-bar-bg'><div class='score-bar-fill' style='width:{min(score,100)}%'></div></div>
</div>
""",
                unsafe_allow_html=True,
            )

            with st.expander(f"Skills detail — {role['role']}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**✅ You already have:**")
                    if role["matched_skills"]:
                        chips = "".join(f"<span class='chip-green'>{s}</span>" for s in role["matched_skills"])
                        st.markdown(chips, unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='color:#64748b'>None yet</span>", unsafe_allow_html=True)
                with c2:
                    st.markdown("**📌 Still needed:**")
                    if role["missing_skills"]:
                        chips = "".join(f"<span class='chip-red'>{s}</span>" for s in role["missing_skills"])
                        st.markdown(chips, unsafe_allow_html=True)
                    else:
                        st.markdown(
                            "<span style='color:#6ee7b7'>🎉 You have all required skills!</span>",
                            unsafe_allow_html=True,
                        )

    # ─── TAB 2 — Skill Gap ───────────────────────────────────────────────
    with tab2:
        st.markdown("<div class='section-title'>Skill Gap Analysis</div>", unsafe_allow_html=True)

        col_have, col_need = st.columns(2)

        with col_have:
            st.markdown("#### ✅ Skills You Have")
            user_skills = result.get("user_skills", [])
            if user_skills:
                for sk in user_skills:
                    st.markdown(f"<span class='chip-green'>{sk}</span>", unsafe_allow_html=True)
            else:
                st.info("No skills entered.")

        with col_need:
            st.markdown("#### 🚧 Skills to Acquire")
            missing = result.get("missing_skills", [])
            if missing:
                for sk in missing:
                    st.markdown(f"<span class='chip-red'>{sk}</span>", unsafe_allow_html=True)
            else:
                st.success("🎉 You have all required skills for your top matches!")

        st.markdown("<br>", unsafe_allow_html=True)

        if missing:
            st.markdown(
                f"<p style='color:#94a3b8;font-size:0.9rem'>You have "
                f"<strong style='color:#a78bfa'>{len(user_skills)}</strong> skills and need to learn "
                f"<strong style='color:#f87171'>{len(missing)}</strong> more to become a strong candidate.</p>",
                unsafe_allow_html=True,
            )

    # ─── TAB 3 — Learning Plan ───────────────────────────────────────────
    with tab3:
        st.markdown("<div class='section-title'>Weekly Learning Roadmap</div>", unsafe_allow_html=True)

        plan = result.get("learning_plan", [])
        if not plan:
            st.success("🎉 No learning plan needed — you already have all required skills!")
        else:
            st.markdown(
                f"<p style='color:#94a3b8;font-size:0.9rem'>Your personalised "
                f"<strong style='color:#a78bfa'>{len(plan)}-week roadmap</strong> to close your skill gaps:</p>",
                unsafe_allow_html=True,
            )

            for week in plan:
                steps_html = "".join(
                    f"<li style='margin:4px 0;color:#cbd5e1'>{step}</li>"
                    for step in week["steps"]
                )
                st.markdown(
                    f"""
<div class='week-card'>
    <div class='week-number'>Week {week['week']}</div>
    <div class='week-skill'>📖 {week['skill']}</div>
    <ul style='margin:0;padding-left:1.2rem'>{steps_html}</ul>
    <div class='week-hint'>💡 {week['resource_hint']}</div>
</div>
""",
                    unsafe_allow_html=True,
                )

    # ─── TAB 4 — Interview Prep ──────────────────────────────────────────
    with tab4:
        iq = result.get("interview_questions", {})
        target_role = iq.get("role", "your target role")

        st.markdown(
            f"<div class='section-title'>Interview Prep — {target_role}</div>",
            unsafe_allow_html=True,
        )

        col_tech, col_beh = st.columns(2)

        with col_tech:
            st.markdown(
                "<h4 style='color:#a78bfa'>🔧 Technical Questions</h4>",
                unsafe_allow_html=True,
            )
            for i, q in enumerate(iq.get("technical", []), 1):
                st.markdown(
                    f"<div class='q-technical'><strong>Q{i}.</strong> {q}</div>",
                    unsafe_allow_html=True,
                )

        with col_beh:
            st.markdown(
                "<h4 style='color:#38bdf8'>🤝 Behavioral Questions</h4>",
                unsafe_allow_html=True,
            )
            for i, q in enumerate(iq.get("behavioral", []), 1):
                st.markdown(
                    f"<div class='q-behavioral'><strong>Q{i}.</strong> {q}</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)
        st.info(
            "💡 Tip: Use the STAR method (Situation · Task · Action · Result) "
            "to structure your answers to behavioral questions."
        )

# ── footer ─────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center;color:#374151;font-size:0.8rem;margin-top:3rem'>"
    "Agentic AI Career Mentor · Built with Streamlit · Multi-Agent Architecture"
    "</div>",
    unsafe_allow_html=True,
)
